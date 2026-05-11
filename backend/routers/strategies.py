"""Strategy router: list registered strategies, scaffold new ones."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

from ..models import ScaffoldRequest, ScaffoldResponse, StrategiesResponse, StrategyInfo
from ..run_quantpipe import AsyncCLIJob, build_cli_args, REPO_ROOT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategies", tags=["strategies"])


def _get_registry():
    """Lazy import to avoid module-level side effects."""
    from src.strategy.registry import StrategyRegistry

    return StrategyRegistry(load_private=True)


@router.get("", response_model=StrategiesResponse)
async def list_strategies() -> StrategiesResponse:
    """List all registered strategies from StrategyRegistry."""
    try:
        registry = _get_registry()
        strategies = registry.list()
    except Exception as e:
        logger.error("Failed to load strategy registry: %s", e)
        strategies = []

    # Also include hard-coded strategies from the engine
    from src.backtest.engine import STRATEGY_MAP

    known_names = {s.name for s in strategies}
    for name in STRATEGY_MAP:
        if name not in known_names:
            strategies.append(
                StrategyInfo(name=name, tags=["builtin"], version=None)
            )

    info_list = [
        StrategyInfo(name=s.name, tags=s.tags, version=s.version)
        for s in strategies
    ]

    return StrategiesResponse(
        strategies=info_list,
        count=len(info_list),
    )


@router.post("/scaffold", response_model=ScaffoldResponse)
async def scaffold_strategy(req: ScaffoldRequest) -> ScaffoldResponse:
    """Scaffold a new strategy from template."""
    kwargs: dict = {
        "name": req.name,
        "description": req.description,
        "tags": ",".join(req.tags) if req.tags else "",
        "register": not req.auto_register,
    }

    if req.output_dir:
        kwargs["output"] = req.output_dir

    cli_args = build_cli_args("scaffold", **kwargs)
    cli_job = AsyncCLIJob(job_id=f"sc_{req.name}", command=cli_args, cwd=REPO_ROOT)

    returncode = await cli_job.run()
    output = cli_job.get_combined_output()

    if returncode != 0:
        logger.error("Scaffold failed: %s", output)
        return ScaffoldResponse(
            success=False,
            name=req.name,
            strategy_dir="",
            created_files=[],
            registered=False,
            error=output[:2000],
        )

    # Parse created files from output
    created_files: list[str] = []
    strategy_dir = ""
    for line in output.splitlines():
        if line.strip().startswith("-") and ".py" in line:
            fname = line.strip().lstrip("- ").strip()
            created_files.append(fname)
        if "Directory:" in line:
            strategy_dir = line.split("Directory:")[1].strip()

    # Fallback: infer directory
    if not strategy_dir:
        strategy_dir = str(REPO_ROOT / "src" / "strategy" / req.name)

    return ScaffoldResponse(
        success=True,
        name=req.name,
        strategy_dir=str(strategy_dir),
        created_files=created_files,
        registered=req.auto_register,
    )
