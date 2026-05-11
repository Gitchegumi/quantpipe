"""Async subprocess wrapper for running quantpipe CLI commands."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
import signal
import uuid
from pathlib import Path
from typing import AsyncIterator, Callable, Optional

logger = logging.getLogger(__name__)

REPO_ROOT = Path("/home/dockegumi/.openclaw/workspace/quantpipe").resolve()
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"


def _get_python() -> str:
    """Return path to the Python interpreter from the virtualenv."""
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    # Fallback: try to use the venv python via uv/poetry
    return "python"


def build_cli_args(
    command: str,
    **kwargs,
) -> list[str]:
    """Build CLI argument list for quantpipe subcommands.

    Args:
        command: Subcommand name (backtest, ingest, scaffold).
        **kwargs: CLI flags and values.

    Returns:
        List of CLI argument strings.
    """
    args = ["-m", "src.cli.main", command]

    for key, value in kwargs.items():
        if value is None:
            continue
        # Convert snake_case to kebab-case
        flag = f"--{key.replace('_', '-')}"

        if isinstance(value, bool):
            if value:
                if key == "dry_run":
                    args.append("--dry-run")
                elif key == "no_register":
                    args.append("--no-register")
                else:
                    args.append(flag)
        elif isinstance(value, (list, tuple)):
            args.append(flag)
            for item in value:
                args.append(str(item))
        elif isinstance(value, Path):
            args.append(flag)
            args.append(str(value))
        else:
            args.append(flag)
            args.append(str(value))

    return args


class AsyncCLIJob:
    """Represents an async CLI job with streaming and cancellation."""

    def __init__(
        self,
        job_id: str,
        command: list[str],
        cwd: Path = REPO_ROOT,
        env: Optional[dict] = None,
    ) -> None:
        self.job_id = job_id
        self.command = command
        self.cwd = cwd
        self.env = env or {}
        self.process: Optional[asyncio.subprocess.Process] = None
        self.returncode: Optional[int] = None
        self.stdout_lines: list[str] = []
        self.stderr_lines: list[str] = []
        self.cancelled = False

    async def run(
        self,
        stdout_cb: Optional[Callable[[str], None]] = None,
        stderr_cb: Optional[Callable[[str], None]] = None,
    ) -> int:
        """Run the CLI command asynchronously.

        Args:
            stdout_cb: Optional callback for each stdout line.
            stderr_cb: Optional callback for each stderr line.

        Returns:
            Process return code.
        """
        python = _get_python()
        full_cmd = [python] + self.command

        logger.info("Job %s: starting command: %s", self.job_id, shlex.join(full_cmd))

        env = {**os.environ, **self.env}
        # Ensure PYTHONPATH includes repo root so imports work
        pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{REPO_ROOT}{os.pathsep}{pp}" if pp else str(REPO_ROOT)

        self.process = await asyncio.create_subprocess_exec(
            *full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.cwd),
            env=env,
        )

        async def _read_stream(
            stream: asyncio.StreamReader,
            buffer: list[str],
            cb: Optional[Callable[[str], None]],
        ) -> None:
            while True:
                line = await stream.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip("\n")
                buffer.append(text)
                if cb:
                    try:
                        cb(text)
                    except Exception:
                        logger.exception("Callback error for job %s", self.job_id)

        await asyncio.gather(
            _read_stream(self.process.stdout, self.stdout_lines, stdout_cb),
            _read_stream(self.process.stderr, self.stderr_lines, stderr_cb),
        )

        self.returncode = await self.process.wait()
        logger.info("Job %s: finished with code %s", self.job_id, self.returncode)
        return self.returncode

    async def cancel(self) -> None:
        """Cancel the running job."""
        if self.process is None or self.process.returncode is not None:
            return
        self.cancelled = True
        try:
            self.process.send_signal(signal.SIGTERM)
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Job %s: SIGTERM timeout, sending SIGKILL", self.job_id)
                self.process.kill()
                await self.process.wait()
        except ProcessLookupError:
            pass
        logger.info("Job %s: cancelled", self.job_id)

    def get_stdout(self) -> str:
        """Return full stdout as string."""
        return "\n".join(self.stdout_lines)

    def get_stderr(self) -> str:
        """Return full stderr as string."""
        return "\n".join(self.stderr_lines)

    def get_combined_output(self) -> str:
        """Return stdout + stderr combined."""
        return "\n".join(self.stdout_lines + self.stderr_lines)


def parse_progress_from_line(line: str) -> Optional[dict]:
    """Try to extract progress info from a CLI output line.

    Looks for patterns like:
    - "Progress: 45%"
    - "[45/100]"
    - "45% complete"
    """
    import re

    # Pattern: "Progress: 45%" or "45% complete"
    m = re.search(r"(\d{1,3})%", line)
    if m:
        progress = min(int(m.group(1)), 100)
        return {"progress": progress, "log": line}

    # Pattern: "[45/100]" or "45/100"
    m = re.search(r"\[(\d+)\s*/\s*(\d+)\]", line)
    if m:
        current, total = int(m.group(1)), int(m.group(2))
        if total > 0:
            progress = min(int(current / total * 100), 100)
            return {"progress": progress, "log": line}

    # Pattern: "45/100" without brackets
    m = re.search(r"(\d+)\s*/\s*(\d+)", line)
    if m:
        current, total = int(m.group(1)), int(m.group(2))
        if total > 0 and total <= 100000:
            progress = min(int(current / total * 100), 100)
            return {"progress": progress, "log": line}

    return None


def extract_result_manifest_path(output: str) -> Optional[str]:
    """Try to find a result manifest JSON path in CLI output."""
    import re

    # Look for JSON file paths in results/
    for match in re.finditer(r"(results[/\\][^\s\"]+\.json)", output):
        return match.group(1)
    return None


def extract_run_id(output: str) -> Optional[str]:
    """Try to extract run_id from CLI output."""
    import re

    m = re.search(r"run_id[:\s]+([a-zA-Z0-9_\-]+)", output, re.IGNORECASE)
    if m:
        return m.group(1)

    # Look in saved filename: backtest_<run_id>.json
    m = re.search(r"backtest_([a-zA-Z0-9_\-]+)\.(json|txt)", output)
    if m:
        return m.group(1)

    return None
