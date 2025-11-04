"""Structured metrics schema for multi-strategy portfolio aggregation.

This module defines the schema and validation for aggregated portfolio metrics
emitted during multi-strategy backtest runs per FR-022.

The schema captures combined performance, exposure, weighting, risk events,
and reproducibility linkage as specified in research.md.
"""

# pylint: disable=unused-import

from typing import Any
from pydantic import BaseModel, Field


class StructuredMetrics(BaseModel):
    """
    Aggregated portfolio metrics schema for multi-strategy runs.

    Attributes:
        strategies_count: Number of strategies executed.
        instruments_count: Distinct instruments across all strategies.
        runtime_seconds: Wall-clock runtime from start to aggregation completion.
        aggregate_pnl: Weighted portfolio PnL (base currency).
        max_drawdown_pct: Maximum portfolio drawdown percentage.
        volatility_annualized: Annualized return volatility (stub initial).
        net_exposure_by_instrument: Mapping instrument -> net exposure value.
        weights_applied: Final normalized weights used.
        global_drawdown_limit: Configured global drawdown threshold if provided.
        global_abort_triggered: True if global abort conditions fired.
        risk_breaches: Strategy identifiers with local risk breaches.
        deterministic_run_id: Stable hash linking inputs & manifest.
        manifest_hash_ref: RunManifest reference hash for reproducibility.
        correlation_status: 'deferred' until correlation implemented.

    Examples:
        >>> metrics = StructuredMetrics(
        ...     strategies_count=2,
        ...     instruments_count=1,
        ...     runtime_seconds=12.5,
        ...     aggregate_pnl=1250.0,
        ...     max_drawdown_pct=0.08,
        ...     volatility_annualized=0.15,
        ...     net_exposure_by_instrument={"EURUSD": 0.025},
        ...     weights_applied=[0.6, 0.4],
        ...     global_drawdown_limit=0.15,
        ...     global_abort_triggered=False,
        ...     risk_breaches=[],
        ...     deterministic_run_id="abc123def456",
        ...     manifest_hash_ref="hash789",
        ...     correlation_status="deferred"
        ... )
        >>> metrics.strategies_count
        2
    """

    strategies_count: int = Field(
        ..., ge=1, description="Number of strategies executed"
    )
    instruments_count: int = Field(
        ..., ge=0, description="Distinct instruments across strategies"
    )
    runtime_seconds: float = Field(..., ge=0.0, description="Wall-clock runtime")
    aggregate_pnl: float = Field(..., description="Weighted portfolio PnL")
    max_drawdown_pct: float = Field(
        ..., ge=0.0, le=1.0, description="Maximum portfolio drawdown"
    )
    volatility_annualized: float = Field(
        default=0.0, ge=0.0, description="Annualized volatility (stub)"
    )
    net_exposure_by_instrument: dict[str, float] = Field(
        default_factory=dict, description="Net exposure per instrument"
    )
    weights_applied: list[float] = Field(
        ..., description="Final normalized weights"
    )
    global_drawdown_limit: float | None = Field(
        default=None, description="Global drawdown threshold"
    )
    global_abort_triggered: bool = Field(
        default=False, description="Global abort flag"
    )
    risk_breaches: list[str] = Field(
        default_factory=list, description="Strategies with local breaches"
    )
    deterministic_run_id: str = Field(..., description="Stable run identifier")
    manifest_hash_ref: str = Field(..., description="Manifest reference hash")
    correlation_status: str = Field(
        default="deferred", description="Correlation analysis status"
    )

    class Config:
        """Pydantic model configuration."""

        frozen = False
        validate_assignment = True


__all__ = ["StructuredMetrics"]
