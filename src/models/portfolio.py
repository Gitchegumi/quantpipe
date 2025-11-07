"""Portfolio entity models for multi-symbol backtesting.

This module defines core entities for portfolio and independent multi-symbol
execution modes, including currency pairs, symbol configurations, and portfolio
parameters.
"""
import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CurrencyPair(BaseModel):
    """Represents a normalized 6-letter FX pair code.

    Attributes:
        code: 6-letter uppercase FX pair code (e.g., 'EURUSD')
        base: First 3 characters (base currency)
        quote: Last 3 characters (quote currency)
    """

    code: str = Field(..., pattern=r"^[A-Z]{6}$")

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        """Validate currency pair code format."""
        if not re.match(r"^[A-Z]{6}$", value):
            raise ValueError(
                "Currency pair code must be 6 uppercase letters (e.g., EURUSD)"
            )
        return value

    @property
    def base(self) -> str:
        """Return base currency (first 3 characters)."""
        return self.code[:3]

    @property
    def quote(self) -> str:
        """Return quote currency (last 3 characters)."""
        return self.code[3:]

    def __str__(self) -> str:
        """Return string representation."""
        return self.code

    def __hash__(self) -> int:
        """Make hashable for use in sets and dict keys."""
        return hash(self.code)


class SymbolConfig(BaseModel):
    """Per-symbol configuration overrides.

    Attributes:
        pair: Currency pair for this configuration
        correlation_threshold_override: Optional override for correlation threshold
        base_weight: Optional base weight for allocation (non-negative)
        enabled: Whether this symbol is enabled for trading
        spread_pips: Optional symbol-specific spread in pips
        commission_rate: Optional symbol-specific commission as fraction
    """

    pair: CurrencyPair
    correlation_threshold_override: Optional[float] = Field(
        default=None, ge=0.0, le=1.0
    )
    base_weight: Optional[float] = Field(default=None, ge=0.0)
    enabled: bool = Field(default=True)
    spread_pips: Optional[float] = Field(default=None, ge=0.0)
    commission_rate: Optional[float] = Field(default=None, ge=0.0)


class PortfolioConfig(BaseModel):
    """Portfolio-level configuration parameters.

    Attributes:
        correlation_threshold_default: Default correlation threshold
        snapshot_interval_candles: Candles between portfolio snapshots
        max_memory_growth_factor: Maximum allowed memory growth multiplier
        abort_on_symbol_failure: Whether to abort on any symbol failure
        allocation_rounding_dp: Decimal places for allocation rounding
    """

    correlation_threshold_default: float = Field(default=0.8, ge=0.0, le=1.0)
    snapshot_interval_candles: int = Field(default=50, ge=1)
    max_memory_growth_factor: float = Field(default=1.5, gt=1.0)
    abort_on_symbol_failure: bool = Field(default=False)
    allocation_rounding_dp: int = Field(default=2, ge=0, le=10)
