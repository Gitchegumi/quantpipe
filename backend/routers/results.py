"""Results router: read manifests, trade history, serve charts."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import polars as pl
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..models import ResultDetail, ResultSummary, ResultsResponse
from ..run_quantpipe import REPO_ROOT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/results", tags=["results"])

RESULTS_DIR = REPO_ROOT / "results"
CHARTS_DIR = RESULTS_DIR / "dashboards"


def _discover_result_files() -> list[Path]:
    """Find all result JSON files in results/ directory."""
    if not RESULTS_DIR.exists():
        return []

    files: list[Path] = []
    for f in RESULTS_DIR.iterdir():
        if f.is_file() and f.suffix == ".json":
            files.append(f)
        elif f.is_dir():
            # Look for manifest.json in subdirs
            manifest = f / "manifest.json"
            if manifest.exists():
                files.append(manifest)

    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def _parse_manifest(path: Path) -> Optional[dict[str, Any]]:
    """Try to parse a result JSON file."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _build_summary(path: Path, data: dict[str, Any]) -> ResultSummary:
    """Build ResultSummary from manifest data."""
    run_id = data.get("run_id", path.stem)
    pair = data.get("pair") or data.get("symbol")
    direction = data.get("direction_mode") or data.get("direction")
    strategy = data.get("strategy")
    timeframe = data.get("timeframe")

    created_at: Optional[datetime] = None
    try:
        ts = path.stat().st_mtime
        created_at = datetime.fromtimestamp(ts, tz=timezone.utc)
    except Exception:
        pass

    return ResultSummary(
        run_id=run_id,
        pair=pair,
        direction=direction,
        strategy=strategy,
        timeframe=timeframe,
        result_path=str(path.relative_to(REPO_ROOT)),
        created_at=created_at,
    )


@router.get("", response_model=ResultsResponse)
async def list_results() -> ResultsResponse:
    """List all backtest result manifests."""
    files = _discover_result_files()
    results: list[ResultSummary] = []

    for f in files:
        data = _parse_manifest(f)
        if data:
            results.append(_build_summary(f, data))
        else:
            # Include even if unparseable, with minimal info
            results.append(
                ResultSummary(
                    run_id=f.stem,
                    result_path=str(f.relative_to(REPO_ROOT)),
                )
            )

    return ResultsResponse(results=results, count=len(results))


@router.get("/{run_id}", response_model=ResultDetail)
async def get_result(run_id: str) -> ResultDetail:
    """Get a specific result manifest and trade history."""
    # Find the manifest file
    manifest_path: Optional[Path] = None

    # Direct file match
    direct = RESULTS_DIR / f"backtest_{run_id}.json"
    if direct.exists():
        manifest_path = direct

    # Subdir match
    if not manifest_path:
        for subdir in RESULTS_DIR.iterdir():
            if subdir.is_dir() and run_id in subdir.name:
                candidate = subdir / "manifest.json"
                if candidate.exists():
                    manifest_path = candidate
                    break

    # Any .json file containing the run_id
    if not manifest_path:
        for f in RESULTS_DIR.glob("*.json"):
            if run_id in f.name:
                manifest_path = f
                break

    if not manifest_path or not manifest_path.exists():
        raise HTTPException(status_code=404, detail=f"Result not found for run_id={run_id}")

    data = _parse_manifest(manifest_path)
    if not data:
        raise HTTPException(status_code=500, detail="Failed to parse result manifest")

    # Extract metrics
    metrics = data.get("metrics")

    # Extract trades
    trades: list[dict[str, Any]] = []
    if "executions" in data and data["executions"]:
        trades = data["executions"]
    elif "closed_trades" in data and data["closed_trades"]:
        trades = data["closed_trades"]
    elif "signals" in data and data["signals"]:
        trades = data["signals"]

    # Look for chart
    chart_url: Optional[str] = None
    if CHARTS_DIR.exists():
        for html_file in CHARTS_DIR.glob(f"*{run_id}*.html"):
            chart_url = f"/charts/{html_file.name}"
            break

    return ResultDetail(
        run_id=run_id,
        manifest=data,
        trades=trades,
        metrics=metrics,
        chart_url=chart_url,
    )


@router.get("/{run_id}/trades")
async def get_result_trades(run_id: str) -> list[dict[str, Any]]:
    """Get trade history for a specific result."""
    detail = await get_result(run_id)
    return detail.trades


@router.get("/{run_id}/metrics")
async def get_result_metrics(run_id: str) -> Optional[dict[str, Any]]:
    """Get metrics for a specific result."""
    detail = await get_result(run_id)
    return detail.metrics
