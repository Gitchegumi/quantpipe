"""
Lightweight trade signal dataclass.

Signals contain only direction and entry information - no risk management data.
Risk policies are applied separately by the RiskManager to produce OrderPlans.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class Signal:
    """
    Lightweight signal emitted by strategies containing only direction and entry information.

    Signals are decoupled from risk management - they contain no stop-loss, take-profit,
    or position size information. The RiskManager transforms Signals into OrderPlans
    by applying configured risk policies.

    Attributes:
        symbol: Trading pair symbol (e.g., "EURUSD").
        direction: Trade direction - "LONG" or "SHORT".
        timestamp: Signal generation time (UTC, timezone-aware).
        entry_hint: Optional suggested entry price. If None, market price is used.
        metadata: Strategy-specific tags and context (e.g., {"strategy": "trend_pullback"}).

    Examples:
        >>> from datetime import datetime, timezone
        >>> signal = Signal(
        ...     symbol="EURUSD",
        ...     direction="LONG",
        ...     timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ...     entry_hint=1.1000,
        ...     metadata={"strategy": "trend_pullback", "tags": ["pullback"]}
        ... )
        >>> signal.direction
        'LONG'
    """

    symbol: str
    direction: Literal["LONG", "SHORT"]
    timestamp: datetime
    entry_hint: float | None = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate signal fields."""
        if not self.symbol:
            raise ValueError("Symbol must be non-empty string")
        if self.direction not in ("LONG", "SHORT"):
            raise ValueError(
                f"Direction must be 'LONG' or 'SHORT', got '{self.direction}'"
            )
        if self.timestamp.tzinfo is None:
            raise ValueError("Timestamp must be timezone-aware (UTC)")
