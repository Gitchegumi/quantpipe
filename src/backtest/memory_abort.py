"""Structured memory abort logging utility for scan and simulation operations.

This module provides graceful abort mechanisms with structured logging
for memory exhaustion scenarios during performance-critical operations.

Implements FR-009 (memory abort scenario handling) for Feature 010.
"""

import logging
from datetime import UTC, datetime
from enum import Enum


logger = logging.getLogger(__name__)


class MemoryAbortReason(Enum):
    """Enumeration of memory-related abort reasons."""

    MEMORY_EXHAUSTED = "memory_exhausted"
    ALLOCATION_THRESHOLD_EXCEEDED = "allocation_threshold_exceeded"
    SYSTEM_MEMORY_LOW = "system_memory_low"


class MemoryAbortRecord:
    """Structured record for memory abort events."""

    def __init__(
        self,
        reason: MemoryAbortReason,
        phase: str,
        timestamp: datetime,
        available_memory_mb: float | None = None,
        peak_memory_mb: float | None = None,
        candles_processed: int | None = None,
        allocation_count: int | None = None,
        details: str | None = None,
    ):
        """Initialize memory abort record.

        Args:
            reason: Categorized abort reason
            phase: Current processing phase (scan, simulation, etc.)
            timestamp: When abort occurred
            available_memory_mb: Available system memory at abort time
            peak_memory_mb: Peak memory usage before abort
            candles_processed: Number of candles processed before abort
            allocation_count: Number of allocations before abort
            details: Additional context-specific details
        """
        self.reason = reason
        self.phase = phase
        self.timestamp = timestamp
        self.available_memory_mb = available_memory_mb
        self.peak_memory_mb = peak_memory_mb
        self.candles_processed = candles_processed
        self.allocation_count = allocation_count
        self.details = details

    def to_dict(self) -> dict:
        """Convert abort record to dictionary for logging/serialization.

        Returns:
            Dictionary representation of abort record
        """
        return {
            "reason": self.reason.value,
            "phase": self.phase,
            "timestamp": self.timestamp.isoformat(),
            "available_memory_mb": self.available_memory_mb,
            "peak_memory_mb": self.peak_memory_mb,
            "candles_processed": self.candles_processed,
            "allocation_count": self.allocation_count,
            "details": self.details,
        }


def emit_memory_abort_log(
    reason: MemoryAbortReason,
    phase: str,
    available_memory_mb: float | None = None,
    peak_memory_mb: float | None = None,
    candles_processed: int | None = None,
    allocation_count: int | None = None,
    details: str | None = None,
) -> MemoryAbortRecord:
    """Emit structured memory abort log entry.

    Creates a MemoryAbortRecord and logs it with appropriate severity level.
    This function should be called when gracefully aborting operations
    due to memory exhaustion.

    Args:
        reason: Categorized abort reason
        phase: Current processing phase
        available_memory_mb: Available system memory at abort time
        peak_memory_mb: Peak memory usage before abort
        candles_processed: Number of candles processed before abort
        allocation_count: Number of allocations before abort
        details: Additional context-specific details

    Returns:
        MemoryAbortRecord instance for further processing if needed

    Example:
        >>> abort_record = emit_memory_abort_log(
        ...     reason=MemoryAbortReason.MEMORY_EXHAUSTED,
        ...     phase="scan",
        ...     available_memory_mb=512.0,
        ...     peak_memory_mb=7168.0,
        ...     candles_processed=1_000_000,
        ...     details="Exceeded 8GB memory threshold"
        ... )
    """
    record = MemoryAbortRecord(
        reason=reason,
        phase=phase,
        timestamp=datetime.now(UTC),
        available_memory_mb=available_memory_mb,
        peak_memory_mb=peak_memory_mb,
        candles_processed=candles_processed,
        allocation_count=allocation_count,
        details=details,
    )

    # Log with error severity for memory issues
    log_message = (
        "Memory abort triggered: reason=%s, phase=%s, available_memory_mb=%s, "
        "peak_memory_mb=%s, candles_processed=%s, allocation_count=%s, details=%s"
    )

    logger.error(
        log_message,
        reason.value,
        phase,
        available_memory_mb,
        peak_memory_mb,
        candles_processed,
        allocation_count,
        details,
    )

    return record


def check_memory_threshold(
    available_memory_mb: float,
    threshold_mb: float,
    phase: str,
    candles_processed: int,
    peak_memory_mb: float | None = None,
    allocation_count: int | None = None,
) -> MemoryAbortRecord | None:
    """Check if available memory is below threshold and emit abort if needed.

    Args:
        available_memory_mb: Current available system memory
        threshold_mb: Minimum required memory threshold
        phase: Current processing phase
        candles_processed: Number of candles processed so far
        peak_memory_mb: Peak memory usage so far
        allocation_count: Number of allocations so far

    Returns:
        MemoryAbortRecord if threshold violated, None otherwise
    """
    if available_memory_mb < threshold_mb:
        details = (
            f"Available memory ({available_memory_mb:.1f}MB) "
            f"below threshold ({threshold_mb:.1f}MB)"
        )
        return emit_memory_abort_log(
            reason=MemoryAbortReason.SYSTEM_MEMORY_LOW,
            phase=phase,
            available_memory_mb=available_memory_mb,
            peak_memory_mb=peak_memory_mb,
            candles_processed=candles_processed,
            allocation_count=allocation_count,
            details=details,
        )

    return None
