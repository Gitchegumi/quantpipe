"""
Unit tests for directional backtesting data models.

Tests ConflictEvent, DirectionalMetrics, and BacktestResult data structures.
"""

from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.unit

from src.models.core import MetricsSummary
from src.models.directional import BacktestResult, ConflictEvent, DirectionalMetrics
from src.models.enums import DirectionMode


class TestConflictEvent:
    """Test cases for ConflictEvent model."""

    def test_conflict_event_creation(self):
        """Verify ConflictEvent can be instantiated with required fields."""
        timestamp = datetime(2025, 1, 29, 12, 0, 0, tzinfo=UTC)
        conflict = ConflictEvent(
            timestamp_utc=timestamp,
            pair="EURUSD",
            long_signal_id="abc123",
            short_signal_id="def456",
        )

        assert conflict.timestamp_utc == timestamp
        assert conflict.pair == "EURUSD"
        assert conflict.long_signal_id == "abc123"
        assert conflict.short_signal_id == "def456"

    def test_conflict_event_frozen(self):
        """Verify ConflictEvent is immutable (frozen dataclass)."""
        conflict = ConflictEvent(
            timestamp_utc=datetime.now(UTC),
            pair="USDJPY",
            long_signal_id="xyz789",
            short_signal_id="uvw321",
        )

        with pytest.raises(AttributeError):
            conflict.pair = "GBPUSD"  # type: ignore[misc]


class TestDirectionalMetrics:
    """Test cases for DirectionalMetrics model."""

    @pytest.fixture()
    def sample_metrics(self):
        """Provide sample MetricsSummary instances for testing."""
        long_metrics = MetricsSummary(
            trade_count=10,
            win_count=6,
            loss_count=4,
            win_rate=0.60,
            avg_win_r=2.5,
            avg_loss_r=1.0,
            avg_r=1.5,
            expectancy=0.5,
            sharpe_estimate=1.2,
            profit_factor=2.0,
            max_drawdown_r=3.0,
            latency_p95_ms=3.2,
            latency_mean_ms=1.8,
        )
        short_metrics = MetricsSummary(
            trade_count=8,
            win_count=4,
            loss_count=4,
            win_rate=0.50,
            avg_win_r=2.4,
            avg_loss_r=1.2,
            avg_r=1.2,
            expectancy=0.3,
            sharpe_estimate=0.9,
            profit_factor=1.5,
            max_drawdown_r=2.5,
            latency_p95_ms=2.8,
            latency_mean_ms=1.5,
        )
        combined_metrics = MetricsSummary(
            trade_count=18,
            win_count=10,
            loss_count=8,
            win_rate=0.556,
            avg_win_r=2.45,
            avg_loss_r=1.1,
            avg_r=1.367,
            expectancy=0.417,
            sharpe_estimate=1.05,
            profit_factor=1.78,
            max_drawdown_r=3.0,
            latency_p95_ms=3.0,
            latency_mean_ms=1.65,
        )
        return long_metrics, short_metrics, combined_metrics

    def test_directional_metrics_creation(self, sample_metrics):
        """Verify DirectionalMetrics can be instantiated with three MetricsSummary."""
        long_metrics, short_metrics, combined_metrics = sample_metrics
        dir_metrics = DirectionalMetrics(
            long_only=long_metrics,
            short_only=short_metrics,
            combined=combined_metrics,
        )

        assert dir_metrics.long_only.trade_count == 10
        assert dir_metrics.short_only.trade_count == 8
        assert dir_metrics.combined.trade_count == 18

    def test_directional_metrics_frozen(self, sample_metrics):
        """Verify DirectionalMetrics is immutable (frozen dataclass)."""
        long_metrics, short_metrics, combined_metrics = sample_metrics
        dir_metrics = DirectionalMetrics(
            long_only=long_metrics,
            short_only=short_metrics,
            combined=combined_metrics,
        )

        with pytest.raises(AttributeError):
            dir_metrics.combined = combined_metrics  # type: ignore[misc]


class TestBacktestResult:
    """Test cases for BacktestResult model."""

    @pytest.fixture()
    def sample_result_long(self):
        """Provide sample BacktestResult for LONG mode."""
        metrics = MetricsSummary(
            trade_count=15,
            win_count=9,
            loss_count=6,
            win_rate=0.60,
            avg_win_r=2.3,
            avg_loss_r=0.95,
            avg_r=1.4,
            expectancy=0.45,
            sharpe_estimate=1.1,
            profit_factor=1.9,
            max_drawdown_r=4.0,
            latency_p95_ms=3.5,
            latency_mean_ms=2.0,
        )
        return BacktestResult(
            run_id="20250129_120000_LONG",
            direction_mode=DirectionMode.LONG.value,
            start_time=datetime(2025, 1, 29, 12, 0, 0, tzinfo=UTC),
            end_time=datetime(2025, 1, 29, 12, 5, 30, tzinfo=UTC),
            data_start_date=datetime(2020, 1, 1, tzinfo=UTC),
            data_end_date=datetime(2024, 12, 31, tzinfo=UTC),
            total_candles=100000,
            metrics=metrics,
            signals=None,
            executions=None,
            conflicts=[],
            dry_run=False,
        )

    def test_backtest_result_creation(self, sample_result_long):
        """Verify BacktestResult can be instantiated with required fields."""
        result = sample_result_long

        assert result.run_id == "20250129_120000_LONG"
        assert result.direction_mode == "LONG"
        assert result.total_candles == 100000
        assert isinstance(result.metrics, MetricsSummary)
        assert result.metrics.trade_count == 15
        assert result.dry_run is False

    def test_backtest_result_dry_run_mode(self):
        """Verify BacktestResult supports dry_run flag and None executions."""
        metrics = MetricsSummary(
            trade_count=0,
            win_count=0,
            loss_count=0,
            win_rate=0.0,
            avg_win_r=0.0,
            avg_loss_r=0.0,
            avg_r=0.0,
            expectancy=0.0,
            sharpe_estimate=0.0,
            profit_factor=0.0,
            max_drawdown_r=0.0,
            latency_p95_ms=0.0,
            latency_mean_ms=0.0,
        )
        result = BacktestResult(
            run_id="20250129_120000_DRY",
            direction_mode=DirectionMode.SHORT.value,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            data_start_date=datetime(2020, 1, 1, tzinfo=UTC),
            data_end_date=datetime(2024, 12, 31, tzinfo=UTC),
            total_candles=50000,
            metrics=metrics,
            signals=[],  # Dry-run mode includes signals
            executions=None,  # No executions in dry-run
            conflicts=[],
            dry_run=True,
        )

        assert result.dry_run is True
        assert result.signals == []
        assert result.executions is None

    def test_backtest_result_both_mode_with_conflicts(self):
        """Verify BacktestResult supports BOTH mode with conflicts and DirectionalMetrics."""
        long_metrics = MetricsSummary(
            trade_count=10,
            win_count=6,
            loss_count=4,
            win_rate=0.60,
            avg_win_r=2.5,
            avg_loss_r=1.0,
            avg_r=1.5,
            expectancy=0.5,
            sharpe_estimate=1.2,
            profit_factor=2.0,
            max_drawdown_r=3.0,
            latency_p95_ms=3.2,
            latency_mean_ms=1.8,
        )
        short_metrics = MetricsSummary(
            trade_count=8,
            win_count=4,
            loss_count=4,
            win_rate=0.50,
            avg_win_r=2.4,
            avg_loss_r=1.2,
            avg_r=1.2,
            expectancy=0.3,
            sharpe_estimate=0.9,
            profit_factor=1.5,
            max_drawdown_r=2.5,
            latency_p95_ms=2.8,
            latency_mean_ms=1.5,
        )
        combined_metrics = MetricsSummary(
            trade_count=18,
            win_count=10,
            loss_count=8,
            win_rate=0.556,
            avg_win_r=2.45,
            avg_loss_r=1.1,
            avg_r=1.367,
            expectancy=0.417,
            sharpe_estimate=1.05,
            profit_factor=1.78,
            max_drawdown_r=3.0,
            latency_p95_ms=3.0,
            latency_mean_ms=1.65,
        )
        dir_metrics = DirectionalMetrics(
            long_only=long_metrics,
            short_only=short_metrics,
            combined=combined_metrics,
        )
        conflict = ConflictEvent(
            timestamp_utc=datetime(2023, 5, 15, 14, 30, tzinfo=UTC),
            pair="GBPUSD",
            long_signal_id="signal_long_123",
            short_signal_id="signal_short_456",
        )

        result = BacktestResult(
            run_id="20250129_120000_BOTH",
            direction_mode=DirectionMode.BOTH.value,
            start_time=datetime(2025, 1, 29, 12, 0, 0, tzinfo=UTC),
            end_time=datetime(2025, 1, 29, 12, 10, 45, tzinfo=UTC),
            data_start_date=datetime(2020, 1, 1, tzinfo=UTC),
            data_end_date=datetime(2024, 12, 31, tzinfo=UTC),
            total_candles=150000,
            metrics=dir_metrics,
            signals=None,
            executions=None,
            conflicts=[conflict],
            dry_run=False,
        )

        assert result.direction_mode == "BOTH"
        assert isinstance(result.metrics, DirectionalMetrics)
        assert result.metrics.combined.trade_count == 18
        assert len(result.conflicts) == 1
        assert result.conflicts[0].pair == "GBPUSD"

    def test_backtest_result_frozen(self, sample_result_long):
        """Verify BacktestResult is immutable (frozen dataclass)."""
        result = sample_result_long

        with pytest.raises(AttributeError):
            result.run_id = "modified_id"  # type: ignore[misc]
