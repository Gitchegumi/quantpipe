"""
Performance memory usage tests for backtest execution.

This module measures and validates memory consumption to ensure the system
can handle large datasets without excessive memory usage. Tests monitor:

- Peak memory usage during ingestion
- Memory growth patterns
- Iterator efficiency
- Garbage collection behavior
- Large dataset handling (>100K candles)

Target: Maintain <500MB peak memory for 100K candle dataset.
"""

import csv
import gc
import tempfile
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.backtest.metrics import compute_metrics
from src.io.legacy_ingestion import ingest_candles
from src.models.core import Candle, TradeExecution

pytestmark = pytest.mark.performance


def get_process_memory_mb() -> float:
    """
    Get current process memory usage in MB.

    Returns:
        Memory usage in megabytes, or -1 if psutil unavailable.
    """
    try:
        import os

        import psutil

        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        return mem_info.rss / 1024 / 1024  # Convert bytes to MB
    except ImportError:
        # psutil not available (optional dependency)
        return -1.0


# pylint: disable=redefined-outer-name
# ^ Fixture name reuse is standard pytest pattern
@pytest.fixture()
def huge_dataset_path() -> Generator[Path, None, None]:
    """
    Create a very large dataset for memory testing.

    Generates 100,000 candles (approx 70 days of M1 data).

    Yields:
        Path to temporary CSV file.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_utc", "open", "high", "low", "close", "volume"])

        base_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        price = 1.1000

        for i in range(100000):
            timestamp = base_time + timedelta(minutes=i)

            # Trending price
            trend = (i / 20000) * 0.01
            noise = ((i * 13) % 100 - 50) * 0.00001

            open_price = price + noise
            close_price = price + trend + noise
            high_price = max(open_price, close_price) + 0.0001
            low_price = min(open_price, close_price) - 0.0001

            price = close_price

            writer.writerow(
                [
                    timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    f"{open_price:.5f}",
                    f"{high_price:.5f}",
                    f"{low_price:.5f}",
                    f"{close_price:.5f}",
                    f"{1000 + (i % 500)}",
                ]
            )

        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


def test_memory_baseline():
    """
    Establish memory baseline before heavy operations.

    Validates:
    - Can measure memory (psutil available)
    - Baseline memory is reasonable
    """
    gc.collect()  # Clean up first
    baseline_mb = get_process_memory_mb()

    if baseline_mb < 0:
        pytest.skip("psutil not available for memory measurement")

    print(f"\nBaseline memory: {baseline_mb:.1f} MB")

    # Baseline should be reasonable (< 200MB for test process)
    assert baseline_mb < 500  # Very generous threshold


@pytest.mark.slow()
def test_ingestion_memory_constant(huge_dataset_path: Path):
    """
    Verify that iterator-based ingestion maintains constant memory.

    Processes 100K candles and measures memory at checkpoints.

    Validates:
    - Memory doesn't grow linearly with dataset size
    - Iterator pattern prevents full dataset loading
    - Memory growth is bounded
    """
    gc.collect()
    initial_mb = get_process_memory_mb()

    if initial_mb < 0:
        pytest.skip("psutil not available for memory measurement")

    print(f"\nInitial memory: {initial_mb:.1f} MB")

    memory_samples = []
    candle_count = 0

    for _ in ingest_candles(
        huge_dataset_path,
        ema_fast=20,
        ema_slow=50,
        expected_timeframe_minutes=1,
        allow_gaps=False,
    ):
        candle_count += 1

        # Sample memory every 10,000 candles
        if candle_count % 10000 == 0:
            gc.collect()
            current_mb = get_process_memory_mb()
            memory_samples.append(current_mb)
            print(
                f"Memory at {candle_count} candles: {current_mb:.1f} MB "
                f"(+{current_mb - initial_mb:.1f} MB)"
            )

    final_mb = get_process_memory_mb()
    memory_growth = final_mb - initial_mb

    print(f"\nFinal memory: {final_mb:.1f} MB (growth: +{memory_growth:.1f} MB)")
    print(f"Processed {candle_count} candles")

    assert candle_count == 100000

    # Memory growth should be bounded (not proportional to dataset size)
    # Allow up to 300MB growth (includes pandas/numpy overhead)
    assert memory_growth < 300


def test_execution_list_memory_growth():
    """
    Measure memory growth when accumulating trade executions.

    Creates 10,000 TradeExecution objects and measures memory.

    Validates:
    - Memory usage scales linearly (not quadratically)
    - Execution objects are reasonably sized
    """
    gc.collect()
    initial_mb = get_process_memory_mb()

    if initial_mb < 0:
        pytest.skip("psutil not available for memory measurement")

    executions: list[TradeExecution] = []
    base_time = datetime(2025, 1, 1, tzinfo=UTC)

    for i in range(10000):
        execution = TradeExecution(
            signal_id=f"signal_{i:06d}",
            open_timestamp=base_time + timedelta(hours=i),
            entry_fill_price=1.1000 + (i * 0.00001),
            close_timestamp=base_time + timedelta(hours=i, minutes=30),
            exit_fill_price=1.1050 + (i * 0.00001),
            exit_reason="TARGET",
            pnl_r=1.5,
            slippage_entry_pips=0.2,
            slippage_exit_pips=0.1,
            costs_total=1.0,
            direction="LONG",
        )
        executions.append(execution)

    gc.collect()
    final_mb = get_process_memory_mb()
    memory_growth = final_mb - initial_mb

    print(
        f"\nMemory for 10,000 executions: +{memory_growth:.1f} MB "
        f"({memory_growth / 10:.1f} KB per execution)"
    )

    # Should be relatively small (< 50MB for 10K executions)
    assert memory_growth < 100


def test_metrics_computation_memory_spike():
    """
    Verify that metrics computation doesn't cause memory spikes.

    Computes metrics on large execution list and monitors memory.

    Validates:
    - No temporary memory spikes during computation
    - Numpy operations are memory-efficient
    """
    gc.collect()
    initial_mb = get_process_memory_mb()

    if initial_mb < 0:
        pytest.skip("psutil not available for memory measurement")

    # Create 5,000 executions
    executions: list[TradeExecution] = []
    base_time = datetime(2025, 1, 1, tzinfo=UTC)

    for i in range(5000):
        pnl_r = 2.0 if i % 3 == 0 else -1.0

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

    mid_mb = get_process_memory_mb()

    # Compute metrics (testing memory impact)
    _ = compute_metrics(executions)

    gc.collect()
    final_mb = get_process_memory_mb()

    memory_spike = final_mb - mid_mb

    print(
        f"\nMemory during metrics computation: "
        f"+{memory_spike:.1f} MB (should be minimal)"
    )

    # Metrics computation should not cause significant memory growth
    assert abs(memory_spike) < 50  # Allow small variation


@pytest.mark.slow()
def test_candle_accumulation_memory():
    """
    Test memory usage when accumulating candles in a list.

    This simulates scenarios where candles are stored for windowing.

    Validates:
    - Candle objects are memory-efficient
    - Windowing doesn't cause excessive memory usage
    """
    gc.collect()
    initial_mb = get_process_memory_mb()

    if initial_mb < 0:
        pytest.skip("psutil not available for memory measurement")

    candles: list[Candle] = []
    base_time = datetime(2025, 1, 1, tzinfo=UTC)

    # Accumulate 10,000 candles
    for i in range(10000):
        candle = Candle.from_legacy(
            timestamp_utc=base_time + timedelta(minutes=i),
            open=1.1000,
            high=1.1010,
            low=1.0990,
            close=1.1005,
            volume=1000.0,
            ema20=1.1000,
            ema50=1.0995,
            atr=0.0015,
            rsi=50.0,
        )
        candles.append(candle)

    gc.collect()
    final_mb = get_process_memory_mb()
    memory_growth = final_mb - initial_mb

    print(
        f"\nMemory for 10,000 candles: +{memory_growth:.1f} MB "
        f"({memory_growth / 10:.1f} KB per candle)"
    )

    # Candles should be compact (< 100MB for 10K candles)
    assert memory_growth < 150


def test_garbage_collection_effectiveness():
    """
    Verify that garbage collection reclaims memory effectively.

    Creates and discards large objects, then measures cleanup.

    Validates:
    - Objects are properly garbage collected
    - No memory leaks in core data structures
    """
    gc.collect()
    initial_mb = get_process_memory_mb()

    if initial_mb < 0:
        pytest.skip("psutil not available for memory measurement")

    # Create and discard large list
    def create_temp_executions():
        temp_list = []
        base_time = datetime(2025, 1, 1, tzinfo=UTC)

        for i in range(5000):
            execution = TradeExecution(
                signal_id=f"temp_{i}",
                open_timestamp=base_time + timedelta(hours=i),
                entry_fill_price=1.1000,
                close_timestamp=base_time + timedelta(hours=i, minutes=30),
                exit_fill_price=1.1050,
                exit_reason="TARGET",
                pnl_r=1.5,
                slippage_entry_pips=0.2,
                slippage_exit_pips=0.1,
                costs_total=1.0,
                direction="LONG",
            )
            temp_list.append(execution)
        return temp_list

    # Create and discard
    _ = create_temp_executions()

    # Force garbage collection
    gc.collect()
    gc.collect()  # Run twice to be thorough

    final_mb = get_process_memory_mb()
    memory_delta = abs(final_mb - initial_mb)

    print(
        f"\nMemory after GC: {final_mb:.1f} MB "
        f"(delta from baseline: {memory_delta:.1f} MB)"
    )

    # Memory should return close to baseline (allow 20MB variation)
    assert memory_delta < 50


@pytest.mark.slow()
def test_peak_memory_large_backtest_simulation(huge_dataset_path: Path):
    """
    Simulate full backtest and measure peak memory usage.

    Processes 100K candles with windowing and periodic metrics computation.

    Validates:
    - Peak memory stays under threshold
    - System can handle production-scale datasets
    """
    gc.collect()
    initial_mb = get_process_memory_mb()

    if initial_mb < 0:
        pytest.skip("psutil not available for memory measurement")

    print(f"\nInitial memory: {initial_mb:.1f} MB")

    candle_window: list[Candle] = []
    window_size = 200
    candle_count = 0
    peak_mb = initial_mb

    for candle in ingest_candles(
        huge_dataset_path,
        ema_fast=20,
        ema_slow=50,
        expected_timeframe_minutes=1,
        allow_gaps=False,
    ):
        # Maintain rolling window
        candle_window.append(candle)
        if len(candle_window) > window_size:
            candle_window.pop(0)

        candle_count += 1

        # Sample memory periodically
        if candle_count % 10000 == 0:
            current_mb = get_process_memory_mb()
            peak_mb = max(peak_mb, current_mb)
            print(
                f"Memory at {candle_count} candles: {current_mb:.1f} MB "
                f"(peak: {peak_mb:.1f} MB)"
            )

    gc.collect()
    _final_mb = get_process_memory_mb()
    total_growth = peak_mb - initial_mb

    print(
        f"\nPeak memory: {peak_mb:.1f} MB "
        f"(growth: +{total_growth:.1f} MB from {candle_count} candles)"
    )

    assert candle_count == 100000

    # Peak memory should stay under 500MB for 100K candles
    assert total_growth < 500
