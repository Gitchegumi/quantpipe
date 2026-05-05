"""Dataset router: list pairs, datasets, trigger ingest."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import polars as pl
from fastapi import APIRouter, BackgroundTasks

from ..models import (
    DatasetInfo,
    DatasetsResponse,
    IngestRequest,
    IngestResponse,
    JobStatus,
)
from ..run_quantpipe import (
    AsyncCLIJob,
    build_cli_args,
    REPO_ROOT,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["datasets"])

# In-memory job storage (shared namespace)
_ingest_jobs: dict[str, JobStatus] = {}
_ingest_processes: dict[str, AsyncCLIJob] = {}

PROCESSED_DIR = REPO_ROOT / "price_data" / "processed"
RAW_DIR = REPO_ROOT / "price_data" / "raw"


def _list_pairs() -> list[str]:
    """Discover available pairs from processed data directory."""
    if not PROCESSED_DIR.exists():
        return []

    pairs = []
    for item in PROCESSED_DIR.iterdir():
        if item.is_dir():
            # Verify it has some data files
            has_data = any(
                f.suffix in (".parquet", ".csv")
                for f in item.rglob("*")
            )
            if has_data:
                pairs.append(item.name)

    return sorted(pairs)


def _get_dataset_info(pair: str) -> DatasetInfo:
    """Build DatasetInfo for a specific pair."""
    pair_dir = PROCESSED_DIR / pair
    test_path: Optional[str] = None
    validate_path: Optional[str] = None
    test_rows: Optional[int] = None
    validate_rows: Optional[int] = None
    manifest_path: Optional[str] = None

    # Look for standard structure: pair_dir/test/ and pair_dir/validate/
    for subdir in ("test", "validate"):
        sub = pair_dir / subdir
        if sub.exists():
            # Look for parquet or csv
            for ext in ("parquet", "csv"):
                for f in sub.rglob(f"*.{ext}"):
                    rel = str(f.relative_to(REPO_ROOT))
                    if subdir == "test":
                        test_path = rel
                        try:
                            df = pl.scan_parquet(f).collect()
                            test_rows = len(df)
                        except Exception:
                            pass
                    else:
                        validate_path = rel
                        try:
                            df = pl.scan_parquet(f).collect()
                            validate_rows = len(df)
                        except Exception:
                            pass
                    break

    # Look for manifest JSON
    manifest = pair_dir / "manifest.json"
    if manifest.exists():
        manifest_path = str(manifest.relative_to(REPO_ROOT))

    return DatasetInfo(
        pair=pair,
        test_path=test_path,
        validate_path=validate_path,
        test_rows=test_rows,
        validate_rows=validate_rows,
        manifest_path=manifest_path,
    )


@router.get("", response_model=DatasetsResponse)
async def list_datasets() -> DatasetsResponse:
    """List all available pairs with their test/validate datasets."""
    pairs = _list_pairs()
    datasets = [_get_dataset_info(p) for p in pairs]

    return DatasetsResponse(
        pairs=pairs,
        datasets=datasets,
        count=len(datasets),
    )


@router.get("/pairs", response_model=list[str])
async def list_pairs() -> list[str]:
    """List available currency pairs."""
    return _list_pairs()


import asyncio
import uuid


async def _run_ingest_job(job_id: str, symbol: str) -> None:
    """Execute ingest CLI in the background."""
    job = _ingest_jobs[job_id]
    job.status = "running"
    job.updated_at = datetime.now(timezone.utc)

    cli_args = build_cli_args("ingest", symbol=symbol, all=False, log_level="INFO")
    cli_job = AsyncCLIJob(job_id=job_id, command=cli_args, cwd=REPO_ROOT)
    _ingest_processes[job_id] = cli_job

    def on_stdout(line: str) -> None:
        job.log = line
        parsed = None
        # Try to infer progress from log
        if "%" in line:
            try:
                pct = int(line.split("%")[0].rsplit()[-1])
                job.progress = min(pct, 100)
            except (ValueError, IndexError):
                pass
        job.updated_at = datetime.now(timezone.utc)

    def on_stderr(line: str) -> None:
        job.log = line
        job.updated_at = datetime.now(timezone.utc)

    returncode = await cli_job.run(stdout_cb=on_stdout, stderr_cb=on_stderr)
    output = cli_job.get_combined_output()

    if returncode == 0:
        job.status = "complete"
        job.progress = 100

        # Try to extract metadata from output
        result: dict = {"symbol": symbol, "output": output[:2000]}
        try:
            # Look for JSON summary in output
            if "{" in output:
                json_start = output.rfind("{")
                json_end = output.rfind("}")
                if json_start != -1 and json_end != -1 and json_end > json_start:
                    data = json.loads(output[json_start : json_end + 1])
                    result["metadata"] = data
        except Exception:
            pass

        job.result = result
    elif cli_job.cancelled:
        job.status = "cancelled"
        job.error = "Job was cancelled"
    else:
        job.status = "error"
        job.error = f"CLI exited with code {returncode}. Output:\n{output[:2000]}"

    job.updated_at = datetime.now(timezone.utc)
    if job_id in _ingest_processes:
        del _ingest_processes[job_id]


@router.post("/ingest", response_model=IngestResponse)
async def trigger_ingest(
    req: IngestRequest,
    background_tasks: BackgroundTasks,
) -> IngestResponse:
    """Trigger dataset ingest for a symbol."""
    job_id = f"ing_{uuid.uuid4().hex[:12]}"
    _ingest_jobs[job_id] = JobStatus(
        job_id=job_id,
        status="pending",
        progress=0,
        created_at=datetime.now(timezone.utc),
    )

    asyncio.create_task(_run_ingest_job(job_id, req.symbol))

    return IngestResponse(
        job_id=job_id,
        status="pending",
        symbol=req.symbol,
    )


@router.get("/ingest/{job_id}/status")
async def get_ingest_status(job_id: str) -> JobStatus:
    """Get ingest job status."""
    if job_id not in _ingest_jobs:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Ingest job not found")
    return _ingest_jobs[job_id]


@router.get("/ingest/{job_id}/stream")
async def ingest_status_stream(job_id: str):
    """SSE stream for ingest progress."""
    import asyncio

    from fastapi import HTTPException
    from fastapi.responses import StreamingResponse

    if job_id not in _ingest_jobs:
        raise HTTPException(status_code=404, detail="Ingest job not found")

    async def event_stream():
        job = _ingest_jobs[job_id]
        last_progress = -1
        last_log = ""

        while job.status in ("pending", "running"):
            if job.progress != last_progress or job.log != last_log:
                event = {
                    "status": job.status,
                    "progress": job.progress,
                    "log": job.log,
                }
                yield f"event: progress\ndata: {json.dumps(event)}\n\n"
                last_progress = job.progress
                last_log = job.log
            await asyncio.sleep(0.5)

        # Final event
        if job.status == "complete":
            event = {"status": "complete", "progress": 100, "result": job.result}
        elif job.status == "error":
            event = {"status": "error", "progress": job.progress, "error": job.error}
        else:
            event = {"status": job.status, "progress": job.progress, "log": job.log}

        yield f"event: {event['status']}\ndata: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
    )
