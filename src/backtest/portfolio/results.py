"""Results aggregation for multi-symbol backtests.

This module provides utilities for aggregating and summarizing results
from independent multi-symbol backtest runs.
"""

import logging
from typing import Optional

from src.models.directional import BacktestResult

logger = logging.getLogger(__name__)


class MultiSymbolResultsAggregator:
    """Aggregates results from multiple independent symbol backtests.

    Computes cross-symbol statistics while maintaining individual symbol
    result integrity.
    """

    def __init__(self, results: dict[str, BacktestResult]):
        """Initialize aggregator with symbol results.

        Args:
            results: Dictionary mapping symbol codes to BacktestResult
        """
        self.results = results
        self.symbols = list(results.keys())

    def _get_trade_count(self, result: BacktestResult) -> int:
        """Extract trade count from BacktestResult metrics.

        Handles both MetricsSummary (LONG/SHORT) and DirectionalMetrics (BOTH).

        Args:
            result: BacktestResult to extract trade count from

        Returns:
            Number of trades executed
        """
        if hasattr(result.metrics, "combined"):
            # DirectionalMetrics (BOTH mode)
            return result.metrics.combined.trade_count
        # MetricsSummary (LONG/SHORT mode)
        return result.metrics.trade_count

    def _get_win_rate(self, result: BacktestResult) -> float:
        """Extract win rate from BacktestResult metrics.

        Handles both MetricsSummary (LONG/SHORT) and DirectionalMetrics (BOTH).

        Args:
            result: BacktestResult to extract win rate from

        Returns:
            Win rate as fraction (0.0 to 1.0)
        """
        if hasattr(result.metrics, "combined"):
            # DirectionalMetrics (BOTH mode)
            return result.metrics.combined.win_rate
        # MetricsSummary (LONG/SHORT mode)
        return result.metrics.win_rate

    def get_total_trades(self) -> int:
        """Get total number of trades across all symbols.

        Returns:
            Sum of trades across all symbols
        """
        return sum(self._get_trade_count(r) for r in self.results.values())

    def get_average_win_rate(self) -> float:
        """Get average win rate across symbols with trades.

        Only includes symbols that had at least one trade.

        Returns:
            Average win rate (0.0 if no trades)
        """
        win_rates = [
            self._get_win_rate(r)
            for r in self.results.values()
            if self._get_trade_count(r) > 0
        ]
        if not win_rates:
            return 0.0
        return sum(win_rates) / len(win_rates)

    def get_total_pnl(self) -> float:
        """Get total P&L across all symbols.

        Sums final balance deltas (final_balance - initial_capital).

        Returns:
            Total P&L across all symbols
        """
        total_pnl = 0.0
        for result in self.results.values():
            # Assuming BacktestResult has final_balance and initial_capital
            if hasattr(result, "final_balance"):
                pnl = result.final_balance - getattr(result, "initial_capital", 10000.0)
                total_pnl += pnl
        return total_pnl

    def get_symbol_summary(self, symbol: str) -> Optional[dict]:
        """Get summary statistics for a specific symbol.

        Args:
            symbol: Symbol code to summarize

        Returns:
            Dictionary with symbol statistics, or None if not found
        """
        if symbol not in self.results:
            return None

        result = self.results[symbol]
        trade_count = self._get_trade_count(result)
        win_rate = self._get_win_rate(result) if trade_count > 0 else 0.0

        return {
            "symbol": symbol,
            "total_trades": trade_count,
            "win_rate": win_rate,
            "final_balance": getattr(result, "final_balance", 0.0),
        }

    def get_aggregate_summary(self) -> dict:
        """Get aggregate summary across all symbols.

        Returns:
            Dictionary with aggregate statistics
        """
        return {
            "total_symbols": len(self.symbols),
            "total_trades": self.get_total_trades(),
            "average_win_rate": self.get_average_win_rate(),
            "total_pnl": self.get_total_pnl(),
            "symbols": self.symbols,
        }

    def get_per_symbol_summary(self) -> dict[str, dict]:
        """Get summary for each symbol individually.

        Returns:
            Dictionary mapping symbol codes to their summaries
        """
        return {symbol: self.get_symbol_summary(symbol) for symbol in self.symbols}

    def format_summary_text(self) -> str:
        """Format aggregate summary as human-readable text.

        Returns:
            Formatted text summary
        """
        summary = self.get_aggregate_summary()
        lines = []

        lines.append("=" * 60)
        lines.append("INDEPENDENT MULTI-SYMBOL BACKTEST SUMMARY")
        lines.append("=" * 60)
        lines.append("")

        lines.append(f"Total Symbols: {summary['total_symbols']}")
        lines.append(f"Total Trades: {summary['total_trades']}")
        lines.append(f"Average Win Rate: {summary['average_win_rate'] * 100:.2f}%")
        lines.append(f"Total P&L: ${summary['total_pnl']:.2f}")
        lines.append("")

        lines.append("PER-SYMBOL BREAKDOWN")
        lines.append("-" * 60)

        for symbol in sorted(self.symbols):
            symbol_summary = self.get_symbol_summary(symbol)
            if symbol_summary:
                lines.append(
                    f"{symbol}: {symbol_summary['total_trades']} trades, "
                    f"{symbol_summary['win_rate'] * 100:.2f}% win rate, "
                    f"${symbol_summary['final_balance']:.2f} final"
                )

        lines.append("=" * 60)
        return "\n".join(lines)
