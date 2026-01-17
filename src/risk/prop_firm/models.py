"""
Data models for Prop Firm evaluation and scaling logic.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.models.core import MetricsSummary


class ChallengeConfig(BaseModel):
    """Configuration for a specific Prop Firm challenge."""

    program_id: str
    account_size: float
    max_daily_loss_pct: Optional[float] = None
    max_total_drawdown_pct: float
    profit_target_pct: float
    min_trading_days: int
    max_time_days: Optional[int] = None
    drawdown_type: str = "TRAILING"  # TRAILING or STATIC
    drawdown_mode: str = "CLOSED_BALANCE"


class ScalingConfig(BaseModel):
    """Configuration for scaling rules."""

    review_period_months: int
    profit_target_pct: float
    increments: List[float]


@dataclass(frozen=True)
class LifeResult:
    """Result of a single 'Life' (Attempt) within a scaling simulation."""

    life_id: int
    start_tier_balance: float
    end_balance: float
    status: str  # PASSED, FAILED_DRAWDOWN, FAILED_DAILY, IN_PROGRESS
    start_date: datetime
    end_date: datetime
    trade_count: int
    pnl: float
    # Note: MetricsSummary is defined in src.models.core, but we avoid
    # circular imports by storing it as a generic object or dict if needed,
    # or importing it inside methods. For now, we'll omit strict typing
    # or use 'Any' if we can't import it easily.
    # To keep this module standalone, we might use a simplified dict for now
    # or import if possible. Let's use a dict for independent metrics storage.
    metrics: Optional["MetricsSummary"] = None
    failure_reason: Optional[str] = None


@dataclass(frozen=True)
class ScalingReport:
    """Aggregate report of a multi-life simulation."""

    lives: List[LifeResult]
    total_duration_days: int
    active_life_index: int

    @property
    def tier_stats(self) -> Dict[float, Dict[str, int]]:
        """
        Returns stats per tier balance.
        Example: {10000.0: {'PASSED': 2, 'FAILED_DRAWDOWN': 1}}
        """
        stats = {}
        for life in self.lives:
            balance = life.start_tier_balance
            if balance not in stats:
                stats[balance] = {}

            # Count status
            current_count = stats[balance].get(life.status, 0)
            stats[balance][life.status] = current_count + 1

        return stats
