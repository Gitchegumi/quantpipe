"""Backtest async job router with SSE progress streaming."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from ..models import (
    BacktestProgress,
    BacktestRequest,
    BacktestResponse,
    BacktestResultResponse,
    JobStatus,
)
from ..run_quantpipe import (
    AsyncCLIJob,
    build_cli_args,
    extract_result_manifest_path,
    extract_run_id,
    parse_progress_from_line,
    REPO_ROOT,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtest", tags=["backtest"])

# In-memory job storage
_jobs: dict[str, JobStatus] = {}
_job_processes: dict[str, AsyncCLIJob] = {}


def _new_job_id() -> str:
    return f"bt_{uuid.uuid4().hex[:12]}"


def _build_backtest_cli_args(req: BacktestRequest) -> list[str]:
    """Convert API request to CLI arguments."""
    kwargs: dict = {
        "direction": req.direction,
        "pair": req.pair,
        "strategy": req.strategy,
        "dataset": req.dataset,
        "timeframe": req.timeframe,
        "starting_balance": req.starting_balance,
        "output_format": req.output_format,
        "dry_run": req.dry_run,
        "simulation_type": req.simulation_type,
        "non_interactive": True,
    }

    # Risk percent — the CLI uses --risk-pct
    kwargs["risk_pct"] = req.risk_percent

    # Stop policy
    kwargs["stop_policy"] = req.stop_policy

    # Reward-risk ratio — CLI uses --rr-ratio
    kwargs["rr_ratio"] = req.reward_risk_ratio

    # CTI mode if CTI simulation
    if req.simulation_type == "City Traders Imperium (CTI)":
        kwargs["cti_mode"] = req.cti_mode

    return build_cli_args("backtest", **kwargs)


async def _run_backtest_job(job_id: str, req: BacktestRequest) -> None:
    """Execute a backtest job in the background."""
    job = _jobs[job_id]
    job.status = "running"
    job.updated_at = datetime.now(timezone.utc)

    cli_args = _build_backtest_cli_args(req)
    cli_job = AsyncCLIJob(job_id=job_id, command=cli_args, cwd=REPO_ROOT)
    _job_processes[job_id] = cli_job

    last_progress = 0
    log_buffer: list[str] = []

    def on_stdout(line: str) -> None:
        log_buffer.append(line)
        parsed = parse_progress_from_line(line)
        if parsed:
            nonlocal last_progress
            last_progress = parsed["progress"]
            job.progress = last_progress
            job.log = line
        else:
            job.log = line
        job.updated_at = datetime.now(timezone.utc)

    def on_stderr(line: str) -> None:
        log_buffer.append(line)
        job.log = line
        job.updated_at = datetime.now(timezone.utc)

    returncode = await cli_job.run(stdout_cb=on_stdout, stderr_cb=on_stderr)

    output = cli_job.get_combined_output()
    manifest_path = extract_result_manifest_path(output)
    run_id = extract_run_id(output)

    # Fallback: look for saved files in results/
    results_dir = REPO_ROOT / "results"
    if not manifest_path and results_dir.exists():
        # Find most recently created backtest file
        files = sorted(
            [f for f in results_dir.iterdir() if f.suffix in (".json", ".txt")],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if files:
            manifest_path = str(files[0].relative_to(REPO_ROOT))
            if not run_id:
                m = re.search(r"backtest_([a-zA-Z0-9_\-]+)\.(json|txt)", files[0].name)
                if m:
                    run_id = m.group(1)

    if returncode == 0 and not cli_job.cancelled:
        job.status = "complete"
        job.progress = 100

        # Build result dict
        result: dict = {
            "run_id": run_id or job_id,
            "pair": req.pair,
            "strategy": req.strategy,
            "direction": req.direction,
            "dataset": req.dataset,
            "timeframe": req.timeframe,
            "manifest_path": manifest_path,
        }

        # Try to read metrics from JSON output
        if manifest_path and manifest_path.endswith(".json"):
            try:
                json_path = REPO_ROOT / manifest_path
                if json_path.exists():
                    data = json.loads(json_path.read_text(encoding="utf-8"))
                    if "metrics" in data:
                        result["metrics"] = data["metrics"]
                    if "run_id" in data:
                        result["run_id"] = data["run_id"]
            except Exception as e:
                logger.warning("Failed to parse result JSON for job %s: %s", job_id, e)

        job.result = result
    elif cli_job.cancelled:
        job.status = "cancelled"
        job.error = "Job was cancelled by user"
    else:
        job.status = "error"
        job.error = f"CLI exited with code {returncode}. Output:\n{output[:2000]}"

    job.updated_at = datetime.now(timezone.utc)
    del _job_processes[job_id]


@router.post("", response_model=BacktestResponse)
async def start_backtest(
    req: BacktestRequest,
    background_tasks: BackgroundTasks,
) -> BacktestResponse:
    """Start a new backtest job asynchronously."""
    job_id = _new_job_id()
    _jobs[job_id] = JobStatus(
        job_id=job_id,
        status="pending",
        progress=0,
        created_at=datetime.now(timezone.utc),
    )

    # Run in background so we can return job_id immediately
    task = asyncio.create_task(_run_backtest_job(job_id, req))

    return BacktestResponse(job_id=job_id, status="pending")


async def _sse_event_stream(job_id: str) -> AsyncIterator[str]:
    """Yield SSE events for a backtest job."""
    if job_id not in _jobs:
        yield f"event: error\ndata: {json.dumps({'error': 'Unknown job_id'})}\n\n"
        return

    job = _jobs[job_id]
    last_sent_progress = -1
    last_sent_log = ""

    while job.status in ("pending", "running"):
        if job.progress != last_sent_progress or job.log != last_sent_log:
            event = BacktestProgress(
                status=job.status,  # type: ignore[arg-type]
                progress=job.progress,
                log=job.log,
            )
            yield f"event: progress\ndata: {event.model_dump_json()}\n\n"
            last_sent_progress = job.progress
            last_sent_log = job.log
        await asyncio.sleep(0.5)

    # Final event
    if job.status == "complete":
        event = BacktestProgress(
            status="complete",
            progress=100,
            log="Backtest completed successfully",
            result=job.result,
        )
    elif job.status == "error":
        event = BacktestProgress(
            status="error",
            progress=job.progress,
            log=job.error or "Unknown error",
        )
    elif job.status == "cancelled":
        event = BacktestProgress(
            status="cancelled",
            progress=job.progress,
            log="Job cancelled",
        )
    else:
        event = BacktestProgress(status=job.status, progress=job.progress, log=job.log)  # type: ignore[arg-type]

    yield f"event: {event.status}\ndata: {event.model_dump_json()}\n\n"


@router.get("/{job_id}/status")
async def backtest_status_stream(job_id: str) -> StreamingResponse:
    """SSE stream of backtest progress."""
    return StreamingResponse(
        _sse_event_stream(job_id),
        media_type="text/event-stream",
    )


@router.get("/{job_id}/result", response_model=BacktestResultResponse)
async def get_backtest_result(job_id: str) -> BacktestResultResponse:
    """Get completed backtest result."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = _jobs[job_id]
    if job.status != "complete":
        raise HTTPException(
            status_code=400,
            detail=f"Job status is {job.status}, not complete",
        )

    result = job.result or {}
    run_id = result.get("run_id", job_id)

    # Look for chart HTML
    chart_url: Optional[str] = None
    charts_dir = REPO_ROOT / "results" / "dashboards"
    if charts_dir.exists():
        for html_file in charts_dir.glob(f"*{run_id}*.html"):
            chart_url = f"/charts/{html_file.name}"
            break
        if not chart_url:
            # Fallback: any chart for this run
            for html_file in charts_dir.glob("*.html"):
                chart_url = f"/charts/{html_file.name}"
                break

    return BacktestResultResponse(
        run_id=run_id,
        pair=result.get("pair", ""),
        strategy=result.get("strategy", ""),
        direction=result.get("direction", ""),
        dataset=result.get("dataset", ""),
        timeframe=result.get("timeframe", ""),
        metrics=result.get("metrics"),
        manifest_path=result.get("manifest_path"),
        result_path=result.get("manifest_path"),
        chart_url=chart_url,
    )


@router.delete("/{job_id}")
async def cancel_backtest(job_id: str) -> dict:
    """Cancel a running backtest job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_id in _job_processes:
        await _job_processes[job_id].cancel()

    _jobs[job_id].status = "cancelled"
    _jobs[job_id].updated_at = datetime.now(timezone.utc)
    return {"job_id": job_id, "status": "cancelled"}


