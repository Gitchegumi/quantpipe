"""
Stop-loss policy implementations.

Contains the StopPolicy protocol and concrete implementations for
different stop-loss calculation strategies.
"""

from typing import Protocol


class StopPolicy(Protocol):
    """
    Protocol for stop-loss calculation strategies.

    StopPolicy defines the interface for calculating initial stop-loss prices
    and updating stops for trailing strategies. All stop policy implementations
    must conform to this protocol.

    Methods:
        initial_stop: Calculate initial stop-loss price at trade entry.
        update_stop: Calculate updated stop for trailing policies.
    """

    def initial_stop(
        self,
        entry_price: float,
        direction: str,
        context: dict,
    ) -> float:
        """
        Calculate initial stop-loss price.

        Args:
            entry_price: Trade entry price.
            direction: Trade direction ("LONG" or "SHORT").
            context: Market context containing ATR, high, low, close.

        Returns:
            Initial stop-loss price.

        Raises:
            RiskConfigurationError: If required context data is missing.
        """
        ...

    def update_stop(
        self,
        current_stop: float,
        entry_price: float,
        direction: str,
        market: dict,
    ) -> float:
        """
        Calculate updated stop for trailing policies.

        For non-trailing policies, this should return current_stop unchanged.
        For trailing policies, this should return a new stop that only moves
        in the favorable direction (never widens risk).

        Args:
            current_stop: Current stop-loss price.
            entry_price: Original entry price.
            direction: Trade direction ("LONG" or "SHORT").
            market: Market data containing high, low, close, ATR.

        Returns:
            Updated stop-loss price (may be same as current_stop).
        """
        ...


class RiskConfigurationError(Exception):
    """Raised when risk configuration is invalid or required data is missing."""

    pass
