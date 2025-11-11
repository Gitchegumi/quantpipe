"""
Progress overhead performance tests for Spec 010.

Validates that progress tracking overhead remains ≤1% of total runtime
(PROGRESS_MAX_OVERHEAD_PCT target).

Test Coverage:
- T050: Progress overhead ≤1% in scan phase
- T050: Progress overhead ≤1% in simulation phase
- T050: Progress overhead validation with large datasets
- T050: No progress vs. with progress comparison
- T050: Progress overhead scales linearly
"""

import time

import pandas as pd
import polars as pl
import pytest

from src.backtest.batch_scan import BatchScan
from src.backtest.batch_simulation import BatchSimulation
from src.config.backtest_config import SimulationConfig
from src.config.strategy_config import StrategyConfig
from src.io.progress import ProgressConfig, ProgressDispatcher


# Constants from Spec 010
PROGRESS_MAX_OVERHEAD_PCT = 1.0  # Maximum allowed overhead: 1%
PROGRESS_STRIDE_ITEMS = 16384  # Progress reporting stride: 2^14
PROGRESS_MAX_INTERVAL_SECONDS = 120  # Maximum seconds between updates


def _measure_scan_runtime(
    df: pl.LazyFrame,
    strategy_config: StrategyConfig,
    with_progress: bool,
) -> float:
    """
    Measure scan runtime with or without progress tracking.

    Args:
        df: LazyFrame with OHLCV data
        strategy_config: Strategy configuration
        with_progress: Whether to enable progress tracking

    Returns:
        Runtime in seconds
    """
    if with_progress:
        progress_config = ProgressConfig(
            enabled=True,
            stride_items=PROGRESS_STRIDE_ITEMS,
            max_interval_seconds=PROGRESS_MAX_INTERVAL_SECONDS,
        )
        dispatcher = ProgressDispatcher(config=progress_config)
    else:
        dispatcher = None

    scanner = BatchScan(
        strategy_config=strategy_config,
        symbol="TEST",
        progress_dispatcher=dispatcher,
    )

    start_time = time.perf_counter()
    scanner.scan(df)
    end_time = time.perf_counter()

    return end_time - start_time


def _measure_simulation_runtime(
    signals_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    sim_config: SimulationConfig,
    with_progress: bool,
) -> float:
    """
    Measure simulation runtime with or without progress tracking.

    Args:
        signals_df: DataFrame with trade signals
        prices_df: DataFrame with OHLCV data
        sim_config: Simulation configuration
        with_progress: Whether to enable progress tracking

    Returns:
        Runtime in seconds
    """
    if with_progress:
        progress_config = ProgressConfig(
            enabled=True,
            stride_items=PROGRESS_STRIDE_ITEMS,
            max_interval_seconds=PROGRESS_MAX_INTERVAL_SECONDS,
        )
        dispatcher = ProgressDispatcher(config=progress_config)
    else:
        dispatcher = None

    simulator = BatchSimulation(
        config=sim_config,
        prices=prices_df,
        progress_dispatcher=dispatcher,
    )

    start_time = time.perf_counter()
    simulator.simulate(signals_df)
    end_time = time.perf_counter()

    return end_time - start_time


def _create_test_lazyframe(num_rows: int) -> pl.LazyFrame:
    """
    Create synthetic OHLCV LazyFrame for testing.

    Args:
        num_rows: Number of rows to generate

    Returns:
        LazyFrame with OHLCV columns
    """
    timestamps = pd.date_range(
        start="2020-01-01",
        periods=num_rows,
        freq="15min",
    )
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": 1.1000 + (pd.Series(range(num_rows)) % 100) * 0.0001,
            "high": 1.1010 + (pd.Series(range(num_rows)) % 100) * 0.0001,
            "low": 1.0990 + (pd.Series(range(num_rows)) % 100) * 0.0001,
            "close": 1.1005 + (pd.Series(range(num_rows)) % 100) * 0.0001,
            "volume": 1000.0,
        }
    )
    return pl.LazyFrame(df)


def _create_test_signals(num_signals: int) -> pd.DataFrame:
    """
    Create synthetic trade signals for testing.

    Args:
        num_signals: Number of signals to generate

    Returns:
        DataFrame with trade signals
    """
    timestamps = pd.date_range(
        start="2020-01-01",
        periods=num_signals,
        freq="1h",
    )
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "direction": ["LONG"] * num_signals,
            "entry_price": 1.1000,
            "stop_loss": 1.0950,
            "take_profit": 1.1100,
        }
    )


@pytest.mark.performance()
def test_scan_progress_overhead():
    """
    T050: Validate scan progress overhead ≤1%.

    Measures runtime with and without progress tracking.
    Overhead = ((with_progress - no_progress) / no_progress) * 100
    """
    # Arrange: Create test data (100,000 candles)
    df = _create_test_lazyframe(num_rows=100_000)
    strategy_config = StrategyConfig(
        name="TrendPullbackStrategy",
        ema_fast_period=10,
        ema_slow_period=20,
        atr_period=14,
        atr_multiplier=1.5,
        rsi_period=14,
        rsi_overbought=70.0,
        rsi_oversold=30.0,
        risk_reward_ratio=2.0,
        risk_per_trade_pct=1.0,
    )

    # Act: Measure runtime without progress
    no_progress_time = _measure_scan_runtime(
        df=df,
        strategy_config=strategy_config,
        with_progress=False,
    )

    # Act: Measure runtime with progress
    with_progress_time = _measure_scan_runtime(
        df=df,
        strategy_config=strategy_config,
        with_progress=True,
    )

    # Assert: Overhead ≤1%
    overhead_pct = ((with_progress_time - no_progress_time) / no_progress_time) * 100
    assert (
        overhead_pct <= PROGRESS_MAX_OVERHEAD_PCT
    ), f"Progress overhead {overhead_pct:.2f}% exceeds {PROGRESS_MAX_OVERHEAD_PCT}%"


@pytest.mark.performance()
def test_simulation_progress_overhead():
    """
    T050: Validate simulation progress overhead ≤1%.

    Measures simulation runtime with and without progress tracking.
    """
    # Arrange: Create test data (10,000 trades)
    num_signals = 10_000
    signals_df = _create_test_signals(num_signals=num_signals)

    # Create prices DataFrame for simulation
    timestamps = pd.date_range(
        start="2020-01-01",
        periods=num_signals * 10,
        freq="15min",
    )
    prices_df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": 1.1000,
            "high": 1.1010,
            "low": 1.0990,
            "close": 1.1005,
            "volume": 1000.0,
        }
    )

    sim_config = SimulationConfig(
        initial_balance=10000.0,
        slippage_pct=0.1,
        commission_pct=0.0,
    )

    # Act: Measure runtime without progress
    no_progress_time = _measure_simulation_runtime(
        signals_df=signals_df,
        prices_df=prices_df,
        sim_config=sim_config,
        with_progress=False,
    )

    # Act: Measure runtime with progress
    with_progress_time = _measure_simulation_runtime(
        signals_df=signals_df,
        prices_df=prices_df,
        sim_config=sim_config,
        with_progress=True,
    )

    # Assert: Overhead ≤1%
    overhead_pct = ((with_progress_time - no_progress_time) / no_progress_time) * 100
    assert (
        overhead_pct <= PROGRESS_MAX_OVERHEAD_PCT
    ), f"Progress overhead {overhead_pct:.2f}% exceeds {PROGRESS_MAX_OVERHEAD_PCT}%"


@pytest.mark.performance()
def test_progress_overhead_large_dataset():
    """
    T050: Validate progress overhead ≤1% with large datasets.

    Tests with 500,000 candles to ensure overhead remains low at scale.
    """
    # Arrange: Create large test data
    df = _create_test_lazyframe(num_rows=500_000)
    strategy_config = StrategyConfig(
        name="TrendPullbackStrategy",
        ema_fast_period=10,
        ema_slow_period=20,
        atr_period=14,
        atr_multiplier=1.5,
        rsi_period=14,
        rsi_overbought=70.0,
        rsi_oversold=30.0,
        risk_reward_ratio=2.0,
        risk_per_trade_pct=1.0,
    )

    # Act: Measure both runs
    no_progress_time = _measure_scan_runtime(
        df=df,
        strategy_config=strategy_config,
        with_progress=False,
    )
    with_progress_time = _measure_scan_runtime(
        df=df,
        strategy_config=strategy_config,
        with_progress=True,
    )

    # Assert: Overhead ≤1% even at large scale
    overhead_pct = ((with_progress_time - no_progress_time) / no_progress_time) * 100
    assert (
        overhead_pct <= PROGRESS_MAX_OVERHEAD_PCT
    ), f"Large dataset progress overhead {overhead_pct:.2f}% exceeds {PROGRESS_MAX_OVERHEAD_PCT}%"


@pytest.mark.performance()
def test_progress_stride_impact():
    """
    T050: Validate progress stride configuration impact.

    Tests that PROGRESS_STRIDE_ITEMS=16384 provides good balance
    between overhead and update frequency.
    """
    # Arrange: Create test data
    df = _create_test_lazyframe(num_rows=200_000)
    strategy_config = StrategyConfig(
        name="TrendPullbackStrategy",
        ema_fast_period=10,
        ema_slow_period=20,
        atr_period=14,
        atr_multiplier=1.5,
        rsi_period=14,
        rsi_overbought=70.0,
        rsi_oversold=30.0,
        risk_reward_ratio=2.0,
        risk_per_trade_pct=1.0,
    )

    # Act: Measure with default stride
    default_stride_config = ProgressConfig(
        enabled=True,
        stride_items=PROGRESS_STRIDE_ITEMS,
        max_interval_seconds=PROGRESS_MAX_INTERVAL_SECONDS,
    )
    dispatcher_default = ProgressDispatcher(config=default_stride_config)
    scanner_default = BatchScan(
        strategy_config=strategy_config,
        symbol="TEST",
        progress_dispatcher=dispatcher_default,
    )

    start_time = time.perf_counter()
    scanner_default.scan(df)
    default_time = time.perf_counter() - start_time

    # Act: Measure with larger stride (less overhead but fewer updates)
    large_stride_config = ProgressConfig(
        enabled=True,
        stride_items=PROGRESS_STRIDE_ITEMS * 4,
        max_interval_seconds=PROGRESS_MAX_INTERVAL_SECONDS,
    )
    dispatcher_large = ProgressDispatcher(config=large_stride_config)
    scanner_large = BatchScan(
        strategy_config=strategy_config,
        symbol="TEST",
        progress_dispatcher=dispatcher_large,
    )

    start_time = time.perf_counter()
    scanner_large.scan(df)
    large_stride_time = time.perf_counter() - start_time

    # Assert: Both configurations have acceptable performance
    # (No strict assertion; just documenting behavior)
    time_diff_pct = abs(default_time - large_stride_time) / default_time * 100
    assert (
        time_diff_pct < 5.0
    ), f"Stride configuration impact {time_diff_pct:.2f}% unexpectedly high"


@pytest.mark.performance()
def test_progress_overhead_scales_linearly():
    """
    T050: Validate progress overhead scales linearly with data size.

    Tests that overhead percentage remains constant across different
    dataset sizes (no O(n²) patterns).
    """
    # Arrange: Test with multiple dataset sizes
    dataset_sizes = [50_000, 100_000, 200_000]
    overheads = []

    strategy_config = StrategyConfig(
        name="TrendPullbackStrategy",
        ema_fast_period=10,
        ema_slow_period=20,
        atr_period=14,
        atr_multiplier=1.5,
        rsi_period=14,
        rsi_overbought=70.0,
        rsi_oversold=30.0,
        risk_reward_ratio=2.0,
        risk_per_trade_pct=1.0,
    )

    # Act: Measure overhead at each size
    for size in dataset_sizes:
        df = _create_test_lazyframe(num_rows=size)

        no_progress_time = _measure_scan_runtime(
            df=df,
            strategy_config=strategy_config,
            with_progress=False,
        )
        with_progress_time = _measure_scan_runtime(
            df=df,
            strategy_config=strategy_config,
            with_progress=True,
        )

        overhead_pct = (
            (with_progress_time - no_progress_time) / no_progress_time
        ) * 100
        overheads.append(overhead_pct)

    # Assert: All overheads ≤1%
    for overhead_pct in overheads:
        assert (
            overhead_pct <= PROGRESS_MAX_OVERHEAD_PCT
        ), f"Overhead {overhead_pct:.2f}% exceeds {PROGRESS_MAX_OVERHEAD_PCT}%"

    # Assert: Overhead variance is low (scales linearly)
    # Allow 0.5% variance across dataset sizes
    overhead_variance = max(overheads) - min(overheads)
    assert (
        overhead_variance <= 0.5
    ), f"Overhead variance {overhead_variance:.2f}% suggests non-linear scaling"
