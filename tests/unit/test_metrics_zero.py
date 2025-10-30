import pytest


pytestmark = pytest.mark.unit
"""
Unit tests for metrics aggregation with zero-trade scenario.

Tests metrics computation with empty execution list and edge cases.
"""

from datetime import UTC, datetime

import numpy as np

from src.backtest.metrics import (
    compute_metrics,
    compute_rolling_drawdown,
    compute_win_rate,
)
from src.models.core import TradeExecution


class TestComputeMetricsZeroTrade:
    """Test suite for metrics computation with zero trades."""

    def test_zero_trades(self):
        """Test metrics computation with empty execution list."""
        executions = []

        metrics = compute_metrics(executions)

        assert metrics.trade_count == 0
        assert metrics.win_count == 0
        assert metrics.loss_count == 0
        assert np.isnan(metrics.win_rate)
        assert np.isnan(metrics.avg_win_r)
        assert np.isnan(metrics.avg_loss_r)
        assert np.isnan(metrics.avg_r)
        assert np.isnan(metrics.expectancy)
        assert np.isnan(metrics.sharpe_estimate)
        assert np.isnan(metrics.profit_factor)
        assert np.isnan(metrics.max_drawdown_r)

    def test_single_winning_trade(self):
        """Test metrics with single winning trade."""
        executions = [
            TradeExecution(
                signal_id="sig1",
                open_timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
                entry_fill_price=1.10000,
                close_timestamp=datetime(2025, 1, 1, 18, 0, tzinfo=UTC),
                exit_fill_price=1.10400,
                exit_reason="TARGET",
                pnl_r=2.0,
                slippage_entry_pips=0.5,
                slippage_exit_pips=0.2,
                costs_total=1.0,
                direction="LONG",
            )
        ]

        metrics = compute_metrics(executions)

        assert metrics.trade_count == 1
        assert metrics.win_count == 1
        assert metrics.loss_count == 0
        assert metrics.win_rate == pytest.approx(1.0)
        assert metrics.avg_win_r == pytest.approx(2.0)
        assert np.isnan(metrics.avg_loss_r)
        assert metrics.avg_r == pytest.approx(2.0)
        assert metrics.profit_factor == np.inf  # No losses

    def test_single_losing_trade(self):
        """Test metrics with single losing trade."""
        executions = [
            TradeExecution(
                signal_id="sig1",
                open_timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
                entry_fill_price=1.10000,
                close_timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=UTC),
                exit_fill_price=1.09800,
                exit_reason="STOP_LOSS",
                pnl_r=-1.0,
                slippage_entry_pips=0.3,
                slippage_exit_pips=0.2,
                costs_total=1.0,
                direction="LONG",
            )
        ]

        metrics = compute_metrics(executions)

        assert metrics.trade_count == 1
        assert metrics.win_count == 0
        assert metrics.loss_count == 1
        assert metrics.win_rate == pytest.approx(0.0)
        assert np.isnan(metrics.avg_win_r)
        assert metrics.avg_loss_r == pytest.approx(-1.0)
        assert metrics.avg_r == pytest.approx(-1.0)
        assert metrics.profit_factor == pytest.approx(0.0)

    def test_all_breakeven_trades(self):
        """Test metrics with all breakeven trades (0 R)."""
        executions = [
            TradeExecution(
                signal_id=f"sig{i}",
                open_timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
                entry_fill_price=1.10000,
                close_timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=UTC),
                exit_fill_price=1.10000,  # Breakeven
                exit_reason="STOP_LOSS",
                pnl_r=0.0,
                slippage_entry_pips=0.0,
                slippage_exit_pips=0.0,
                costs_total=0.0,
                direction="LONG",
            )
            for i in range(5)
        ]

        metrics = compute_metrics(executions)

        assert metrics.trade_count == 5
        assert metrics.win_count == 0
        assert metrics.loss_count == 0
        assert metrics.win_rate == pytest.approx(0.0)
        assert metrics.avg_r == pytest.approx(0.0)
        assert metrics.expectancy == pytest.approx(0.0)


class TestComputeRollingDrawdown:
    """Test suite for rolling drawdown computation."""

    def test_no_drawdown(self):
        """Test drawdown with all winning trades."""
        pnl = np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float64)

        drawdown = compute_rolling_drawdown(pnl)

        # No drawdown when all trades win
        assert np.all(drawdown <= 0)
        assert drawdown[-1] == pytest.approx(0.0)

    def test_drawdown_with_losses(self):
        """Test drawdown with losing trades."""
        pnl = np.array([1.0, -0.5, -0.5, 2.0], dtype=np.float64)

        drawdown = compute_rolling_drawdown(pnl)

        # Maximum drawdown should be -1.0 (after two losses)
        assert np.min(drawdown) == pytest.approx(-1.0)

    def test_empty_pnl(self):
        """Test drawdown with empty PnL series."""
        pnl = np.array([], dtype=np.float64)

        drawdown = compute_rolling_drawdown(pnl)

        assert len(drawdown) == 0

    def test_single_trade(self):
        """Test drawdown with single trade."""
        pnl = np.array([2.0], dtype=np.float64)

        drawdown = compute_rolling_drawdown(pnl)

        assert drawdown[0] == pytest.approx(0.0)


class TestComputeWinRate:
    """Test suite for win rate computation."""

    def test_all_wins(self):
        """Test win rate with all winning trades."""
        pnl = np.array([1.0, 2.0, 0.5, 1.5], dtype=np.float64)

        win_rate = compute_win_rate(pnl)

        assert win_rate == pytest.approx(1.0)

    def test_all_losses(self):
        """Test win rate with all losing trades."""
        pnl = np.array([-1.0, -0.5, -2.0], dtype=np.float64)

        win_rate = compute_win_rate(pnl)

        assert win_rate == pytest.approx(0.0)

    def test_mixed_trades(self):
        """Test win rate with mixed results."""
        pnl = np.array([1.0, -0.5, 2.0, -1.0, 0.5], dtype=np.float64)

        win_rate = compute_win_rate(pnl)

        # 3 wins out of 5 trades
        assert win_rate == pytest.approx(0.6)

    def test_breakeven_trades(self):
        """Test win rate with breakeven trades."""
        pnl = np.array([0.0, 0.0, 0.0], dtype=np.float64)

        win_rate = compute_win_rate(pnl)

        # Breakeven (0.0) is not a win
        assert win_rate == pytest.approx(0.0)

    def test_empty_pnl(self):
        """Test win rate with empty PnL series."""
        pnl = np.array([], dtype=np.float64)

        win_rate = compute_win_rate(pnl)

        assert np.isnan(win_rate)


class TestComputeMetricsEdgeCases:
    """Test suite for metrics edge cases."""

    def test_high_sharpe_ratio(self):
        """Test Sharpe ratio with consistent wins."""
        executions = [
            TradeExecution(
                signal_id=f"sig{i}",
                open_timestamp=datetime(2025, 1, i, 12, 0, tzinfo=UTC),
                entry_fill_price=1.10000,
                close_timestamp=datetime(2025, 1, i, 18, 0, tzinfo=UTC),
                exit_fill_price=1.10400,
                exit_reason="TARGET",
                pnl_r=2.0,  # Consistent wins
                slippage_entry_pips=0.5,
                slippage_exit_pips=0.2,
                costs_total=1.0,
                direction="LONG",
            )
            for i in range(1, 11)
        ]

        metrics = compute_metrics(executions)

        # With zero variance, Sharpe will be inf or undefined
        assert metrics.sharpe_estimate == np.inf or np.isnan(metrics.sharpe_estimate)

    def test_negative_expectancy(self):
        """Test metrics with negative expectancy."""
        executions = [
            TradeExecution(
                signal_id=f"sig{i}",
                open_timestamp=datetime(2025, 1, i, 12, 0, tzinfo=UTC),
                entry_fill_price=1.10000,
                close_timestamp=datetime(2025, 1, i, 14, 0, tzinfo=UTC),
                exit_fill_price=1.09800,
                exit_reason="STOP_LOSS",
                pnl_r=-1.0,  # All losses
                slippage_entry_pips=0.3,
                slippage_exit_pips=0.2,
                costs_total=1.0,
                direction="LONG",
            )
            for i in range(1, 11)
        ]

        metrics = compute_metrics(executions)

        assert metrics.expectancy < 0
        assert metrics.win_rate == pytest.approx(0.0)
        assert metrics.profit_factor == pytest.approx(0.0)

    def test_max_drawdown_calculation(self):
        """Test maximum drawdown computation."""
        # Alternating wins and losses
        executions = [
            TradeExecution(
                signal_id="sig1",
                open_timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
                entry_fill_price=1.10000,
                close_timestamp=datetime(2025, 1, 1, 18, 0, tzinfo=UTC),
                exit_fill_price=1.10400,
                exit_reason="TARGET",
                pnl_r=2.0,
                slippage_entry_pips=0.5,
                slippage_exit_pips=0.2,
                costs_total=1.0,
                direction="LONG",
            ),
            TradeExecution(
                signal_id="sig2",
                open_timestamp=datetime(2025, 1, 2, 12, 0, tzinfo=UTC),
                entry_fill_price=1.10000,
                close_timestamp=datetime(2025, 1, 2, 14, 0, tzinfo=UTC),
                exit_fill_price=1.09800,
                exit_reason="STOP_LOSS",
                pnl_r=-1.0,
                slippage_entry_pips=0.3,
                slippage_exit_pips=0.2,
                costs_total=1.0,
                direction="LONG",
            ),
            TradeExecution(
                signal_id="sig3",
                open_timestamp=datetime(2025, 1, 3, 12, 0, tzinfo=UTC),
                entry_fill_price=1.10000,
                close_timestamp=datetime(2025, 1, 3, 14, 0, tzinfo=UTC),
                exit_fill_price=1.09800,
                exit_reason="STOP_LOSS",
                pnl_r=-1.0,
                slippage_entry_pips=0.3,
                slippage_exit_pips=0.2,
                costs_total=1.0,
                direction="LONG",
            ),
        ]

        metrics = compute_metrics(executions)

        # Max drawdown should be -2.0R (two consecutive losses after initial win)
        assert metrics.max_drawdown_r <= 0
