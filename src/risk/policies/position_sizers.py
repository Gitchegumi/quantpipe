"""
Position sizing implementations.

Contains the PositionSizer protocol and concrete implementations for
different position sizing strategies.
"""

from typing import Protocol


class PositionSizer(Protocol):
    """
    Protocol for position size calculation strategies.

    PositionSizer defines the interface for calculating position sizes
    based on risk parameters and stop distance.

    Methods:
        size: Calculate position size in lots.
    """

    def size(
        self,
        entry_price: float,
        stop_price: float,
        portfolio_balance: float,
        risk_pct: float,
        pip_value: float = 10.0,
        lot_step: float = 0.01,
        max_size: float = 10.0,
    ) -> float:
        """
        Calculate position size in lots.

        Args:
            entry_price: Trade entry price.
            stop_price: Stop-loss price.
            portfolio_balance: Current portfolio balance.
            risk_pct: Risk percentage per trade (e.g., 0.25 for 0.25%).
            pip_value: Value of 1 pip per lot in base currency.
            lot_step: Minimum lot size increment.
            max_size: Maximum allowed position size.

        Returns:
            Position size in lots, rounded to lot_step.

        Raises:
            ValueError: If inputs are invalid (e.g., zero stop distance).
        """
        ...
