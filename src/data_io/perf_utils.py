"""Performance measurement utilities for ingestion operations.

This module provides utilities for timing, throughput calculation, and
memory footprint sampling during ingestion operations.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for ingestion operations.

    Attributes:
        runtime_seconds: Wall-clock runtime in seconds.
        total_rows_input: Number of raw input rows.
        total_rows_output: Number of rows after processing.
        throughput_rows_per_sec: Calculated throughput.
        memory_peak_mb: Peak memory usage in megabytes (optional).
    """

    runtime_seconds: float
    total_rows_input: int
    total_rows_output: int
    throughput_rows_per_sec: float
    memory_peak_mb: Optional[float] = None


class PerformanceTimer:
    """Context manager for measuring operation runtime."""

    def __init__(self) -> None:
        """Initialize the timer."""
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def __enter__(self) -> "PerformanceTimer":
        """Start the timer."""
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop the timer."""
        self.end_time = time.perf_counter()

    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds.

        Returns:
            float: Elapsed time in seconds.

        Raises:
            RuntimeError: If timer hasn't been completed.
        """
        if self.start_time is None or self.end_time is None:
            raise RuntimeError("Timer has not been completed")
        return self.end_time - self.start_time


def calculate_throughput(rows: int, runtime_seconds: float) -> float:
    """Calculate throughput in rows per second.

    Args:
        rows: Number of rows processed.
        runtime_seconds: Runtime in seconds.

    Returns:
        float: Throughput in rows per second.
    """
    if runtime_seconds <= 0:
        return 0.0
    return rows / runtime_seconds


def sample_memory_peak() -> Optional[float]:
    """Sample peak memory usage (optional, requires psutil).

    Returns:
        Optional[float]: Peak memory in MB, or None if psutil unavailable.
    """
    try:
        import psutil
        import os

        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / (1024 * 1024)
        return memory_mb
    except ImportError:
        logger.debug("psutil not available, skipping memory sampling")
        return None
    except (OSError, AttributeError) as e:
        logger.warning("Failed to sample memory: %s", str(e))
        return None
