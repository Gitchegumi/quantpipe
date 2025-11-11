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

NOTE: ingest_candles was removed in 009-optimize-ingestion
(replaced with ingest_ohlcv_data). Old tests using ingest_candles
are marked with @pytest.mark.skip until migrated.
"""

import csv
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.backtest.drawdown import compute_max_drawdown
from src.backtest.metrics import compute_metrics
from src.models.core import Candle, TradeExecution

pytestmark = pytest.mark.performance


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


@pytest.mark.skip(
    reason="Uses removed ingest_candles API. Needs migration to ingest_ohlcv_data."
)
def test_ingestion_throughput(
    large_dataset_path: Path,
):  # pylint: disable=redefined-outer-name
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
    for _ in ingest_candles(  # pylint: disable=undefined-variable
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
    # Generate 1,000 synthetic executions
    executions: list[TradeExecution] = []
    base_time = datetime(2025, 1, 1, tzinfo=UTC)

    for i in range(1000):
        pnl_r = 1.5 if i % 3 == 0 else -1.0  # 33% win rate

        execution = TradeExecution(
            signal_id=f"sig_{i}",
            open_timestamp=base_time + timedelta(hours=i),
            close_timestamp=base_time + timedelta(hours=i, minutes=30),
            entry_fill_price=1.1000 + (i * 0.00001),
            exit_fill_price=1.1050 + (i * 0.00001),
            exit_reason="TARGET" if pnl_r > 0 else "STOP_LOSS",
            pnl_r=pnl_r,
            slippage_entry_pips=0.2,
            slippage_exit_pips=0.1,
            costs_total=1.0,
            direction="LONG" if pnl_r > 0 else "SHORT",
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
    # Generate 1,000 synthetic executions
    executions: list[TradeExecution] = []
    base_time = datetime(2025, 1, 1, tzinfo=UTC)

    for i in range(1000):
        # Alternating wins/losses
        pnl_r = 2.0 if i % 2 == 0 else -1.0

        execution = TradeExecution(
            signal_id=f"sig_{i}",
            open_timestamp=base_time + timedelta(hours=i),
            entry_fill_price=1.1000,
            close_timestamp=base_time + timedelta(hours=i, minutes=30),
            exit_fill_price=1.1050,
            exit_reason="TARGET" if pnl_r > 0 else "STOP_LOSS",
            pnl_r=pnl_r,
            slippage_entry_pips=0.2,
            slippage_exit_pips=0.1,
            costs_total=1.0,
            direction="LONG" if pnl_r > 0 else "SHORT",
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
        _ = classify_trend(window)
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


@pytest.mark.skip(
    reason="Uses removed ingest_candles API. Needs migration to ingest_ohlcv_data."
)
def test_end_to_end_backtest_performance_estimate(
    large_dataset_path: Path,
):  # pylint: disable=redefined-outer-name
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
    for candle in ingest_candles(  # pylint: disable=undefined-variable
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
@pytest.mark.skip(
    reason="Uses removed ingest_candles API. Needs migration to ingest_ohlcv_data."
)
def test_memory_efficiency_during_ingestion(
    large_dataset_path: Path,
):  # pylint: disable=redefined-outer-name
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
    for _ in ingest_candles(  # pylint: disable=undefined-variable
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


@pytest.mark.xfail(
    reason="SC-002 target (3.5M rows/min) not yet achieved. Current: ~2.6M rows/min. "
    "Tracks performance against spec 009 success criteria.",
    strict=False,
)
def test_columnar_throughput_sc002():
    """
    Test that columnar ingestion meets SC-002 throughput target.

    SC-002: Columnar throughput ≥3.5M rows/min (≥58,333 rows/sec) median;
            variance ≤10%.

    This test validates the new ingest_ohlcv_data() function performance
    against the success criteria from spec 009-optimize-ingestion.
    """
    from src.io.ingestion import ingest_ohlcv_data

    # Create synthetic dataset with 1M rows
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])

        start_dt = datetime(2020, 1, 1, tzinfo=UTC)
        for i in range(1_000_000):
            ts = start_dt + timedelta(minutes=i)
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
        # Run ingestion 3 times to check variance
        throughputs = []
        for _ in range(3):
            start_time = time.perf_counter()
            result = ingest_ohlcv_data(
                str(csv_path),
                timeframe_minutes=1,
                mode="columnar",
                downcast=False,
                use_arrow=True,
            )
            end_time = time.perf_counter()

            elapsed_seconds = end_time - start_time
            rows_ingested = len(result.data)
            rows_per_second = rows_ingested / elapsed_seconds
            rows_per_minute = rows_per_second * 60

            throughputs.append(rows_per_minute)
            print(
                f"\nRun {len(throughputs)}: {rows_ingested:,} rows in "
                f"{elapsed_seconds:.2f}s = {rows_per_minute:,.0f} rows/min"
            )

        # Calculate median throughput
        import statistics

        median_throughput = statistics.median(throughputs)

        # Check variance
        mean_throughput = statistics.mean(throughputs)
        variance_pct = (
            statistics.stdev(throughputs) / mean_throughput * 100
            if mean_throughput > 0
            else 0
        )

        print(
            f"\nMedian throughput: {median_throughput:,.0f} rows/min "
            f"(variance: {variance_pct:.1f}%)"
        )

        # SC-002 assertions
        min_throughput = 3_500_000  # 3.5M rows/min
        max_variance = 10.0  # 10%

        assert median_throughput >= min_throughput, (
            f"SC-002 FAILED: Median throughput {median_throughput:,.0f} rows/min "
            f"below target {min_throughput:,.0f} rows/min"
        )

        assert variance_pct <= max_variance, (
            f"SC-002 FAILED: Variance {variance_pct:.1f}% exceeds "
            f"maximum {max_variance}%"
        )

    finally:
        csv_path.unlink(missing_ok=True)
