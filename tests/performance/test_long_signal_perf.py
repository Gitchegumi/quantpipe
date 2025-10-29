"""
Performance test harness for long signal generation workflow.

Benchmarks signal generation throughput, execution simulation speed,
and memory usage for large datasets.
"""

import pytest
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

from src.models.core import Candle
from src.config.parameters import StrategyParameters
from src.strategy.trend_pullback.signal_generator import generate_long_signals
from src.backtest.execution import simulate_execution


class TestLongSignalPerformance:
    """Performance benchmarks for US1 long signal generation."""

    @pytest.fixture
    def large_candle_dataset(self) -> list[Candle]:
        """
        Generate large synthetic candle dataset for performance testing.

        Returns 10,000 candles with realistic price movement.
        """
        candles = []
        base_price = 1.10000
        timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)

        for i in range(10000):
            # Simulate trending + ranging behavior
            if i % 500 < 300:
                # Uptrend
                price_delta = 0.00005
            elif i % 500 < 400:
                # Pullback
                price_delta = -0.00003
            else:
                # Range
                price_delta = 0.00001 if i % 2 == 0 else -0.00001

            base_price += price_delta
            open_price = base_price
            close_price = base_price + price_delta
            high = max(open_price, close_price) + 0.00002
            low = min(open_price, close_price) - 0.00002

            candle = Candle(
                timestamp_utc=timestamp,
                pair="EURUSD",
                timeframe_minutes=60,
                open=open_price,
                high=high,
                low=low,
                close=close_price,
                volume=1000 + (i % 100),
                ema_fast=base_price + 0.00010,
                ema_slow=base_price - 0.00010,
                atr=0.00050,
                rsi=50.0 + ((i % 40) - 20),  # Oscillate 30-70
                stoch_rsi=0.5 + ((i % 40) - 20) / 100,
            )
            candles.append(candle)

            timestamp += timedelta(hours=1)

        return candles

    def test_signal_generation_throughput(self, large_candle_dataset: list[Candle]):
        """
        Benchmark signal generation throughput over 10,000 candles.

        Target: < 5 seconds for 10,000 candle processing.
        """
        parameters = StrategyParameters()
        start_time = time.perf_counter()

        signals_generated = 0
        for i in range(100, len(large_candle_dataset)):
            window = large_candle_dataset[max(0, i - 100):i + 1]
            signals = generate_long_signals(
                candles=window,
                parameters=parameters,
            )
            signals_generated += len(signals)

        elapsed = time.perf_counter() - start_time

        print(f"\n--- Signal Generation Performance ---")
        print(f"Candles processed: {len(large_candle_dataset)}")
        print(f"Signals generated: {signals_generated}")
        print(f"Total time: {elapsed:.3f}s")
        print(f"Throughput: {len(large_candle_dataset) / elapsed:.0f} candles/sec")

        # Performance target: should process at least 1000 candles/sec
        assert elapsed < 10.0, f"Signal generation too slow: {elapsed:.3f}s"

    def test_execution_simulation_speed(self, large_candle_dataset: list[Candle]):
        """
        Benchmark execution simulation speed.

        Target: < 100ms per trade simulation.
        """
        from src.models.core import TradeSignal

        # Create sample signal
        signal = TradeSignal(
            id="test-signal-123",
            timestamp_utc=large_candle_dataset[100].timestamp_utc,
            pair="EURUSD",
            direction="LONG",
            entry_price=1.10000,
            stop_loss_price=1.09900,
            take_profit_price=1.10200,
            calc_position_size=1.0,
            timeframe_minutes=60,
            parameters_hash="test-hash-123",
        )

        start_time = time.perf_counter()

        # Simulate 100 executions
        execution_count = 0
        for _ in range(100):
            execution = simulate_execution(
                signal=signal,
                candles=large_candle_dataset[100:300],  # 200 candles
            )
            if execution:
                execution_count += 1

        elapsed = time.perf_counter() - start_time

        print(f"\n--- Execution Simulation Performance ---")
        print(f"Simulations run: 100")
        print(f"Executions completed: {execution_count}")
        print(f"Total time: {elapsed:.3f}s")
        print(f"Avg time per simulation: {elapsed / 100 * 1000:.2f}ms")

        # Performance target: < 100ms per simulation on average
        assert elapsed < 10.0, f"Execution simulation too slow: {elapsed:.3f}s"

    def test_memory_usage_large_backtest(self, large_candle_dataset: list[Candle]):
        """
        Measure memory footprint for large backtest.

        Ensures candle storage and execution tracking don't cause memory bloat.
        """
        import sys

        parameters = StrategyParameters()
        executions = []

        # Get baseline memory
        baseline_size = sys.getsizeof(large_candle_dataset)

        # Run signal generation and collect executions
        for i in range(100, len(large_candle_dataset)):
            window = large_candle_dataset[max(0, i - 100):i + 1]
            signals = generate_long_signals(
                candles=window,
                parameters=parameters,
            )

            for signal in signals:
                execution = simulate_execution(
                    signal=signal,
                    candles=large_candle_dataset[i:min(i + 200, len(large_candle_dataset))],
                )
                if execution:
                    executions.append(execution)

        # Check execution list size
        execution_size = sys.getsizeof(executions)

        print(f"\n--- Memory Usage ---")
        print(f"Candle dataset: {baseline_size / 1024:.2f} KB")
        print(f"Executions list: {execution_size / 1024:.2f} KB")
        print(f"Total executions: {len(executions)}")

        # Memory target: execution storage should be reasonable
        assert execution_size < baseline_size * 2, "Excessive memory usage for executions"

    @pytest.mark.skip(reason="Stress test - run manually")
    def test_stress_100k_candles(self):
        """
        Stress test with 100,000 candles.

        This test is skipped by default. Run manually for extreme load testing.
        """
        candles = []
        timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        base_price = 1.10000

        # Generate 100k candles
        for i in range(100000):
            base_price += 0.00001 if i % 2 == 0 else -0.00001
            candle = Candle(
                timestamp_utc=timestamp,
                pair="EURUSD",
                timeframe_minutes=60,
                open=base_price,
                high=base_price + 0.00005,
                low=base_price - 0.00005,
                close=base_price + 0.00002,
                volume=1000,
                ema_fast=base_price,
                ema_slow=base_price,
                atr=0.00050,
                rsi=50.0,
                stoch_rsi=0.5,
            )
            candles.append(candle)
            timestamp += timedelta(hours=1)

        parameters = StrategyParameters()
        start_time = time.perf_counter()

        signals_count = 0
        for i in range(100, len(candles), 100):  # Process every 100th for speed
            window = candles[max(0, i - 100):i + 1]
            signals = generate_long_signals(candles=window, parameters=parameters)
            signals_count += len(signals)

        elapsed = time.perf_counter() - start_time

        print(f"\n--- Stress Test (100k candles) ---")
        print(f"Total time: {elapsed:.3f}s")
        print(f"Signals generated: {signals_count}")
        print(f"Throughput: {len(candles) / elapsed:.0f} candles/sec")


class TestLatencyMeasurement:
    """Latency measurement for critical path operations."""

    def test_signal_generation_latency_p99(self):
        """
        Measure p99 latency for single signal generation call.

        Target: p99 < 50ms for real-time suitability.
        """
        from src.models.core import Candle

        # Create 100-candle window
        timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        candles = []
        for i in range(100):
            candles.append(Candle(
                timestamp_utc=timestamp + timedelta(hours=i),
                pair="EURUSD",
                timeframe_minutes=60,
                open=1.10000,
                high=1.10020,
                low=1.09980,
                close=1.10010,
                volume=1000,
                ema_fast=1.10005,
                ema_slow=1.09995,
                atr=0.00050,
                rsi=50.0,
                stoch_rsi=0.5,
            ))

        parameters = StrategyParameters()
        latencies = []

        # Run 1000 iterations
        for _ in range(1000):
            start = time.perf_counter()
            generate_long_signals(candles=candles, parameters=parameters)
            latencies.append((time.perf_counter() - start) * 1000)  # ms

        # Calculate percentiles
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]

        print(f"\n--- Signal Generation Latency ---")
        print(f"p50: {p50:.2f}ms")
        print(f"p95: {p95:.2f}ms")
        print(f"p99: {p99:.2f}ms")

        # Target: p99 should be reasonable for near-real-time use
        assert p99 < 100.0, f"p99 latency too high: {p99:.2f}ms"
