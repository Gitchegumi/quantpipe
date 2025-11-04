"""Run manifest model for multi-strategy backtest execution tracking.

This module defines the RunManifest dataclass capturing all metadata required
for reproducibility and audit tracking of multi-strategy backtest runs.

Per project Constitution (Principle VI: Data Version Control), manifests must
link data sources, strategy configurations, and runtime decisions to enable
deterministic replay.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Sequence


@dataclass(frozen=True)
class RunManifest:
    """
    Immutable manifest of a multi-strategy backtest execution.

    Captures strategy selection, configurations, risk limits, data sources,
    and deterministic identifiers for full reproducibility.

    Attributes:
        run_id: Unique run identifier (deterministic hash preferred).
        strategies: List of strategy names included in this run.
        strategy_versions: Mapping strategy name -> version string.
        weights: Sequence of normalized weights applied for aggregation.
        global_drawdown_limit: Optional global portfolio drawdown threshold.
        data_manifest_refs: List of data manifest file paths/checksums.
        start_time: UTC timestamp when run started.
        end_time: UTC timestamp when run completed.
        correlation_status: Placeholder ('deferred' until correlation implemented).
        deterministic_run_id: Stable hash linking inputs + manifest.
        global_abort_triggered: True if global abort condition fired.
        risk_breaches: List of strategy names that breached local limits.

    Examples:
        >>> from datetime import datetime, timezone
        >>> manifest = RunManifest(
        ...     run_id="multi_run_20251104_120000",
        ...     strategies=["alpha", "beta"],
        ...     strategy_versions={"alpha": "1.0.0", "beta": "0.9.2"},
        ...     weights=[0.6, 0.4],
        ...     global_drawdown_limit=0.15,
        ...     data_manifest_refs=["data/manifests/eurusd_2024.json"],
        ...     start_time=datetime(2025, 11, 4, 12, 0, tzinfo=timezone.utc),
        ...     end_time=datetime(2025, 11, 4, 12, 30, tzinfo=timezone.utc),
        ...     correlation_status="deferred",
        ...     deterministic_run_id="abc123def456",
        ...     global_abort_triggered=False,
        ...     risk_breaches=[]
        ... )
        >>> manifest.strategies
        ['alpha', 'beta']
    """

    run_id: str
    strategies: Sequence[str]
    strategy_versions: dict[str, str]
    weights: Sequence[float]
    global_drawdown_limit: float | None
    data_manifest_refs: Sequence[str]
    start_time: datetime
    end_time: datetime
    correlation_status: str = "deferred"
    deterministic_run_id: str = ""
    global_abort_triggered: bool = False
    risk_breaches: Sequence[str] = field(default_factory=list)


__all__ = ["RunManifest"]
