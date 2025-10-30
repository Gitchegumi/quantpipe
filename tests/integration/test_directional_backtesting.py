"""
Integration tests for directional backtesting (Phase 3).

Tests the end-to-end flow:
- CLI argument parsing
- Candle ingestion
- Orchestrator execution
- Metrics calculation
- Output file generation
"""

import json

import pytest

from src.backtest.orchestrator import BacktestOrchestrator
from src.config.parameters import StrategyParameters
from src.io.formatters import format_json_output, format_text_output
from src.io.ingestion import ingest_candles
from src.models.enums import DirectionMode


class TestLongModeBacktest:
    """Test LONG-only backtest execution (User Story 1)."""

    @pytest.fixture
    def sample_candles(self, tmp_path):
        """Create a small CSV fixture with valid candles."""
        csv_content = """timestamp_utc,open,high,low,close,volume
2020-01-01 00:00:00,1.1000,1.1010,1.0990,1.1005,100
2020-01-01 00:01:00,1.1005,1.1015,1.0995,1.1010,110
2020-01-01 00:02:00,1.1010,1.1020,1.1000,1.1015,120
2020-01-01 00:03:00,1.1015,1.1025,1.1005,1.1020,130
2020-01-01 00:04:00,1.1020,1.1030,1.1010,1.1025,140
"""
        csv_path = tmp_path / "test_eurusd_m1.csv"
        csv_path.write_text(csv_content)
        return csv_path

    def test_long_backtest_execution(self, sample_candles):
        """Test LONG mode executes without errors."""
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
            direction_mode=DirectionMode.LONG, dry_run=False
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
            candles=candles, pair="EURUSD", run_id="test_long_001", **signal_params
        )

        # Verify result structure
        assert result.run_id == "test_long_001"
        assert result.direction_mode == DirectionMode.LONG.value
        assert result.total_candles == 5
        assert result.data_start_date == candles[0].timestamp_utc
        assert result.data_end_date == candles[-1].timestamp_utc
        assert result.dry_run is False
        # Note: metrics may be None if no signals generated (data-dependent)

    def test_long_backtest_dry_run(self, sample_candles):
        """Test LONG mode dry-run (signals only, no execution)."""
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

        orchestrator = BacktestOrchestrator(
            direction_mode=DirectionMode.LONG, dry_run=True
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
            candles=candles, pair="EURUSD", run_id="test_long_dry_001", **signal_params
        )

        # Dry-run specific checks
        assert result.dry_run is True
        assert result.metrics is None  # No metrics in dry-run
        assert result.executions is None  # No executions in dry-run
        # signals may be empty list if no signals generated

    def test_long_backtest_text_output(self, sample_candles):
        """Test text output formatting for LONG mode."""
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
            candles=candles, pair="EURUSD", run_id="test_long_002", **signal_params
        )

        # Format as text
        text_output = format_text_output(result)

        # Verify key sections present
        assert "BACKTEST RESULTS" in text_output
        assert "RUN METADATA" in text_output
        assert "DATA RANGE" in text_output
        assert "PERFORMANCE METRICS" in text_output
        assert "Run ID:" in text_output
        assert "test_long_002" in text_output
        assert "Direction Mode:" in text_output
        assert "LONG" in text_output

    def test_long_backtest_json_output(self, sample_candles):
        """Test JSON output formatting for LONG mode."""
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
            candles=candles, pair="EURUSD", run_id="test_long_003", **signal_params
        )

        # Format as JSON
        json_output = format_json_output(result)

        # Parse and verify structure
        data = json.loads(json_output)
        assert data["run_id"] == "test_long_003"
        assert data["direction_mode"] == "LONG"
        assert data["total_candles"] == 5
        assert "start_time" in data
        assert "end_time" in data
        assert "metrics" in data


class TestShortModeBacktest:
    """Test SHORT-only backtest execution (User Story 2)."""

    @pytest.fixture
    def sample_candles(self, tmp_path):
        """Create a small CSV fixture with valid candles."""
        csv_content = """timestamp_utc,open,high,low,close,volume
2020-01-01 00:00:00,1.1000,1.1010,1.0990,1.1005,100
2020-01-01 00:01:00,1.1005,1.1015,1.0995,1.1010,110
2020-01-01 00:02:00,1.1010,1.1020,1.1000,1.1015,120
2020-01-01 00:03:00,1.1015,1.1025,1.1005,1.1020,130
2020-01-01 00:04:00,1.1020,1.1030,1.1010,1.1025,140
"""
        csv_path = tmp_path / "test_eurusd_m1_short.csv"
        csv_path.write_text(csv_content)
        return csv_path

    def test_short_backtest_execution(self, sample_candles):
        """Test SHORT mode executes without errors."""
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
            direction_mode=DirectionMode.SHORT, dry_run=False
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
            candles=candles, pair="EURUSD", run_id="test_short_001", **signal_params
        )

        # Verify result structure
        assert result.run_id == "test_short_001"
        assert result.direction_mode == DirectionMode.SHORT.value
        assert result.total_candles == 5
        assert result.data_start_date == candles[0].timestamp_utc
        assert result.data_end_date == candles[-1].timestamp_utc
        assert result.dry_run is False

    def test_short_backtest_dry_run(self, sample_candles):
        """Test SHORT mode dry-run (signals only, no execution)."""
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

        orchestrator = BacktestOrchestrator(
            direction_mode=DirectionMode.SHORT, dry_run=True
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
            candles=candles, pair="EURUSD", run_id="test_short_dry_001", **signal_params
        )

        # Dry-run specific checks
        assert result.dry_run is True
        assert result.metrics is None
        assert result.executions is None

    def test_short_backtest_text_output(self, sample_candles):
        """Test text output formatting for SHORT mode."""
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

        orchestrator = BacktestOrchestrator(
            direction_mode=DirectionMode.SHORT, dry_run=False
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
            candles=candles, pair="EURUSD", run_id="test_short_002", **signal_params
        )

        # Format as text
        text_output = format_text_output(result)

        # Verify key sections present
        assert "BACKTEST RESULTS" in text_output
        assert "RUN METADATA" in text_output
        assert "DATA RANGE" in text_output
        assert "PERFORMANCE METRICS" in text_output
        assert "Run ID:" in text_output
        assert "test_short_002" in text_output
        assert "Direction Mode:" in text_output
        assert "SHORT" in text_output

    def test_short_backtest_json_output(self, sample_candles):
        """Test JSON output formatting for SHORT mode."""
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

        orchestrator = BacktestOrchestrator(
            direction_mode=DirectionMode.SHORT, dry_run=False
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
            candles=candles, pair="EURUSD", run_id="test_short_003", **signal_params
        )

        # Format as JSON
        json_output = format_json_output(result)

        # Parse and verify structure
        data = json.loads(json_output)
        assert data["run_id"] == "test_short_003"
        assert data["direction_mode"] == "SHORT"
        assert data["total_candles"] == 5
        assert "start_time" in data
        assert "end_time" in data
        assert "metrics" in data


class TestJsonOutputAllModes:
    """Test JSON output format for all direction modes (T127)."""

    @pytest.fixture
    def sample_candles(self, tmp_path):
        """Create a small CSV fixture with valid candles."""
        csv_content = """timestamp_utc,open,high,low,close,volume
2020-01-01 00:00:00,1.1000,1.1010,1.0990,1.1005,100
2020-01-01 00:01:00,1.1005,1.1015,1.0995,1.1010,110
2020-01-01 00:02:00,1.1010,1.1020,1.1000,1.1015,120
2020-01-01 00:03:00,1.1015,1.1025,1.1005,1.1020,130
2020-01-01 00:04:00,1.1020,1.1030,1.1010,1.1025,140
"""
        csv_path = tmp_path / "test_eurusd_m1_json.csv"
        csv_path.write_text(csv_content)
        return csv_path

    def test_json_output_long_mode(self, sample_candles):
        """Test JSON output for LONG mode."""
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
            candles=candles, pair="EURUSD", run_id="test_json_long_001", **signal_params
        )

        # Format as JSON
        json_output = format_json_output(result)

        # Verify it's valid JSON
        data = json.loads(json_output)

        # Verify required fields
        assert data["run_id"] == "test_json_long_001"
        assert data["direction_mode"] == "LONG"
        assert data["total_candles"] == 5
        assert data["dry_run"] is False

        # Verify timestamp format (ISO 8601)
        assert "T" in data["start_time"]
        assert "+" in data["start_time"] or "Z" in data["start_time"]

        # Verify structure
        assert "conflicts" in data
        assert isinstance(data["conflicts"], list)

    def test_json_output_short_mode(self, sample_candles):
        """Test JSON output for SHORT mode."""
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

        orchestrator = BacktestOrchestrator(
            direction_mode=DirectionMode.SHORT, dry_run=False
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
            run_id="test_json_short_001",
            **signal_params,
        )

        # Format as JSON
        json_output = format_json_output(result)

        # Verify it's valid JSON
        data = json.loads(json_output)

        # Verify required fields
        assert data["run_id"] == "test_json_short_001"
        assert data["direction_mode"] == "SHORT"
        assert data["total_candles"] == 5
        assert data["dry_run"] is False

    def test_json_output_both_mode(self, sample_candles):
        """Test JSON output for BOTH mode with directional metrics."""
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
            candles=candles, pair="EURUSD", run_id="test_json_both_001", **signal_params
        )

        # Format as JSON
        json_output = format_json_output(result)

        # Verify it's valid JSON
        data = json.loads(json_output)

        # Verify required fields
        assert data["run_id"] == "test_json_both_001"
        assert data["direction_mode"] == "BOTH"
        assert data["total_candles"] == 5
        assert data["dry_run"] is False

        # Verify three-tier metrics structure for BOTH mode
        # (may be None if no trades generated from 5 candles)
        assert "metrics" in data
