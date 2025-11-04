"""Risk limits model with validation.

This module defines RiskLimits, a pydantic model capturing per-strategy
and global portfolio risk thresholds enforced during backtest execution.

Per FR-003 and FR-015, the system supports layered risk controls:
per-strategy limits plus optional global portfolio drawdown threshold.
"""

from pydantic import BaseModel, Field, field_validator


class RiskLimits(BaseModel):
    """
    Risk thresholds for strategy execution control.

    Attributes:
        max_position_size: Maximum position size in base units/lots.
        max_drawdown_pct: Maximum drawdown percentage (0.0-1.0) before halt.
        daily_loss_threshold: Optional daily loss limit (absolute value).
        max_open_trades: Maximum number of concurrent open positions.
        stop_on_breach: Whether to halt strategy on first breach.

    Examples:
        >>> limits = RiskLimits(
        ...     max_position_size=100000.0,
        ...     max_drawdown_pct=0.10,
        ...     daily_loss_threshold=500.0,
        ...     max_open_trades=3
        ... )
        >>> limits.max_drawdown_pct
        0.1
        >>> limits.stop_on_breach
        True
    """

    max_position_size: float | None = Field(
        default=None, ge=0.0, description="Maximum position size"
    )
    max_drawdown_pct: float = Field(
        ..., ge=0.0, le=1.0, description="Maximum drawdown percentage"
    )
    daily_loss_threshold: float | None = Field(
        default=None, ge=0.0, description="Daily loss limit (absolute)"
    )
    max_open_trades: int = Field(
        default=1, ge=1, description="Maximum concurrent open positions"
    )
    stop_on_breach: bool = Field(
        default=True, description="Halt strategy on first breach"
    )

    @field_validator("max_drawdown_pct")
    @classmethod
    def drawdown_within_range(cls, v: float) -> float:
        """Ensure drawdown percentage is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("max_drawdown_pct must be between 0.0 and 1.0")
        return v

    @field_validator("max_position_size")
    @classmethod
    def position_size_positive(cls, v: float | None) -> float | None:
        """Ensure position size is positive if provided."""
        if v is not None and v < 0.0:
            raise ValueError("max_position_size must be non-negative")
        return v

    class Config:
        """Pydantic model configuration."""

        frozen = False
        validate_assignment = True


__all__ = ["RiskLimits"]
