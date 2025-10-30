"""
Unit tests for output formatters.

Tests generate_output_filename, format_text_output, and format_json_output.
"""

import json
from datetime import datetime, timezone

import pytest

from src.io.formatters import (
    format_json_output,
    format_text_output,
    generate_output_filename,
)
from src.models.directional import BacktestResult, ConflictEvent
from src.models.core import MetricsSummary
from src.models.enums import DirectionMode, OutputFormat


class TestGenerateOutputFilename:
    """Test cases for generate_output_filename function."""

    def test_long_mode_text_format(self):
        """Verify filename generation for LONG mode with TEXT format."""
        ts = datetime(2025, 1, 15, 14, 30, 45, tzinfo=timezone.utc)
        filename = generate_output_filename(DirectionMode.LONG, OutputFormat.TEXT, ts)

        assert filename == "backtest_long_20250115_143045.txt"

    def test_short_mode_json_format(self):
        """Verify filename generation for SHORT mode with JSON format."""
        ts = datetime(2025, 2, 20, 9, 15, 30, tzinfo=timezone.utc)
        filename = generate_output_filename(DirectionMode.SHORT, OutputFormat.JSON, ts)

        assert filename == "backtest_short_20250220_091530.json"

    def test_both_mode_text_format(self):
        """Verify filename generation for BOTH mode with TEXT format."""
        ts = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        filename = generate_output_filename(DirectionMode.BOTH, OutputFormat.TEXT, ts)

        assert filename == "backtest_both_20251231_235959.txt"

    def test_timestamp_formatting(self):
        """Verify timestamp formatting in filename."""
        ts = datetime(2025, 3, 5, 8, 5, 3, tzinfo=timezone.utc)
        filename = generate_output_filename(DirectionMode.LONG, OutputFormat.TEXT, ts)

        # Check zero-padding
        assert "20250305" in filename
        assert "080503" in filename


class TestFormatTextOutput:
    """Test cases for format_text_output function."""

    @pytest.fixture
    def minimal_result(self):
        """Provide minimal BacktestResult for testing."""
        return BacktestResult(
            run_id="test_run_001",
            direction_mode="LONG",
            start_time=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            data_start_date=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            data_end_date=datetime(2024, 12, 31, 23, 59, tzinfo=timezone.utc),
            total_candles=100000,
            metrics=None,
            signals=None,
            executions=None,
            conflicts=[],
            dry_run=False,
        )

    @pytest.fixture
    def result_with_metrics(self):
        """Provide BacktestResult with metrics for testing."""
        metrics = MetricsSummary(
            trade_count=50,
            win_count=30,
            loss_count=20,
            win_rate=0.6,
            avg_win_r=2.5,
            avg_loss_r=1.0,
            avg_r=0.9,
            expectancy=0.8,
            sharpe_estimate=1.5,
            profit_factor=2.4,
            max_drawdown_r=5.0,
            latency_p95_ms=3.2,
            latency_mean_ms=1.8,
        )

        return BacktestResult(
            run_id="test_run_002",
            direction_mode="SHORT",
            start_time=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            data_start_date=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            data_end_date=datetime(2024, 12, 31, 23, 59, tzinfo=timezone.utc),
            total_candles=50000,
            metrics=metrics,
            signals=None,
            executions=None,
            conflicts=[],
            dry_run=False,
        )

    def test_minimal_result_formatting(self, minimal_result):
        """Verify text formatting for minimal result (no metrics)."""
        text = format_text_output(minimal_result)

        assert "BACKTEST RESULTS" in text
        assert "test_run_001" in text
        assert "LONG" in text
        assert "100000" in text  # total_candles
        assert "(No metrics available)" in text

    def test_result_with_metrics_formatting(self, result_with_metrics):
        """Verify text formatting includes metrics."""
        text = format_text_output(result_with_metrics)

        assert "PERFORMANCE METRICS" in text
        assert "Trades:           50" in text
        assert "Win Rate:         60.00%" in text
        assert "Avg R:            0.90" in text

    def test_dry_run_indicator(self, minimal_result):
        """Verify dry-run indicator appears in output."""
        minimal_result = BacktestResult(
            run_id=minimal_result.run_id,
            direction_mode=minimal_result.direction_mode,
            start_time=minimal_result.start_time,
            end_time=minimal_result.end_time,
            data_start_date=minimal_result.data_start_date,
            data_end_date=minimal_result.data_end_date,
            total_candles=minimal_result.total_candles,
            metrics=minimal_result.metrics,
            signals=minimal_result.signals,
            executions=minimal_result.executions,
            conflicts=minimal_result.conflicts,
            dry_run=True,
        )

        text = format_text_output(minimal_result)

        assert "DRY-RUN MODE" in text
        assert "signals only" in text

    def test_conflicts_formatting(self):
        """Verify conflict formatting in output."""
        conflicts = [
            ConflictEvent(
                timestamp_utc=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
                pair="EURUSD",
                long_signal_id="long_001",
                short_signal_id="short_001",
            ),
            ConflictEvent(
                timestamp_utc=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
                pair="EURUSD",
                long_signal_id="long_002",
                short_signal_id="short_002",
            ),
        ]

        result = BacktestResult(
            run_id="test_run_003",
            direction_mode="BOTH",
            start_time=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            data_start_date=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            data_end_date=datetime(2024, 12, 31, 23, 59, tzinfo=timezone.utc),
            total_candles=10000,
            metrics=None,
            signals=None,
            executions=None,
            conflicts=conflicts,
            dry_run=False,
        )

        text = format_text_output(result)

        assert "SIGNAL CONFLICTS" in text
        assert "Total Conflicts:  2" in text
        assert "long_001" in text
        assert "short_001" in text


class TestFormatJsonOutput:
    """Test cases for format_json_output function."""

    @pytest.fixture
    def minimal_result(self):
        """Provide minimal BacktestResult for testing."""
        return BacktestResult(
            run_id="test_run_json_001",
            direction_mode="LONG",
            start_time=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            data_start_date=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            data_end_date=datetime(2024, 12, 31, 23, 59, tzinfo=timezone.utc),
            total_candles=100000,
            metrics=None,
            signals=None,
            executions=None,
            conflicts=[],
            dry_run=False,
        )

    def test_json_valid_structure(self, minimal_result):
        """Verify JSON output is valid and parseable."""
        json_str = format_json_output(minimal_result)
        data = json.loads(json_str)

        assert data["run_id"] == "test_run_json_001"
        assert data["direction_mode"] == "LONG"
        assert data["total_candles"] == 100000
        assert data["dry_run"] is False

    def test_json_timestamp_format(self, minimal_result):
        """Verify timestamps are ISO 8601 formatted."""
        json_str = format_json_output(minimal_result)
        data = json.loads(json_str)

        assert "2025-01-01T12:00:00+00:00" in data["start_time"]
        assert "2024-01-01T00:00:00+00:00" in data["data_start_date"]

    def test_json_empty_arrays(self, minimal_result):
        """Verify empty conflicts/signals/executions are handled."""
        json_str = format_json_output(minimal_result)
        data = json.loads(json_str)

        assert data["conflicts"] == []
        assert data["signals"] is None
        assert data["executions"] is None
        assert data["metrics"] is None

    def test_json_with_metrics(self):
        """Verify JSON includes metrics when available."""
        metrics = MetricsSummary(
            trade_count=10,
            win_count=6,
            loss_count=4,
            win_rate=0.6,
            avg_win_r=2.0,
            avg_loss_r=1.0,
            avg_r=0.8,
            expectancy=0.7,
            sharpe_estimate=1.2,
            profit_factor=2.0,
            max_drawdown_r=3.0,
            latency_p95_ms=5.0,
            latency_mean_ms=2.5,
        )

        result = BacktestResult(
            run_id="test_run_json_002",
            direction_mode="SHORT",
            start_time=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            data_start_date=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            data_end_date=datetime(2024, 12, 31, 23, 59, tzinfo=timezone.utc),
            total_candles=50000,
            metrics=metrics,
            signals=None,
            executions=None,
            conflicts=[],
            dry_run=False,
        )

        json_str = format_json_output(result)
        data = json.loads(json_str)

        assert data["metrics"]["trade_count"] == 10
        assert data["metrics"]["win_rate"] == 0.6
        assert data["metrics"]["avg_r"] == 0.8
