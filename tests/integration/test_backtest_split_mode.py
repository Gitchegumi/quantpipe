"""Integration tests for split-mode backtesting.

Feature: 004-timeseries-dataset
Task: T033 - Integration test for backtest split mode
"""

# pylint: disable=unused-import

from pathlib import Path
from datetime import UTC, datetime
import pytest

from src.backtest.orchestrator import BacktestOrchestrator
from src.config.parameters import StrategyParameters
from src.data_io.partition_loader import (
    check_partitions_exist,
    load_both_partitions,
    load_partition,
)
from src.models.directional import PartitionMetrics, SplitModeResult, PartitionType
from src.models.enums import DirectionMode


class TestBacktestSplitMode:
    """Test split-mode backtesting with test/validation partitions."""

    def test_check_partitions_exist(self, tmp_path):
        """Test partition existence check."""
        # Create mock partitions
        symbol_path = tmp_path / "eurusd"
        symbol_path.mkdir()

        test_csv = symbol_path / "test.csv"
        validation_csv = symbol_path / "validation.csv"
        metadata_json = symbol_path / "metadata.json"

        test_csv.write_text("timestamp,open,high,low,close,volume\n")
        validation_csv.write_text("timestamp,open,high,low,close,volume\n")
        metadata_json.write_text("{}")

        status = check_partitions_exist("eurusd", tmp_path)

        assert status["test"] is True
        assert status["validation"] is True
        assert status["metadata"] is True

    def test_check_partitions_missing(self, tmp_path):
        """Test partition existence check with missing files."""
        status = check_partitions_exist("eurusd", tmp_path)

        assert status["test"] is False
        assert status["validation"] is False
        assert status["metadata"] is False

    def test_load_partition_file_not_found(self, tmp_path):
        """Test load_partition raises FileNotFoundError when partition missing."""

        with pytest.raises(FileNotFoundError, match="Partition file not found"):
            load_partition("eurusd", "test", tmp_path)

    def test_load_partition_invalid_type(self, tmp_path):
        """Test load_partition raises ValueError for invalid partition type."""

        with pytest.raises(ValueError, match="Invalid partition type"):
            load_partition("eurusd", "invalid", tmp_path)

    def test_split_mode_result_creation(self):
        """Test SplitModeResult dataclass creation."""
        from src.models.core import MetricsSummary

        test_metrics = MetricsSummary(
            trade_count=50,
            win_count=30,
            loss_count=20,
            win_rate=0.60,
            avg_win_r=2.0,
            avg_loss_r=-1.0,
            avg_r=0.8,
            expectancy=0.8,
            sharpe_estimate=1.2,
            profit_factor=2.0,
            max_drawdown_r=3.0,
            latency_p95_ms=10.0,
            latency_mean_ms=5.0,
        )

        val_metrics = MetricsSummary(
            trade_count=25,
            win_count=12,
            loss_count=13,
            win_rate=0.48,
            avg_win_r=1.8,
            avg_loss_r=-1.2,
            avg_r=0.3,
            expectancy=0.3,
            sharpe_estimate=0.6,
            profit_factor=1.2,
            max_drawdown_r=2.5,
            latency_p95_ms=12.0,
            latency_mean_ms=6.0,
        )

        start_time = datetime(2025, 1, 30, 10, 0, tzinfo=UTC)
        end_time = datetime(2025, 1, 30, 10, 5, tzinfo=UTC)

        split_result = SplitModeResult(
            run_id="split_long_eurusd_20250130_100000",
            symbol="eurusd",
            direction_mode="LONG",
            start_time=start_time,
            end_time=end_time,
            test_partition=PartitionMetrics(
                partition="test",
                metrics=test_metrics,
            ),
            validation_partition=PartitionMetrics(
                partition="validation",
                metrics=val_metrics,
            ),
        )

        assert split_result.symbol == "eurusd"
        assert split_result.direction_mode == "LONG"
        assert split_result.test_partition.partition == "test"
        assert split_result.validation_partition.partition == "validation"
        assert split_result.test_partition.metrics.trade_count == 50
        assert split_result.validation_partition.metrics.trade_count == 25

    def test_partition_metrics_wraps_summary(self):
        """Test PartitionMetrics wraps MetricsSummary correctly."""
        from src.models.core import MetricsSummary

        metrics = MetricsSummary(
            trade_count=100,
            win_count=60,
            loss_count=40,
            win_rate=0.60,
            avg_win_r=2.0,
            avg_loss_r=-1.0,
            avg_r=0.8,
            expectancy=0.8,
            sharpe_estimate=1.2,
            profit_factor=2.0,
            max_drawdown_r=3.0,
            latency_p95_ms=10.0,
            latency_mean_ms=5.0,
        )

        partition_result = PartitionMetrics(
            partition="test",
            metrics=metrics,
        )

        assert partition_result.partition == "test"
        assert partition_result.metrics.trade_count == 100
        assert partition_result.metrics.win_rate == 0.60

    def test_split_mode_formatters_exist(self):
        """Test split-mode formatters are available."""
        from src.data_io.formatters import format_split_mode_text, format_split_mode_json

        assert callable(format_split_mode_text)
        assert callable(format_split_mode_json)

    def test_partition_loader_functions_exist(self):
        """Test partition loader functions are available."""

        assert callable(check_partitions_exist)
        assert callable(load_partition)
        assert callable(load_both_partitions)

    def test_split_mode_cli_exists(self):
        """Test split-mode CLI script exists."""
        cli_path = Path("src/cli/run_split_backtest.py")
        assert cli_path.exists()

    def test_split_mode_models_imported(self):
        """Test split-mode models can be imported."""

        assert PartitionMetrics is not None
        assert SplitModeResult is not None
        # PartitionType is a Literal type alias, just check it's defined
        assert PartitionType is not None
