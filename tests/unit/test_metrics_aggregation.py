"""
Unit tests for metrics aggregation functions.

Tests calculate_metrics, calculate_directional_metrics, and edge cases
like empty executions.
"""

from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.unit

from src.backtest.metrics import calculate_directional_metrics, calculate_metrics
from src.models.core import TradeExecution
from src.models.enums import DirectionMode


class TestCalculateMetrics:
    """Test cases for calculate_metrics function."""

    def test_empty_executions_returns_zero_metrics(self):
        """Verify empty executions list returns zero/NaN metrics."""
        metrics = calculate_metrics([])

        assert metrics.trade_count == 0
        assert metrics.win_count == 0
        assert metrics.loss_count == 0

    def test_single_winning_trade(self):
        """Verify metrics for single winning trade."""
        executions = [
            TradeExecution(
                signal_id="sig1",
                open_timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
                entry_fill_price=1.1000,
                close_timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=UTC),
                exit_fill_price=1.1020,
                exit_reason="TARGET",
                pnl_r=2.0,
                slippage_entry_pips=0.1,
                slippage_exit_pips=0.1,
                costs_total=1.0,
            )
        ]

        metrics = calculate_metrics(executions)

        assert metrics.trade_count == 1
        assert metrics.win_count == 1
        assert metrics.loss_count == 0
        assert metrics.win_rate == 1.0
        assert metrics.avg_r == 2.0

    def test_single_losing_trade(self):
        """Verify metrics for single losing trade."""
        executions = [
            TradeExecution(
                signal_id="sig1",
                open_timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
                entry_fill_price=1.1000,
                close_timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=UTC),
                exit_fill_price=1.0990,
                exit_reason="STOP_LOSS",
                pnl_r=-1.0,
                slippage_entry_pips=0.1,
                slippage_exit_pips=0.1,
                costs_total=1.0,
            )
        ]

        metrics = calculate_metrics(executions)

        assert metrics.trade_count == 1
        assert metrics.win_count == 0
        assert metrics.loss_count == 1
        assert metrics.win_rate == 0.0
        assert metrics.avg_r == -1.0

    def test_mixed_trades(self):
        """Verify metrics for mix of winning and losing trades."""
        executions = [
            TradeExecution(
                signal_id="sig1",
                open_timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
                entry_fill_price=1.1000,
                close_timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=UTC),
                exit_fill_price=1.1020,
                exit_reason="TARGET",
                pnl_r=2.0,
                slippage_entry_pips=0.1,
                slippage_exit_pips=0.1,
                costs_total=1.0,
            ),
            TradeExecution(
                signal_id="sig2",
                open_timestamp=datetime(2025, 1, 2, 12, 0, tzinfo=UTC),
                entry_fill_price=1.1050,
                close_timestamp=datetime(2025, 1, 2, 14, 0, tzinfo=UTC),
                exit_fill_price=1.1040,
                exit_reason="STOP_LOSS",
                pnl_r=-1.0,
                slippage_entry_pips=0.1,
                slippage_exit_pips=0.1,
                costs_total=1.0,
            ),
            TradeExecution(
                signal_id="sig3",
                open_timestamp=datetime(2025, 1, 3, 12, 0, tzinfo=UTC),
                entry_fill_price=1.1030,
                close_timestamp=datetime(2025, 1, 3, 14, 0, tzinfo=UTC),
                exit_fill_price=1.1050,
                exit_reason="TARGET",
                pnl_r=2.0,
                slippage_entry_pips=0.1,
                slippage_exit_pips=0.1,
                costs_total=1.0,
            ),
        ]

        metrics = calculate_metrics(executions)

        assert metrics.trade_count == 3
        assert metrics.win_count == 2
        assert metrics.loss_count == 1
        assert metrics.win_rate == pytest.approx(2 / 3, rel=1e-3)
        assert metrics.avg_r == pytest.approx(1.0, rel=1e-3)  # (2 + -1 + 2) / 3


class TestCalculateDirectionalMetrics:
    """Test cases for calculate_directional_metrics function."""

    @pytest.fixture()
    def sample_executions(self):
        """Provide sample executions for testing."""
        return [
            TradeExecution(
                signal_id="sig1",
                open_timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
                entry_fill_price=1.1000,
                close_timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=UTC),
                exit_fill_price=1.1020,
                exit_reason="TARGET",
                pnl_r=2.0,
                slippage_entry_pips=0.1,
                slippage_exit_pips=0.1,
                costs_total=1.0,
            ),
            TradeExecution(
                signal_id="sig2",
                open_timestamp=datetime(2025, 1, 2, 12, 0, tzinfo=UTC),
                entry_fill_price=1.1050,
                close_timestamp=datetime(2025, 1, 2, 14, 0, tzinfo=UTC),
                exit_fill_price=1.1040,
                exit_reason="STOP_LOSS",
                pnl_r=-1.0,
                slippage_entry_pips=0.1,
                slippage_exit_pips=0.1,
                costs_total=1.0,
            ),
        ]

    def test_long_mode_metrics(self, sample_executions):
        """Verify LONG mode populates long_only and combined (identical)."""
        metrics = calculate_directional_metrics(sample_executions, DirectionMode.LONG)

        assert metrics.long_only is not None
        assert metrics.short_only is None
        assert metrics.combined is not None
        assert metrics.long_only.trade_count == 2
        assert metrics.combined.trade_count == 2
        assert metrics.long_only.trade_count == metrics.combined.trade_count

    def test_short_mode_metrics(self, sample_executions):
        """Verify SHORT mode populates short_only and combined (identical)."""
        metrics = calculate_directional_metrics(sample_executions, DirectionMode.SHORT)

        assert metrics.long_only is None
        assert metrics.short_only is not None
        assert metrics.combined is not None
        assert metrics.short_only.trade_count == 2
        assert metrics.combined.trade_count == 2
        assert metrics.short_only.trade_count == metrics.combined.trade_count

    def test_both_mode_metrics(self, sample_executions):
        """Verify BOTH mode calculates combined metrics (direction breakdown pending)."""
        metrics = calculate_directional_metrics(sample_executions, DirectionMode.BOTH)

        # Current implementation: combined only (direction filtering TODO)
        assert metrics.long_only is None
        assert metrics.short_only is None
        assert metrics.combined is not None
        assert metrics.combined.trade_count == 2

    def test_empty_executions_long_mode(self):
        """Verify empty executions in LONG mode."""
        metrics = calculate_directional_metrics([], DirectionMode.LONG)

        assert metrics.long_only is not None
        assert metrics.long_only.trade_count == 0
        assert metrics.combined.trade_count == 0
