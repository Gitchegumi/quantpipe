"""Unit tests for memory abort scenario handling.

This module validates structured abort logging for memory exhaustion
scenarios per FR-009.

Test Coverage:
- Memory threshold violation triggers abort
- Structured abort record contains all required fields
- Abort log emitted with appropriate severity
- Multiple abort reasons handled correctly
"""
# pylint: disable=redefined-outer-name
# Justification:
# - redefined-outer-name: pytest fixtures intentionally shadow fixture names

import logging
from datetime import UTC, datetime

from src.backtest.memory_abort import (
    MemoryAbortReason,
    MemoryAbortRecord,
    check_memory_threshold,
    emit_memory_abort_log,
)


def test_memory_abort_record_creation():
    """Test MemoryAbortRecord initialization and to_dict conversion."""
    timestamp = datetime.now(UTC)
    record = MemoryAbortRecord(
        reason=MemoryAbortReason.MEMORY_EXHAUSTED,
        phase="scan",
        timestamp=timestamp,
        available_memory_mb=512.0,
        peak_memory_mb=7168.0,
        candles_processed=1_000_000,
        allocation_count=500_000,
        details="Test abort scenario",
    )

    assert record.reason == MemoryAbortReason.MEMORY_EXHAUSTED
    assert record.phase == "scan"
    assert record.timestamp == timestamp
    assert record.available_memory_mb == 512.0
    assert record.peak_memory_mb == 7168.0
    assert record.candles_processed == 1_000_000
    assert record.allocation_count == 500_000
    assert record.details == "Test abort scenario"

    # Test dictionary conversion
    record_dict = record.to_dict()
    assert record_dict["reason"] == "memory_exhausted"
    assert record_dict["phase"] == "scan"
    assert record_dict["timestamp"] == timestamp.isoformat()
    assert record_dict["available_memory_mb"] == 512.0
    assert record_dict["peak_memory_mb"] == 7168.0
    assert record_dict["candles_processed"] == 1_000_000
    assert record_dict["allocation_count"] == 500_000
    assert record_dict["details"] == "Test abort scenario"


def test_emit_memory_abort_log_structure(caplog):
    """Test emit_memory_abort_log produces structured log entry.

    Validates:
    - Returns MemoryAbortRecord instance
    - Logs with ERROR severity
    - Log message contains all key fields
    """
    with caplog.at_level(logging.ERROR):
        record = emit_memory_abort_log(
            reason=MemoryAbortReason.MEMORY_EXHAUSTED,
            phase="scan",
            available_memory_mb=512.0,
            peak_memory_mb=7168.0,
            candles_processed=1_000_000,
            allocation_count=500_000,
            details="Test memory exhaustion",
        )

    # Verify record returned
    assert isinstance(record, MemoryAbortRecord)
    assert record.reason == MemoryAbortReason.MEMORY_EXHAUSTED
    assert record.phase == "scan"
    assert record.available_memory_mb == 512.0

    # Verify structured log entry
    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "ERROR"
    assert "Memory abort triggered" in log_record.message
    assert "memory_exhausted" in log_record.message
    assert "scan" in log_record.message
    assert "512.0" in log_record.message


def test_check_memory_threshold_below_limit(caplog):
    """Test check_memory_threshold triggers abort when below threshold.

    Validates:
    - Returns MemoryAbortRecord when memory below threshold
    - Structured log contains threshold details
    """
    with caplog.at_level(logging.ERROR):
        record = check_memory_threshold(
            available_memory_mb=256.0,
            threshold_mb=512.0,
            phase="scan",
            candles_processed=500_000,
            peak_memory_mb=6144.0,
            allocation_count=300_000,
        )

    # Verify abort triggered
    assert record is not None
    assert isinstance(record, MemoryAbortRecord)
    assert record.reason == MemoryAbortReason.SYSTEM_MEMORY_LOW
    assert record.phase == "scan"
    assert record.available_memory_mb == 256.0
    assert record.candles_processed == 500_000

    # Verify log contains threshold violation details
    assert len(caplog.records) == 1
    assert "Memory abort triggered" in caplog.records[0].message
    assert "system_memory_low" in caplog.records[0].message
    assert "256.0" in caplog.records[0].message
    assert "512.0" in caplog.text


def test_check_memory_threshold_above_limit(caplog):
    """Test check_memory_threshold does NOT trigger when above threshold.

    Validates:
    - Returns None when memory above threshold
    - No abort log emitted
    """
    with caplog.at_level(logging.ERROR):
        record = check_memory_threshold(
            available_memory_mb=1024.0,
            threshold_mb=512.0,
            phase="scan",
            candles_processed=500_000,
            peak_memory_mb=6144.0,
        )

    # Verify no abort triggered
    assert record is None

    # Verify no error logs emitted
    assert len(caplog.records) == 0


def test_memory_abort_different_reasons(caplog):
    """Test memory abort handles different abort reasons correctly."""
    reasons = [
        MemoryAbortReason.MEMORY_EXHAUSTED,
        MemoryAbortReason.ALLOCATION_THRESHOLD_EXCEEDED,
        MemoryAbortReason.SYSTEM_MEMORY_LOW,
    ]

    for reason in reasons:
        caplog.clear()
        with caplog.at_level(logging.ERROR):
            record = emit_memory_abort_log(
                reason=reason,
                phase="test_phase",
                available_memory_mb=512.0,
                details=f"Test {reason.value}",
            )

        assert record.reason == reason
        assert len(caplog.records) == 1
        assert reason.value in caplog.records[0].message


def test_memory_abort_optional_fields():
    """Test memory abort works with minimal required fields only."""
    record = emit_memory_abort_log(
        reason=MemoryAbortReason.MEMORY_EXHAUSTED,
        phase="simulation",
    )

    assert record.reason == MemoryAbortReason.MEMORY_EXHAUSTED
    assert record.phase == "simulation"
    assert record.available_memory_mb is None
    assert record.peak_memory_mb is None
    assert record.candles_processed is None
    assert record.allocation_count is None
    assert record.details is None


def test_memory_abort_timestamp_is_utc():
    """Test memory abort record timestamp is always UTC."""
    record = emit_memory_abort_log(
        reason=MemoryAbortReason.MEMORY_EXHAUSTED,
        phase="scan",
    )

    # Verify timestamp is UTC-aware
    assert record.timestamp.tzinfo is not None
    assert record.timestamp.tzinfo == UTC

    # Verify timestamp is recent (within last 5 seconds)
    now = datetime.now(UTC)
    time_diff = (now - record.timestamp).total_seconds()
    assert time_diff < 5.0


def test_memory_abort_simulation_phase(caplog):
    """Test memory abort during simulation phase.

    Validates abort can be triggered from simulation phase with
    appropriate context.
    """
    with caplog.at_level(logging.ERROR):
        record = emit_memory_abort_log(
            reason=MemoryAbortReason.ALLOCATION_THRESHOLD_EXCEEDED,
            phase="simulation",
            available_memory_mb=768.0,
            peak_memory_mb=8192.0,
            candles_processed=2_000_000,
            allocation_count=1_000_000,
            details="Allocation threshold during position evaluation",
        )

    assert record.phase == "simulation"
    assert record.candles_processed == 2_000_000
    assert "simulation" in caplog.records[0].message
    assert "allocation_threshold_exceeded" in caplog.records[0].message
