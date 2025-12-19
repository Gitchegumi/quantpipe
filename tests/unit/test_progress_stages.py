"""Unit tests for progress stage names and limit enforcement (T099, FR-010, NFR-003)."""

import pytest

from src.data_io.logging_constants import MAX_PROGRESS_UPDATES, IngestionStage
from src.data_io.progress import ProgressReporter


def test_max_progress_updates_constant():
    """Test that MAX_PROGRESS_UPDATES is set to 5 per NFR-003."""
    assert (
        MAX_PROGRESS_UPDATES == 5
    ), f"NFR-003: MAX_PROGRESS_UPDATES must be 5, got {MAX_PROGRESS_UPDATES}"


def test_ingestion_stage_names():
    """Test that IngestionStage enum has expected stage names (FR-010)."""
    expected_stages = {"READ", "PROCESS", "GAP_FILL", "SCHEMA", "FINALIZE"}
    actual_stages = {stage.name for stage in IngestionStage}

    assert actual_stages == expected_stages, (
        f"FR-010: IngestionStage names mismatch.\n"
        f"Expected: {expected_stages}\n"
        f"Actual: {actual_stages}"
    )


def test_ingestion_stage_values():
    """Test that IngestionStage enum values are lowercase."""
    for stage in IngestionStage:
        assert (
            stage.value.islower()
        ), f"Stage value should be lowercase: {stage.name}={stage.value}"


def test_ingestion_stage_count_matches_max():
    """Test that number of IngestionStage members equals MAX_PROGRESS_UPDATES."""
    stage_count = len(IngestionStage)
    assert stage_count == MAX_PROGRESS_UPDATES, (
        f"IngestionStage has {stage_count} members but "
        f"MAX_PROGRESS_UPDATES={MAX_PROGRESS_UPDATES}"
    )


def test_progress_reporter_can_be_instantiated():
    """Test ProgressReporter can be created with show_progress flag."""
    # With progress enabled
    reporter = ProgressReporter(show_progress=True)
    assert reporter.show_progress is True

    # With progress disabled
    reporter_disabled = ProgressReporter(show_progress=False)
    assert reporter_disabled.show_progress is False


def test_progress_reporter_can_report_stages():
    """Test ProgressReporter can report stages without errors."""
    reporter = ProgressReporter(show_progress=False)

    # Should not raise
    reporter.start_stage(IngestionStage.READ, "Loading data", total=1000)
    reporter.update_progress(advance=100)
    reporter.report_stage(IngestionStage.PROCESS, message="Processing")
    reporter.finish()
