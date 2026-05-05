"""Pydantic schemas for the QuantPipe FastAPI backend."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared enums / constants
# ---------------------------------------------------------------------------

TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]
DIRECTIONS = ["LONG", "SHORT", "BOTH"]
DATASETS = ["test", "validate"]
SIMULATION_TYPES = ["personal_capital", "cti"]


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class BacktestRequest(BaseModel):
    """Payload to start a new backtest."""

    strategy: str = Field(..., description="Strategy name (from /api/strategies)")
    pairs: list[str] = Field(..., min_length=1, description="Currency pairs to backtest")
    direction: Literal["LONG", "SHORT", "BOTH"] = "LONG"
    dataset: Literal["test", "validate"] = "test"
    timeframe: Literal["1m", "5m", "15m", "1h", "4h", "1d"] = "1m"
    simulation_type: Literal["personal_capital", "cti"] = "personal_capital"
    starting_equity: float = Field(2500.0, ge=100.0)
    max_risk_pct: float = Field(1.0, ge=0.1, le=100.0)
    sl_multiplier: float = Field(1.0, ge=0.1)
    tp_multiplier: float = Field(2.0, ge=0.1)
    dry_run: bool = False
    profiling: bool = False
    # Optional strategy-specific overrides
    overrides: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Progress / status models
# ---------------------------------------------------------------------------

class ProgressEvent(BaseModel):
    """SSE event emitted during backtest execution."""

    phase: str = Field(..., description="Current phase: scanning | simulating | reporting | done | failed")
    current: int = Field(0, description="Items processed in current phase")
    total: int = Field(0, description="Total items in current phase")
    percent: float = Field(0.0, ge=0.0, le=100.0)
    message: str = ""
    metrics: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BacktestStatus(BaseModel):
    """Current status of a backtest run."""

    run_id: str
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    config: dict[str, Any]
    start_time: datetime | None = None
    end_time: datetime | None = None
    current_phase: str | None = None
    percent_complete: float = 0.0
    error: str | None = None


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------

class TradeRecord(BaseModel):
    """Single trade execution record."""

    signal_id: str
    direction: str
    open_timestamp: datetime
    entry_fill_price: float
    close_timestamp: datetime | None = None
    exit_fill_price: float | None = None
    exit_reason: str | None = None
    pnl_r: float | None = None


class MetricsSummary(BaseModel):
    """Aggregated backtest metrics."""

    trade_count: int = 0
    win_rate: float = 0.0
    avg_r: float = 0.0
    sharpe_estimate: float | None = None
    max_drawdown_r: float = 0.0
    max_drawdown_pct: float = 0.0
    profit_factor: float | None = None
    total_return_pct: float = 0.0


class EquityPoint(BaseModel):
    """Single point on the equity curve."""

    timestamp: datetime
    equity: float
    drawdown_pct: float = 0.0


class BacktestResult(BaseModel):
    """Complete backtest result payload."""

    run_id: str
    pair: str
    direction: str
    metrics: MetricsSummary
    trades: list[TradeRecord] = []
    equity_curve: list[EquityPoint] = []
    conflicts: list[dict[str, Any]] = []
    duration_seconds: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# List models
# ---------------------------------------------------------------------------

class StrategyInfo(BaseModel):
    """Strategy metadata for listing."""

    name: str
    description: str
    tags: list[str] = []


class RunSummary(BaseModel):
    """Minimal summary for the runs list."""

    run_id: str
    status: str
    strategy: str
    pairs: list[str]
    direction: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    results_path: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "0.5.0"
    uptime_seconds: float = 0.0
