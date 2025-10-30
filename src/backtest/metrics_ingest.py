"""
Metrics ingestion for tracking trade executions during backtest runs.

This module maintains running aggregates of trade performance metrics as
executions complete, enabling real-time monitoring and final summary generation.
"""

import logging
from collections.abc import Sequence

from ..models.core import MetricsSummary, TradeExecution


logger = logging.getLogger(__name__)


class MetricsIngestor:
    """
    Accumulates trade executions to compute summary statistics.

    Tracks wins, losses, PnL, drawdown, and other metrics incrementally
    as trades complete during a backtest run.

    Attributes:
        executions: List of completed trade executions.
        total_trades: Count of completed trades.
        winning_trades: Count of trades with pnl_r > 0.
        losing_trades: Count of trades with pnl_r < 0.
        breakeven_trades: Count of trades with pnl_r == 0.
        total_pnl_r: Cumulative PnL in R-multiples.
        peak_balance_r: Peak balance in R-multiples (for drawdown).
        current_balance_r: Current balance in R-multiples.
        max_drawdown_r: Maximum drawdown in R-multiples.

    Examples:
        >>> ingestor = MetricsIngestor()
        >>> ingestor.ingest(execution1)
        >>> ingestor.ingest(execution2)
        >>> summary = ingestor.get_summary()
        >>> summary.win_rate_pct
        60.0
        >>> summary.expectancy
        0.5
    """

    def __init__(self) -> None:
        """Initialize empty metrics accumulator."""
        self.executions: list[TradeExecution] = []
        self.total_trades: int = 0
        self.winning_trades: int = 0
        self.losing_trades: int = 0
        self.breakeven_trades: int = 0
        self.total_pnl_r: float = 0.0
        self.peak_balance_r: float = 0.0
        self.current_balance_r: float = 0.0
        self.max_drawdown_r: float = 0.0

    def ingest(self, execution: TradeExecution) -> None:
        """
        Add a completed trade execution to the metrics accumulator.

        Updates all running statistics incrementally.

        Args:
            execution: Completed trade execution to add.

        Examples:
            >>> from models.core import TradeExecution
            >>> execution = TradeExecution(pnl_r=1.5, ...)
            >>> ingestor = MetricsIngestor()
            >>> ingestor.ingest(execution)
            >>> ingestor.total_trades
            1
            >>> ingestor.winning_trades
            1
        """
        self.executions.append(execution)
        self.total_trades += 1

        # Classify trade
        if execution.pnl_r > 0:
            self.winning_trades += 1
        elif execution.pnl_r < 0:
            self.losing_trades += 1
        else:
            self.breakeven_trades += 1

        # Update PnL and drawdown
        self.total_pnl_r += execution.pnl_r
        self.current_balance_r = self.total_pnl_r

        if self.current_balance_r > self.peak_balance_r:
            self.peak_balance_r = self.current_balance_r

        current_drawdown = self.peak_balance_r - self.current_balance_r
        if current_drawdown > self.max_drawdown_r:
            self.max_drawdown_r = current_drawdown

        logger.debug(
            "Ingested execution: signal_id=%s..., pnl_r=%.2fR, total_trades=%d",
            execution.signal_id[:16],
            execution.pnl_r,
            self.total_trades,
        )

    def get_summary(self) -> MetricsSummary:
        """
        Generate MetricsSummary from accumulated executions.

        Returns:
            MetricsSummary with all computed metrics.

        Examples:
            >>> ingestor = MetricsIngestor()
            >>> # ... ingest trades ...
            >>> summary = ingestor.get_summary()
            >>> summary.total_trades
            10
        """
        if self.total_trades == 0:
            # Return zero metrics
            return MetricsSummary(
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

        # Calculate win rate
        win_rate_pct = (self.winning_trades / self.total_trades) * 100.0

        # Calculate expectancy (average R per trade)
        expectancy = self.total_pnl_r / self.total_trades

        # Calculate profit factor (gross wins / gross losses)
        gross_wins = sum(e.pnl_r for e in self.executions if e.pnl_r > 0)
        gross_losses = abs(sum(e.pnl_r for e in self.executions if e.pnl_r < 0))
        profit_factor = gross_wins / gross_losses if gross_losses > 0 else 0.0

        # Estimate Sharpe ratio (simplified: mean/std of R returns)
        if self.total_trades > 1:
            pnl_returns = [e.pnl_r for e in self.executions]
            mean_return = sum(pnl_returns) / len(pnl_returns)
            variance = sum((r - mean_return) ** 2 for r in pnl_returns) / (
                len(pnl_returns) - 1
            )
            std_dev = variance**0.5
            sharpe_estimate = mean_return / std_dev if std_dev > 0 else 0.0
        else:
            sharpe_estimate = 0.0

        # Calculate avg win/loss
        avg_win_r = (
            sum(e.pnl_r for e in self.executions if e.pnl_r > 0) / self.winning_trades
            if self.winning_trades > 0
            else 0.0
        )
        avg_loss_r = (
            abs(sum(e.pnl_r for e in self.executions if e.pnl_r < 0))
            / self.losing_trades
            if self.losing_trades > 0
            else 0.0
        )
        avg_r = self.total_pnl_r / self.total_trades if self.total_trades > 0 else 0.0

        summary = MetricsSummary(
            trade_count=self.total_trades,
            win_count=self.winning_trades,
            loss_count=self.losing_trades,
            win_rate=win_rate_pct / 100.0,  # Convert to 0.0-1.0
            avg_win_r=avg_win_r,
            avg_loss_r=avg_loss_r,
            avg_r=avg_r,
            expectancy=expectancy,
            sharpe_estimate=sharpe_estimate,
            profit_factor=profit_factor,
            max_drawdown_r=self.max_drawdown_r,
            latency_p95_ms=0.0,  # TODO: implement latency tracking
            latency_mean_ms=0.0,
        )

        logger.info(
            "Metrics summary: trade_count=%d, win_rate=%.1f%%, expectancy=%.2fR",
            summary.trade_count,
            summary.win_rate * 100,
            summary.expectancy,
        )

        return summary

    def reset(self) -> None:
        """
        Reset all accumulated metrics to zero.

        Examples:
            >>> ingestor = MetricsIngestor()
            >>> ingestor.ingest(execution)
            >>> ingestor.reset()
            >>> ingestor.total_trades
            0
        """
        self.executions.clear()
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.breakeven_trades = 0
        self.total_pnl_r = 0.0
        self.peak_balance_r = 0.0
        self.current_balance_r = 0.0
        self.max_drawdown_r = 0.0
        logger.debug("Metrics ingestor reset")


def compute_trade_duration_stats(
    executions: Sequence[TradeExecution],
) -> dict[str, float]:
    """
    Calculate trade duration statistics.

    Args:
        executions: Completed trade executions.

    Returns:
        Dictionary with 'mean_hours', 'median_hours', 'max_hours' keys.

    Examples:
        >>> executions = [...]
        >>> stats = compute_trade_duration_stats(executions)
        >>> stats['mean_hours']
        12.5
    """
    if not executions:
        return {
            "mean_hours": 0.0,
            "median_hours": 0.0,
            "max_hours": 0.0,
        }

    durations_hours = [
        (e.close_timestamp - e.open_timestamp).total_seconds() / 3600
        for e in executions
    ]

    durations_hours.sort()
    mean_hours = sum(durations_hours) / len(durations_hours)
    median_hours = durations_hours[len(durations_hours) // 2]
    max_hours = max(durations_hours)

    return {
        "mean_hours": mean_hours,
        "median_hours": median_hours,
        "max_hours": max_hours,
    }
