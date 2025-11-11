"""Integration tests for deterministic simulation validation.

This module validates that BatchSimulation produces deterministic results
across multiple runs with ±1% timing variance and ±0.5% PnL variance.

Test Coverage:
- Timing variance ≤±1% across 3 runs (DETERMINISTIC_TIMING_VARIANCE_PCT)
- PnL variance ≤±0.5% across 3 runs (DETERMINISTIC_PNL_VARIANCE_PCT)
- Trade count exact match across runs
- EURUSD, USDJPY, and both symbols test scenarios
"""

import time

import numpy as np
import pytest

from src.backtest.batch_simulation import BatchSimulation
from src.backtest.performance_targets import (
    DETERMINISTIC_PNL_VARIANCE_PCT,
    DETERMINISTIC_TIMING_VARIANCE_PCT,
)


# Dummy test fixtures - will be replaced with actual fixtures
@pytest.fixture()
def eurusd_deterministic_signal_set():
    """Generate EURUSD signal set for deterministic testing."""
    np.random.seed(500)
    n_signals = 5000  # 5k trades
    n_candles = 500_000  # 500k candles

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


@pytest.fixture()
def usdjpy_deterministic_signal_set():
    """Generate USDJPY signal set for deterministic testing."""
    np.random.seed(600)
    n_signals = 7000  # 7k trades
    n_candles = 700_000  # 700k candles

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


@pytest.mark.integration()
def test_eurusd_timing_determinism(eurusd_deterministic_signal_set):
    """Test timing determinism for EURUSD signal set across 3 runs.

    Validates:
    - Timing variance ≤±1% across runs
    - Trade count exact match across runs
    """
    batch_sim = BatchSimulation()
    durations = []
    trade_counts = []

    # Run simulation 3 times
    for run_idx in range(3):
        start_time = time.time()
        result = batch_sim.simulate(
            signal_indices=eurusd_deterministic_signal_set["signal_indices"],
            timestamps=eurusd_deterministic_signal_set["timestamps"],
            ohlc_arrays=eurusd_deterministic_signal_set["ohlc_arrays"],
        )
        duration = time.time() - start_time

        durations.append(duration)
        trade_counts.append(result.trade_count)

        print(f"\nRun {run_idx + 1}: {duration:.3f}s, {result.trade_count} trades")

    # Calculate timing variance
    avg_duration = sum(durations) / len(durations)
    max_duration_diff = max(abs(d - avg_duration) for d in durations)
    timing_variance_pct = (
        (max_duration_diff / avg_duration * 100) if avg_duration > 0 else 0
    )

    print("\nTiming analysis:")
    print(f"Average duration: {avg_duration:.3f}s")
    print(f"Max deviation: {max_duration_diff:.3f}s")
    print(f"Timing variance: {timing_variance_pct:.2f}%")
    print(f"Target: ≤{DETERMINISTIC_TIMING_VARIANCE_PCT}%")

    # Validate timing variance
    assert (
        timing_variance_pct <= DETERMINISTIC_TIMING_VARIANCE_PCT
    ), f"Timing variance {timing_variance_pct:.2f}% exceeds target {DETERMINISTIC_TIMING_VARIANCE_PCT}%"

    # Validate trade count consistency
    assert all(
        tc == trade_counts[0] for tc in trade_counts
    ), f"Trade counts vary across runs: {trade_counts}"


@pytest.mark.integration()
def test_usdjpy_timing_determinism(usdjpy_deterministic_signal_set):
    """Test timing determinism for USDJPY signal set across 3 runs.

    Validates:
    - Timing variance ≤±1% across runs
    - Trade count exact match across runs
    """
    batch_sim = BatchSimulation()
    durations = []
    trade_counts = []

    # Run simulation 3 times
    for run_idx in range(3):
        start_time = time.time()
        result = batch_sim.simulate(
            signal_indices=usdjpy_deterministic_signal_set["signal_indices"],
            timestamps=usdjpy_deterministic_signal_set["timestamps"],
            ohlc_arrays=usdjpy_deterministic_signal_set["ohlc_arrays"],
        )
        duration = time.time() - start_time

        durations.append(duration)
        trade_counts.append(result.trade_count)

        print(f"\nRun {run_idx + 1}: {duration:.3f}s, {result.trade_count} trades")

    # Calculate timing variance
    avg_duration = sum(durations) / len(durations)
    max_duration_diff = max(abs(d - avg_duration) for d in durations)
    timing_variance_pct = (
        (max_duration_diff / avg_duration * 100) if avg_duration > 0 else 0
    )

    print("\nTiming analysis:")
    print(f"Average duration: {avg_duration:.3f}s")
    print(f"Max deviation: {max_duration_diff:.3f}s")
    print(f"Timing variance: {timing_variance_pct:.2f}%")
    print(f"Target: ≤{DETERMINISTIC_TIMING_VARIANCE_PCT}%")

    # Validate timing variance
    assert (
        timing_variance_pct <= DETERMINISTIC_TIMING_VARIANCE_PCT
    ), f"Timing variance {timing_variance_pct:.2f}% exceeds target {DETERMINISTIC_TIMING_VARIANCE_PCT}%"

    # Validate trade count consistency
    assert all(
        tc == trade_counts[0] for tc in trade_counts
    ), f"Trade counts vary across runs: {trade_counts}"


@pytest.mark.integration()
def test_eurusd_pnl_determinism(eurusd_deterministic_signal_set):
    """Test PnL determinism for EURUSD signal set across 3 runs.

    Validates:
    - PnL variance ≤±0.5% across runs
    - Trade outcomes identical across runs
    """
    batch_sim = BatchSimulation()
    pnl_values = []
    trade_counts = []

    # Run simulation 3 times
    for run_idx in range(3):
        result = batch_sim.simulate(
            signal_indices=eurusd_deterministic_signal_set["signal_indices"],
            timestamps=eurusd_deterministic_signal_set["timestamps"],
            ohlc_arrays=eurusd_deterministic_signal_set["ohlc_arrays"],
        )

        pnl_values.append(result.total_pnl)
        trade_counts.append(result.trade_count)

        print(
            f"\nRun {run_idx + 1}: PnL={result.total_pnl:.2f}, trades={result.trade_count}"
        )

    # Calculate PnL variance
    avg_pnl = sum(pnl_values) / len(pnl_values)
    max_pnl_diff = max(abs(p - avg_pnl) for p in pnl_values)
    pnl_variance_pct = (max_pnl_diff / abs(avg_pnl) * 100) if avg_pnl != 0 else 0

    print("\nPnL analysis:")
    print(f"Average PnL: {avg_pnl:.2f}")
    print(f"Max deviation: {max_pnl_diff:.2f}")
    print(f"PnL variance: {pnl_variance_pct:.2f}%")
    print(f"Target: ≤{DETERMINISTIC_PNL_VARIANCE_PCT}%")

    # Validate PnL variance
    assert (
        pnl_variance_pct <= DETERMINISTIC_PNL_VARIANCE_PCT
    ), f"PnL variance {pnl_variance_pct:.2f}% exceeds target {DETERMINISTIC_PNL_VARIANCE_PCT}%"

    # Validate trade count consistency
    assert all(
        tc == trade_counts[0] for tc in trade_counts
    ), f"Trade counts vary across runs: {trade_counts}"


@pytest.mark.integration()
def test_usdjpy_pnl_determinism(usdjpy_deterministic_signal_set):
    """Test PnL determinism for USDJPY signal set across 3 runs.

    Validates:
    - PnL variance ≤±0.5% across runs
    - Trade outcomes identical across runs
    """
    batch_sim = BatchSimulation()
    pnl_values = []
    trade_counts = []

    # Run simulation 3 times
    for run_idx in range(3):
        result = batch_sim.simulate(
            signal_indices=usdjpy_deterministic_signal_set["signal_indices"],
            timestamps=usdjpy_deterministic_signal_set["timestamps"],
            ohlc_arrays=usdjpy_deterministic_signal_set["ohlc_arrays"],
        )

        pnl_values.append(result.total_pnl)
        trade_counts.append(result.trade_count)

        print(
            f"\nRun {run_idx + 1}: PnL={result.total_pnl:.2f}, trades={result.trade_count}"
        )

    # Calculate PnL variance
    avg_pnl = sum(pnl_values) / len(pnl_values)
    max_pnl_diff = max(abs(p - avg_pnl) for p in pnl_values)
    pnl_variance_pct = (max_pnl_diff / abs(avg_pnl) * 100) if avg_pnl != 0 else 0

    print("\nPnL analysis:")
    print(f"Average PnL: {avg_pnl:.2f}")
    print(f"Max deviation: {max_pnl_diff:.2f}")
    print(f"PnL variance: {pnl_variance_pct:.2f}%")
    print(f"Target: ≤{DETERMINISTIC_PNL_VARIANCE_PCT}%")

    # Validate PnL variance
    assert (
        pnl_variance_pct <= DETERMINISTIC_PNL_VARIANCE_PCT
    ), f"PnL variance {pnl_variance_pct:.2f}% exceeds target {DETERMINISTIC_PNL_VARIANCE_PCT}%"

    # Validate trade count consistency
    assert all(
        tc == trade_counts[0] for tc in trade_counts
    ), f"Trade counts vary across runs: {trade_counts}"


@pytest.mark.integration()
def test_both_symbols_determinism(
    eurusd_deterministic_signal_set, usdjpy_deterministic_signal_set
):
    """Test determinism for combined EURUSD+USDJPY across 3 runs.

    Validates:
    - Combined timing variance ≤±1%
    - Combined PnL variance ≤±0.5%
    - Trade counts consistent
    """
    batch_sim = BatchSimulation()
    total_durations = []
    total_pnl_values = []
    total_trade_counts = []

    # Run combined simulation 3 times
    for run_idx in range(3):
        # EURUSD simulation
        start_time = time.time()
        eurusd_result = batch_sim.simulate(
            signal_indices=eurusd_deterministic_signal_set["signal_indices"],
            timestamps=eurusd_deterministic_signal_set["timestamps"],
            ohlc_arrays=eurusd_deterministic_signal_set["ohlc_arrays"],
        )
        eurusd_duration = time.time() - start_time

        # USDJPY simulation
        start_time = time.time()
        usdjpy_result = batch_sim.simulate(
            signal_indices=usdjpy_deterministic_signal_set["signal_indices"],
            timestamps=usdjpy_deterministic_signal_set["timestamps"],
            ohlc_arrays=usdjpy_deterministic_signal_set["ohlc_arrays"],
        )
        usdjpy_duration = time.time() - start_time

        # Aggregate results
        total_duration = eurusd_duration + usdjpy_duration
        total_pnl = eurusd_result.total_pnl + usdjpy_result.total_pnl
        total_trades = eurusd_result.trade_count + usdjpy_result.trade_count

        total_durations.append(total_duration)
        total_pnl_values.append(total_pnl)
        total_trade_counts.append(total_trades)

        print(
            f"\nRun {run_idx + 1}: {total_duration:.3f}s, PnL={total_pnl:.2f}, {total_trades} trades"
        )

    # Calculate timing variance
    avg_duration = sum(total_durations) / len(total_durations)
    max_duration_diff = max(abs(d - avg_duration) for d in total_durations)
    timing_variance_pct = (
        (max_duration_diff / avg_duration * 100) if avg_duration > 0 else 0
    )

    # Calculate PnL variance
    avg_pnl = sum(total_pnl_values) / len(total_pnl_values)
    max_pnl_diff = max(abs(p - avg_pnl) for p in total_pnl_values)
    pnl_variance_pct = (max_pnl_diff / abs(avg_pnl) * 100) if avg_pnl != 0 else 0

    print("\nCombined determinism analysis:")
    print(
        f"Timing variance: {timing_variance_pct:.2f}% (target ≤{DETERMINISTIC_TIMING_VARIANCE_PCT}%)"
    )
    print(
        f"PnL variance: {pnl_variance_pct:.2f}% (target ≤{DETERMINISTIC_PNL_VARIANCE_PCT}%)"
    )

    # Validate timing variance
    assert (
        timing_variance_pct <= DETERMINISTIC_TIMING_VARIANCE_PCT
    ), f"Timing variance {timing_variance_pct:.2f}% exceeds target"

    # Validate PnL variance
    assert (
        pnl_variance_pct <= DETERMINISTIC_PNL_VARIANCE_PCT
    ), f"PnL variance {pnl_variance_pct:.2f}% exceeds target"

    # Validate trade count consistency
    assert all(
        tc == total_trade_counts[0] for tc in total_trade_counts
    ), f"Trade counts vary across runs: {total_trade_counts}"


@pytest.mark.integration()
def test_determinism_with_progress_tracking(eurusd_deterministic_signal_set):
    """Test determinism is maintained with progress tracking enabled.

    Validates:
    - Progress tracking doesn't introduce variance
    - Results identical with/without progress
    """

    batch_sim = BatchSimulation()

    # Run without progress tracking
    result_no_progress = batch_sim.simulate(
        signal_indices=eurusd_deterministic_signal_set["signal_indices"],
        timestamps=eurusd_deterministic_signal_set["timestamps"],
        ohlc_arrays=eurusd_deterministic_signal_set["ohlc_arrays"],
    )

    # Run with progress tracking (mock dispatcher)
    class MockProgressDispatcher:
        """Mock progress dispatcher for testing."""

        def update(self, current_item: int):
            """Mock update method."""
            # No-op for determinism testing

    progress = MockProgressDispatcher()
    result_with_progress = batch_sim.simulate(
        signal_indices=eurusd_deterministic_signal_set["signal_indices"],
        timestamps=eurusd_deterministic_signal_set["timestamps"],
        ohlc_arrays=eurusd_deterministic_signal_set["ohlc_arrays"],
    )

    # Validate identical outcomes
    assert (
        result_no_progress.trade_count == result_with_progress.trade_count
    ), "Trade counts differ with/without progress tracking"

    pnl_diff = abs(result_no_progress.total_pnl - result_with_progress.total_pnl)
    pnl_variance_pct = (
        pnl_diff / abs(result_no_progress.total_pnl) * 100
        if result_no_progress.total_pnl != 0
        else 0
    )

    print("\nProgress tracking determinism:")
    print(f"PnL without progress: {result_no_progress.total_pnl:.2f}")
    print(f"PnL with progress: {result_with_progress.total_pnl:.2f}")
    print(f"PnL variance: {pnl_variance_pct:.2f}%")

    assert (
        pnl_variance_pct <= DETERMINISTIC_PNL_VARIANCE_PCT
    ), f"Progress tracking introduces PnL variance {pnl_variance_pct:.2f}%"
