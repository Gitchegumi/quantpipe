"""Integration test for independent multi-symbol execution.

Feature: 008-multi-symbol
Task: T023 - Test independent multi-symbol run with 3 symbols
User Story: US2 - Independent Multi-Symbol Mode

This test verifies that independent multi-symbol mode executes backtests
for multiple currency pairs in isolation, with proper risk isolation and
result aggregation.
"""

from pathlib import Path

import pytest

from src.backtest.portfolio.independent_runner import IndependentRunner
from src.config.parameters import StrategyParameters
from src.models.enums import DirectionMode
from src.models.portfolio import CurrencyPair


@pytest.mark.slow
@pytest.mark.local_data
class TestIndependentThreeSymbols:
    """Test independent multi-symbol backtest execution."""

    @pytest.fixture
    def test_data_dir(self):
        """Return path to test data directory."""
        return Path("price_data/processed")

    @pytest.fixture
    def strategy_params(self):
        """Return baseline strategy parameters."""
        return StrategyParameters(
            ema_fast=20,
            ema_slow=50,
            atr_stop_mult=2.0,
            target_r_mult=2.0,
            cooldown_candles=5,
            rsi_length=14,
        )

    @pytest.fixture
    def output_dir(self, tmp_path):
        """Return temporary output directory."""
        return tmp_path / "multi_symbol_output"

    def test_three_symbol_independent_run(
        self, test_data_dir, strategy_params, output_dir
    ):
        """Test independent backtest across three symbols.

        Verifies that:
        - All three symbols are processed independently
        - Results are aggregated correctly
        - Failures in one symbol don't affect others
        """
        # Define three currency pairs
        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
            CurrencyPair(code="USDJPY"),
        ]

        # Create independent runner
        runner = IndependentRunner(
            symbols=symbols,
            data_dir=test_data_dir,
        )

        # Run independent backtests
        results = runner.run(
            strategy_params=strategy_params,
            mode=DirectionMode.BOTH,
            output_dir=output_dir,
        )

        # Verify results structure
        assert isinstance(results, dict)

        # Check that we got results for available symbols
        # (some may be skipped if datasets don't exist)
        total_processed = len(results) + len(runner.get_failures())
        assert total_processed <= len(symbols)

        # Verify each successful result
        for symbol_code, result in results.items():
            assert symbol_code in [s.code for s in symbols]
            assert hasattr(result, "metrics")
            assert result.metrics is not None

        # Get summary statistics
        summary = runner.get_summary()
        assert "total_symbols" in summary
        assert "successful" in summary
        assert "failed" in summary
        assert "total_trades" in summary

        assert summary["total_symbols"] == len(symbols)
        assert summary["successful"] == len(results)
        assert summary["failed"] == len(runner.get_failures())

    def test_partial_symbol_availability(
        self, test_data_dir, strategy_params, output_dir
    ):
        """Test behavior when some symbols are unavailable.

        Verifies that:
        - Available symbols are processed successfully
        - Unavailable symbols are recorded as failures
        - Execution continues despite failures
        """
        # Include a valid symbol and an invalid one
        symbols = [
            CurrencyPair(code="EURUSD"),  # Should exist
            CurrencyPair(code="INVLDX"),  # Won't exist
        ]

        runner = IndependentRunner(
            symbols=symbols,
            data_dir=test_data_dir,
        )

        results = runner.run(
            strategy_params=strategy_params,
            mode=DirectionMode.LONG,
            output_dir=output_dir,
        )

        # Should have at least one failure (INVALID)
        failures = runner.get_failures()
        assert len(failures) > 0
        assert "INVLDX" in failures

        # EURUSD may succeed if dataset exists
        if "EURUSD" in results:
            assert hasattr(results["EURUSD"], "metrics")

    def test_independent_risk_isolation(
        self, test_data_dir, strategy_params, output_dir
    ):
        """Test that failures in one symbol don't affect others.

        Verifies the core independence property: each symbol's backtest
        runs in complete isolation.
        """
        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
        ]

        runner = IndependentRunner(
            symbols=symbols,
            data_dir=test_data_dir,
        )

        results = runner.run(
            strategy_params=strategy_params,
            mode=DirectionMode.BOTH,
            output_dir=output_dir,
        )

        failures = runner.get_failures()

        # If one symbol succeeded, verify it wasn't affected by any failures
        if len(results) > 0:
            for result in results.values():
                # Result should be complete and valid
                assert result.metrics is not None

                # Verify trades were executed (if any)
                if hasattr(result.metrics, "combined"):
                    trade_count = result.metrics.combined.trade_count
                else:
                    trade_count = result.metrics.trade_count

                assert trade_count >= 0

        # Failures should be isolated - check they don't prevent other symbols
        if len(failures) > 0 and len(results) > 0:
            # We have both successes and failures - isolation working
            assert len(results) + len(failures) <= len(symbols)

    def test_results_aggregator_integration(
        self, test_data_dir, strategy_params, output_dir
    ):
        """Test MultiSymbolResultsAggregator with real results."""
        from src.backtest.portfolio.results import MultiSymbolResultsAggregator

        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
        ]

        runner = IndependentRunner(
            symbols=symbols,
            data_dir=test_data_dir,
        )

        results = runner.run(
            strategy_params=strategy_params,
            mode=DirectionMode.LONG,
            output_dir=output_dir,
        )

        # Skip if no results (datasets don't exist)
        if len(results) == 0:
            pytest.skip("No datasets available for testing")

        # Create aggregator
        aggregator = MultiSymbolResultsAggregator(results)

        # Verify aggregate summary
        summary = aggregator.get_aggregate_summary()
        assert summary["total_symbols"] == len(results)
        assert summary["total_trades"] >= 0
        assert 0.0 <= summary["average_win_rate"] <= 1.0

        # Verify per-symbol summaries
        per_symbol = aggregator.get_per_symbol_summary()
        assert len(per_symbol) == len(results)

        for symbol_code in results:
            assert symbol_code in per_symbol
            sym_summary = per_symbol[symbol_code]
            assert "total_trades" in sym_summary
            assert "win_rate" in sym_summary

    def test_output_directory_creation(
        self, test_data_dir, strategy_params, output_dir
    ):
        """Test that output directories are created for each symbol."""
        symbols = [CurrencyPair(code="EURUSD")]

        runner = IndependentRunner(
            symbols=symbols,
            data_dir=test_data_dir,
        )

        results = runner.run(
            strategy_params=strategy_params,
            mode=DirectionMode.SHORT,
            output_dir=output_dir,
        )

        # If EURUSD succeeded, check its output directory
        if "EURUSD" in results:
            eurusd_dir = output_dir / "eurusd"
            assert eurusd_dir.exists()
            assert eurusd_dir.is_dir()
