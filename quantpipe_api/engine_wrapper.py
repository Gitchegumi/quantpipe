"""Wrapper to run QuantPipe backtests in background with SSE progress streaming.

Design:
- Backtests run in a ThreadPoolExecutor (CPU-bound, releases GIL via numpy/polars).
- ProgressDispatcher is monkey-patched via a context manager to push updates
  into an asyncio queue so SSE consumers receive them in real time.
- Run metadata is persisted to a JSON file and reloaded on startup.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Run storage
# ---------------------------------------------------------------------------

RUNS_FILE = Path(os.environ.get("QUANTPIPE_RESULTS_DIR", "results")) / "backtest_runs.json"
RUNS_FILE.parent.mkdir(parents=True, exist_ok=True)

_run_lock = threading.Lock()
_run_queues: dict[str, asyncio.Queue[dict]] = {}
_run_store: dict[str, dict] = {}
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="backtest-")


def _load_runs() -> dict[str, dict]:
    """Load persisted runs from disk."""
    if RUNS_FILE.exists():
        try:
            with RUNS_FILE.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                return {r["run_id"]: r for r in data.get("runs", [])}
        except Exception:
            logger.exception("Failed to load runs file")
    return {}


def _save_runs() -> None:
    """Persist current runs to disk."""
    with _run_lock:
        try:
            payload = {"runs": list(_run_store.values())}
            with RUNS_FILE.open("w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, default=str)
        except Exception:
            logger.exception("Failed to save runs file")


# Load once at import time
_run_store.update(_load_runs())


# ---------------------------------------------------------------------------
# ProgressDispatcher monkey-patch context manager
# ---------------------------------------------------------------------------

@contextmanager
def _patch_progress(run_id: str):
    """Temporarily monkey-patch ProgressDispatcher to stream to an asyncio queue."""
    # Lazy import to avoid circular deps at module load
    from src.backtest.progress import ProgressDispatcher

    original_init = ProgressDispatcher.__init__
    original_update = ProgressDispatcher.update
    original_finish = ProgressDispatcher.finish

    run_queue = _run_queues.get(run_id)

    def _patched_init(self, total_items, *args, **kwargs):
        original_init(self, total_items, *args, **kwargs)
        self._run_id = run_id
        self._run_queue = run_queue

    def _patched_update(self, current_item: int) -> None:
        original_update(self, current_item)
        if self._run_queue and self._start_time is not None:
            pct = min(100.0, (current_item / self.total_items) * 100) if self.total_items > 0 else 0.0
            try:
                self._run_queue.put_nowait({
                    "phase": self.description.lower(),
                    "current": current_item,
                    "total": self.total_items,
                    "percent": round(pct, 2),
                    "message": f"{self.description}: {current_item:,} / {self.total_items:,}",
                    "timestamp": datetime.now(UTC).isoformat(),
                })
            except asyncio.QueueFull:
                pass

    def _patched_finish(self) -> dict:
        result = original_finish(self)
        if self._run_queue and self._start_time is not None:
            try:
                self._run_queue.put_nowait({
                    "phase": self.description.lower(),
                    "current": self.total_items,
                    "total": self.total_items,
                    "percent": 100.0,
                    "message": f"{self.description} complete",
                    "timestamp": datetime.now(UTC).isoformat(),
                })
            except asyncio.QueueFull:
                pass
        return result

    ProgressDispatcher.__init__ = _patched_init
    ProgressDispatcher.update = _patched_update
    ProgressDispatcher.finish = _patched_finish
    try:
        yield
    finally:
        ProgressDispatcher.__init__ = original_init
        ProgressDispatcher.update = original_update
        ProgressDispatcher.finish = original_finish


# ---------------------------------------------------------------------------
# Backtest runner
# ---------------------------------------------------------------------------

def _run_backtest_task(run_id: str, config: dict[str, Any]) -> dict[str, Any]:
    """Blocking function executed in a thread pool."""
    from src.backtest.engine import STRATEGY_MAP, construct_data_paths, run_portfolio_backtest
    from src.config.parameters import StrategyParameters
    from src.models.enums import DirectionMode

    pair = config["pairs"][0]
    pairs = config["pairs"]
    dataset = config.get("dataset", "test")
    direction_str = config.get("direction", "LONG")
    direction = DirectionMode(direction_str)
    timeframe = config.get("timeframe", "1m")
    strategy_name = config.get("strategy", "trend-pullback")
    dry_run = config.get("dry_run", False)
    profiling = config.get("profiling", False)
    starting_equity = config.get("starting_equity", 2500.0)
    max_risk_pct = config.get("max_risk_pct", 1.0)
    sl_mult = config.get("sl_multiplier", 1.0)
    tp_mult = config.get("tp_multiplier", 2.0)
    overrides = config.get("overrides", {})

    # Build strategy params
    strategy_params = StrategyParameters(
        strategy_name=strategy_name,
        ema_fast=overrides.get("ema_fast", 20),
        ema_slow=overrides.get("ema_slow", 50),
        atr_length=overrides.get("atr_length", 14),
        rsi_length=overrides.get("rsi_length", 14),
        risk_per_trade_pct=max_risk_pct / 100.0,
        atr_stop_mult=sl_mult,
        atr_target_mult=tp_mult,
        cooldown_candles=overrides.get("cooldown_candles", 5),
    )

    base_dir = Path("price_data/processed")
    pair_paths = construct_data_paths(pairs, dataset, base_dir)

    if not pair_paths:
        raise RuntimeError(f"No data found for pairs {pairs} in dataset '{dataset}'")

    results_dir = Path(os.environ.get("QUANTPIPE_RESULTS_DIR", "results"))
    results_dir.mkdir(parents=True, exist_ok=True)

    with _patch_progress(run_id):
        result = run_portfolio_backtest(
            pair_paths=pair_paths,
            direction_mode=direction,
            strategy_params=strategy_params,
            starting_equity=starting_equity,
            dry_run=dry_run,
            show_progress=True,  # Enable so ProgressDispatcher is created and patched
            timeframe=timeframe,
        )

    # Serialize result
    output_file = results_dir / f"{run_id}.json"
    serializable = _serialize_result(result, pair)
    with output_file.open("w", encoding="utf-8") as fh:
        json.dump(serializable, fh, indent=2, default=str)

    # Update run store
    with _run_lock:
        _run_store[run_id]["status"] = "completed"
        _run_store[run_id]["end_time"] = datetime.now(UTC).isoformat()
        _run_store[run_id]["results_path"] = str(output_file)
    _save_runs()

    # Final progress event
    queue = _run_queues.get(run_id)
    if queue:
        try:
            queue.put_nowait({
                "phase": "done",
                "current": 1,
                "total": 1,
                "percent": 100.0,
                "message": "Backtest complete",
                "timestamp": datetime.now(UTC).isoformat(),
            })
        except asyncio.QueueFull:
            pass

    return serializable


def _serialize_result(result: Any, pair: str) -> dict[str, Any]:
    """Convert a PortfolioResult / BacktestResult to a JSON-friendly dict."""
    # Handle both PortfolioResult (multi-symbol) and BacktestResult
    if hasattr(result, "results") and result.results:
        # Multi-symbol: pick first or aggregate
        first = next(iter(result.results.values()))
        return _serialize_single(first)
    if hasattr(result, "executions"):
        return _serialize_single(result)
    # Fallback: try to extract what we can
    return {"raw": str(result)}


def _serialize_single(result: Any) -> dict[str, Any]:
    """Serialize a single BacktestResult."""
    metrics = getattr(result, "metrics", None)
    metrics_dict: dict[str, Any] = {}
    if metrics:
        if hasattr(metrics, "combined"):
            m = metrics.combined
        else:
            m = metrics
        metrics_dict = {
            "trade_count": getattr(m, "trade_count", 0),
            "win_rate": getattr(m, "win_rate", 0.0),
            "avg_r": getattr(m, "avg_r", 0.0),
            "sharpe_estimate": getattr(m, "sharpe_estimate", None),
            "max_drawdown_r": getattr(m, "max_drawdown_r", 0.0),
            "max_drawdown_pct": getattr(m, "max_drawdown_pct", 0.0),
            "profit_factor": getattr(m, "profit_factor", None),
            "total_return_pct": getattr(m, "total_return_pct", 0.0),
        }

    trades = []
    executions = getattr(result, "executions", None) or []
    equity = 2500.0
    equity_curve: list[dict] = []
    peak = equity
    for ex in executions:
        trade = {
            "signal_id": getattr(ex, "signal_id", ""),
            "direction": getattr(ex, "direction", ""),
            "open_timestamp": getattr(ex, "open_timestamp", None),
            "entry_fill_price": getattr(ex, "entry_fill_price", 0.0),
            "close_timestamp": getattr(ex, "close_timestamp", None),
            "exit_fill_price": getattr(ex, "exit_fill_price", 0.0),
            "exit_reason": getattr(ex, "exit_reason", ""),
            "pnl_r": getattr(ex, "pnl_r", 0.0),
        }
        trades.append(trade)
        pnl_r = trade["pnl_r"] or 0.0
        # Rough equity estimation based on risk %
        risk_amt = equity * 0.01  # 1% risk per trade
        pnl_amt = pnl_r * risk_amt
        equity += pnl_amt
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0.0
        equity_curve.append({
            "timestamp": trade["close_timestamp"],
            "equity": round(equity, 2),
            "drawdown_pct": round(dd * 100, 4),
        })

    return {
        "run_id": getattr(result, "run_id", ""),
        "pair": getattr(result, "pair", pair),
        "direction": getattr(result, "direction_mode", "LONG"),
        "metrics": metrics_dict,
        "trades": trades,
        "equity_curve": equity_curve,
        "start_time": getattr(result, "start_time", None),
        "end_time": getattr(result, "end_time", None),
        "total_candles": getattr(result, "total_candles", 0),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_backtest(config: dict[str, Any]) -> str:
    """Enqueue a backtest and return its run ID."""
    run_id = config.get("run_id") or f"run_{uuid.uuid4().hex[:12]}"
    config["run_id"] = run_id

    # Register run
    with _run_lock:
        _run_store[run_id] = {
            "run_id": run_id,
            "status": "pending",
            "config": config,
            "start_time": datetime.now(UTC).isoformat(),
            "end_time": None,
            "results_path": None,
        }
    _save_runs()

    # Create queue for SSE
    _run_queues[run_id] = asyncio.Queue(maxsize=1000)

    # Submit to thread pool
    future = _executor.submit(_run_backtest_task, run_id, config)

    # Attach error handler
    def _on_done(f):
        try:
            f.result()
        except Exception as exc:
            logger.exception("Backtest %s failed", run_id)
            with _run_lock:
                _run_store[run_id]["status"] = "failed"
                _run_store[run_id]["end_time"] = datetime.now(UTC).isoformat()
                _run_store[run_id]["error"] = str(exc)
            _save_runs()
            queue = _run_queues.get(run_id)
            if queue:
                try:
                    queue.put_nowait({
                        "phase": "failed",
                        "current": 0,
                        "total": 1,
                        "percent": 0.0,
                        "message": str(exc),
                        "timestamp": datetime.now(UTC).isoformat(),
                    })
                except asyncio.QueueFull:
                    pass

    future.add_done_callback(_on_done)

    # Update status to running immediately
    with _run_lock:
        _run_store[run_id]["status"] = "running"
    _save_runs()

    return run_id


def get_status(run_id: str) -> dict[str, Any] | None:
    """Return current run status, or None if unknown."""
    with _run_lock:
        return _run_store.get(run_id)


def get_result(run_id: str) -> dict[str, Any] | None:
    """Load serialized result from disk if available."""
    with _run_lock:
        run = _run_store.get(run_id)
    if not run or not run.get("results_path"):
        return None
    path = Path(run["results_path"])
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        logger.exception("Failed to load result for %s", run_id)
        return None


def get_log(run_id: str) -> str:
    """Return log output for a run (stub — logs could be captured to a file)."""
    run = get_status(run_id)
    if not run:
        return ""
    # Simple status-based log for now
    lines = [
        f"[{run.get('start_time', 'N/A')}] Run started",
        f"[{run.get('end_time', 'N/A') or 'now'}] Status: {run.get('status', 'unknown')}",
    ]
    if run.get("error"):
        lines.append(f"ERROR: {run['error']}")
    return "\n".join(lines)


def cancel_run(run_id: str) -> bool:
    """Cancel a running backtest by marking it cancelled."""
    with _run_lock:
        run = _run_store.get(run_id)
        if not run:
            return False
        run["status"] = "cancelled"
        run["end_time"] = datetime.now(UTC).isoformat()
    _save_runs()
    queue = _run_queues.pop(run_id, None)
    if queue:
        try:
            queue.put_nowait({"phase": "cancelled", "message": "Run cancelled"})
        except asyncio.QueueFull:
            pass
    return True


def list_runs() -> list[dict[str, Any]]:
    """Return all runs sorted by start time descending."""
    with _run_lock:
        runs = list(_run_store.values())
    runs.sort(key=lambda r: r.get("start_time") or "", reverse=True)
    return runs


def get_progress_queue(run_id: str) -> asyncio.Queue[dict] | None:
    """Get the asyncio queue for SSE streaming."""
    return _run_queues.get(run_id)


def list_strategies() -> list[dict[str, Any]]:
    """Return available strategies from STRATEGY_MAP."""
    from src.backtest.engine import STRATEGY_MAP

    strategies = []
    for name, strat in STRATEGY_MAP.items():
        meta = getattr(strat, "metadata", None)
        strategies.append({
            "name": name,
            "description": getattr(meta, "description", "") if meta else "",
            "tags": getattr(meta, "tags", []) if meta else [],
        })
    return strategies


def list_pairs() -> list[str]:
    """Scan price_data/processed/ for available pairs."""
    base_dir = Path("price_data/processed")
    if not base_dir.exists():
        return []
    pairs = []
    for sub in base_dir.iterdir():
        if sub.is_dir():
            pairs.append(sub.name.upper())
    pairs.sort()
    return pairs
