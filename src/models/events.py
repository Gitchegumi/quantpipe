"""Runtime failure event models for portfolio error handling.

This module defines data structures for logging and tracking runtime failures
during multi-symbol backtesting.
"""
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from src.models.portfolio import CurrencyPair


class CandleEvent(BaseModel):
    """Single candle data point for streaming replay."""

    timestamp: datetime = Field(..., description="Candle open time")
    open: float = Field(..., description="Open price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Close price")
    volume: float = Field(default=0.0, description="Volume")

    class Config:
        """Pydantic configuration."""

        frozen = True


class TradeEvent(BaseModel):
    """Trade signal event emitted during replay."""

    timestamp: datetime = Field(..., description="Signal time")
    pair: CurrencyPair = Field(..., description="Currency pair")
    signal: str = Field(..., description="Signal type (buy/sell/hold)")
    price: float = Field(..., description="Entry/exit price")
    size: float = Field(default=0.0, description="Position size")
    reason: str = Field(default="", description="Signal rationale")

    class Config:
        """Pydantic configuration."""

        frozen = True


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
