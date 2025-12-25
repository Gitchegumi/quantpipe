"""
Order plan dataclass for complete order specifications.

OrderPlans are produced by the RiskManager from Signals and contain all
information needed to execute a trade: entry, stop, target, and position size.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.signal import Signal


@dataclass(frozen=True)
class OrderPlan:
    """
    Complete order specification output by RiskManager.

    An OrderPlan contains everything needed to execute a trade, including
    entry price, stop-loss, take-profit, and position size. It is produced
    by the RiskManager by applying risk policies to a Signal.

    Attributes:
        signal: Original Signal reference.
        entry_price: Actual entry price for the order.
        stop_price: Initial stop-loss price.
        target_price: Take-profit price, or None for trail-only strategies.
        position_size: Position size in lots.
        stop_policy_type: Name of the stop policy used (e.g., "ATR", "ATR_Trailing").
        is_trailing: Whether the stop updates dynamically.
        trailing_params: Parameters for trailing stop updates (e.g., {"atr_mult": 2.0}).

    Examples:
        >>> from datetime import datetime, timezone
        >>> from src.models.signal import Signal
        >>> signal = Signal(
        ...     symbol="EURUSD",
        ...     direction="LONG",
        ...     timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc)
        ... )
        >>> order = OrderPlan(
        ...     signal=signal,
        ...     entry_price=1.1000,
        ...     stop_price=1.0950,
        ...     target_price=1.1100,
        ...     position_size=0.1,
        ...     stop_policy_type="ATR",
        ...     is_trailing=False
        ... )
        >>> order.position_size
        0.1
    """

    signal: "Signal"
    entry_price: float
    stop_price: float
    target_price: float | None
    position_size: float
    stop_policy_type: str
    is_trailing: bool
    trailing_params: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate order plan fields."""
        if self.position_size <= 0:
            raise ValueError(
                f"Position size must be positive, got {self.position_size}"
            )
        if self.stop_price == self.entry_price:
            raise ValueError("Stop price must differ from entry price")

        # Validate stop direction
        direction = self.signal.direction
        if direction == "LONG" and self.stop_price >= self.entry_price:
            raise ValueError(
                f"LONG stop must be below entry: stop={self.stop_price}, entry={self.entry_price}"
            )
        if direction == "SHORT" and self.stop_price <= self.entry_price:
            raise ValueError(
                f"SHORT stop must be above entry: stop={self.stop_price}, entry={self.entry_price}"
            )

    @property
    def risk_distance(self) -> float:
        """Calculate the absolute distance from entry to stop in price units."""
        return abs(self.entry_price - self.stop_price)

    @property
    def reward_distance(self) -> float | None:
        """Calculate the absolute distance from entry to target in price units."""
        if self.target_price is None:
            return None
        return abs(self.target_price - self.entry_price)

    @property
    def risk_reward_ratio(self) -> float | None:
        """Calculate the reward-to-risk ratio (target distance / stop distance)."""
        if self.target_price is None:
            return None
        return (
            self.reward_distance / self.risk_distance
            if self.risk_distance > 0
            else None
        )
