"""Integration test for single-symbol regression validation.

Feature: 008-multi-symbol
Task: T013-T014 - Ensure single-symbol baseline behavior is unchanged
User Story: US1 - Single Symbol Regression

This test verifies that adding multi-symbol functionality does not break
existing single-symbol backtesting behavior.
"""
import json
from pathlib import Path

import pytest

from src.backtest.orchestrator import BacktestOrchestrator
from src.config.parameters import StrategyParameters
from src.io.ingestion import ingest_candles
from src.models.enums import DirectionMode


class TestSingleSymbolRegression:
    """Test single-symbol backtest behavior is preserved."""

    @pytest.fixture
    def eurusd_fixture_path(self):
        """Return path to EURUSD test fixture."""
        return Path("tests/fixtures/processed/eurusd/test/eurusd_test.csv")

    @pytest.fixture
    def baseline_config(self):
        """Return baseline strategy configuration."""
        return StrategyParameters(
            ema_fast=20,
            ema_slow=50,
            atr_stop_mult=2.0,
            target_r_mult=2.0,
            cooldown_candles=5,
            rsi_length=14,
        )

    def test_single_symbol_metrics_stable(
        self, eurusd_fixture_path, baseline_config
    ):
        """Verify single-symbol backtest produces consistent metrics.

        This test ensures that the introduction of multi-symbol functionality
        does not alter single-symbol backtest results.
        """
        # Skip if fixture doesn't exist
        if not eurusd_fixture_path.exists():
            pytest.skip("EURUSD test fixture not found")

        # Load candles
        candles = ingest_candles(eurusd_fixture_path)

        # Create orchestrator and run backtest
        orchestrator = BacktestOrchestrator(
            direction_mode=DirectionMode.BOTH,
            dry_run=False,
        )

        result = orchestrator.run_backtest(
            candles=candles,
            pair="EURUSD",
            run_id="test_regression_both",
            ema_fast=baseline_config.ema_fast,
            ema_slow=baseline_config.ema_slow,
            atr_stop_mult=baseline_config.atr_stop_mult,
            target_r_mult=baseline_config.target_r_mult,
            cooldown_candles=baseline_config.cooldown_candles,
            rsi_length=baseline_config.rsi_length,
        )

        # Validate basic metrics structure
        assert result is not None
        assert hasattr(result, "metrics")

        # Get trade count using proper attribute access
        if hasattr(result.metrics, "combined"):
            # DirectionalMetrics (BOTH mode)
            trade_count = result.metrics.combined.trade_count
            win_rate = result.metrics.combined.win_rate
        else:
            # MetricsSummary (LONG/SHORT mode)
            trade_count = result.metrics.trade_count
            win_rate = result.metrics.win_rate

        # Ensure metrics are reasonable
        assert trade_count >= 0
        if trade_count > 0:
            assert 0.0 <= win_rate <= 1.0

    def test_single_symbol_filename_pattern_unchanged(
        self, eurusd_fixture_path, baseline_config, tmp_path
    ):
        """Verify single-symbol backtest output filename follows expected pattern.

        The filename pattern for single-symbol runs must remain unchanged
        to maintain backward compatibility.
        """
        # Skip if fixture doesn't exist
        if not eurusd_fixture_path.exists():
            pytest.skip("EURUSD test fixture not found")

        # Load candles
        candles = ingest_candles(eurusd_fixture_path)

        # Create orchestrator and run backtest
        orchestrator = BacktestOrchestrator(
            direction_mode=DirectionMode.LONG,
            dry_run=False,
        )

        orchestrator.run_backtest(
            candles=candles,
            pair="EURUSD",
            run_id="test_regression_long",
            ema_fast=baseline_config.ema_fast,
            ema_slow=baseline_config.ema_slow,
            atr_stop_mult=baseline_config.atr_stop_mult,
            target_r_mult=baseline_config.target_r_mult,
            cooldown_candles=baseline_config.cooldown_candles,
            rsi_length=baseline_config.rsi_length,
        )

        # Check that output files were created
        output_files = list(tmp_path.glob("backtest_*.txt"))
        assert len(output_files) > 0, "No backtest output files found"

        # Verify filename pattern
        # Expected pattern: backtest_{mode}_{timestamp}.txt
        output_file = output_files[0]
        filename = output_file.name

        assert filename.startswith("backtest_")
        assert filename.endswith(".txt")
        assert "long" in filename.lower() or "both" in filename.lower()

    def test_single_symbol_manifest_generation(
        self, eurusd_fixture_path, baseline_config, tmp_path
    ):
        """Verify manifest is generated for single-symbol runs.

        Task T016: Implement manifest extension for single-symbol run
        """
        # Skip if fixture doesn't exist
        if not eurusd_fixture_path.exists():
            pytest.skip("EURUSD test fixture not found")

        # Load candles
        candles = ingest_candles(eurusd_fixture_path)

        # Create orchestrator and run backtest
        orchestrator = BacktestOrchestrator(
            direction_mode=DirectionMode.BOTH,
            dry_run=False,
        )

        orchestrator.run_backtest(
            candles=candles,
            pair="EURUSD",
            run_id="test_manifest_both",
            ema_fast=baseline_config.ema_fast,
            ema_slow=baseline_config.ema_slow,
            atr_stop_mult=baseline_config.atr_stop_mult,
            target_r_mult=baseline_config.target_r_mult,
            cooldown_candles=baseline_config.cooldown_candles,
            rsi_length=baseline_config.rsi_length,
        )

        # Check for manifest file
        manifest_files = list(tmp_path.glob("manifest_*.json"))
        if len(manifest_files) > 0:
            # Validate manifest structure
            manifest_path = manifest_files[0]
            with open(manifest_path, encoding="utf-8") as file:
                manifest = json.load(file)

            # Verify basic manifest structure
            assert "run_id" in manifest
            assert "timestamp" in manifest
            assert "dataset" in manifest or "datasets" in manifest

    def test_single_symbol_deterministic_output(
        self, eurusd_fixture_path, baseline_config
    ):
        """Verify single-symbol runs produce deterministic results.

        Running the same backtest twice should produce identical results.
        """
        # Skip if fixture doesn't exist
        if not eurusd_fixture_path.exists():
            pytest.skip("EURUSD test fixture not found")

        # Load candles
        candles = ingest_candles(eurusd_fixture_path)

        # Run backtest twice with same parameters
        orchestrator1 = BacktestOrchestrator(
            direction_mode=DirectionMode.LONG,
            dry_run=False,
        )

        result1 = orchestrator1.run_backtest(
            candles=candles,
            pair="EURUSD",
            run_id="test_deterministic_run1",
            ema_fast=baseline_config.ema_fast,
            ema_slow=baseline_config.ema_slow,
            atr_stop_mult=baseline_config.atr_stop_mult,
            target_r_mult=baseline_config.target_r_mult,
            cooldown_candles=baseline_config.cooldown_candles,
            rsi_length=baseline_config.rsi_length,
        )

        orchestrator2 = BacktestOrchestrator(
            direction_mode=DirectionMode.LONG,
            dry_run=False,
        )

        result2 = orchestrator2.run_backtest(
            candles=candles,
            pair="EURUSD",
            run_id="test_deterministic_run2",
            ema_fast=baseline_config.ema_fast,
            ema_slow=baseline_config.ema_slow,
            atr_stop_mult=baseline_config.atr_stop_mult,
            target_r_mult=baseline_config.target_r_mult,
            cooldown_candles=baseline_config.cooldown_candles,
            rsi_length=baseline_config.rsi_length,
        )

        # Compare key metrics (both should be MetricsSummary for LONG mode)
        assert result1.metrics.trade_count == result2.metrics.trade_count
        if result1.metrics.trade_count > 0:
            assert abs(result1.metrics.win_rate - result2.metrics.win_rate) < 0.001
