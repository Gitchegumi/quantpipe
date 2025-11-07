"""Runtime failure event models for portfolio error handling.

This module defines data structures for logging and tracking runtime failures
during multi-symbol backtesting.
"""
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from src.models.portfolio import CurrencyPair


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
