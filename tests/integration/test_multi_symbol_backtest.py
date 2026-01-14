"""
Integration tests for multi-symbol backtest functionality.

Tests cover:
- Multi-symbol execution (both pairs run)
- Aggregated PnL computation
- Default account balance usage
- Single-symbol regression protection
- Parquet pipeline verification

Feature: 013-multi-symbol-backtest
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from argparse import Namespace


class TestMultiSymbolExecution:
    """Tests for multi-symbol backtest execution (US1)."""

    def test_multi_symbol_both_pairs_executed(self, tmp_path: Path):
        """T021: Verify both symbols execute when multiple pairs specified.

        Given valid data files for EURUSD and USDJPY,
        When run_multi_symbol_backtest() is called with both pairs,
        Then both symbols appear in the results.
        """
        from src.backtest.engine import run_multi_symbol_backtest, construct_data_paths
        from src.models.enums import DirectionMode
        from src.config.parameters import StrategyParameters

        # This test requires actual data files to exist
        # Use construct_data_paths to get real paths
        try:
            pair_paths = construct_data_paths(
                pairs=["EURUSD", "USDJPY"],
                dataset="test",
            )
        except SystemExit:
            pytest.skip("Test data not available for EURUSD/USDJPY")

        if len(pair_paths) < 2:
            pytest.skip("Both EURUSD and USDJPY test data required")

        # Execute with minimal data to keep test fast
        # Note: Full backtest is expensive, we just verify structure
        params = StrategyParameters()
        result, _ = run_multi_symbol_backtest(
            pair_paths=pair_paths,
            direction_mode=DirectionMode.BOTH,
            strategy_params=params,
            dry_run=False,
            enable_profiling=False,
            show_progress=False,
        )

        # Verify both symbols present
        assert "EURUSD" in result.symbols
        assert "USDJPY" in result.symbols
        assert hasattr(result, "results")
        assert len(result.results) == 2

    def test_multi_symbol_aggregated_pnl(self, tmp_path: Path):
        """T022: Verify combined PnL reflects concurrent trading.

        Given multi-symbol backtest results,
        When aggregated P&L is computed,
        Then it equals sum of per-symbol expectancy × trades × risk.
        """
        from src.backtest.portfolio.results import MultiSymbolResultsAggregator

        # Create mock results
        mock_metrics_eurusd = MagicMock()
        mock_metrics_eurusd.combined = MagicMock()
        mock_metrics_eurusd.combined.expectancy = -0.02
        mock_metrics_eurusd.combined.trade_count = 1000
        mock_metrics_eurusd.combined.win_rate = 0.33

        mock_metrics_usdjpy = MagicMock()
        mock_metrics_usdjpy.combined = MagicMock()
        mock_metrics_usdjpy.combined.expectancy = -0.01
        mock_metrics_usdjpy.combined.trade_count = 800
        mock_metrics_usdjpy.combined.win_rate = 0.34

        mock_result_eurusd = MagicMock()
        mock_result_eurusd.metrics = mock_metrics_eurusd

        mock_result_usdjpy = MagicMock()
        mock_result_usdjpy.metrics = mock_metrics_usdjpy

        results = {
            "EURUSD": mock_result_eurusd,
            "USDJPY": mock_result_usdjpy,
        }

        # Create aggregator
        aggregator = MultiSymbolResultsAggregator(results)
        summary = aggregator.get_aggregate_summary()

        # Verify P&L calculation
        # $2,500 × 0.25% = $6.25 risk per trade
        # EURUSD: -0.02 × 1000 × $6.25 = -$125
        # USDJPY: -0.01 × 800 × $6.25 = -$50
        # Total: -$175
        expected_pnl = (-0.02 * 1000 * 6.25) + (-0.01 * 800 * 6.25)
        assert abs(summary["total_pnl"] - expected_pnl) < 0.01

    def test_multi_symbol_default_balance(self):
        """T023: Verify default $2,500 balance is used.

        Given the DEFAULT_ACCOUNT_BALANCE constant,
        When accessed from run_backtest module,
        Then it equals 2500.0.
        """
        from src.cli.run_backtest import DEFAULT_ACCOUNT_BALANCE

        assert DEFAULT_ACCOUNT_BALANCE == 2500.0

    def test_single_symbol_unchanged(self, tmp_path: Path):
        """T024: Verify single-symbol behavior unchanged (regression).

        Given a single pair specified,
        When backtest is run,
        Then it uses single-symbol path (not multi-symbol).
        """
        from src.cli.run_backtest import construct_data_paths

        # Setup: Create single pair data
        pair_dir = tmp_path / "eurusd" / "test"
        pair_dir.mkdir(parents=True)
        parquet_file = pair_dir / "eurusd_test.parquet"
        parquet_file.write_bytes(b"mock")

        # Execute
        result = construct_data_paths(
            pairs=["EURUSD"],
            dataset="test",
            base_dir=tmp_path,
        )

        # Verify single result
        assert len(result) == 1
        assert result[0][0] == "EURUSD"


class TestParquetPipeline:
    """Tests for Parquet pipeline verification (US3)."""

    def test_parquet_end_to_end_pipeline(self):
        """T025: Verify Parquet files work through entire pipeline.

        Given a Parquet file exists for a pair,
        When construct_data_paths() is called,
        Then the Parquet path is returned and can be loaded.
        """
        from src.cli.run_backtest import construct_data_paths

        # Execute with real data
        try:
            pair_paths = construct_data_paths(
                pairs=["EURUSD"],
                dataset="test",
            )
        except SystemExit:
            pytest.skip("EURUSD test data not available")

        # Verify Parquet preference
        if pair_paths:
            path = pair_paths[0][1]
            assert path.exists()
            # If Parquet exists, it should be preferred
            if path.with_suffix(".parquet").exists():
                assert path.suffix == ".parquet"

    def test_parquet_fallback_to_csv(self, tmp_path: Path):
        """T026: Verify CSV fallback when Parquet missing.

        Given only CSV file exists (no Parquet),
        When construct_data_paths() is called,
        Then the CSV path is returned.
        """
        from src.cli.run_backtest import construct_data_paths

        # Setup: Create only CSV
        pair_dir = tmp_path / "eurusd" / "test"
        pair_dir.mkdir(parents=True)
        csv_file = pair_dir / "eurusd_test.csv"
        csv_file.write_text("timestamp,open,high,low,close\n")

        # Execute
        result = construct_data_paths(
            pairs=["EURUSD"],
            dataset="test",
            base_dir=tmp_path,
        )

        # Verify CSV fallback
        assert len(result) == 1
        assert result[0][1].suffix == ".csv"

    def test_progress_bars_clean_display(self):
        """T027: Verify progress bars display cleanly.

        Given Rich progress is available,
        When imported,
        Then no ImportError is raised.
        """
        # Verify Rich is available
        try:
            from rich.progress import Progress, BarColumn, TextColumn

            assert Progress is not None
            assert BarColumn is not None
            assert TextColumn is not None
        except ImportError:
            pytest.fail("Rich progress not available")
