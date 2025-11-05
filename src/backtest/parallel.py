"""Parallel execution utilities for independent parameter sets.

This module provides worker orchestration, shared memory optimization,
and parallel efficiency tracking for running multiple backtest configurations
concurrently.

Requirements: FR-008 (parallel execution), FR-008a (max-workers cap),
SC-011 (≥70% efficiency).
"""

# pylint: disable=unused-import

from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import logging

logger = logging.getLogger(__name__)


def get_worker_count(requested: Optional[int] = None) -> int:
    """Determine worker count with logical core cap.

    Args:
        requested: Requested number of workers, or None for auto-detection.

    Returns:
        Validated worker count (capped to logical cores).

    Side effects:
        Emits single warning if requested > logical cores.
    """
    logical_cores = multiprocessing.cpu_count()

    if requested is None:
        return max(1, logical_cores - 1)  # Leave one core free

    if requested > logical_cores:
        logger.warning(
            "Requested workers (%d) exceeds logical cores (%d); capping to %d",
            requested,
            logical_cores,
            logical_cores,
        )
        return logical_cores

    return max(1, requested)


def run_parallel(
    worker_fn: Callable[[Any], Any], tasks: List[Any], max_workers: Optional[int] = None
) -> List[Any]:
    """Execute tasks in parallel using process pool.

    Args:
        worker_fn: Function to execute per task (must be picklable).
        tasks: List of task arguments to pass to worker_fn.
        max_workers: Maximum number of parallel workers.

    Returns:
        List of results in same order as tasks.
    """
    worker_count = get_worker_count(max_workers)
    results = [None] * len(tasks)

    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        future_to_idx = {
            executor.submit(worker_fn, task): idx for idx, task in enumerate(tasks)
        }

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                logger.error("Task %d generated exception: %s", idx, exc)
                raise

    return results
