"""
Metrics aggregation for backtest performance.

This module computes trading performance metrics from a collection of trade
executions. It provides basic statistics (win rate, average R) and advanced
metrics (expectancy, Sharpe ratio estimate, profit factor, max drawdown).

All metrics handle the zero-trade case gracefully, returning NaN or appropriate
defaults when no trades are executed.

Supports directional metrics for LONG/SHORT/BOTH mode backtesting.
"""

import logging
from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from ..models.core import MetricsSummary, TradeExecution
from ..models.directional import DirectionalMetrics
from ..models.enums import DirectionMode


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
            expectancy=np.nan,
            sharpe_estimate=np.nan,
            profit_factor=np.nan,
            max_drawdown_r=np.nan,
            latency_p95_ms=np.nan,
            latency_mean_ms=np.nan,
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

    # Expectancy (R) - expected value per trade
    expectancy = avg_r

    # Sharpe ratio estimate (assuming independent trades)
    sharpe_estimate = (
        float(np.mean(pnl_r_values) / np.std(pnl_r_values))
        if np.std(pnl_r_values) > 0
        else np.nan
    )

    # Profit factor
    total_wins = np.sum(pnl_r_values[wins]) if win_count > 0 else 0.0
    total_losses = abs(np.sum(pnl_r_values[losses])) if loss_count > 0 else 0.0
    profit_factor = float(total_wins / total_losses) if total_losses > 0 else np.inf

    # Maximum drawdown (cumulative R)
    cumulative_r = np.cumsum(pnl_r_values)
    running_max = np.maximum.accumulate(cumulative_r)
    drawdown_r = cumulative_r - running_max
    max_drawdown_r = float(np.min(drawdown_r)) if len(drawdown_r) > 0 else 0.0

    # Latency metrics (placeholder - requires actual latency data)
    latency_p95_ms = np.nan
    latency_mean_ms = np.nan

    metrics = MetricsSummary(
        trade_count=trade_count,
        win_count=win_count,
        loss_count=loss_count,
        win_rate=win_rate,
        avg_win_r=avg_win_r,
        avg_loss_r=avg_loss_r,
        avg_r=avg_r,
        expectancy=expectancy,
        sharpe_estimate=sharpe_estimate,
        profit_factor=profit_factor,
        max_drawdown_r=max_drawdown_r,
        latency_p95_ms=latency_p95_ms,
        latency_mean_ms=latency_mean_ms,
    )

    logger.info(
        "Metrics computed: %d trades, win_rate=%.2f%%, expectancy=%.2fR",
        trade_count,
        win_rate * 100,
        expectancy,
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


def calculate_metrics(executions: Sequence[TradeExecution]) -> MetricsSummary:
    """
    Alias for compute_metrics for directional backtesting compatibility.

    Args:
        executions: Sequence of completed TradeExecution objects.

    Returns:
        MetricsSummary with computed performance statistics.
    """
    return compute_metrics(executions)


def calculate_directional_metrics(
    executions: Sequence[TradeExecution], direction: DirectionMode
) -> DirectionalMetrics:
    """
    Calculate three-tier metrics for directional backtesting.

    Provides metrics breakdown for LONG-only, SHORT-only, and combined results.
    The tier population depends on the direction mode:
    - LONG mode: long_only and combined are identical (short_only is None)
    - SHORT mode: short_only and combined are identical (long_only is None)
    - BOTH mode: all three tiers populated (requires direction tracking)

    Args:
        executions: Sequence of completed trade executions to analyze.
        direction: Direction mode of the backtest (LONG/SHORT/BOTH).

    Returns:
        DirectionalMetrics with long_only, short_only, and combined metrics.

    Examples:
        >>> metrics = calculate_directional_metrics(executions, DirectionMode.LONG)
        >>> metrics.combined.trade_count
        50
        >>> metrics.long_only.trade_count
        50
        >>> metrics.short_only is None
        True

    Note:
        BOTH mode currently calculates combined metrics only. Full directional
        breakdown requires TradeExecution to include direction field or signal
        tracking mechanism. This is a known limitation to be addressed in
        future iterations.
    """
    logger.info("Calculating directional metrics for mode=%s", direction.value)

    if direction == DirectionMode.LONG:
        combined = calculate_metrics(executions)
        return DirectionalMetrics(
            long_only=combined, short_only=None, combined=combined
        )
    elif direction == DirectionMode.SHORT:
        combined = calculate_metrics(executions)
        return DirectionalMetrics(
            long_only=None, short_only=combined, combined=combined
        )
    else:  # DirectionMode.BOTH
        # Filter executions by direction
        long_executions = [e for e in executions if e.direction == "LONG"]
        short_executions = [e for e in executions if e.direction == "SHORT"]

        long_metrics = calculate_metrics(long_executions) if long_executions else None
        short_metrics = (
            calculate_metrics(short_executions) if short_executions else None
        )
        combined = calculate_metrics(executions)

        return DirectionalMetrics(
            long_only=long_metrics, short_only=short_metrics, combined=combined
        )


def compute_portfolio_metrics(
    aggregated_pnl: float,
    max_drawdown: float,
    runtime_seconds: float,
    strategies_count: int,
    instruments_count: int,
) -> dict:
    """
    Compute portfolio-level performance metrics for multi-strategy runs.

    Calculates portfolio statistics from aggregated results per FR-022.
    Volatility computation is stubbed initially (returns 0.0).

    Args:
        aggregated_pnl: Weighted portfolio PnL.
        max_drawdown: Maximum drawdown percentage (0.0-1.0).
        runtime_seconds: Wall-clock runtime.
        strategies_count: Number of strategies executed.
        instruments_count: Distinct instruments traded.

    Returns:
        Dictionary with portfolio metrics:
            - aggregate_pnl: Total weighted PnL
            - max_drawdown_pct: Maximum portfolio drawdown
            - volatility_annualized: Annualized volatility (stub: 0.0)
            - runtime_seconds: Execution time
            - strategies_count: Strategy count
            - instruments_count: Instrument count

    Examples:
        >>> metrics = compute_portfolio_metrics(
        ...     aggregated_pnl=1250.0,
        ...     max_drawdown=0.08,
        ...     runtime_seconds=12.5,
        ...     strategies_count=2,
        ...     instruments_count=1
        ... )
        >>> metrics["aggregate_pnl"]
        1250.0
        >>> metrics["max_drawdown_pct"]
        0.08
    """
    # Stub volatility (future: compute from PnL time series)
    volatility_annualized = 0.0

    portfolio_metrics = {
        "aggregate_pnl": aggregated_pnl,
        "max_drawdown_pct": max_drawdown,
        "volatility_annualized": volatility_annualized,
        "runtime_seconds": runtime_seconds,
        "strategies_count": strategies_count,
        "instruments_count": instruments_count,
    }

    logger.info(
        "Portfolio metrics: pnl=%.4f drawdown=%.4f strategies=%d",
        aggregated_pnl,
        max_drawdown,
        strategies_count,
    )

    return portfolio_metrics
