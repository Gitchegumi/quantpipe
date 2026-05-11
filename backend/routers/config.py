"""Config router: simple read/write for YAML config files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException

from ..models import ConfigReadResponse, ConfigWriteRequest, ConfigWriteResponse
from ..run_quantpipe import REPO_ROOT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])

CONFIG_DIRS = [
    REPO_ROOT / "src" / "config",
    REPO_ROOT / "configs",
    REPO_ROOT / "config",
]


def _resolve_config_path(name: str) -> Path:
    """Find a config file by name in known config directories."""
    # Sanitize: no path traversal
    safe_name = Path(name).name

    for cfg_dir in CONFIG_DIRS:
        candidate = cfg_dir / safe_name
        if candidate.exists():
            return candidate

    # Also check with .yaml/.yml extension
    for ext in (".yaml", ".yml", ".json"):
        for cfg_dir in CONFIG_DIRS:
            candidate = cfg_dir / f"{safe_name}{ext}"
            if candidate.exists():
                return candidate

    raise HTTPException(status_code=404, detail=f"Config file not found: {name}")


@router.get("/{name}", response_model=ConfigReadResponse)
async def read_config(name: str) -> ConfigReadResponse:
    """Read a YAML/JSON config file by name."""
    path = _resolve_config_path(name)

    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        # Fallback to JSON
        import json

        content = json.loads(path.read_text(encoding="utf-8"))

    return ConfigReadResponse(
        path=str(path.relative_to(REPO_ROOT)),
        content=content if content else {},
    )


@router.post("/{name}", response_model=ConfigWriteResponse)
async def write_config(name: str, req: ConfigWriteRequest) -> ConfigWriteResponse:
    """Write a YAML config file by name."""
    safe_name = Path(name).name

    # Default to src/config/
    cfg_dir = CONFIG_DIRS[0]
    cfg_dir.mkdir(parents=True, exist_ok=True)

    path = cfg_dir / safe_name
    if not path.suffix:
        path = path.with_suffix(".yaml")

    try:
        text = yaml.safe_dump(req.content, default_flow_style=False, sort_keys=False)
        path.write_text(text, encoding="utf-8")
        return ConfigWriteResponse(
            path=str(path.relative_to(REPO_ROOT)),
            success=True,
        )
    except Exception as e:
        logger.error("Failed to write config %s: %s", path, e)
        raise HTTPException(status_code=500, detail=f"Failed to write config: {e}")


@router.get("")
async def list_configs() -> list[str]:
    """List available config files."""
    files: list[str] = []
    for cfg_dir in CONFIG_DIRS:
        if not cfg_dir.exists():
            continue
        for f in cfg_dir.rglob("*"):
            if f.is_file() and f.suffix in (".yaml", ".yml", ".json"):
                rel = str(f.relative_to(REPO_ROOT))
                files.append(rel)
    return sorted(files)
