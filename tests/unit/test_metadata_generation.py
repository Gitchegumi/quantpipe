"""Unit tests for metadata generation.

Feature: 004-timeseries-dataset
Task: T019 - Test metadata correctness
"""

from datetime import datetime, timezone
import pytest

from src.io.dataset_builder import build_metadata
from src.models.metadata import MetadataRecord


class TestMetadataGeneration:
    """Test metadata record builder correctness."""

    def test_metadata_basic_fields(self):
        """Test that metadata contains all required fields."""
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2020, 1, 2, tzinfo=timezone.utc)
        validation_start = datetime(2020, 1, 1, 20, 0, tzinfo=timezone.utc)

        metadata = build_metadata(
            symbol="eurusd",
            total_rows=1000,
            test_rows=800,
            validation_rows=200,
            start_timestamp=start,
            end_timestamp=end,
            validation_start_timestamp=validation_start,
            gap_count=5,
            overlap_count=3,
            source_files=["file1.csv", "file2.csv"],
        )

        assert isinstance(metadata, MetadataRecord)
        assert metadata.symbol == "eurusd"
        assert metadata.total_rows == 1000
        assert metadata.test_rows == 800
        assert metadata.validation_rows == 200
        assert metadata.start_timestamp == start
        assert metadata.end_timestamp == end
        assert metadata.validation_start_timestamp == validation_start
        assert metadata.gap_count == 5
        assert metadata.overlap_count == 3
        assert metadata.canonical_timezone == "UTC"
        assert metadata.schema_version == "v1"
        assert len(metadata.source_files) == 2

    def test_metadata_row_count_consistency(self):
        """Test that test_rows + validation_rows equals total_rows."""
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2020, 1, 2, tzinfo=timezone.utc)
        validation_start = datetime(2020, 1, 1, 20, 0, tzinfo=timezone.utc)

        metadata = build_metadata(
            symbol="eurusd",
            total_rows=600,
            test_rows=480,
            validation_rows=120,
            start_timestamp=start,
            end_timestamp=end,
            validation_start_timestamp=validation_start,
            gap_count=0,
            overlap_count=0,
            source_files=["test.csv"],
        )

        assert metadata.test_rows + metadata.validation_rows == metadata.total_rows

    def test_metadata_invalid_row_counts(self):
        """Test that inconsistent row counts raise validation error."""
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2020, 1, 2, tzinfo=timezone.utc)
        validation_start = datetime(2020, 1, 1, 20, 0, tzinfo=timezone.utc)

        with pytest.raises(ValueError, match="must equal total_rows"):
            build_metadata(
                symbol="eurusd",
                total_rows=1000,
                test_rows=800,
                validation_rows=300,  # 800 + 300 != 1000
                start_timestamp=start,
                end_timestamp=end,
                validation_start_timestamp=validation_start,
                gap_count=0,
                overlap_count=0,
                source_files=["test.csv"],
            )

    def test_metadata_timestamp_ordering(self):
        """Test that end_timestamp >= start_timestamp."""
        start = datetime(2020, 1, 2, tzinfo=timezone.utc)
        end = datetime(2020, 1, 1, tzinfo=timezone.utc)  # Before start!
        validation_start = datetime(2020, 1, 1, 12, 0, tzinfo=timezone.utc)

        with pytest.raises(
            ValueError, match="end_timestamp must be >= start_timestamp"
        ):
            build_metadata(
                symbol="eurusd",
                total_rows=600,
                test_rows=480,
                validation_rows=120,
                start_timestamp=start,
                end_timestamp=end,
                validation_start_timestamp=validation_start,
                gap_count=0,
                overlap_count=0,
                source_files=["test.csv"],
            )

    def test_metadata_validation_timestamp_range(self):
        """Test that validation_start is between start and end timestamps."""
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2020, 1, 2, tzinfo=timezone.utc)
        validation_start = datetime(2020, 1, 3, tzinfo=timezone.utc)  # After end!

        with pytest.raises(
            ValueError, match="validation_start_timestamp must be between"
        ):
            build_metadata(
                symbol="eurusd",
                total_rows=600,
                test_rows=480,
                validation_rows=120,
                start_timestamp=start,
                end_timestamp=end,
                validation_start_timestamp=validation_start,
                gap_count=0,
                overlap_count=0,
                source_files=["test.csv"],
            )

    def test_metadata_utc_timezone(self):
        """Test that canonical_timezone is always UTC."""
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2020, 1, 2, tzinfo=timezone.utc)
        validation_start = datetime(2020, 1, 1, 20, 0, tzinfo=timezone.utc)

        metadata = build_metadata(
            symbol="eurusd",
            total_rows=600,
            test_rows=480,
            validation_rows=120,
            start_timestamp=start,
            end_timestamp=end,
            validation_start_timestamp=validation_start,
            gap_count=0,
            overlap_count=0,
            source_files=["test.csv"],
        )

        assert metadata.canonical_timezone == "UTC"

    def test_metadata_zero_gaps_overlaps(self):
        """Test metadata with zero gaps and overlaps."""
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2020, 1, 2, tzinfo=timezone.utc)
        validation_start = datetime(2020, 1, 1, 20, 0, tzinfo=timezone.utc)

        metadata = build_metadata(
            symbol="eurusd",
            total_rows=600,
            test_rows=480,
            validation_rows=120,
            start_timestamp=start,
            end_timestamp=end,
            validation_start_timestamp=validation_start,
            gap_count=0,
            overlap_count=0,
            source_files=["test.csv"],
        )

        assert metadata.gap_count == 0
        assert metadata.overlap_count == 0

    def test_metadata_build_timestamp_set(self):
        """Test that build_timestamp is automatically set."""
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2020, 1, 2, tzinfo=timezone.utc)
        validation_start = datetime(2020, 1, 1, 20, 0, tzinfo=timezone.utc)

        before_build = datetime.now(timezone.utc)
        metadata = build_metadata(
            symbol="eurusd",
            total_rows=600,
            test_rows=480,
            validation_rows=120,
            start_timestamp=start,
            end_timestamp=end,
            validation_start_timestamp=validation_start,
            gap_count=0,
            overlap_count=0,
            source_files=["test.csv"],
        )
        after_build = datetime.now(timezone.utc)

        assert before_build <= metadata.build_timestamp <= after_build

    def test_metadata_json_serialization(self):
        """Test that metadata can be serialized to JSON."""
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2020, 1, 2, tzinfo=timezone.utc)
        validation_start = datetime(2020, 1, 1, 20, 0, tzinfo=timezone.utc)

        metadata = build_metadata(
            symbol="eurusd",
            total_rows=600,
            test_rows=480,
            validation_rows=120,
            start_timestamp=start,
            end_timestamp=end,
            validation_start_timestamp=validation_start,
            gap_count=0,
            overlap_count=0,
            source_files=["test.csv"],
        )

        # Test pydantic model_dump
        json_data = metadata.model_dump(mode="json")

        assert json_data["symbol"] == "eurusd"
        assert json_data["total_rows"] == 600
        assert json_data["canonical_timezone"] == "UTC"
        assert isinstance(json_data["start_timestamp"], str)
