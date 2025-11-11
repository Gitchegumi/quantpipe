"""
Smoke tests for flakiness detection (T026-T026b).

This module runs existing unit and integration tests multiple times to verify
they produce deterministic results without flakiness. Tests from this module
are typically run as part of CI/CD pipelines to catch non-deterministic behavior.

Success criteria:
- Unit tier: Run 3 times, all tests pass each time
- Integration tier: Run 3 times, all tests pass each time
- Results are identical across runs (same counts, metrics)
"""

# pylint: disable=line-too-long

import subprocess

import pytest


# Mark as slow to exclude from default test runs
# Run explicitly with: pytest -m flakiness
pytestmark = [pytest.mark.flakiness, pytest.mark.slow]


class TestFlakinessSmoke:
    """Smoke tests to detect flaky test behavior."""

    def test_unit_tests_run_three_times_without_failures(self):
        """
        T026: Run all unit tests 3 times and verify no failures.

        Given: All unit tests in tests/unit/
        When: Running pytest 3 times
        Then: All runs should pass with identical test counts.
        """
        test_counts = []

        for run_number in range(1, 4):
            # Run unit tests
            result = subprocess.run(
                ["poetry", "run", "pytest", "tests/unit/", "-v", "--tb=no"],
                capture_output=True,
                text=True,
                check=False,
            )

            # Verify no failures
            assert (
                result.returncode == 0
            ), f"Unit tests failed on run {run_number}\n{result.stdout}\n{result.stderr}"

            # Extract test count from output
            # Look for pattern like "37 passed in 2.34s"
            import re

            match = re.search(r"(\d+) passed", result.stdout)
            if match:
                test_counts.append(int(match.group(1)))

        # Verify all runs had same test count
        assert (
            len(set(test_counts)) == 1
        ), f"Test counts varied across runs: {test_counts}"

    def test_integration_tests_run_three_times_without_failures(self):
        """
        T026b: Run all integration tests 3 times and verify no failures.

        Given: All integration tests in tests/integration/
        When: Running pytest 3 times
        Then: All runs should pass with identical test counts.
        """
        test_counts = []

        for run_number in range(1, 4):
            # Run integration tests
            result = subprocess.run(
                ["poetry", "run", "pytest", "tests/integration/", "-v", "--tb=no"],
                capture_output=True,
                text=True,
                check=False,
            )

            # Verify no failures
            assert (
                result.returncode == 0
            ), f"Integration tests failed on run {run_number}\n{result.stdout}\n{result.stderr}"

            # Extract test count from output
            import re

            match = re.search(r"(\d+) passed", result.stdout)
            if match:
                test_counts.append(int(match.group(1)))

        # Verify all runs had same test count
        assert (
            len(set(test_counts)) == 1
        ), f"Test counts varied across runs: {test_counts}"

    def test_deterministic_backtest_results(self):
        """
        T026: Verify backtest results are deterministic across multiple runs.

        Given: Same backtest configuration
        When: Running backtest 3 times
        Then: All metrics should be identical.
        """
        from pathlib import Path

        from src.backtest.orchestrator import BacktestOrchestrator
        from src.config.parameters import StrategyParameters
        from src.io.legacy_ingestion import ingest_candles
        from src.models.enums import DirectionMode

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

        results = []

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

            result = orchestrator.run_backtest(
                candles=candles,
                pair="EURUSD",
                run_id=f"flake_test_{i}",
                **signal_params,
            )

            results.append(result)

        # Verify all results are identical
        for i in range(1, len(results)):
            if results[0].metrics and results[i].metrics:
                assert (
                    results[i].metrics.trade_count == results[0].metrics.trade_count
                ), f"Trade count mismatch: run 0={results[0].metrics.trade_count}, run {i}={results[i].metrics.trade_count}"

                assert (
                    abs(results[i].metrics.win_rate - results[0].metrics.win_rate)
                    < 0.0001
                ), f"Win rate mismatch: run 0={results[0].metrics.win_rate}, run {i}={results[i].metrics.win_rate}"
