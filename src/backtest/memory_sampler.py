"""Memory usage sampling utilities for performance benchmarking.

This module provides lightweight memory sampling functionality using tracemalloc
with psutil fallback for tracking peak memory usage during execution phases.
"""

import logging
from typing import Optional


logger = logging.getLogger(__name__)

# Track whether tracemalloc is available and active
_tracemalloc_available = False
_tracemalloc_started = False

try:
    import tracemalloc

    _tracemalloc_available = True
except ImportError:
    logger.warning("tracemalloc not available, memory tracking will be limited")

# Try to import psutil as fallback
_psutil_available = False
try:
    import psutil

    _psutil_available = True
except ImportError:
    logger.info("psutil not available, using tracemalloc only for memory tracking")


class MemorySampler:
    """Lightweight memory sampler for tracking peak memory usage.

    Uses tracemalloc for detailed allocation tracking or falls back to psutil
    for RSS (Resident Set Size) measurements if available.

    Example:
        >>> sampler = MemorySampler()
        >>> sampler.start()
        >>> # ... do work ...
        >>> peak_mb = sampler.get_peak_memory_mb()
        >>> sampler.stop()
    """

    def __init__(self):
        """Initialize memory sampler."""
        self._started = False
        self._use_tracemalloc = _tracemalloc_available
        self._use_psutil = _psutil_available
        self._process = None
        self._baseline_rss = 0

    def start(self) -> None:
        """Start memory sampling.

        Raises:
            RuntimeError: If sampler is already started
        """
        if self._started:
            raise RuntimeError("Memory sampler already started")

        if self._use_tracemalloc:
            tracemalloc.start()
            logger.debug("Started tracemalloc memory sampling")
        elif self._use_psutil:
            self._process = psutil.Process()
            self._baseline_rss = self._process.memory_info().rss
            logger.debug(
                "Started psutil memory sampling (baseline: %d bytes)",
                self._baseline_rss,
            )
        else:
            logger.warning("No memory sampling backend available")

        self._started = True

    def get_peak_memory_mb(self) -> Optional[float]:
        """Get peak memory usage in megabytes.

        Returns:
            Peak memory usage in MB or None if sampling unavailable

        Note:
            - With tracemalloc: returns peak of traced Python allocations
            - With psutil: returns peak RSS (Resident Set Size)
            - Returns None if no backend available
        """
        if not self._started:
            logger.warning("Memory sampler not started, returning None")
            return None

        if self._use_tracemalloc:
            current, peak = tracemalloc.get_traced_memory()
            return peak / (1024 * 1024)  # Convert bytes to MB
        elif self._use_psutil and self._process:
            rss = self._process.memory_info().rss
            return rss / (1024 * 1024)  # Convert bytes to MB
        else:
            return None

    def stop(self) -> None:
        """Stop memory sampling and release resources.

        Safe to call multiple times.
        """
        if not self._started:
            return

        if self._use_tracemalloc:
            tracemalloc.stop()
            logger.debug("Stopped tracemalloc memory sampling")

        self._started = False
        self._process = None

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False


def is_memory_sampling_available() -> bool:
    """Check if memory sampling is available.

    Returns:
        True if either tracemalloc or psutil is available, False otherwise
    """
    return _tracemalloc_available or _psutil_available
