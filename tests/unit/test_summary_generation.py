"""Unit tests for build summary generation and validation.

Feature: 004-timeseries-dataset
Task: T026 - Test summary validation
"""

# pylint: disable=unused-import

from datetime import datetime, timezone, timedelta
import pytest

from src.io.dataset_builder import build_summary
from src.models.metadata import BuildSummary, SkippedSymbol, SkipReason


class TestSummaryGeneration:
    """Test build summary generation and validation."""

    def test_summary_basic_fields(self):
        """Test that summary contains all required fields."""
        start = datetime(2025, 10, 30, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 10, 30, 10, 5, 0, tzinfo=timezone.utc)

        summary = build_summary(
            build_start=start,
            build_end=end,
            symbols_processed=["eurusd", "usdjpy"],
            symbols_skipped=[],
            total_rows=1400,
            total_test_rows=1120,
            total_validation_rows=280,
        )

        assert isinstance(summary, BuildSummary)
        assert summary.build_timestamp == start
        assert summary.build_completed_at == end
        assert len(summary.symbols_processed) == 2
        assert len(summary.symbols_skipped) == 0
        assert summary.total_rows_processed == 1400
        assert summary.total_test_rows == 1120
        assert summary.total_validation_rows == 280

    def test_summary_duration_calculation(self):
        """Test that duration is correctly calculated."""
        start = datetime(2025, 10, 30, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(
            2025, 10, 30, 10, 5, 30, tzinfo=timezone.utc
        )  # 5.5 minutes later

        summary = build_summary(
            build_start=start,
            build_end=end,
            symbols_processed=["eurusd"],
            symbols_skipped=[],
            total_rows=600,
            total_test_rows=480,
            total_validation_rows=120,
        )

        assert summary.duration_seconds == 330.0  # 5.5 * 60

    def test_summary_with_skipped_symbols(self):
        """Test summary with skipped symbols."""
        start = datetime(2025, 10, 30, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 10, 30, 10, 1, 0, tzinfo=timezone.utc)

        skipped = [
            SkippedSymbol(
                symbol="gbpusd",
                reason=SkipReason.INSUFFICIENT_ROWS,
                details="Only 100 rows, minimum 500 required",
            ),
            SkippedSymbol(
                symbol="audusd",
                reason=SkipReason.SCHEMA_MISMATCH,
                details="Missing required column: close",
            ),
        ]

        summary = build_summary(
            build_start=start,
            build_end=end,
            symbols_processed=["eurusd"],
            symbols_skipped=skipped,
            total_rows=600,
            total_test_rows=480,
            total_validation_rows=120,
        )

        assert len(summary.symbols_skipped) == 2
        assert summary.symbols_skipped[0].symbol == "gbpusd"
        assert summary.symbols_skipped[1].symbol == "audusd"
        assert summary.symbols_skipped[0].reason == SkipReason.INSUFFICIENT_ROWS
        assert summary.symbols_skipped[1].reason == SkipReason.SCHEMA_MISMATCH

    def test_summary_row_count_consistency(self):
        """Test that test + validation rows equals total rows."""
        start = datetime(2025, 10, 30, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 10, 30, 10, 1, 0, tzinfo=timezone.utc)

        summary = build_summary(
            build_start=start,
            build_end=end,
            symbols_processed=["eurusd", "usdjpy"],
            symbols_skipped=[],
            total_rows=1400,
            total_test_rows=1120,
            total_validation_rows=280,
        )

        assert (
            summary.total_test_rows + summary.total_validation_rows
            == summary.total_rows_processed
        )

    def test_summary_invalid_row_counts(self):
        """Test that inconsistent row counts raise validation error."""
        start = datetime(2025, 10, 30, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 10, 30, 10, 1, 0, tzinfo=timezone.utc)

        with pytest.raises(ValueError, match="must equal total_rows_processed"):
            build_summary(
                build_start=start,
                build_end=end,
                symbols_processed=["eurusd"],
                symbols_skipped=[],
                total_rows=1000,
                total_test_rows=800,
                total_validation_rows=300,  # 800 + 300 != 1000
            )

    def test_summary_invalid_timestamps(self):
        """Test that end before start raises validation error."""
        start = datetime(2025, 10, 30, 10, 5, 0, tzinfo=timezone.utc)
        end = datetime(2025, 10, 30, 10, 0, 0, tzinfo=timezone.utc)  # Before start!

        with pytest.raises(
            ValueError, match="build_completed_at must be >= build_timestamp"
        ):
            build_summary(
                build_start=start,
                build_end=end,
                symbols_processed=["eurusd"],
                symbols_skipped=[],
                total_rows=600,
                total_test_rows=480,
                total_validation_rows=120,
            )

    def test_summary_zero_rows(self):
        """Test summary with no symbols processed."""
        start = datetime(2025, 10, 30, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 10, 30, 10, 0, 1, tzinfo=timezone.utc)

        summary = build_summary(
            build_start=start,
            build_end=end,
            symbols_processed=[],
            symbols_skipped=[],
            total_rows=0,
            total_test_rows=0,
            total_validation_rows=0,
        )

        assert summary.total_rows_processed == 0
        assert summary.total_test_rows == 0
        assert summary.total_validation_rows == 0
        assert len(summary.symbols_processed) == 0

    def test_summary_all_skipped(self):
        """Test summary where all symbols were skipped."""
        start = datetime(2025, 10, 30, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 10, 30, 10, 1, 0, tzinfo=timezone.utc)

        skipped = [
            SkippedSymbol(
                symbol="gbpusd",
                reason=SkipReason.INSUFFICIENT_ROWS,
                details="Insufficient data",
            ),
            SkippedSymbol(
                symbol="audusd",
                reason=SkipReason.SCHEMA_MISMATCH,
                details="Schema error",
            ),
        ]

        summary = build_summary(
            build_start=start,
            build_end=end,
            symbols_processed=[],
            symbols_skipped=skipped,
            total_rows=0,
            total_test_rows=0,
            total_validation_rows=0,
        )

        assert len(summary.symbols_processed) == 0
        assert len(summary.symbols_skipped) == 2
        assert summary.total_rows_processed == 0

    def test_summary_no_silent_failures(self):
        """Test that all skipped symbols have explicit reasons and details."""
        start = datetime(2025, 10, 30, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 10, 30, 10, 1, 0, tzinfo=timezone.utc)

        skipped = [
            SkippedSymbol(
                symbol="gbpusd",
                reason=SkipReason.INSUFFICIENT_ROWS,
                details="Only 100 rows",
            ),
        ]

        summary = build_summary(
            build_start=start,
            build_end=end,
            symbols_processed=["eurusd"],
            symbols_skipped=skipped,
            total_rows=600,
            total_test_rows=480,
            total_validation_rows=120,
        )

        for skipped_symbol in summary.symbols_skipped:
            assert skipped_symbol.reason is not None
            assert skipped_symbol.details is not None
            assert len(skipped_symbol.details) > 0

    def test_summary_json_serialization(self):
        """Test that summary can be serialized to JSON."""
        start = datetime(2025, 10, 30, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 10, 30, 10, 1, 0, tzinfo=timezone.utc)

        summary = build_summary(
            build_start=start,
            build_end=end,
            symbols_processed=["eurusd", "usdjpy"],
            symbols_skipped=[],
            total_rows=1400,
            total_test_rows=1120,
            total_validation_rows=280,
        )

        # Test pydantic model_dump
        json_data = summary.model_dump(mode="json")

        assert json_data["total_rows_processed"] == 1400
        assert json_data["total_test_rows"] == 1120
        assert json_data["total_validation_rows"] == 280
        assert len(json_data["symbols_processed"]) == 2
        assert isinstance(json_data["build_timestamp"], str)
        assert isinstance(json_data["duration_seconds"], (int, float))

    def test_summary_large_dataset(self):
        """Test summary with large row counts."""
        start = datetime(2025, 10, 30, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 10, 30, 10, 10, 0, tzinfo=timezone.utc)

        summary = build_summary(
            build_start=start,
            build_end=end,
            symbols_processed=["eurusd"] * 10,
            symbols_skipped=[],
            total_rows=10_000_000,
            total_test_rows=8_000_000,
            total_validation_rows=2_000_000,
        )

        assert summary.total_rows_processed == 10_000_000
        assert summary.total_test_rows == 8_000_000
        assert summary.total_validation_rows == 2_000_000
        assert summary.duration_seconds == 600.0

    def test_summary_skip_reason_enum_values(self):
        """Test that all skip reason enum values are valid."""
        start = datetime(2025, 10, 30, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 10, 30, 10, 1, 0, tzinfo=timezone.utc)

        # Test all three skip reasons
        skipped = [
            SkippedSymbol(
                symbol="sym1", reason=SkipReason.INSUFFICIENT_ROWS, details="Detail 1"
            ),
            SkippedSymbol(
                symbol="sym2", reason=SkipReason.SCHEMA_MISMATCH, details="Detail 2"
            ),
            SkippedSymbol(
                symbol="sym3", reason=SkipReason.READ_ERROR, details="Detail 3"
            ),
        ]

        summary = build_summary(
            build_start=start,
            build_end=end,
            symbols_processed=[],
            symbols_skipped=skipped,
            total_rows=0,
            total_test_rows=0,
            total_validation_rows=0,
        )

        assert summary.symbols_skipped[0].reason == SkipReason.INSUFFICIENT_ROWS
        assert summary.symbols_skipped[1].reason == SkipReason.SCHEMA_MISMATCH
        assert summary.symbols_skipped[2].reason == SkipReason.READ_ERROR
