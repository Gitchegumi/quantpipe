"""Risk isolation utilities for independent multi-symbol execution.

This module provides utilities to ensure risk events in one symbol do not
affect other symbols during independent multi-symbol backtesting.
"""
import logging
from typing import Optional

from src.models.events import RuntimeFailureEvent
from src.models.portfolio import CurrencyPair

logger = logging.getLogger(__name__)


class RiskIsolationTracker:
    """Tracks and manages risk isolation for independent symbol execution.

    Ensures that risk breaches or failures in one symbol do not propagate
    to other symbols in the same multi-symbol run.
    """

    def __init__(self):
        """Initialize risk isolation tracker."""
        self._isolated_symbols: set[str] = set()
        self._failure_events: list[RuntimeFailureEvent] = []
        self._risk_breaches: dict[str, list[str]] = {}

    def isolate_symbol(
        self, pair: CurrencyPair, reason: str
    ) -> RuntimeFailureEvent:
        """Mark a symbol as isolated due to failure.

        Args:
            pair: Currency pair to isolate
            reason: Reason for isolation

        Returns:
            RuntimeFailureEvent recording the isolation
        """
        self._isolated_symbols.add(pair.code)
        event = RuntimeFailureEvent(pair=pair, reason=reason)
        self._failure_events.append(event)

        logger.warning(
            "Symbol %s isolated: %s",
            pair.code,
            reason,
        )

        return event

    def record_risk_breach(
        self, pair: CurrencyPair, breach_type: str
    ) -> None:
        """Record a risk limit breach for a symbol.

        Args:
            pair: Currency pair that breached
            breach_type: Type of breach (e.g., 'max_drawdown', 'position_size')
        """
        if pair.code not in self._risk_breaches:
            self._risk_breaches[pair.code] = []

        self._risk_breaches[pair.code].append(breach_type)

        logger.info(
            "Risk breach recorded for %s: %s",
            pair.code,
            breach_type,
        )

    def is_symbol_isolated(self, pair: CurrencyPair) -> bool:
        """Check if a symbol has been isolated.

        Args:
            pair: Currency pair to check

        Returns:
            True if symbol is isolated, False otherwise
        """
        return pair.code in self._isolated_symbols

    def get_isolated_symbols(self) -> list[str]:
        """Get list of isolated symbol codes.

        Returns:
            List of symbol codes that have been isolated
        """
        return list(self._isolated_symbols)

    def get_failure_events(self) -> list[RuntimeFailureEvent]:
        """Get all recorded failure events.

        Returns:
            List of RuntimeFailureEvent objects
        """
        return self._failure_events.copy()

    def get_risk_breaches(
        self, pair: Optional[CurrencyPair] = None
    ) -> dict[str, list[str]] | list[str]:
        """Get risk breach records.

        Args:
            pair: Optional currency pair to get breaches for

        Returns:
            If pair is None, returns dict mapping all symbols to breach lists
            If pair is provided, returns list of breaches for that symbol
        """
        if pair is None:
            return self._risk_breaches.copy()

        return self._risk_breaches.get(pair.code, [])

    def get_summary(self) -> dict:
        """Get summary of risk isolation activity.

        Returns:
            Dictionary with isolation statistics
        """
        total_breaches = sum(
            len(breaches) for breaches in self._risk_breaches.values()
        )

        return {
            "isolated_symbols_count": len(self._isolated_symbols),
            "isolated_symbols": list(self._isolated_symbols),
            "total_failure_events": len(self._failure_events),
            "total_risk_breaches": total_breaches,
            "symbols_with_breaches": list(self._risk_breaches.keys()),
        }

    def clear(self) -> None:
        """Clear all isolation and breach records.

        Used primarily for testing or between runs.
        """
        self._isolated_symbols.clear()
        self._failure_events.clear()
        self._risk_breaches.clear()
