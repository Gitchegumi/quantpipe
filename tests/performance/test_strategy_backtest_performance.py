"""
Performance tests for strategy backtest execution (T025).

This module verifies that the backtesting engine can process large datasets
within acceptable time limits. Performance criteria from requirements:

- Process 6+ months of M1 data in < 5 seconds
- Memory usage remains stable
- Results are deterministic regardless of execution time

These tests use the @pytest.mark.performance marker and are typically run
separately from unit/integration tests during CI or before releases.
"""

from pathlib import Path

import pytest

from src.backtest.orchestrator import BacktestOrchestrator
from src.config.parameters import StrategyParameters
from src.data_io.legacy_ingestion import ingest_candles
from src.models.enums import DirectionMode


pytestmark = pytest.mark.performance


class TestBacktestPerformance:
    """Test backtest execution performance with large datasets."""

    def test_backtest_performance_full_year(self):
        """
        T025: Verify backtest completes within reasonable time for full year data.

        Given: Full year 2020 M1 data (~372,335 candles)
        When: Running backtest
        Then: Should complete within 10 seconds.
        """
        import time

        data_path = Path("price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv")

        if not data_path.exists():
            pytest.skip(f"Test data not found: {data_path}")

        # Create strategy parameters
        parameters = StrategyParameters()

        # Ingest candles
        start_time = time.perf_counter()
        candles = list(
            ingest_candles(
                csv_path=data_path,
                ema_fast=parameters.ema_fast,
                ema_slow=parameters.ema_slow,
                atr_period=parameters.atr_length,
                rsi_period=parameters.rsi_length,
                stoch_rsi_period=parameters.rsi_length,
                expected_timeframe_minutes=1,
                allow_gaps=True,
            )
        )

        # Create orchestrator
        orchestrator = BacktestOrchestrator(
            direction_mode=DirectionMode.BOTH, dry_run=False
        )

        # Run backtest
        signal_params = {
            "ema_fast": parameters.ema_fast,
            "ema_slow": parameters.ema_slow,
            "atr_stop_mult": parameters.atr_stop_mult,
            "target_r_mult": parameters.target_r_mult,
            "cooldown_candles": parameters.cooldown_candles,
            "rsi_length": parameters.rsi_length,
        }

        result = orchestrator.run_backtest(
            candles=candles, pair="EURUSD", run_id="perf_test_001", **signal_params
        )

        elapsed_time = time.perf_counter() - start_time

        # Verify performance requirement (< 10s for full year)
        assert (
            elapsed_time < 10.0
        ), f"Full year backtest should complete in < 10s, took {elapsed_time:.2f}s"

        # Verify results are valid
        assert result.total_candles > 350000, "Should process full year of data"
        assert result.metrics is not None, "Should generate metrics"

    def test_backtest_performance_determinism(self):
        """
        T025: Verify performance doesn't affect determinism.

        Given: Same dataset run multiple times
        When: Measuring execution time
        Then: Results should be identical despite timing variations.
        """
        import time

        data_path = Path("price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv")

        if not data_path.exists():
            pytest.skip(f"Test data not found: {data_path}")

        parameters = StrategyParameters()

        # Ingest candles once
        candles = list(
            ingest_candles(
                csv_path=data_path,
                ema_fast=parameters.ema_fast,
                ema_slow=parameters.ema_slow,
                atr_period=parameters.atr_length,
                rsi_period=parameters.rsi_length,
                stoch_rsi_period=parameters.rsi_length,
                expected_timeframe_minutes=1,
                allow_gaps=True,
            )
        )

        # Run 3 times and collect results
        results = []
        times = []

        for i in range(3):
            orchestrator = BacktestOrchestrator(
                direction_mode=DirectionMode.LONG, dry_run=False
            )

            signal_params = {
                "ema_fast": parameters.ema_fast,
                "ema_slow": parameters.ema_slow,
                "atr_stop_mult": parameters.atr_stop_mult,
                "target_r_mult": parameters.target_r_mult,
                "cooldown_candles": parameters.cooldown_candles,
                "rsi_length": parameters.rsi_length,
            }

            start_time = time.perf_counter()
            result = orchestrator.run_backtest(
                candles=candles, pair="EURUSD", run_id=f"perf_det_{i}", **signal_params
            )
            elapsed_time = time.perf_counter() - start_time

            results.append(result)
            times.append(elapsed_time)

        # Results should be identical
        for i in range(1, len(results)):
            if results[0].metrics and results[i].metrics:
                assert (
                    results[i].metrics.trade_count == results[0].metrics.trade_count
                ), "Trade count should be deterministic"

        # Timing can vary but should be consistently fast
        avg_time = sum(times) / len(times)
        assert (
            avg_time < 10.0
        ), f"Average execution time should be < 10s, got {avg_time:.2f}s"

    def test_backtest_memory_stability(self):
        """
        T025: Verify memory usage remains stable during execution.

        Given: Large dataset being processed
        When: Running backtest
        Then: Memory usage should not grow excessively.
        """
        import gc

        import psutil

        data_path = Path("price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv")

        if not data_path.exists():
            pytest.skip(f"Test data not found: {data_path}")

        # Get baseline memory
        gc.collect()
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        parameters = StrategyParameters()

        candles = list(
            ingest_candles(
                csv_path=data_path,
                ema_fast=parameters.ema_fast,
                ema_slow=parameters.ema_slow,
                atr_period=parameters.atr_length,
                rsi_period=parameters.rsi_length,
                stoch_rsi_period=parameters.rsi_length,
                expected_timeframe_minutes=1,
                allow_gaps=True,
            )
        )

        orchestrator = BacktestOrchestrator(
            direction_mode=DirectionMode.BOTH, dry_run=False
        )

        signal_params = {
            "ema_fast": parameters.ema_fast,
            "ema_slow": parameters.ema_slow,
            "atr_stop_mult": parameters.atr_stop_mult,
            "target_r_mult": parameters.target_r_mult,
            "cooldown_candles": parameters.cooldown_candles,
            "rsi_length": parameters.rsi_length,
        }

        result = orchestrator.run_backtest(
            candles=candles, pair="EURUSD", run_id="perf_mem_001", **signal_params
        )

        # Check memory after backtest
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - baseline_memory

        # Memory increase should be reasonable (< 500 MB for full year)
        assert (
            memory_increase < 500
        ), f"Memory usage grew by {memory_increase:.1f} MB (should be < 500 MB)"

        # Verify backtest completed successfully
        assert result.total_candles > 0
