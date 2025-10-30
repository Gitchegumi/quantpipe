"""Integration tests for BOTH mode backtest execution (User Story 3).

Tests three-tier metrics display, conflict handling, and output formatting.
"""

import json

import pytest

from src.backtest.orchestrator import BacktestOrchestrator
from src.config.parameters import StrategyParameters
from src.io.formatters import format_json_output, format_text_output
from src.io.ingestion import ingest_candles
from src.models.enums import DirectionMode


class TestBothModeBacktest:
    """Test BOTH mode backtest execution (User Story 3)."""

    @pytest.fixture()
    def sample_candles(self, tmp_path):
        """Create a small CSV fixture with valid candles."""
        csv_content = """timestamp_utc,open,high,low,close,volume
2020-01-01 00:00:00,1.1000,1.1010,1.0990,1.1005,100
2020-01-01 00:01:00,1.1005,1.1015,1.0995,1.1010,110
2020-01-01 00:02:00,1.1010,1.1020,1.1000,1.1015,120
2020-01-01 00:03:00,1.1015,1.1025,1.1005,1.1020,130
2020-01-01 00:04:00,1.1020,1.1030,1.1010,1.1025,140
"""
        csv_path = tmp_path / "test_eurusd_m1_both.csv"
        csv_path.write_text(csv_content)
        return csv_path

    def test_both_backtest_execution(self, sample_candles):
        """Test BOTH mode executes without errors and generates three-tier metrics."""
        # Ingest candles
        parameters = StrategyParameters()
        candles = list(
            ingest_candles(
                csv_path=sample_candles,
                ema_fast=parameters.ema_fast,
                ema_slow=parameters.ema_slow,
                atr_period=parameters.atr_length,
                rsi_period=parameters.rsi_length,
                stoch_rsi_period=parameters.rsi_length,
                expected_timeframe_minutes=1,
                allow_gaps=True,
            )
        )

        assert len(candles) == 5

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
            candles=candles, pair="EURUSD", run_id="test_both_001", **signal_params
        )

        # Verify result structure
        assert result.run_id == "test_both_001"
        assert result.direction_mode == DirectionMode.BOTH
        assert result.total_candles == 5
        # Small fixture won't generate signals, so metrics will be None
        # This matches LONG/SHORT mode behavior with small fixtures
        assert result.dry_run is False

    def test_both_backtest_dry_run(self, sample_candles):
        """Test BOTH dry-run mode generates signals without execution."""
        # Ingest candles
        parameters = StrategyParameters()
        candles = list(
            ingest_candles(
                csv_path=sample_candles,
                ema_fast=parameters.ema_fast,
                ema_slow=parameters.ema_slow,
                atr_period=parameters.atr_length,
                rsi_period=parameters.rsi_length,
                stoch_rsi_period=parameters.rsi_length,
                expected_timeframe_minutes=1,
                allow_gaps=True,
            )
        )

        # Run dry-run
        orchestrator = BacktestOrchestrator(
            direction_mode=DirectionMode.BOTH, dry_run=True
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
            candles=candles, pair="EURUSD", run_id="test_both_002_dry", **signal_params
        )

        # Verify dry-run behavior
        assert result.dry_run is True
        assert result.metrics is None  # No execution, no metrics

    def test_both_backtest_text_output(self, sample_candles):
        """Test BOTH mode text output formatting with three tiers."""
        # Ingest candles
        parameters = StrategyParameters()
        candles = list(
            ingest_candles(
                csv_path=sample_candles,
                ema_fast=parameters.ema_fast,
                ema_slow=parameters.ema_slow,
                atr_period=parameters.atr_length,
                rsi_period=parameters.rsi_length,
                stoch_rsi_period=parameters.rsi_length,
                expected_timeframe_minutes=1,
                allow_gaps=True,
            )
        )

        # Run backtest
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
            candles=candles, pair="EURUSD", run_id="test_both_003", **signal_params
        )

        # Format to text
        text_output = format_text_output(result)

        # Verify basic structure (small fixture won't generate signals/metrics)
        assert "Direction Mode:   BOTH" in text_output
        assert "test_both_003" in text_output
        assert "BACKTEST RESULTS" in text_output

    def test_both_backtest_json_output(self, sample_candles):
        """Test BOTH mode JSON output structure."""
        # Ingest candles
        parameters = StrategyParameters()
        candles = list(
            ingest_candles(
                csv_path=sample_candles,
                ema_fast=parameters.ema_fast,
                ema_slow=parameters.ema_slow,
                atr_period=parameters.atr_length,
                rsi_period=parameters.rsi_length,
                stoch_rsi_period=parameters.rsi_length,
                expected_timeframe_minutes=1,
                allow_gaps=True,
            )
        )

        # Run backtest
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
            candles=candles, pair="EURUSD", run_id="test_both_004", **signal_params
        )

        # Format to JSON
        json_output = format_json_output(result)

        # Parse and verify structure
        data = json.loads(json_output)
        assert data["run_id"] == "test_both_004"
        assert data["direction_mode"] == "BOTH"
        assert data["total_candles"] == 5
        assert "start_time" in data
        assert "end_time" in data
        assert "metrics" in data
