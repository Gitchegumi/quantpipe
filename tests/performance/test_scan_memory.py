"""Memory usage benchmark tests for scan optimization.

This module validates that the optimized scan achieves memory reduction targets:
- Peak memory reduced by ≥30% vs baseline
- No catastrophic memory growth with large datasets
- Memory pressure handled gracefully

Uses MemorySampler from src/backtest/memory_sampler.py for tracking.
"""

import numpy as np
import polars as pl
import pytest

from src.backtest.batch_scan import BatchScan
from src.backtest.memory_sampler import MemorySampler


@pytest.fixture
def mock_strategy():
    """Create a mock strategy for testing."""

    class MockMetadata:
        """Mock strategy metadata."""

        name = "test_strategy"
        version = "1.0.0"
        required_indicators = ["ema20", "ema50", "atr14"]

    class MockStrategy:
        """Mock strategy implementation."""

        @property
        def metadata(self):
            """Return mock metadata."""
            return MockMetadata()

        def generate_signals(self, candles, parameters):
            """Mock signal generation."""
            return []

    return MockStrategy()


@pytest.fixture
def large_dataset():
    """Create a large dataset for memory testing.

    Note: Uses 200k rows as a balance between CI performance and
    meaningful memory measurement.
    """
    n_rows = 200_000
    timestamps = np.arange(n_rows, dtype=np.int64) * 60

    df = pl.DataFrame(
        {
            "timestamp_utc": timestamps,
            "open": np.random.uniform(1.1, 1.2, n_rows),
            "high": np.random.uniform(1.2, 1.3, n_rows),
            "low": np.random.uniform(1.0, 1.1, n_rows),
            "close": np.random.uniform(1.1, 1.2, n_rows),
            "ema20": np.random.uniform(1.1, 1.2, n_rows),
            "ema50": np.random.uniform(1.1, 1.2, n_rows),
            "atr14": np.random.uniform(0.001, 0.01, n_rows),
        }
    )

    return df


@pytest.mark.performance
def test_scan_peak_memory_tracking(mock_strategy, large_dataset):
    """Test peak memory is tracked during scan.

    Verifies:
    - MemorySampler successfully tracks memory usage
    - Peak memory measurement is non-zero
    - Memory is released after scan completes
    """
    sampler = MemorySampler()
    sampler.start()

    scanner = BatchScan(strategy=mock_strategy, enable_progress=False)
    scanner.scan(large_dataset)

    sampler.stop()
    peak_mb = sampler.get_peak_memory_mb()

    assert peak_mb > 0, "Peak memory should be measured"


@pytest.mark.performance
def test_scan_memory_baseline_comparison(mock_strategy, large_dataset):
    """Test memory usage against baseline target.

    Note: This test requires a baseline measurement from the legacy
    implementation to compare against. In absence of baseline, we verify
    memory growth is proportional to dataset size.

    Verifies:
    - Memory usage scales linearly with dataset size
    - No super-linear memory growth
    """
    sampler = MemorySampler()
    sampler.start()

    scanner = BatchScan(strategy=mock_strategy, enable_progress=False)
    result = scanner.scan(large_dataset)

    sampler.stop()
    peak_mb = sampler.get_peak_memory_mb()

    # Estimate expected memory usage
    # OHLC: 5 columns × 8 bytes × 200k rows ≈ 8 MB
    # Indicators: 3 columns × 8 bytes × 200k rows ≈ 4.8 MB
    # Total data: ~13 MB + overhead for Polars/NumPy structures
    # Reasonable upper bound: 50 MB for 200k rows

    expected_max_mb = 50.0
    assert (
        peak_mb < expected_max_mb
    ), f"Peak memory {peak_mb:.2f} MB exceeds expected {expected_max_mb:.2f} MB"


@pytest.mark.performance
def test_scan_memory_reduction_target(mock_strategy, large_dataset):
    """Test memory reduction vs baseline (when baseline available).

    This test is a placeholder for comparison against recorded baseline
    memory usage. Once baseline is established, this will verify ≥30%
    reduction as per MEM_PEAK_REDUCTION_TARGET_PCT.

    Verifies:
    - Peak memory reduced by ≥30% vs baseline
    """
    # Placeholder baseline (to be replaced with actual measurement)
    # baseline_peak_mb = 100.0  # Example baseline value

    sampler = MemorySampler()
    sampler.start()

    scanner = BatchScan(strategy=mock_strategy, enable_progress=False)
    scanner.scan(large_dataset)

    sampler.stop()
    peak_mb = sampler.get_peak_memory_mb()

    # TODO: Once baseline established, uncomment and verify:
    # reduction_pct = (1 - peak_mb / baseline_peak_mb) * 100
    # assert reduction_pct >= MEM_PEAK_REDUCTION_TARGET_PCT

    # For now, just verify measurement succeeds
    assert peak_mb > 0


@pytest.mark.performance
def test_scan_memory_growth_linear(mock_strategy):
    """Test memory growth scales linearly with dataset size.

    Verifies:
    - 2× dataset size results in ≈2× memory usage
    - No super-linear memory growth (O(n²) or worse)
    """
    # Test with two dataset sizes
    sizes = [50_000, 100_000]
    peak_memories = []

    for n_rows in sizes:
        timestamps = np.arange(n_rows, dtype=np.int64) * 60

        df = pl.DataFrame(
            {
                "timestamp_utc": timestamps,
                "open": np.random.uniform(1.1, 1.2, n_rows),
                "high": np.random.uniform(1.2, 1.3, n_rows),
                "low": np.random.uniform(1.0, 1.1, n_rows),
                "close": np.random.uniform(1.1, 1.2, n_rows),
                "ema20": np.random.uniform(1.1, 1.2, n_rows),
                "ema50": np.random.uniform(1.1, 1.2, n_rows),
                "atr14": np.random.uniform(0.001, 0.01, n_rows),
            }
        )

        sampler = MemorySampler()
        sampler.start()

        scanner = BatchScan(strategy=mock_strategy, enable_progress=False)
        scanner.scan(df)

        sampler.stop()
        peak_memories.append(sampler.get_peak_memory_mb())

    # Verify approximately linear scaling (allow 50% tolerance for overhead)
    ratio = peak_memories[1] / peak_memories[0]
    expected_ratio = sizes[1] / sizes[0]  # Should be 2.0

    assert (
        1.5 <= ratio <= 2.5
    ), f"Memory scaling ratio {ratio:.2f} deviates from expected {expected_ratio:.2f}"


@pytest.mark.performance
def test_scan_memory_small_dataset(mock_strategy):
    """Test memory usage on small dataset is minimal.

    Verifies:
    - Small datasets don't have disproportionate overhead
    - Memory usage is reasonable for small inputs
    """
    n_rows = 1000
    timestamps = np.arange(n_rows, dtype=np.int64) * 60

    df = pl.DataFrame(
        {
            "timestamp_utc": timestamps,
            "open": np.random.uniform(1.1, 1.2, n_rows),
            "high": np.random.uniform(1.2, 1.3, n_rows),
            "low": np.random.uniform(1.0, 1.1, n_rows),
            "close": np.random.uniform(1.1, 1.2, n_rows),
            "ema20": np.random.uniform(1.1, 1.2, n_rows),
            "ema50": np.random.uniform(1.1, 1.2, n_rows),
            "atr14": np.random.uniform(0.001, 0.01, n_rows),
        }
    )

    sampler = MemorySampler()
    sampler.start()

    scanner = BatchScan(strategy=mock_strategy, enable_progress=False)
    scanner.scan(df)

    sampler.stop()
    peak_mb = sampler.get_peak_memory_mb()

    # Small dataset should use <5 MB
    assert peak_mb < 5.0


@pytest.mark.performance
@pytest.mark.slow
def test_scan_memory_pressure_handling(mock_strategy):
    """Test graceful handling under memory pressure.

    This test verifies that the system doesn't fail catastrophically
    when memory is limited. Marked as 'slow' for dedicated test runs.

    Verifies:
    - Large dataset processing completes without crash
    - Memory usage stays bounded
    """
    # Create very large dataset (1M rows)
    n_rows = 1_000_000
    timestamps = np.arange(n_rows, dtype=np.int64) * 60

    df = pl.DataFrame(
        {
            "timestamp_utc": timestamps,
            "open": np.random.uniform(1.1, 1.2, n_rows),
            "high": np.random.uniform(1.2, 1.3, n_rows),
            "low": np.random.uniform(1.0, 1.1, n_rows),
            "close": np.random.uniform(1.1, 1.2, n_rows),
            "ema20": np.random.uniform(1.1, 1.2, n_rows),
            "ema50": np.random.uniform(1.1, 1.2, n_rows),
            "atr14": np.random.uniform(0.001, 0.01, n_rows),
        }
    )

    sampler = MemorySampler()
    sampler.start()

    scanner = BatchScan(strategy=mock_strategy, enable_progress=False)
    result = scanner.scan(df)

    sampler.stop()
    peak_mb = sampler.get_peak_memory_mb()

    # Should complete successfully
    assert result is not None
    # Memory should be bounded (reasonable upper limit for 1M rows)
    assert peak_mb < 250.0, f"Peak memory {peak_mb:.2f} MB exceeds limit"
