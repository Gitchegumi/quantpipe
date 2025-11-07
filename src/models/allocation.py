"""Allocation request and response models for portfolio capital allocation.

This module defines the interface for the allocation engine, including
request/response structures for capital allocation across symbols.
"""
from datetime import UTC, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from src.models.portfolio import CurrencyPair


class AllocationRequest(BaseModel):
    """Request for capital allocation across symbols.

    Attributes:
        symbols: List of currency pairs to allocate across
        volatility: Per-symbol volatility metrics (key: pair code)
        correlation_matrix: Pairwise correlations (key: sorted pair token)
        base_weights: Optional base allocation weights (must sum to ~1.0)
        capital: Total capital to allocate
    """

    symbols: list[CurrencyPair] = Field(..., min_length=1)
    volatility: dict[str, float]
    correlation_matrix: dict[str, float] = Field(default_factory=dict)
    base_weights: Optional[dict[str, float]] = None
    capital: float = Field(..., gt=0.0)

    @field_validator("volatility")
    @classmethod
    def validate_volatility(cls, value: dict[str, float]) -> dict[str, float]:
        """Validate all volatility values are positive."""
        for symbol, vol in value.items():
            if vol <= 0:
                raise ValueError(
                    f"Volatility must be positive for symbol {symbol}"
                )
        return value

    @field_validator("base_weights")
    @classmethod
    def validate_weights(
        cls, value: Optional[dict[str, float]]
    ) -> Optional[dict[str, float]]:
        """Validate base weights sum to approximately 1.0."""
        if value is None:
            return None

        total = sum(value.values())
        if not 0.99 <= total <= 1.01:
            raise ValueError(
                f"Base weights must sum to approximately 1.0, got {total:.4f}"
            )

        for symbol, weight in value.items():
            if weight < 0:
                raise ValueError(
                    f"Base weight must be non-negative for symbol {symbol}"
                )

        return value


class AllocationResponse(BaseModel):
    """Response with allocated capital per symbol.

    Attributes:
        allocations: Per-symbol capital allocation (sum equals request.capital)
        diversification_ratio: Ratio measuring portfolio diversification
        correlation_penalty: Aggregate correlation penalty factor
        timestamp: Allocation computation timestamp
    """

    allocations: dict[str, float]
    diversification_ratio: float = Field(..., ge=0.0, le=1.0)
    correlation_penalty: float = Field(default=0.0, ge=0.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("allocations")
    @classmethod
    def validate_allocations(cls, value: dict[str, float]) -> dict[str, float]:
        """Validate all allocations are non-negative."""
        for symbol, allocation in value.items():
            if allocation < 0:
                raise ValueError(
                    f"Allocation must be non-negative for symbol {symbol}"
                )
        return value
