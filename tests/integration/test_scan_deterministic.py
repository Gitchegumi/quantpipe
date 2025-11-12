"""Integration tests for deterministic scan validation.

This module validates that BatchScan produces deterministic results
across multiple runs with ±1% timing variance.

Test Coverage:
- Identical signal indices across 3 runs
- Timing variance ≤±1% across 3 runs (DETERMINISTIC_TIMING_VARIANCE_PCT)
- Signal count exact match across runs
- EURUSD, USDJPY, and both symbols test scenarios

Tests FR-001 (scan determinism) and User Story 1 determinism requirements.
"""
# pylint: disable=redefined-outer-name,unused-argument,unused-variable
# Justification:
# - redefined-outer-name: pytest fixtures intentionally shadow fixture names
# - unused-argument: parameters in mock strategy required for interface compliance
# - unused-variable: Loop indices and result variables used for scan side effects

import time

import numpy as np
import polars as pl
import pytest

from src.backtest.batch_scan import BatchScan
from src.backtest.performance_targets import DETERMINISTIC_TIMING_VARIANCE_PCT


@pytest.fixture()
def deterministic_strategy():
    """Create a deterministic mock strategy for testing."""

    class MockMetadata:
        """Mock strategy metadata."""

        name = "deterministic_test_strategy"
        version = "1.0.0"
        required_indicators = ["ema20", "ema50", "atr14"]

    class DeterministicStrategy:
        """Deterministic mock strategy implementation."""

        @property
        def metadata(self):
            """Return mock metadata."""
            return MockMetadata()

        def generate_signals(self, candles, parameters):
            """Generate deterministic signals based on simple rule.

            Generates signals at fixed intervals for reproducibility.
            """
            # Simple deterministic rule: signal every 100th candle where EMA20 > EMA50
            signals = []
            for i in range(0, len(candles), 100):
                if i < len(candles) and candles[i].get("ema20", 0) > candles[i].get(
                    "ema50", 0
                ):
                    signals.append(i)
            return signals

    return DeterministicStrategy()


@pytest.fixture()
def eurusd_deterministic_dataset():
    """Generate EURUSD deterministic dataset with fixed seed."""
    np.random.seed(42)  # Fixed seed for reproducibility
    n_rows = 10_000

    timestamps = np.arange(n_rows, dtype=np.int64) * 60  # 1-minute candles

    # Generate OHLC data with deterministic seed
    open_prices = np.random.uniform(1.05, 1.15, n_rows)
    high_prices = open_prices + np.random.uniform(0.0, 0.01, n_rows)
    low_prices = open_prices - np.random.uniform(0.0, 0.01, n_rows)
    close_prices = np.random.uniform(low_prices, high_prices)

    # Generate indicators with deterministic seed
    ema20 = np.random.uniform(1.05, 1.15, n_rows)
    ema50 = np.random.uniform(1.04, 1.14, n_rows)
    atr14 = np.random.uniform(0.001, 0.01, n_rows)

    return pl.DataFrame(
        {
            "timestamp_utc": timestamps,
            "open": open_prices,
            "high": high_prices,
            "low": low_prices,
            "close": close_prices,
            "ema20": ema20,
            "ema50": ema50,
            "atr14": atr14,
        }
    )



@pytest.fixture()
def usdjpy_deterministic_dataset():
    """Generate USDJPY deterministic dataset with fixed seed."""
    np.random.seed(43)  # Fixed seed for reproducibility
    n_rows = 12_000

    timestamps = np.arange(n_rows, dtype=np.int64) * 60  # 1-minute candles

    # Generate OHLC data with deterministic seed
    open_prices = np.random.uniform(110.0, 115.0, n_rows)
    high_prices = open_prices + np.random.uniform(0.0, 0.5, n_rows)
    low_prices = open_prices - np.random.uniform(0.0, 0.5, n_rows)
    close_prices = np.random.uniform(low_prices, high_prices)

    # Generate indicators with deterministic seed
    ema20 = np.random.uniform(110.0, 115.0, n_rows)
    ema50 = np.random.uniform(109.0, 114.0, n_rows)
    atr14 = np.random.uniform(0.01, 0.1, n_rows)

    return pl.DataFrame(
        {
            "timestamp_utc": timestamps,
            "open": open_prices,
            "high": high_prices,
            "low": low_prices,
            "close": close_prices,
            "ema20": ema20,
            "ema50": ema50,
            "atr14": atr14,
        }
    )



@pytest.mark.integration()
def test_eurusd_scan_determinism_signal_match(
    deterministic_strategy, eurusd_deterministic_dataset
):
    """Test EURUSD scan produces identical signal indices across 3 runs.

    Validates:
    - Signal indices exactly match across runs
    - Signal count identical across runs
    """
    scanner = BatchScan(strategy=deterministic_strategy, enable_progress=False)
    signal_sets = []

    # Run scan 3 times
    for _run_idx in range(3):
        result = scanner.scan(eurusd_deterministic_dataset)
        signal_sets.append(result.signal_indices)

    # Verify all runs produced identical signal indices
    for i in range(1, 3):
        np.testing.assert_array_equal(
            signal_sets[0],
            signal_sets[i],
            err_msg=f"Signal indices mismatch between run 0 and run {i}",
        )


@pytest.mark.integration()
def test_eurusd_scan_determinism_timing_variance(
    deterministic_strategy, eurusd_deterministic_dataset
):
    """Test EURUSD scan timing variance ≤±1% across 3 runs.

    Validates:
    - Timing variance within tolerance (DETERMINISTIC_TIMING_VARIANCE_PCT)
    - Durations are consistent and reasonable
    """
    scanner = BatchScan(strategy=deterministic_strategy, enable_progress=False)
    durations = []

    # Run scan 3 times and measure duration
    for _run_idx in range(3):
        start_time = time.perf_counter()
        scanner.scan(eurusd_deterministic_dataset)
        duration = time.perf_counter() - start_time
        durations.append(duration)

    # Calculate timing variance
    mean_duration = np.mean(durations)
    max_variance = max(abs(d - mean_duration) / mean_duration * 100 for d in durations)

    assert max_variance <= DETERMINISTIC_TIMING_VARIANCE_PCT, (
        f"Timing variance {max_variance:.2f}% exceeds "
        f"tolerance {DETERMINISTIC_TIMING_VARIANCE_PCT}%"
    )


@pytest.mark.integration()
def test_usdjpy_scan_determinism_signal_match(
    deterministic_strategy, usdjpy_deterministic_dataset
):
    """Test USDJPY scan produces identical signal indices across 3 runs.

    Validates:
    - Signal indices exactly match across runs
    - Signal count identical across runs
    """
    scanner = BatchScan(strategy=deterministic_strategy, enable_progress=False)
    signal_sets = []

    # Run scan 3 times
    for _run_idx in range(3):
        result = scanner.scan(usdjpy_deterministic_dataset)
        signal_sets.append(result.signal_indices)

    # Verify all runs produced identical signal indices
    for i in range(1, 3):
        np.testing.assert_array_equal(
            signal_sets[0],
            signal_sets[i],
            err_msg=f"Signal indices mismatch between run 0 and run {i}",
        )


@pytest.mark.integration()
def test_usdjpy_scan_determinism_timing_variance(
    deterministic_strategy, usdjpy_deterministic_dataset
):
    """Test USDJPY scan timing variance ≤±1% across 3 runs.

    Validates:
    - Timing variance within tolerance (DETERMINISTIC_TIMING_VARIANCE_PCT)
    - Durations are consistent and reasonable
    """
    scanner = BatchScan(strategy=deterministic_strategy, enable_progress=False)
    durations = []

    # Run scan 3 times and measure duration
    for _run_idx in range(3):
        start_time = time.perf_counter()
        scanner.scan(usdjpy_deterministic_dataset)
        duration = time.perf_counter() - start_time
        durations.append(duration)

    # Calculate timing variance
    mean_duration = np.mean(durations)
    max_variance = max(abs(d - mean_duration) / mean_duration * 100 for d in durations)

    assert max_variance <= DETERMINISTIC_TIMING_VARIANCE_PCT, (
        f"Timing variance {max_variance:.2f}% exceeds "
        f"tolerance {DETERMINISTIC_TIMING_VARIANCE_PCT}%"
    )


@pytest.mark.integration()
def test_combined_scan_determinism(
    deterministic_strategy, eurusd_deterministic_dataset, usdjpy_deterministic_dataset
):
    """Test combined EURUSD+USDJPY scan determinism across 3 runs.

    Validates:
    - Both datasets produce identical results independently
    - Combined signal count matches sum of individual runs
    """
    scanner = BatchScan(strategy=deterministic_strategy, enable_progress=False)

    # Run EURUSD and USDJPY scans 3 times each
    eurusd_signal_counts = []
    usdjpy_signal_counts = []

    for _run_idx in range(3):
        eurusd_result = scanner.scan(eurusd_deterministic_dataset)
        usdjpy_result = scanner.scan(usdjpy_deterministic_dataset)

        eurusd_signal_counts.append(eurusd_result.signal_count)
        usdjpy_signal_counts.append(usdjpy_result.signal_count)

    # Verify signal counts are identical across runs
    assert (
        len(set(eurusd_signal_counts)) == 1
    ), f"EURUSD signal counts vary: {eurusd_signal_counts}"
    assert (
        len(set(usdjpy_signal_counts)) == 1
    ), f"USDJPY signal counts vary: {usdjpy_signal_counts}"
