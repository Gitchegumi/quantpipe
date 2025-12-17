"""Unit tests for summary metrics including throughput and backend (T101, FR-015)."""

import tempfile
from pathlib import Path

import pandas as pd

from src.data_io.ingestion import ingest_ohlcv_data


def test_metrics_include_throughput():
    """Test that IngestionMetrics includes throughput_rows_per_min (FR-015)."""
    # Create small test dataset
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", newline=""
    ) as f:
        import csv

        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])

        timestamps = pd.date_range("2024-01-01", periods=100, freq="1min", tz="UTC")
        for ts in timestamps:
            writer.writerow(
                [ts.strftime("%Y-%m-%d %H:%M:%S"), 1.1, 1.1, 1.1, 1.1, 1000]
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

        # Check throughput is present and positive
        assert hasattr(result.metrics, "throughput_rows_per_min")
        assert result.metrics.throughput_rows_per_min > 0

        # Throughput should be reasonable (> 1000 rows/min for small dataset)
        assert result.metrics.throughput_rows_per_min > 1000

    finally:
        csv_path.unlink(missing_ok=True)


def test_metrics_include_backend():
    """Test that IngestionMetrics includes acceleration_backend (FR-015)."""
    # Create small test dataset
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", newline=""
    ) as f:
        import csv

        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])

        timestamps = pd.date_range("2024-01-01", periods=100, freq="1min", tz="UTC")
        for ts in timestamps:
            writer.writerow(
                [ts.strftime("%Y-%m-%d %H:%M:%S"), 1.1, 1.1, 1.1, 1.1, 1000]
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

        # Check backend is present and valid
        assert hasattr(result.metrics, "acceleration_backend")
        assert result.metrics.acceleration_backend in ["arrow", "pandas"]

    finally:
        csv_path.unlink(missing_ok=True)


def test_metrics_all_fields_present():
    """Test that all required IngestionMetrics fields are present."""
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", newline=""
    ) as f:
        import csv

        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])

        timestamps = pd.date_range("2024-01-01", periods=100, freq="1min", tz="UTC")
        for ts in timestamps:
            writer.writerow(
                [ts.strftime("%Y-%m-%d %H:%M:%S"), 1.1, 1.1, 1.1, 1.1, 1000]
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

        # Check all expected fields
        required_fields = [
            "total_rows_input",
            "total_rows_output",
            "gaps_inserted",
            "duplicates_removed",
            "runtime_seconds",
            "throughput_rows_per_min",
            "acceleration_backend",
            "downcast_applied",
            "stretch_runtime_candidate",
        ]

        for field in required_fields:
            assert hasattr(result.metrics, field), f"Missing field: {field}"

    finally:
        csv_path.unlink(missing_ok=True)


def test_metrics_throughput_calculation():
    """Test that throughput is present and reasonable."""
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", newline=""
    ) as f:
        import csv

        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])

        timestamps = pd.date_range("2024-01-01", periods=1000, freq="1min", tz="UTC")
        for ts in timestamps:
            writer.writerow(
                [ts.strftime("%Y-%m-%d %H:%M:%S"), 1.1, 1.1, 1.1, 1.1, 1000]
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

        # Verify throughput is present, positive, and reasonable
        assert result.metrics.throughput_rows_per_min > 0

        # Throughput should be reasonable (not absurdly high or low)
        # Minimum: 1000 rows/min (very slow)
        # Maximum: 100M rows/min (unrealistic)
        assert 1000 < result.metrics.throughput_rows_per_min < 100_000_000

    finally:
        csv_path.unlink(missing_ok=True)


def test_metrics_backend_reflects_use_arrow_param():
    """Test that backend field reflects use_arrow parameter."""
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", newline=""
    ) as f:
        import csv

        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])

        timestamps = pd.date_range("2024-01-01", periods=100, freq="1min", tz="UTC")
        for ts in timestamps:
            writer.writerow(
                [ts.strftime("%Y-%m-%d %H:%M:%S"), 1.1, 1.1, 1.1, 1.1, 1000]
            )

        csv_path = Path(f.name)

    try:
        # Try with use_arrow=True
        result_arrow = ingest_ohlcv_data(
            str(csv_path),
            timeframe_minutes=1,
            mode="columnar",
            downcast=False,
            use_arrow=True,
        )

        # Backend should be arrow or pandas (depending on availability)
        assert result_arrow.metrics.acceleration_backend in ["arrow", "pandas"]

        # Try with use_arrow=False
        result_pandas = ingest_ohlcv_data(
            str(csv_path),
            timeframe_minutes=1,
            mode="columnar",
            downcast=False,
            use_arrow=False,
        )

        # Should use pandas backend
        assert result_pandas.metrics.acceleration_backend == "pandas"

    finally:
        csv_path.unlink(missing_ok=True)


def test_metrics_runtime_positive():
    """Test that runtime_seconds is positive."""
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", newline=""
    ) as f:
        import csv

        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])

        timestamps = pd.date_range("2024-01-01", periods=100, freq="1min", tz="UTC")
        for ts in timestamps:
            writer.writerow(
                [ts.strftime("%Y-%m-%d %H:%M:%S"), 1.1, 1.1, 1.1, 1.1, 1000]
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

        assert result.metrics.runtime_seconds > 0

    finally:
        csv_path.unlink(missing_ok=True)


def test_metrics_row_counts_valid():
    """Test that row counts are non-negative and logical."""
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", newline=""
    ) as f:
        import csv

        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])

        timestamps = pd.date_range("2024-01-01", periods=100, freq="1min", tz="UTC")
        for ts in timestamps:
            writer.writerow(
                [ts.strftime("%Y-%m-%d %H:%M:%S"), 1.1, 1.1, 1.1, 1.1, 1000]
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

        # All counts should be non-negative
        assert result.metrics.total_rows_input >= 0
        assert result.metrics.total_rows_output >= 0
        assert result.metrics.gaps_inserted >= 0
        assert result.metrics.duplicates_removed >= 0

        # Output = Input - Duplicates + Gaps
        expected_output = (
            result.metrics.total_rows_input
            - result.metrics.duplicates_removed
            + result.metrics.gaps_inserted
        )
        assert result.metrics.total_rows_output == expected_output

    finally:
        csv_path.unlink(missing_ok=True)


def test_metrics_downcast_flag():
    """Test that downcast_applied flag reflects downcast parameter."""
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", newline=""
    ) as f:
        import csv

        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])

        timestamps = pd.date_range("2024-01-01", periods=100, freq="1min", tz="UTC")
        for ts in timestamps:
            writer.writerow(
                [ts.strftime("%Y-%m-%d %H:%M:%S"), 1.1, 1.1, 1.1, 1.1, 1000]
            )

        csv_path = Path(f.name)

    try:
        # With downcast=True
        result_downcast = ingest_ohlcv_data(
            str(csv_path),
            timeframe_minutes=1,
            mode="columnar",
            downcast=True,
            use_arrow=False,  # Disable arrow for consistent downcast behavior
        )
        assert result_downcast.metrics.downcast_applied is True

        # With downcast=False
        result_no_downcast = ingest_ohlcv_data(
            str(csv_path),
            timeframe_minutes=1,
            mode="columnar",
            downcast=False,
            use_arrow=False,
        )
        assert result_no_downcast.metrics.downcast_applied is False

    finally:
        csv_path.unlink(missing_ok=True)
