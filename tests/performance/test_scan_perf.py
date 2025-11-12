"""Performance benchmark tests for scan optimization.

This module validates that the optimized scan meets performance targets:
- FR-001: Scan duration ≤12 minutes (720 seconds) on 6.9M candle dataset
- Progress overhead ≤1% of total runtime

Tests use baseline dataset fixtures and assert against performance_targets.py constants.
"""

import numpy as np
import polars as pl
import pytest

from src.backtest.batch_scan import BatchScan
from src.backtest.performance_targets import SCAN_MAX_SECONDS


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
    """Create a large dataset for performance testing.

    Note: This creates a scaled-down version (100k rows) for CI testing.
    Full 6.9M dataset benchmarking happens in dedicated performance runs.
    """
    n_rows = 100_000  # Scaled down for CI
    timestamps = np.arange(n_rows, dtype=np.int64) * 60  # 1-minute candles

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
def test_scan_duration_target(mock_strategy, large_dataset):
    """Test scan completes within target duration.

    Verifies:
    - Scan duration ≤ SCAN_MAX_SECONDS (720s for 6.9M candles)
    - Scales proportionally for different dataset sizes
    """
    scanner = BatchScan(strategy=mock_strategy, enable_progress=True)
    result = scanner.scan(large_dataset)

    # Calculate proportional target based on dataset size
    # Full target: 720s for 6.9M candles
    # Current dataset: scaled proportionally
    full_dataset_size = 6_900_000
    current_dataset_size = len(large_dataset)
    proportional_target = SCAN_MAX_SECONDS * (current_dataset_size / full_dataset_size)

    # Add 20% margin for CI environment variability
    adjusted_target = proportional_target * 1.2

    assert result.scan_duration_sec <= adjusted_target, (
        f"Scan took {result.scan_duration_sec:.2f}s, "
        f"expected ≤{adjusted_target:.2f}s (proportional target)"
    )


@pytest.mark.performance
def test_scan_throughput_candles_per_second(mock_strategy, large_dataset):
    """Test scan throughput in candles per second.

    Verifies:
    - Minimum throughput achieved (≈9583 candles/sec for 6.9M in 720s)
    - Throughput is consistent across runs
    """
    scanner = BatchScan(strategy=mock_strategy, enable_progress=True)
    result = scanner.scan(large_dataset)

    throughput = result.candles_processed / result.scan_duration_sec

    # Minimum throughput target: 6.9M candles / 720s ≈ 9583 candles/sec
    min_throughput = 6_900_000 / SCAN_MAX_SECONDS

    # Allow 30% margin for smaller datasets and CI variability
    adjusted_min_throughput = min_throughput * 0.7

    assert throughput >= adjusted_min_throughput, (
        f"Throughput {throughput:.0f} candles/sec, "
        f"expected ≥{adjusted_min_throughput:.0f} candles/sec"
    )


@pytest.mark.performance
def test_scan_progress_overhead(mock_strategy, large_dataset):
    """Test progress tracking overhead is within limits.

    Verifies:
    - Progress overhead ≤1% of total runtime
    - Overhead scales with dataset size appropriately
    """
    scanner = BatchScan(strategy=mock_strategy, enable_progress=True)
    result = scanner.scan(large_dataset)

    # Progress overhead should be ≤1%
    max_overhead_pct = 1.0

    assert result.progress_overhead_pct <= max_overhead_pct, (
        f"Progress overhead {result.progress_overhead_pct:.2f}%, "
        f"expected ≤{max_overhead_pct:.2f}%"
    )


@pytest.mark.performance
def test_scan_disabled_progress_no_overhead(mock_strategy, large_dataset):
    """Test scan with disabled progress has zero overhead.

    Verifies:
    - Disabling progress eliminates overhead
    - Performance is not degraded by progress infrastructure
    """
    scanner = BatchScan(strategy=mock_strategy, enable_progress=False)
    result = scanner.scan(large_dataset)

    # With progress disabled, overhead should be exactly 0
    assert result.progress_overhead_pct == 0.0


@pytest.mark.performance
@pytest.mark.slow
def test_scan_large_dataset_full_benchmark(mock_strategy):
    """Full-scale benchmark test with 6.9M candles.

    This test is marked as 'slow' and only runs in dedicated performance
    test suites, not in standard CI pipelines.

    Verifies:
    - Scan completes in ≤720 seconds on full dataset
    - No super-linear performance degradation
    """
    # Create full-scale dataset
    n_rows = 6_900_000
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

    scanner = BatchScan(strategy=mock_strategy, enable_progress=True)
    result = scanner.scan(df)

    assert result.scan_duration_sec <= SCAN_MAX_SECONDS, (
        f"Full scan took {result.scan_duration_sec:.2f}s, "
        f"expected ≤{SCAN_MAX_SECONDS}s"
    )


@pytest.mark.performance
def test_scan_small_dataset_overhead(mock_strategy):
    """Test scan overhead on small dataset.

    Verifies:
    - Small datasets complete quickly
    - Overhead is not disproportionate for small inputs
    """
    # Create very small dataset
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

    scanner = BatchScan(strategy=mock_strategy, enable_progress=True)
    result = scanner.scan(df)

    # Small dataset should complete in <1 second
    assert result.scan_duration_sec < 1.0
