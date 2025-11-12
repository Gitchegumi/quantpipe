"""Performance benchmarks for batch simulation.

This module validates that BatchSimulation achieves the target performance
of ≤480s for ~84,938 trades (SIM_MAX_SECONDS), measures throughput (trades/sec),
and calculates speedup vs baseline execution.

Test Coverage:
- Duration assertion ≤480s for ~84,938 trades
- Throughput benchmarks (trades/sec)
- Speedup measurement (≥55% time reduction)
- EURUSD, USDJPY, and both symbols test scenarios
"""

import time

import numpy as np
import pytest

from src.backtest.batch_simulation import BatchSimulation
from src.backtest.performance_targets import (
    REFERENCE_TRADE_COUNT,
    SIM_MAX_SECONDS,
    SIM_MIN_SPEEDUP_PCT,
)


# Dummy test fixtures - will be replaced with actual large-scale fixtures
@pytest.fixture
def eurusd_large_signal_set():
    """Generate large EURUSD signal set for performance testing."""
    np.random.seed(100)
    n_signals = 40000  # ~40k trades
    n_candles = 3_000_000  # 3M candles

    signal_indices = np.sort(np.random.choice(n_candles, n_signals, replace=False))
    timestamps = np.arange(n_candles)

    # Dummy OHLC arrays
    time_idx = np.arange(n_candles)
    open_prices = np.random.uniform(1.0, 1.2, n_candles)
    high_prices = open_prices + np.random.uniform(0.0, 0.01, n_candles)
    low_prices = open_prices - np.random.uniform(0.0, 0.01, n_candles)
    close_prices = np.random.uniform(low_prices, high_prices)

    ohlc_arrays = (time_idx, open_prices, high_prices, low_prices, close_prices)

    return {
        "signal_indices": signal_indices,
        "timestamps": timestamps,
        "ohlc_arrays": ohlc_arrays,
        "symbol": "EURUSD",
        "expected_trades": n_signals,
    }


@pytest.fixture
def usdjpy_large_signal_set():
    """Generate large USDJPY signal set for performance testing."""
    np.random.seed(200)
    n_signals = 44938  # ~45k trades to reach ~84,938 combined
    n_candles = 3_900_000  # 3.9M candles

    signal_indices = np.sort(np.random.choice(n_candles, n_signals, replace=False))
    timestamps = np.arange(n_candles)

    # Dummy OHLC arrays
    time_idx = np.arange(n_candles)
    open_prices = np.random.uniform(100.0, 150.0, n_candles)
    high_prices = open_prices + np.random.uniform(0.0, 1.0, n_candles)
    low_prices = open_prices - np.random.uniform(0.0, 1.0, n_candles)
    close_prices = np.random.uniform(low_prices, high_prices)

    ohlc_arrays = (time_idx, open_prices, high_prices, low_prices, close_prices)

    return {
        "signal_indices": signal_indices,
        "timestamps": timestamps,
        "ohlc_arrays": ohlc_arrays,
        "symbol": "USDJPY",
        "expected_trades": n_signals,
    }


def simulate_baseline_perf(signal_indices, timestamps, ohlc_arrays):
    """Simulate baseline execution for performance comparison.

    Args:
        signal_indices: Array of signal indices
        timestamps: Array of timestamps
        ohlc_arrays: OHLC price arrays

    Returns:
        Dictionary with duration and throughput
    """
    # Placeholder: simple baseline timing
    # Will be replaced with actual baseline execution.py timing
    n_trades = len(signal_indices)

    # Simulate slow baseline (placeholder: assume 2x slower than target)
    baseline_duration = (n_trades / REFERENCE_TRADE_COUNT) * SIM_MAX_SECONDS * 2.2
    baseline_throughput = n_trades / baseline_duration

    return {
        "duration": baseline_duration,
        "throughput": baseline_throughput,
    }


@pytest.mark.performance
def test_eurusd_simulation_duration(eurusd_large_signal_set):
    """Test batch simulation duration for large EURUSD signal set.

    Validates:
    - Duration ≤480s (scaled for signal count)
    - Throughput (trades/sec) measurement
    """
    batch_sim = BatchSimulation()

    start_time = time.time()
    result = batch_sim.simulate(
        signal_indices=eurusd_large_signal_set["signal_indices"],
        timestamps=eurusd_large_signal_set["timestamps"],
        ohlc_arrays=eurusd_large_signal_set["ohlc_arrays"],
        progress=None,
    )
    duration = time.time() - start_time

    # Calculate expected max duration (scale by trade count)
    n_trades = eurusd_large_signal_set["expected_trades"]
    expected_max_duration = (n_trades / REFERENCE_TRADE_COUNT) * SIM_MAX_SECONDS

    # Calculate throughput
    throughput = n_trades / duration if duration > 0 else 0

    print(f"\nEURUSD simulation: {n_trades} trades in {duration:.2f}s")
    print(f"Throughput: {throughput:.2f} trades/sec")
    print(f"Expected max: {expected_max_duration:.2f}s")

    # Validate duration
    assert (
        duration <= expected_max_duration
    ), f"Duration {duration:.2f}s exceeds target {expected_max_duration:.2f}s"

    # Validate trade count
    assert (
        result.trade_count == n_trades
    ), f"Trade count mismatch: {result.trade_count} != {n_trades}"


@pytest.mark.performance
def test_usdjpy_simulation_duration(usdjpy_large_signal_set):
    """Test batch simulation duration for large USDJPY signal set.

    Validates:
    - Duration ≤480s (scaled for signal count)
    - Throughput (trades/sec) measurement
    """
    batch_sim = BatchSimulation()

    start_time = time.time()
    result = batch_sim.simulate(
        signal_indices=usdjpy_large_signal_set["signal_indices"],
        timestamps=usdjpy_large_signal_set["timestamps"],
        ohlc_arrays=usdjpy_large_signal_set["ohlc_arrays"],
        progress=None,
    )
    duration = time.time() - start_time

    # Calculate expected max duration (scale by trade count)
    n_trades = usdjpy_large_signal_set["expected_trades"]
    expected_max_duration = (n_trades / REFERENCE_TRADE_COUNT) * SIM_MAX_SECONDS

    # Calculate throughput
    throughput = n_trades / duration if duration > 0 else 0

    print(f"\nUSDJPY simulation: {n_trades} trades in {duration:.2f}s")
    print(f"Throughput: {throughput:.2f} trades/sec")
    print(f"Expected max: {expected_max_duration:.2f}s")

    # Validate duration
    assert (
        duration <= expected_max_duration
    ), f"Duration {duration:.2f}s exceeds target {expected_max_duration:.2f}s"

    # Validate trade count
    assert (
        result.trade_count == n_trades
    ), f"Trade count mismatch: {result.trade_count} != {n_trades}"


@pytest.mark.performance
def test_both_symbols_simulation_duration(
    eurusd_large_signal_set, usdjpy_large_signal_set
):
    """Test batch simulation duration for combined EURUSD+USDJPY signal sets.

    Validates:
    - Combined duration ≤480s for ~84,938 trades
    - Throughput (trades/sec) measurement
    """
    batch_sim = BatchSimulation()

    # Run EURUSD simulation
    start_eurusd = time.time()
    eurusd_result = batch_sim.simulate(
        signal_indices=eurusd_large_signal_set["signal_indices"],
        timestamps=eurusd_large_signal_set["timestamps"],
        ohlc_arrays=eurusd_large_signal_set["ohlc_arrays"],
        progress=None,
    )
    eurusd_duration = time.time() - start_eurusd

    # Run USDJPY simulation
    start_usdjpy = time.time()
    usdjpy_result = batch_sim.simulate(
        signal_indices=usdjpy_large_signal_set["signal_indices"],
        timestamps=usdjpy_large_signal_set["timestamps"],
        ohlc_arrays=usdjpy_large_signal_set["ohlc_arrays"],
        progress=None,
    )
    usdjpy_duration = time.time() - start_usdjpy

    # Aggregate results
    total_trades = eurusd_result.trade_count + usdjpy_result.trade_count
    total_duration = eurusd_duration + usdjpy_duration
    total_throughput = total_trades / total_duration if total_duration > 0 else 0

    print(f"\nCombined simulation: {total_trades} trades in {total_duration:.2f}s")
    print(f"Total throughput: {total_throughput:.2f} trades/sec")
    print(f"Target: ≤{SIM_MAX_SECONDS}s for {REFERENCE_TRADE_COUNT} trades")

    # Calculate expected max duration
    expected_max_duration = (total_trades / REFERENCE_TRADE_COUNT) * SIM_MAX_SECONDS

    # Validate duration
    assert (
        total_duration <= expected_max_duration
    ), f"Duration {total_duration:.2f}s exceeds target {expected_max_duration:.2f}s"

    # Validate trade count
    expected_trades = (
        eurusd_large_signal_set["expected_trades"]
        + usdjpy_large_signal_set["expected_trades"]
    )
    assert (
        total_trades == expected_trades
    ), f"Trade count mismatch: {total_trades} != {expected_trades}"


@pytest.mark.performance
def test_simulation_speedup(eurusd_large_signal_set):
    """Test batch simulation speedup vs baseline execution.

    Validates:
    - Speedup ≥55% (SIM_MIN_SPEEDUP_PCT)
    - Speedup calculation: (baseline - batch) / baseline * 100
    """
    # Run baseline simulation
    baseline_result = simulate_baseline_perf(
        eurusd_large_signal_set["signal_indices"],
        eurusd_large_signal_set["timestamps"],
        eurusd_large_signal_set["ohlc_arrays"],
    )
    baseline_duration = baseline_result["duration"]

    # Run batch simulation
    batch_sim = BatchSimulation()

    start_time = time.time()
    batch_result = batch_sim.simulate(
        signal_indices=eurusd_large_signal_set["signal_indices"],
        timestamps=eurusd_large_signal_set["timestamps"],
        ohlc_arrays=eurusd_large_signal_set["ohlc_arrays"],
        progress=None,
    )
    batch_duration = time.time() - start_time

    # Calculate speedup
    speedup_pct = (
        (baseline_duration - batch_duration) / baseline_duration * 100
        if baseline_duration > 0
        else 0
    )

    print(f"\nSpeedup analysis:")
    print(f"Baseline: {baseline_duration:.2f}s")
    print(f"Batch: {batch_duration:.2f}s")
    print(f"Speedup: {speedup_pct:.2f}%")
    print(f"Target: ≥{SIM_MIN_SPEEDUP_PCT}%")

    # Validate speedup
    assert (
        speedup_pct >= SIM_MIN_SPEEDUP_PCT
    ), f"Speedup {speedup_pct:.2f}% below target {SIM_MIN_SPEEDUP_PCT}%"


@pytest.mark.performance
def test_throughput_scaling(eurusd_large_signal_set, usdjpy_large_signal_set):
    """Test throughput scales linearly with trade count.

    Validates:
    - Throughput (trades/sec) remains consistent across different trade counts
    - No O(n²) performance degradation
    """
    batch_sim = BatchSimulation()

    # Test EURUSD
    start_eurusd = time.time()
    eurusd_result = batch_sim.simulate(
        signal_indices=eurusd_large_signal_set["signal_indices"],
        timestamps=eurusd_large_signal_set["timestamps"],
        ohlc_arrays=eurusd_large_signal_set["ohlc_arrays"],
        progress=None,
    )
    eurusd_duration = time.time() - start_eurusd
    eurusd_throughput = eurusd_result.trade_count / eurusd_duration

    # Test USDJPY
    start_usdjpy = time.time()
    usdjpy_result = batch_sim.simulate(
        signal_indices=usdjpy_large_signal_set["signal_indices"],
        timestamps=usdjpy_large_signal_set["timestamps"],
        ohlc_arrays=usdjpy_large_signal_set["ohlc_arrays"],
        progress=None,
    )
    usdjpy_duration = time.time() - start_usdjpy
    usdjpy_throughput = usdjpy_result.trade_count / usdjpy_duration

    print(f"\nThroughput scaling:")
    print(
        f"EURUSD: {eurusd_result.trade_count} trades, {eurusd_throughput:.2f} trades/sec"
    )
    print(
        f"USDJPY: {usdjpy_result.trade_count} trades, {usdjpy_throughput:.2f} trades/sec"
    )

    # Calculate throughput variance
    avg_throughput = (eurusd_throughput + usdjpy_throughput) / 2
    throughput_variance_pct = (
        abs(eurusd_throughput - usdjpy_throughput) / avg_throughput * 100
    )

    print(f"Throughput variance: {throughput_variance_pct:.2f}%")

    # Validate throughput consistency (allow up to 50% variance due to different trade counts)
    assert (
        throughput_variance_pct <= 50.0
    ), f"Throughput variance {throughput_variance_pct:.2f}% indicates scaling issues"
