"""
Take-profit policy implementations.

Contains the TakeProfitPolicy protocol and concrete implementations for
different take-profit calculation strategies.
"""

from typing import Protocol


class TakeProfitPolicy(Protocol):
    """
    Protocol for take-profit calculation strategies.

    TakeProfitPolicy defines the interface for calculating take-profit prices.
    Implementations may return None to indicate no take-profit (trail-only).

    Methods:
        initial_tp: Calculate initial take-profit price.
    """

    def initial_tp(
        self,
        entry_price: float,
        stop_price: float,
        direction: str,
        context: dict,
    ) -> float | None:
        """
        Calculate take-profit price.

        Args:
            entry_price: Trade entry price.
            stop_price: Stop-loss price (used for risk-multiple calculations).
            direction: Trade direction ("LONG" or "SHORT").
            context: Market context (may include ATR, volatility, etc.).

        Returns:
            Take-profit price, or None for trail-only strategies.
        """
        ...
