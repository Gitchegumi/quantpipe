"""FastAPI application for QuantPipe web dashboard.

Provides REST endpoints for backtest management and SSE progress streaming.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from quantpipe_api import engine_wrapper
from quantpipe_api.models import (
    BacktestRequest,
    BacktestResult,
    BacktestStatus,
    HealthResponse,
    ProgressEvent,
    RunSummary,
    StrategyInfo,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

_start_time = time.perf_counter()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Reload run history on startup; clean up on shutdown."""
    engine_wrapper._run_store.update(engine_wrapper._load_runs())
    logger.info("QuantPipe API started — loaded %d historical runs", len(engine_wrapper._run_store))
    yield
    logger.info("QuantPipe API shutting down")
    engine_wrapper._executor.shutdown(wait=True)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="QuantPipe API",
    version="0.5.0",
    lifespan=lifespan,
)

# CORS — permissive for local dev; tighten for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_status(run: dict) -> BacktestStatus:
    return BacktestStatus(
        run_id=run["run_id"],
        status=run.get("status", "unknown"),
        config=run.get("config", {}),
        start_time=run.get("start_time"),
        end_time=run.get("end_time"),
        current_phase=run.get("current_phase"),
        percent_complete=run.get("percent_complete", 0.0),
        error=run.get("error"),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="0.5.0",
        uptime_seconds=round(time.perf_counter() - _start_time, 2),
    )


@app.get("/api/strategies", response_model=list[StrategyInfo])
async def list_strategies() -> list[StrategyInfo]:
    """List all registered strategies."""
    strategies = engine_wrapper.list_strategies()
    return [StrategyInfo(**s) for s in strategies]


@app.get("/api/pairs")
async def list_pairs() -> list[str]:
    """List available currency pairs from price_data/processed/."""
    return engine_wrapper.list_pairs()


@app.post("/api/backtest")
async def start_backtest(request: BacktestRequest) -> dict[str, str]:
    """Start a new backtest and return its runId."""
    config = request.model_dump()
    run_id = engine_wrapper.start_backtest(config)
    return {"runId": run_id}


@app.get("/api/backtest/{run_id}", response_model=BacktestStatus)
async def get_status(run_id: str) -> BacktestStatus:
    """Get current status of a backtest run."""
    run = engine_wrapper.get_status(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _to_status(run)


@app.get("/api/backtest/{run_id}/stream")
async def stream_progress(run_id: str) -> StreamingResponse:
    """SSE stream of backtest progress events."""
    run = engine_wrapper.get_status(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    queue = engine_wrapper.get_progress_queue(run_id)
    if queue is None:
        # Already completed or cancelled — send final state and close
        async def _final() -> AsyncGenerator[str, None]:
            yield _sse_event("done", {"phase": "done", "percent": 100.0, "message": "Run already finished"})
        return StreamingResponse(_final(), media_type="text/event-stream")

    async def _event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=60.0)
                except asyncio.TimeoutError:
                    # Send keep-alive heartbeat
                    yield _sse_event("heartbeat", {"phase": "heartbeat", "timestamp": datetime.now(UTC).isoformat()})
                    continue

                if event is None:
                    break

                phase = event.get("phase", "unknown")
                yield _sse_event(phase, event)

                if phase in ("done", "failed", "cancelled"):
                    break
        except asyncio.CancelledError:
            pass

    return StreamingResponse(_event_generator(), media_type="text/event-stream")


def _sse_event(event_type: str, data: dict) -> str:
    """Format a dict as an SSE event string."""
    payload = json.dumps(data, default=str)
    return f"event: {event_type}\ndata: {payload}\n\n"


@app.get("/api/backtest/{run_id}/results", response_model=BacktestResult | None)
async def get_results(run_id: str) -> BacktestResult | None:
    """Get final backtest results (trades, metrics, equity curve)."""
    result = engine_wrapper.get_result(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Results not found or run not complete")
    return BacktestResult(**result)


@app.get("/api/backtest/{run_id}/log")
async def get_log(run_id: str) -> dict[str, str]:
    """Get log output for a backtest run."""
    log_text = engine_wrapper.get_log(run_id)
    return {"log": log_text}


@app.delete("/api/backtest/{run_id}")
async def cancel_backtest(run_id: str) -> dict[str, str]:
    """Cancel a running backtest."""
    ok = engine_wrapper.cancel_run(run_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"status": "cancelled", "runId": run_id}


@app.get("/api/backtests", response_model=list[RunSummary])
async def list_backtests() -> list[RunSummary]:
    """List all backtest runs."""
    runs = engine_wrapper.list_runs()
    summaries = []
    for run in runs:
        cfg = run.get("config", {})
        summaries.append(
            RunSummary(
                run_id=run["run_id"],
                status=run.get("status", "unknown"),
                strategy=cfg.get("strategy", "unknown"),
                pairs=cfg.get("pairs", []),
                direction=cfg.get("direction", "LONG"),
                start_time=run.get("start_time"),
                end_time=run.get("end_time"),
                results_path=run.get("results_path"),
            )
        )
    return summaries
