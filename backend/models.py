"""Pydantic models for the QuantPipe API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Simple health check response."""

    status: str = "ok"


class JobStatus(BaseModel):
    """Generic async job status."""

    job_id: str
    status: Literal["pending", "running", "complete", "error", "cancelled"]
    progress: int = Field(0, ge=0, le=100)
    log: str = ""
    created_at: datetime
    updated_at: Optional[datetime] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

class StrategyInfo(BaseModel):
    """Information about a registered strategy."""

    name: str
    tags: list[str]
    version: Optional[str] = None


class StrategiesResponse(BaseModel):
    """List of registered strategies."""

    strategies: list[StrategyInfo]
    count: int


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

class DatasetInfo(BaseModel):
    """Information about a dataset for a specific pair."""

    pair: str
    test_path: Optional[str] = None
    validate_path: Optional[str] = None
    test_rows: Optional[int] = None
    validate_rows: Optional[int] = None
    manifest_path: Optional[str] = None


class DatasetsResponse(BaseModel):
    """List of available datasets."""

    pairs: list[str]
    datasets: list[DatasetInfo]
    count: int


class IngestRequest(BaseModel):
    """Request to trigger dataset ingest."""

    symbol: str = Field(..., description="Symbol to build dataset for (e.g., eurusd)")
    force: bool = False


class IngestResponse(BaseModel):
    """Initial response from ingest trigger."""

    job_id: str
    status: str = "pending"
    symbol: str


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

class BacktestRequest(BaseModel):
    """Request body to start a backtest."""

    pair: str = Field(..., description="Currency pair (e.g., EURUSD)")
    strategy: str = Field(default="trend-pullback", description="Strategy name")
    dataset: Literal["test", "validate"] = Field(default="test")
    direction: Literal["LONG", "SHORT", "BOTH"] = Field(default="LONG")
    timeframe: str = Field(default="1m", description="Timeframe (e.g., 1m, 5m, 1h)")
    starting_balance: float = Field(default=2500.0, gt=0)
    risk_percent: float = Field(default=0.25, gt=0, le=100)
    stop_policy: str = Field(default="ATR", description="Stop policy: ATR, ATR_Trailing, FixedPips, FixedPips_Trailing, MA_Trailing")
    reward_risk_ratio: float = Field(default=2.0, gt=0)
    output_format: Literal["text", "json"] = Field(default="json")
    dry_run: bool = Field(default=False)
    simulation_type: Literal["Personal Capital", "City Traders Imperium (CTI)"] = Field(default="Personal Capital")
    cti_mode: Literal["1STEP", "2STEP", "INSTANT"] = Field(default="2STEP")


class BacktestResponse(BaseModel):
    """Initial response from backtest trigger."""

    job_id: str
    status: str = "pending"


class BacktestProgress(BaseModel):
    """SSE event for backtest progress."""

    status: Literal["running", "complete", "error", "cancelled"]
    progress: int = Field(0, ge=0, le=100)
    log: str = ""
    result: Optional[dict[str, Any]] = None


class BacktestResultResponse(BaseModel):
    """Completed backtest result."""

    run_id: str
    pair: str
    strategy: str
    direction: str
    dataset: str
    timeframe: str
    metrics: Optional[dict[str, Any]] = None
    manifest_path: Optional[str] = None
    result_path: Optional[str] = None
    chart_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

class ResultSummary(BaseModel):
    """Summary of a backtest result manifest."""

    run_id: str
    pair: Optional[str] = None
    direction: Optional[str] = None
    strategy: Optional[str] = None
    timeframe: Optional[str] = None
    result_path: str
    created_at: Optional[datetime] = None


class ResultsResponse(BaseModel):
    """List of all backtest results."""

    results: list[ResultSummary]
    count: int


class ResultDetail(BaseModel):
    """Detailed result with manifest and optional trades."""

    run_id: str
    manifest: dict[str, Any]
    trades: list[dict[str, Any]] = Field(default_factory=list)
    metrics: Optional[dict[str, Any]] = None
    chart_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Scaffold
# ---------------------------------------------------------------------------

class ScaffoldRequest(BaseModel):
    """Request to scaffold a new strategy."""

    name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    output_dir: Optional[str] = None
    auto_register: bool = Field(default=True, description="Auto-register strategy after creation")


class ScaffoldResponse(BaseModel):
    """Response from scaffold creation."""

    success: bool
    name: str
    strategy_dir: str
    created_files: list[str]
    registered: bool
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class ConfigReadResponse(BaseModel):
    """Response for reading a config file."""

    path: str
    content: dict[str, Any]


class ConfigWriteRequest(BaseModel):
    """Request to write a config file."""

    content: dict[str, Any]


class ConfigWriteResponse(BaseModel):
    """Response for writing a config file."""

    path: str
    success: bool
