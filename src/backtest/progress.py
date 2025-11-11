"""Progress dispatcher for coarse-grained execution updates.

This module provides a progress tracking dispatcher that emits updates at
configurable intervals based on item count (stride) or elapsed time to
maintain low overhead (≤1%) while providing user visibility.
"""

import logging
import time
from typing import Optional

from src.backtest.performance_targets import (
    PROGRESS_MAX_INTERVAL_SECONDS,
    PROGRESS_STRIDE_ITEMS,
)


logger = logging.getLogger(__name__)


class ProgressDispatcher:
    """Coarse-grained progress dispatcher with stride and time-based emission.

    Emits progress updates based on:
    1. Item stride (default 16,384 items = 2^14)
    2. Time fallback (default 120 seconds maximum between updates)

    Tracks overhead to ensure ≤1% of total execution time spent on progress.

    Example:
        >>> dispatcher = ProgressDispatcher(total_items=1000000)
        >>> dispatcher.start()
        >>> for i in range(1000000):
        ...     dispatcher.update(i)
        >>> dispatcher.finish()
    """

    def __init__(
        self,
        total_items: int,
        stride: int = PROGRESS_STRIDE_ITEMS,
        time_fallback_sec: float = PROGRESS_MAX_INTERVAL_SECONDS,
    ):
        """Initialize progress dispatcher.

        Args:
            total_items: Total number of items to process
            stride: Emit progress every N items (default: 16384)
            time_fallback_sec: Maximum seconds between updates (default: 120)
        """
        self.total_items = total_items
        self.stride = stride
        self.time_fallback_sec = time_fallback_sec
        self._start_time: Optional[float] = None
        self._last_update_time: Optional[float] = None
        self._update_count = 0
        self._total_progress_time = 0.0
        self._finished = False

    def start(self) -> None:
        """Start progress tracking.

        Raises:
            RuntimeError: If already started
        """
        if self._start_time is not None:
            raise RuntimeError("Progress dispatcher already started")

        self._start_time = time.perf_counter()
        self._last_update_time = self._start_time
        logger.info("Progress tracking started for %d items", self.total_items)

    def update(self, current_item: int) -> None:
        """Update progress if stride or time threshold met.

        Args:
            current_item: Current item index (0-based)

        Note:
            Automatically determines whether to emit based on stride and time.
            Does nothing if thresholds not met to minimize overhead.
        """
        if self._start_time is None:
            return

        # Check stride threshold (modulo for efficiency)
        should_emit_stride = (current_item % self.stride) == 0

        # Check time threshold
        now = time.perf_counter()
        elapsed_since_last = now - self._last_update_time
        should_emit_time = elapsed_since_last >= self.time_fallback_sec

        if should_emit_stride or should_emit_time:
            progress_start = time.perf_counter()

            # Calculate progress percentage
            pct_complete = (current_item / self.total_items) * 100.0
            elapsed_total = now - self._start_time

            # Estimate remaining time
            if current_item > 0:
                avg_time_per_item = elapsed_total / current_item
                remaining_items = self.total_items - current_item
                estimated_remaining = avg_time_per_item * remaining_items
            else:
                estimated_remaining = 0.0

            logger.info(
                "Progress: %.1f%% (%d/%d items) | Elapsed: %.1fs | Est. remaining: %.1fs",
                pct_complete,
                current_item,
                self.total_items,
                elapsed_total,
                estimated_remaining,
            )

            progress_end = time.perf_counter()
            self._total_progress_time += progress_end - progress_start
            self._last_update_time = now
            self._update_count += 1

    def finish(self) -> dict:
        """Finalize progress tracking and emit final update.

        Returns:
            Dictionary containing:
                - update_count: Number of progress updates emitted
                - total_time_sec: Total execution time
                - progress_overhead_sec: Time spent in progress updates
                - progress_overhead_pct: Overhead as percentage of total time

        Raises:
            RuntimeError: If not started
        """
        if self._start_time is None:
            raise RuntimeError("Progress dispatcher not started")

        if self._finished:
            raise RuntimeError("Progress dispatcher already finished")

        now = time.perf_counter()
        total_time = now - self._start_time

        # Emit final 100% update
        progress_start = time.perf_counter()
        logger.info(
            "Progress: 100.0%% (%d/%d items) | Completed in %.1fs",
            self.total_items,
            self.total_items,
            total_time,
        )
        progress_end = time.perf_counter()
        self._total_progress_time += progress_end - progress_start
        self._update_count += 1

        overhead_pct = (self._total_progress_time / total_time) * 100.0

        self._finished = True

        return {
            "update_count": self._update_count,
            "total_time_sec": total_time,
            "progress_overhead_sec": self._total_progress_time,
            "progress_overhead_pct": overhead_pct,
        }

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if not self._finished:
            self.finish()
        return False
