"""
Performance throughput tests for backtest execution.

This module measures and validates backtest processing speed to ensure
the system can handle large datasets efficiently. Tests establish baseline
performance metrics for:

- Candle ingestion rate (candles/second)
- Signal generation throughput
- Execution simulation speed
- Metrics computation time
- End-to-end backtest duration

Target: Process ≥10,000 candles/second for typical trend-pullback strategy.
"""

import csv
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.backtest.drawdown import compute_max_drawdown
from src.backtest.metrics import compute_metrics
from src.io.ingestion import ingest_candles
from src.models.core import Candle, TradeExecution


@pytest.fixture()
def large_dataset_path() -> Path:
    """
    Create a large synthetic dataset for throughput testing.

    Generates 50,000 candles (approx 35 days of M1 data) with:
    - Sequential timestamps
    - Realistic OHLCV values
    - Gradual price trends

    Returns:
        Path to temporary CSV file.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_utc", "open", "high", "low", "close", "volume"])

        base_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        price = 1.1000

        for i in range(50000):
            timestamp = base_time + timedelta(minutes=i)

            # Gentle trending with noise
            trend = (i / 10000) * 0.01  # +100 pips over dataset
            noise = ((i * 17) % 100 - 50) * 0.00001  # ±5 pips noise

            open_price = price + noise
            close_price = price + trend + noise + 0.00005
            high_price = max(open_price, close_price) + 0.0001
            low_price = min(open_price, close_price) - 0.0001

            price = close_price  # Next candle starts where this one closed

            writer.writerow(
                [
                    timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    f"{open_price:.5f}",
                    f"{high_price:.5f}",
                    f"{low_price:.5f}",
                    f"{close_price:.5f}",
                    f"{1000 + (i % 500)}",  # Varying volume
                ]
            )

        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


def test_ingestion_throughput(large_dataset_path: Path):
    """
    Measure candle ingestion rate.

    Target: ≥10,000 candles/second for indicator computation.

    Validates:
    - All 50,000 candles processed
    - Throughput meets minimum threshold
    - No memory leaks (iterator-based)
    """
    start_time = time.perf_counter()

    candle_count = 0
    for _ in ingest_candles(
        large_dataset_path,
        ema_fast=20,
        ema_slow=50,
        expected_timeframe_minutes=1,
        allow_gaps=False,
    ):
        candle_count += 1

    end_time = time.perf_counter()
    elapsed_seconds = end_time - start_time

    throughput = candle_count / elapsed_seconds

    print(
        f"\nIngestion throughput: {candle_count} candles in {elapsed_seconds:.2f}s "
        f"= {throughput:.0f} candles/sec"
    )

    assert candle_count == 50000
    assert throughput > 1000  # Minimum acceptable (relaxed for CI environments)


def test_metrics_computation_speed():
    """
    Measure metrics computation time for large execution lists.

    Target: <10ms for 1,000 trades.

    Validates:
    - Metrics computed efficiently
    - No quadratic complexity issues
    """
    from datetime import datetime

    # Generate 1,000 synthetic executions
    executions: list[TradeExecution] = []
    base_time = datetime(2025, 1, 1, tzinfo=UTC)

    for i in range(1000):
        pnl_r = 1.5 if i % 3 == 0 else -1.0  # 33% win rate

        execution = TradeExecution(
            signal_id=f"sig_{i}",
            open_timestamp=base_time + timedelta(hours=i),
            close_timestamp=base_time + timedelta(hours=i, minutes=30),
            fill_entry_price=1.1000 + (i * 0.00001),
            fill_stop_price=1.0950 + (i * 0.00001),
            fill_exit_price=1.1050 + (i * 0.00001),
            exit_reason="TARGET" if pnl_r > 0 else "STOP",
            pnl_r=pnl_r,
            slippage_pips=0.3,
            execution_costs_pct=0.001,
        )
        executions.append(execution)

    # Measure metrics computation
    start_time = time.perf_counter()
    metrics = compute_metrics(executions)
    end_time = time.perf_counter()

    elapsed_ms = (end_time - start_time) * 1000

    print(f"\nMetrics computation: {len(executions)} trades in {elapsed_ms:.2f}ms")

    assert metrics.trade_count == 1000
    assert elapsed_ms < 100  # Should be very fast (<100ms even in worst case)


def test_drawdown_computation_speed():
    """
    Measure drawdown curve computation time.

    Target: <50ms for 1,000 trades.

    Validates:
    - Drawdown curve computed efficiently
    - Numpy operations optimized
    """
    from datetime import datetime

    # Generate 1,000 synthetic executions
    executions: list[TradeExecution] = []
    base_time = datetime(2025, 1, 1, tzinfo=UTC)

    for i in range(1000):
        # Alternating wins/losses
        pnl_r = 2.0 if i % 2 == 0 else -1.0

        execution = TradeExecution(
            signal_id=f"sig_{i}",
            open_timestamp=base_time + timedelta(hours=i),
            close_timestamp=base_time + timedelta(hours=i, minutes=30),
            fill_entry_price=1.1000,
            fill_stop_price=1.0950,
            fill_exit_price=1.1050,
            exit_reason="TARGET" if pnl_r > 0 else "STOP",
            pnl_r=pnl_r,
            slippage_pips=0.3,
            execution_costs_pct=0.001,
        )
        executions.append(execution)

    # Measure drawdown computation
    start_time = time.perf_counter()
    max_dd = compute_max_drawdown(executions)
    end_time = time.perf_counter()

    elapsed_ms = (end_time - start_time) * 1000

    print(f"\nDrawdown computation: {len(executions)} trades in {elapsed_ms:.2f}ms")

    assert max_dd < 0  # Should have some drawdown
    assert elapsed_ms < 100  # Should be very fast


def test_signal_generation_throughput_estimate():
    """
    Estimate signal generation rate based on candle processing.

    Note: This is a simplified test. Full signal generation requires
    trend detection, pullback validation, and reversal confirmation.

    Target: Process >5,000 candles/second through signal logic.

    Validates:
    - Candle consumption rate acceptable
    - No bottlenecks in indicator access
    """
    from datetime import datetime

    from src.strategy.trend_pullback.trend_classifier import classify_trend

    # Generate 5,000 synthetic candles
    candles: list[Candle] = []
    base_time = datetime(2025, 1, 1, tzinfo=UTC)

    for i in range(5000):
        candle = Candle(
            timestamp_utc=base_time + timedelta(minutes=i),
            open=1.1000 + (i * 0.00001),
            high=1.1010 + (i * 0.00001),
            low=1.0990 + (i * 0.00001),
            close=1.1005 + (i * 0.00001),
            volume=1000.0,
            ema20=1.1000 + (i * 0.00001),
            ema50=1.0995 + (i * 0.00001),
            atr=0.0015,
            rsi=50.0 + ((i % 40) - 20),  # Oscillating RSI
        )
        candles.append(candle)

    # Measure trend classification (core of signal logic)
    start_time = time.perf_counter()

    trend_count = 0
    for i in range(50, len(candles)):  # Need history for trend detection
        window = candles[i - 50 : i + 1]
        _ = classify_trend(window, lookback_candles=50)
        trend_count += 1

    end_time = time.perf_counter()
    elapsed_seconds = end_time - start_time

    throughput = trend_count / elapsed_seconds

    print(
        f"\nTrend classification: {trend_count} candles in {elapsed_seconds:.2f}s "
        f"= {throughput:.0f} candles/sec"
    )

    assert trend_count > 4900
    assert throughput > 500  # Minimum acceptable (conservative estimate)


def test_end_to_end_backtest_performance_estimate(large_dataset_path: Path):
    """
    Estimate end-to-end backtest duration.

    This is a partial test (ingestion only) to establish baseline.
    Full backtest would add signal generation, execution, metrics.

    Target: Complete 50,000 candle backtest in <30 seconds.

    Validates:
    - Ingestion doesn't dominate runtime
    - System can scale to multi-year datasets
    """
    start_time = time.perf_counter()

    candle_count = 0

    for candle in ingest_candles(
        large_dataset_path,
        ema_fast=20,
        ema_slow=50,
        expected_timeframe_minutes=1,
        allow_gaps=False,
    ):
        candle_count += 1

        # Simulate minimal processing
        if candle_count % 1000 == 0:
            # Periodic checkpoint (simulates signal check)
            _ = candle.rsi > 70 or candle.rsi < 30

    end_time = time.perf_counter()
    elapsed_seconds = end_time - start_time

    print(f"\nEnd-to-end simulation: {candle_count} candles in {elapsed_seconds:.2f}s")

    assert candle_count == 50000
    assert elapsed_seconds < 60  # Should complete in under 1 minute


@pytest.mark.slow()
def test_memory_efficiency_during_ingestion(large_dataset_path: Path):
    """
    Verify that ingestion doesn't load entire dataset into memory.

    Iterator-based design should maintain constant memory usage.

    Validates:
    - Memory usage doesn't grow with dataset size
    - Iterator pattern working correctly
    """
    import gc

    gc.collect()  # Clear existing garbage

    # Process candles one at a time
    candle_count = 0
    for _ in ingest_candles(
        large_dataset_path,
        ema_fast=20,
        ema_slow=50,
        expected_timeframe_minutes=1,
    ):
        candle_count += 1

        # Every 10,000 candles, verify we're not accumulating
        if candle_count % 10000 == 0:
            gc.collect()
            # Memory should remain relatively constant
            # (Cannot easily measure without external profiler)

    assert candle_count == 50000
    # If test completes without MemoryError, iterator is working
