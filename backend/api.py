"""FastAPI app for QuantPipe backend.

Entry point:
    cd /home/dockegumi/.openclaw/workspace/quantpipe
    python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload

Or:
    python -m uvicorn backend.api:app --reload
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Ensure repo root is on path for src imports
REPO_ROOT = Path("/home/dockegumi/.openclaw/workspace/quantpipe").resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.models import HealthResponse
from backend.routers import backtest, config, datasets, results, strategies

logger = logging.getLogger(__name__)

# --- Static directories ---
RESULTS_DIR = REPO_ROOT / "results"
CHARTS_DIR = RESULTS_DIR / "dashboards"


def _ensure_static_dirs() -> None:
    """Create static directories if they don't exist."""
    RESULTS_DIR.mkdir(exist_ok=True)
    CHARTS_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    _ensure_static_dirs()
    logger.info("QuantPipe backend started on port 8000")
    yield
    logger.info("QuantPipe backend shutting down")


app = FastAPI(
    title="QuantPipe API",
    description="FastAPI backend for QuantPipe trading strategy backtesting framework",
    version="0.5.0",
    lifespan=lifespan,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Top-level routes (per spec) ---
@app.get("/pairs", response_model=list[str])
async def list_pairs() -> list[str]:
    """List available currency pairs from price_data/processed/."""
    return await datasets.list_pairs()


@app.post("/ingest", response_model=datasets.IngestResponse)
async def trigger_ingest(
    req: datasets.IngestRequest,
    background_tasks: BackgroundTasks,
) -> datasets.IngestResponse:
    """Trigger dataset ingest for a symbol."""
    return await datasets.trigger_ingest(req, background_tasks)


@app.get("/ingest/{job_id}/status")
async def ingest_status_stream(job_id: str):
    """SSE stream of ingest progress."""
    return await datasets.ingest_status_stream(job_id)


# --- Routers ---
app.include_router(backtest.router)
app.include_router(datasets.router)
app.include_router(strategies.router)
app.include_router(results.router)
app.include_router(config.router)

# --- Static files: charts ---
if CHARTS_DIR.exists():
    app.mount("/charts", StaticFiles(directory=str(CHARTS_DIR)), name="charts")
else:
    # Lazy mount when dir is created
    @app.get("/charts/{filename}")
    async def serve_chart(filename: str):
        """Serve chart HTML files from results/dashboards/."""
        path = CHARTS_DIR / filename
        if not path.exists():
            # Also check results/
            alt = RESULTS_DIR / filename
            if alt.exists():
                path = alt
            else:
                from fastapi import HTTPException

                raise HTTPException(status_code=404, detail="Chart not found")
        return FileResponse(path)


# --- Health ---
@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Simple health check."""
    return HealthResponse(status="ok")


# --- Root ---
@app.get("/")
async def root() -> dict:
    """API root with links."""
    return {
        "name": "QuantPipe API",
        "version": "0.5.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "strategies": "/strategies",
            "pairs": "/datasets/pairs",
            "datasets": "/datasets",
            "backtest": "/backtest",
            "results": "/results",
            "charts": "/charts/{filename}",
            "config": "/config",
        },
    }
