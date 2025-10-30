"""Integration test for single-symbol dataset build.

Feature: 004-timeseries-dataset
Task: T020 - Test end-to-end single-symbol build
"""

# pylint: disable=unused-argument unused-import redefined-outer-name

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from src.io.dataset_builder import build_symbol_dataset
from src.models.metadata import MetadataRecord


@pytest.fixture
def temp_data_dirs(tmp_path):
    """Create temporary raw and processed data directories.

    Args:
        tmp_path: pytest tmp_path fixture

    Yields:
        Tuple of (raw_path, processed_path) Path objects
    """
    raw_path = tmp_path / "raw"
    processed_path = tmp_path / "processed"

    raw_path.mkdir(parents=True)
    processed_path.mkdir(parents=True)

    yield raw_path, processed_path

    # Cleanup handled by tmp_path


@pytest.fixture
def sample_eurusd_data(temp_data_dirs):
    """Create sample EURUSD CSV files in temp raw directory.

    Args:
        temp_data_dirs: Fixture providing raw/processed paths

    Returns:
        Path to symbol directory
    """
    raw_path, _ = temp_data_dirs
    symbol_dir = raw_path / "eurusd"
    symbol_dir.mkdir()

    # Create two CSV files to test merging
    df1 = pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2020-01-01", periods=300, freq="1min", tz="UTC"
            ),
            "open": [1.1000 + i * 0.0001 for i in range(300)],
            "high": [1.1005 + i * 0.0001 for i in range(300)],
            "low": [1.0995 + i * 0.0001 for i in range(300)],
            "close": [1.1002 + i * 0.0001 for i in range(300)],
            "volume": [1000 + i for i in range(300)],
        }
    )

    df2 = pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2020-01-01 05:00", periods=300, freq="1min", tz="UTC"
            ),
            "open": [1.1030 + i * 0.0001 for i in range(300)],
            "high": [1.1035 + i * 0.0001 for i in range(300)],
            "low": [1.1025 + i * 0.0001 for i in range(300)],
            "close": [1.1032 + i * 0.0001 for i in range(300)],
            "volume": [1300 + i for i in range(300)],
        }
    )

    df1.to_csv(symbol_dir / "eurusd_part1.csv", index=False)
    df2.to_csv(symbol_dir / "eurusd_part2.csv", index=False)

    return symbol_dir


class TestSingleSymbolBuild:
    """Integration tests for single-symbol dataset building."""

    def test_build_creates_output_structure(self, temp_data_dirs, sample_eurusd_data):
        """Test that build creates expected directory structure."""
        raw_path, processed_path = temp_data_dirs

        result = build_symbol_dataset("eurusd", str(raw_path), str(processed_path))

        assert result["success"] is True

        # Check directory structure
        symbol_output = processed_path / "eurusd"
        assert symbol_output.exists()
        assert (symbol_output / "test").exists()
        assert (symbol_output / "validate").exists()
        assert (symbol_output / "metadata.json").exists()

    def test_build_creates_partition_files(self, temp_data_dirs, sample_eurusd_data):
        """Test that build creates CSV partition files."""
        raw_path, processed_path = temp_data_dirs

        result = build_symbol_dataset("eurusd", str(raw_path), str(processed_path))

        assert result["success"] is True

        symbol_output = processed_path / "eurusd"
        test_csv = symbol_output / "test" / "eurusd_test.csv"
        validate_csv = symbol_output / "validate" / "eurusd_validate.csv"

        assert test_csv.exists()
        assert validate_csv.exists()

    def test_build_correct_row_counts(self, temp_data_dirs, sample_eurusd_data):
        """Test that partitions have correct 80/20 split."""
        raw_path, processed_path = temp_data_dirs

        result = build_symbol_dataset("eurusd", str(raw_path), str(processed_path))

        assert result["success"] is True
        metadata = result["metadata"]

        # 600 rows total -> 480 test, 120 validation
        assert metadata.total_rows == 600
        assert metadata.test_rows == 480
        assert metadata.validation_rows == 120

    def test_build_partition_csv_contents(self, temp_data_dirs, sample_eurusd_data):
        """Test that partition CSV files contain expected data."""
        raw_path, processed_path = temp_data_dirs

        result = build_symbol_dataset("eurusd", str(raw_path), str(processed_path))

        assert result["success"] is True

        symbol_output = processed_path / "eurusd"
        test_df = pd.read_csv(symbol_output / "test" / "eurusd_test.csv")
        validate_df = pd.read_csv(symbol_output / "validate" / "eurusd_validate.csv")

        assert len(test_df) == 480
        assert len(validate_df) == 120
        assert set(test_df.columns) == {
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        }
        assert set(validate_df.columns) == {
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        }

    def test_build_metadata_json_valid(self, temp_data_dirs, sample_eurusd_data):
        """Test that metadata JSON is valid and contains expected fields."""
        raw_path, processed_path = temp_data_dirs

        result = build_symbol_dataset("eurusd", str(raw_path), str(processed_path))

        assert result["success"] is True

        metadata_file = processed_path / "eurusd" / "metadata.json"
        with open(metadata_file, encoding="utf-8") as f:
            metadata_json = json.load(f)

        assert metadata_json["symbol"] == "eurusd"
        assert metadata_json["total_rows"] == 600
        assert metadata_json["test_rows"] == 480
        assert metadata_json["validation_rows"] == 120
        assert metadata_json["canonical_timezone"] == "UTC"
        assert metadata_json["schema_version"] == "v1"
        assert "start_timestamp" in metadata_json
        assert "end_timestamp" in metadata_json
        assert "validation_start_timestamp" in metadata_json

    def test_build_validation_most_recent(self, temp_data_dirs, sample_eurusd_data):
        """Test that validation partition contains most recent data."""
        raw_path, processed_path = temp_data_dirs

        result = build_symbol_dataset("eurusd", str(raw_path), str(processed_path))

        assert result["success"] is True

        symbol_output = processed_path / "eurusd"
        test_df = pd.read_csv(symbol_output / "test" / "eurusd_test.csv")
        validate_df = pd.read_csv(symbol_output / "validate" / "eurusd_validate.csv")

        # Parse timestamps
        test_df["timestamp"] = pd.to_datetime(test_df["timestamp"])
        validate_df["timestamp"] = pd.to_datetime(validate_df["timestamp"])

        # Validation should have later timestamps
        assert test_df["timestamp"].max() < validate_df["timestamp"].min()

    def test_build_insufficient_rows(self, temp_data_dirs):
        """Test that build skips symbol with insufficient rows."""
        raw_path, processed_path = temp_data_dirs

        # Create small dataset (< 500 rows)
        symbol_dir = raw_path / "small"
        symbol_dir.mkdir()

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2020-01-01", periods=100, freq="1min", tz="UTC"
                ),
                "open": [1.1000] * 100,
                "high": [1.1005] * 100,
                "low": [1.0995] * 100,
                "close": [1.1002] * 100,
                "volume": [1000] * 100,
            }
        )
        df.to_csv(symbol_dir / "small.csv", index=False)

        result = build_symbol_dataset("small", str(raw_path), str(processed_path))

        assert result["success"] is False
        assert result["skip_reason"].value == "insufficient_rows"

    def test_build_schema_mismatch(self, temp_data_dirs):
        """Test that build skips symbol with schema mismatch."""
        raw_path, processed_path = temp_data_dirs

        symbol_dir = raw_path / "bad_schema"
        symbol_dir.mkdir()

        # Create CSV with missing required columns
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2020-01-01", periods=600, freq="1min", tz="UTC"
                ),
                "price": [1.1000] * 600,  # Wrong column name
            }
        )
        df.to_csv(symbol_dir / "bad.csv", index=False)

        result = build_symbol_dataset("bad_schema", str(raw_path), str(processed_path))

        assert result["success"] is False
        assert result["skip_reason"].value == "schema_mismatch"

    def test_build_no_csv_files(self, temp_data_dirs):
        """Test that build skips symbol with no CSV files."""
        raw_path, processed_path = temp_data_dirs

        symbol_dir = raw_path / "empty"
        symbol_dir.mkdir()
        # No CSV files created

        result = build_symbol_dataset("empty", str(raw_path), str(processed_path))

        assert result["success"] is False
        assert result["skip_reason"].value == "read_error"

    def test_build_metadata_pydantic_model(self, temp_data_dirs, sample_eurusd_data):
        """Test that returned metadata is valid pydantic model."""
        raw_path, processed_path = temp_data_dirs

        result = build_symbol_dataset("eurusd", str(raw_path), str(processed_path))

        assert result["success"] is True
        assert isinstance(result["metadata"], MetadataRecord)

        # Test model validation passed
        assert (
            result["metadata"].test_rows + result["metadata"].validation_rows
            == result["metadata"].total_rows
        )
