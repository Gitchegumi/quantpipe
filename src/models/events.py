"""Runtime failure event models for portfolio error handling.

This module defines data structures for logging and tracking runtime failures
during multi-symbol backtesting.
"""
from datetime import UTC, datetime
from typing import Optional, Any

from pydantic import BaseModel, Field

from src.models.portfolio import CurrencyPair


class MarketEvent(BaseModel):
    """Base class for market replay events."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: str

class CandleEvent(MarketEvent):
    """Event emitted when a new candle is processed."""
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    event_type: str = "candle"

class TradeEvent(MarketEvent):
    """Event emitted when a trade is opened or closed."""
    symbol: str
    action: str # "OPEN" or "CLOSE"
    price: float
    side: str # "LONG" or "SHORT"
    pnl_r: Optional[float] = None
    event_type: str = "trade"

class RuntimeFailureEvent(BaseModel):
    """Records a runtime failure for a specific symbol.

    Attributes:
        pair: Currency pair that experienced the failure
        reason: Exception message or failure classification
        timestamp: When the failure occurred
    """

    pair: CurrencyPair
    reason: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def __str__(self) -> str:
        """Return formatted string representation."""
        # pylint: disable=no-member
        return (
            f"RuntimeFailure({self.pair.code} at "
            f"{self.timestamp.isoformat()}: {self.reason})"
        )
