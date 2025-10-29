"""
Metrics aggregation for backtest performance.

This module computes trading performance metrics from a collection of trade
executions. It provides basic statistics (win rate, average R) and advanced
metrics (expectancy, Sharpe ratio estimate, profit factor, max drawdown).

All metrics handle the zero-trade case gracefully, returning NaN or appropriate
defaults when no trades are executed.
"""

import logging
from typing import Sequence

import numpy as np
from numpy.typing import NDArray

from ..models.core import MetricsSummary, TradeExecution

logger = logging.getLogger(__name__)


def compute_metrics(executions: Sequence[TradeExecution]) -> MetricsSummary:
    """
    Compute comprehensive performance metrics from trade executions.

    Calculates win rate, average R, expectancy, Sharpe ratio estimate,
    profit factor, and maximum drawdown. Handles zero-trade scenario by
    returning NaN for most metrics.

    Args:
        executions: Sequence of completed TradeExecution objects.

    Returns:
        MetricsSummary with computed performance statistics.

    Examples:
        >>> from datetime import datetime, timezone
        >>> from models.core import TradeExecution
        >>> executions = [
        ...     TradeExecution(
        ...         signal_id="sig1",
        ...         open_timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        ...         close_timestamp=datetime(2025, 1, 1, 18, 0, tzinfo=timezone.utc),
        ...         fill_entry_price=1.10000,
        ...         fill_stop_price=1.09800,
        ...         fill_exit_price=1.10400,
        ...         exit_reason="TARGET",
        ...         pnl_r=2.0,
        ...         slippage_pips=0.5,
        ...         execution_costs_pct=0.001
        ...     ),
        ...     TradeExecution(
        ...         signal_id="sig2",
        ...         open_timestamp=datetime(2025, 1, 2, 12, 0, tzinfo=timezone.utc),
        ...         close_timestamp=datetime(2025, 1, 2, 14, 0, tzinfo=timezone.utc),
        ...         fill_entry_price=1.10500,
        ...         fill_stop_price=1.10300,
        ...         fill_exit_price=1.10300,
        ...         exit_reason="STOP",
        ...         pnl_r=-1.0,
        ...         slippage_pips=0.3,
        ...         execution_costs_pct=0.001
        ...     )
        ... ]
        >>> metrics = compute_metrics(executions)
        >>> metrics.trade_count
        2
        >>> metrics.win_rate
        0.5
    """
    trade_count = len(executions)

    # Zero-trade case
    if trade_count == 0:
        logger.warning("No trades to compute metrics from")
        return MetricsSummary(
            trade_count=0,
            win_count=0,
            loss_count=0,
            win_rate=np.nan,
            avg_win_r=np.nan,
            avg_loss_r=np.nan,
            avg_r=np.nan,
            expectancy_r=np.nan,
            sharpe_ratio=np.nan,
            profit_factor=np.nan,
            max_drawdown_r=np.nan,
            avg_latency_ms=np.nan,
            p95_latency_ms=np.nan,
        )

    # Extract PnL in R multiples
    pnl_r_values = np.array([ex.pnl_r for ex in executions], dtype=np.float64)

    # Win/loss counts
    wins = pnl_r_values > 0
    losses = pnl_r_values < 0
    win_count = int(np.sum(wins))
    loss_count = int(np.sum(losses))

    # Win rate
    win_rate = win_count / trade_count if trade_count > 0 else np.nan

    # Average win/loss
    avg_win_r = np.mean(pnl_r_values[wins]) if win_count > 0 else np.nan
    avg_loss_r = np.mean(pnl_r_values[losses]) if loss_count > 0 else np.nan

    # Average R per trade
    avg_r = float(np.mean(pnl_r_values))

    # Expectancy (R)
    expectancy_r = avg_r

    # Sharpe ratio estimate (assuming independent trades)
    sharpe_ratio = (
        float(np.mean(pnl_r_values) / np.std(pnl_r_values))
        if np.std(pnl_r_values) > 0
        else np.nan
    )

    # Profit factor
    total_wins = np.sum(pnl_r_values[wins]) if win_count > 0 else 0.0
    total_losses = abs(np.sum(pnl_r_values[losses])) if loss_count > 0 else 0.0
    profit_factor = (
        float(total_wins / total_losses) if total_losses > 0 else np.inf
    )

    # Maximum drawdown (cumulative R)
    cumulative_r = np.cumsum(pnl_r_values)
    running_max = np.maximum.accumulate(cumulative_r)
    drawdown_r = cumulative_r - running_max
    max_drawdown_r = float(np.min(drawdown_r)) if len(drawdown_r) > 0 else 0.0

    # Latency metrics (placeholder - requires actual latency data)
    avg_latency_ms = np.nan
    p95_latency_ms = np.nan

    metrics = MetricsSummary(
        trade_count=trade_count,
        win_count=win_count,
        loss_count=loss_count,
        win_rate=win_rate,
        avg_win_r=avg_win_r,
        avg_loss_r=avg_loss_r,
        avg_r=avg_r,
        expectancy_r=expectancy_r,
        sharpe_ratio=sharpe_ratio,
        profit_factor=profit_factor,
        max_drawdown_r=max_drawdown_r,
        avg_latency_ms=avg_latency_ms,
        p95_latency_ms=p95_latency_ms,
    )

    logger.info(
        f"Metrics computed: {trade_count} trades, "
        f"win_rate={win_rate:.2%}, "
        f"expectancy={expectancy_r:.2f}R"
    )

    return metrics


def compute_rolling_drawdown(pnl_r_series: NDArray[np.float64]) -> NDArray[np.float64]:
    """
    Compute rolling drawdown curve from PnL series.

    Calculates the drawdown at each point as the difference between cumulative
    PnL and the running maximum. Useful for visualizing drawdown progression.

    Args:
        pnl_r_series: Array of PnL values in R multiples.

    Returns:
        Array of drawdown values (all ≤ 0).

    Examples:
        >>> pnl = np.array([1.0, -0.5, 2.0, -1.0, 0.5])
        >>> dd = compute_rolling_drawdown(pnl)
        >>> dd
        array([ 0. , -1.5,  0. , -3. , -2.5])
    """
    if len(pnl_r_series) == 0:
        return np.array([], dtype=np.float64)

    cumulative = np.cumsum(pnl_r_series)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = cumulative - running_max

    return drawdown


def compute_win_rate(pnl_r_series: NDArray[np.float64]) -> float:
    """
    Compute win rate from PnL series.

    Args:
        pnl_r_series: Array of PnL values in R multiples.

    Returns:
        Win rate as a fraction (0.0 to 1.0), or NaN if no trades.

    Examples:
        >>> pnl = np.array([1.0, -0.5, 2.0, -1.0, 0.5])
        >>> win_rate = compute_win_rate(pnl)
        >>> win_rate
        0.6
    """
    if len(pnl_r_series) == 0:
        return np.nan

    wins = np.sum(pnl_r_series > 0)
    total = len(pnl_r_series)

    return float(wins / total)
