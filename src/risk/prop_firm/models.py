"""
Data models for Prop Firm evaluation and scaling logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel


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
    cost: float = 0.0
    payout_share: float = 0.8


class ScalingConfig(BaseModel):
    """Configuration for scaling rules."""

    review_period_months: int
    profit_target_pct: float
    increments: list[float]


@dataclass(frozen=True)
class LevelResult:
    """Result of a single 'Level' within an attempt."""

    level_id: int
    start_tier_balance: float
    end_balance: float
    status: str
    start_date: datetime
    end_date: datetime
    trade_count: int
    pnl: float
    beginning_wallet_balance: float = 0.0
    new_wallet_balance: float = 0.0
    life_withdrawals: float = 0.0
    buyback_cost: float = 0.0
    metrics: Optional[MetricsSummary] = None
    failure_reason: Optional[str] = None


@dataclass(frozen=True)
class AttemptResult:
    """Result of a single 'Attempt' (persists until drawdown)."""

    attempt_id: int
    levels: list[LevelResult]
    status: str  # ACTIVE or FAILED
    total_pnl: float = 0.0


@dataclass(frozen=True)
class ScalingReport:
    """Aggregate report of a multi-attempt simulation."""

    attempts: list[AttemptResult]
    total_duration_days: int
    active_attempt_index: int
    wallet_balance: float = 0.0
    net_payouts: float = 0.0
    total_costs: float = 0.0

    @property
    def tier_stats(self) -> dict[float, dict[str, int]]:
        """
        Returns stats per tier balance.
        """
        stats = {}
        for attempt in self.attempts:
            for level in attempt.levels:
                balance = level.start_tier_balance
                if balance not in stats:
                    stats[balance] = {}

                current_count = stats[balance].get(level.status, 0)
                stats[balance][level.status] = current_count + 1

        return stats
