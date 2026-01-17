"""Strategy configuration model with validation.

This module defines StrategyConfig, a pydantic model providing validation
and serialization for per-strategy parameter sets and metadata.

Per FR-009, strategies support runtime configuration overrides without
affecting defaults of other strategies.
"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrategyConfig(BaseModel):
    """
    Configuration and metadata for a single strategy instance.

    Attributes:
        name: Unique strategy identifier matching registry entry.
        parameters: Arbitrary parameter mapping (strategy-specific).
        risk_limits: Optional dict of risk thresholds (e.g., max_position_size).
        tags: Classification tags for filtering.
        version: Semantic version string for reproducibility.
        enabled: Whether strategy is active for this run.

    Examples:
        >>> config = StrategyConfig(
        ...     name="alpha",
        ...     parameters={"ema_fast": 20, "ema_slow": 50},
        ...     risk_limits={"max_drawdown_pct": 0.10},
        ...     tags=["trend", "pullback"],
        ...     version="1.0.0"
        ... )
        >>> config.name
        'alpha'
        >>> config.enabled
        True
    """

    name: str = Field(..., min_length=1, description="Strategy identifier")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Strategy-specific parameters"
    )
    risk_limits: dict[str, float] | None = Field(
        default=None, description="Per-strategy risk thresholds"
    )
    tags: list[str] = Field(default_factory=list, description="Classification tags")
    version: str = Field(default="0.0.0", description="Semantic version")
    enabled: bool = Field(default=True, description="Active flag for this run")

    @field_validator("name")
    @classmethod
    def name_must_be_non_empty(cls, v: str) -> str:
        """Validate strategy name is not empty or whitespace-only."""
        if not v or not v.strip():
            raise ValueError("Strategy name cannot be empty or whitespace")
        return v.strip()

    @field_validator("version")
    @classmethod
    def version_basic_format(cls, v: str) -> str:
        """Basic semantic version format check (x.y.z)."""
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("Version must be semantic format x.y.z")
        for part in parts:
            if not part.isdigit():
                raise ValueError("Version components must be numeric")
        return v

    model_config = ConfigDict(frozen=False, validate_assignment=True)


__all__ = ["StrategyConfig"]
