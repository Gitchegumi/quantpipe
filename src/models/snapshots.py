"""Portfolio snapshot record models for periodic state logging.

This module defines the data structure for portfolio snapshot records that
capture periodic state during portfolio backtesting.
"""
from datetime import datetime

from pydantic import BaseModel, Field


class PortfolioSnapshotRecord(BaseModel):
    """Periodic portfolio state snapshot for JSONL logging.

    Attributes:
        t: Timestamp of snapshot (ISO8601 format)
        positions: Current position sizes per symbol
        unrealized: Per-symbol unrealized P&L
        portfolio_pnl: Aggregate realized + unrealized P&L
        exposure: Notional exposure as fraction of capital
        diversification_ratio: Current diversification ratio
        corr_window: Active correlation window length
    """

    t: datetime
    positions: dict[str, float] = Field(default_factory=dict)
    unrealized: dict[str, float] = Field(default_factory=dict)
    portfolio_pnl: float = Field(default=0.0)
    exposure: float = Field(default=0.0, ge=0.0, le=1.0)
    diversification_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    corr_window: int = Field(default=0, ge=0)

    def to_json_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation suitable for JSON Lines format
        """
        return {
            "t": self.t.isoformat(),
            "positions": self.positions,
            "unrealized": self.unrealized,
            "portfolio_pnl": self.portfolio_pnl,
            "exposure": self.exposure,
            "diversification_ratio": self.diversification_ratio,
            "corr_window": self.corr_window,
        }
