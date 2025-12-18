"""Performance tests for memory footprint (T097, SC-006, NFR-002)."""

import gc
import tempfile
from pathlib import Path

import pandas as pd
import pytest


def get_process_memory_mb():
    """Get current process memory usage in MB."""
    try:
        import psutil

        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        pytest.skip("psutil not installed - cannot measure memory")


@pytest.fixture()
def synthetic_csv_5m_rows(tmp_path: Path) -> Path:
    """Create synthetic CSV with 5M rows for memory testing."""
    csv_path = tmp_path / "synthetic_5m.csv"

    # Generate 5M rows
    timestamps = pd.date_range("2020-01-01", periods=5_000_000, freq="1min", tz="UTC")
    df = pd.DataFrame(
        {
            "timestamp": timestamps.strftime("%Y-%m-%d %H:%M:%S"),
            "open": 1.1000,
            "high": 1.1001,
            "low": 1.0999,
            "close": 1.1000,
            "volume": 1000,
        }
    )

    df.to_csv(csv_path, index=False)
    return csv_path


def test_columnar_memory_within_sc006_limit(
    synthetic_csv_5m_rows: Path,
):  # pylint: disable=redefined-outer-name
    """Test that columnar mode memory stays within SC-006 limit.

    SC-006: Memory for 5M rows ≤650 MB (columnar mode).
    NFR-002: Memory footprint must stay within acceptable limits.
    """
    from src.data_io.ingestion import ingest_ohlcv_data

    # Force garbage collection
    gc.collect()
    memory_before = get_process_memory_mb()

    # Ingest in columnar mode
    result = ingest_ohlcv_data(
        str(synthetic_csv_5m_rows),
        timeframe_minutes=1,
        mode="columnar",
        downcast=False,
        use_arrow=True,
    )

    gc.collect()
    memory_after = get_process_memory_mb()

    memory_used = memory_after - memory_before
    data_size_mb = result.data.memory_usage(deep=True).sum() / 1024 / 1024

    print("\n5M rows ingested:")
    print(f"  Process memory increase: {memory_used:.1f} MB")
    print(f"  DataFrame memory_usage(): {data_size_mb:.1f} MB")
    print("  Target: ≤650 MB (SC-006)")

    # SC-006 assertion
    max_memory = 650  # MB
    assert memory_used <= max_memory, (
        f"SC-006 FAILED: Memory usage {memory_used:.1f} MB exceeds "
        f"limit {max_memory} MB for 5M rows"
    )


def test_iterator_memory_constant(
    synthetic_csv_5m_rows: Path,
):  # pylint: disable=redefined-outer-name
    """Test that iterator mode maintains constant memory.

    Iterator mode should not load entire dataset into memory.
    """
    from src.data_io.ingestion import ingest_ohlcv_data

    gc.collect()
    memory_before = get_process_memory_mb()

    # Ingest in iterator mode
    result = ingest_ohlcv_data(
        str(synthetic_csv_5m_rows),
        timeframe_minutes=1,
        mode="iterator",
        downcast=False,
        use_arrow=True,
    )

    # Process first 100k rows
    row_count = 0
    for _ in result.data:
        row_count += 1
        if row_count >= 100_000:
            break

    gc.collect()
    memory_during = get_process_memory_mb()
    memory_used = memory_during - memory_before

    print("\nIterator mode (100k of 5M rows processed):")
    print(f"  Memory increase: {memory_used:.1f} MB")
    print("  Should be << 650 MB (columnar limit)")

    # Iterator should use much less memory than columnar
    max_iterator_memory = 100  # MB (conservative estimate)
    assert memory_used <= max_iterator_memory, (
        f"Iterator mode using {memory_used:.1f} MB exceeds "
        f"expected {max_iterator_memory} MB"
    )


def test_downcast_reduces_memory():
    """Test that downcast=True reduces memory footprint."""
    from src.data_io.ingestion import ingest_ohlcv_data

    # Create small dataset for comparison
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", newline=""
    ) as f:
        import csv

        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])

        timestamps = pd.date_range("2020-01-01", periods=100_000, freq="1min", tz="UTC")
        for ts in timestamps:
            writer.writerow(
                [
                    ts.strftime("%Y-%m-%d %H:%M:%S"),
                    1.1000,
                    1.1001,
                    1.0999,
                    1.1000,
                    1000,
                ]
            )

        csv_path = Path(f.name)

    try:
        # Ingest without downcast
        result_no_downcast = ingest_ohlcv_data(
            str(csv_path),
            timeframe_minutes=1,
            mode="columnar",
            downcast=False,
            use_arrow=True,
        )
        memory_no_downcast = (
            result_no_downcast.data.memory_usage(deep=True).sum() / 1024 / 1024
        )

        # Ingest with downcast
        result_downcast = ingest_ohlcv_data(
            str(csv_path),
            timeframe_minutes=1,
            mode="columnar",
            downcast=True,
            use_arrow=True,
        )
        memory_downcast = (
            result_downcast.data.memory_usage(deep=True).sum() / 1024 / 1024
        )

        reduction_pct = (
            (memory_no_downcast - memory_downcast) / memory_no_downcast * 100
        )

        print("\nMemory comparison (100k rows):")
        print(f"  Without downcast: {memory_no_downcast:.2f} MB")
        print(f"  With downcast: {memory_downcast:.2f} MB")
        print(f"  Reduction: {reduction_pct:.1f}%")

        # Downcast should reduce memory by at least 30% (float64→float32 ~50%)
        min_reduction = 30.0
        assert reduction_pct >= min_reduction, (
            f"Downcast only reduced memory by {reduction_pct:.1f}% "
            f"(expected ≥{min_reduction}%)"
        )

    finally:
        csv_path.unlink(missing_ok=True)


def test_memory_scales_linearly():
    """Test that memory usage scales linearly with dataset size."""
    from src.data_io.ingestion import ingest_ohlcv_data

    sizes = [100_000, 500_000, 1_000_000]
    memory_per_row = []

    for size in sizes:
        # Create dataset
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv", newline=""
        ) as f:
            import csv

            writer = csv.writer(f)
            writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])

            timestamps = pd.date_range(
                "2020-01-01", periods=size, freq="1min", tz="UTC"
            )
            for ts in timestamps:
                writer.writerow(
                    [
                        ts.strftime("%Y-%m-%d %H:%M:%S"),
                        1.1000,
                        1.1001,
                        1.0999,
                        1.1000,
                        1000,
                    ]
                )

            csv_path = Path(f.name)

        try:
            result = ingest_ohlcv_data(
                str(csv_path),
                timeframe_minutes=1,
                mode="columnar",
                downcast=False,
                use_arrow=True,
            )

            memory_mb = result.data.memory_usage(deep=True).sum() / 1024 / 1024
            bytes_per_row = (memory_mb * 1024 * 1024) / size
            memory_per_row.append(bytes_per_row)

            print(
                f"\n{size:,} rows: {memory_mb:.1f} MB ({bytes_per_row:.1f} bytes/row)"
            )

        finally:
            csv_path.unlink(missing_ok=True)

    # Memory per row should be consistent (±20%)
    import numpy as np

    mean_bytes = np.mean(memory_per_row)
    for bytes_per_row in memory_per_row:
        deviation_pct = abs(bytes_per_row - mean_bytes) / mean_bytes * 100
        assert deviation_pct < 20, (
            f"Memory per row {bytes_per_row:.1f} deviates {deviation_pct:.1f}% "
            f"from mean {mean_bytes:.1f} (>20% threshold)"
        )


def test_memory_cleanup_after_ingestion():
    """Test that memory is properly released after ingestion completes."""
    from src.data_io.ingestion import ingest_ohlcv_data

    # Create dataset
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", newline=""
    ) as f:
        import csv

        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])

        timestamps = pd.date_range(
            "2020-01-01", periods=1_000_000, freq="1min", tz="UTC"
        )
        for ts in timestamps:
            writer.writerow(
                [
                    ts.strftime("%Y-%m-%d %H:%M:%S"),
                    1.1000,
                    1.1001,
                    1.0999,
                    1.1000,
                    1000,
                ]
            )

        csv_path = Path(f.name)

    try:
        gc.collect()
        memory_before = get_process_memory_mb()

        # Ingest and release
        result = ingest_ohlcv_data(
            str(csv_path),
            timeframe_minutes=1,
            mode="columnar",
            downcast=False,
            use_arrow=True,
        )
        del result

        gc.collect()
        memory_after = get_process_memory_mb()

        memory_leaked = memory_after - memory_before

        print("\nMemory after cleanup:")
        print(f"  Before: {memory_before:.1f} MB")
        print(f"  After: {memory_after:.1f} MB")
        print(f"  Leaked: {memory_leaked:.1f} MB")

        # Allow 50 MB tolerance for garbage collection timing
        max_leak = 50
        assert memory_leaked <= max_leak, (
            f"Memory leak detected: {memory_leaked:.1f} MB remains after cleanup "
            f"(threshold: {max_leak} MB)"
        )

    finally:
        csv_path.unlink(missing_ok=True)
