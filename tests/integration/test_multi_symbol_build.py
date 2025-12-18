"""Integration test for multi-symbol dataset build.

Feature: 004-timeseries-dataset
Task: T024 - Test multi-symbol orchestration
"""

# pylint: disable=unused-argument unused-import redefined-outer-name

import json
from pathlib import Path

import pandas as pd
import pytest

from src.data_io.dataset_builder import build_all_symbols
from src.models.metadata import BuildSummary, SkipReason


@pytest.fixture
def multi_symbol_data(tmp_path):
    """Create multiple symbol datasets in temp directory.

    Args:
        tmp_path: pytest tmp_path fixture

    Returns:
        Tuple of (raw_path, processed_path)
    """
    raw_path = tmp_path / "raw"
    processed_path = tmp_path / "processed"

    raw_path.mkdir(parents=True)
    processed_path.mkdir(parents=True)

    # Create EURUSD (valid, 600 rows)
    eurusd_dir = raw_path / "eurusd"
    eurusd_dir.mkdir()
    df_eurusd = pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2020-01-01", periods=600, freq="1min", tz="UTC"
            ),
            "open": [1.1000 + i * 0.0001 for i in range(600)],
            "high": [1.1005 + i * 0.0001 for i in range(600)],
            "low": [1.0995 + i * 0.0001 for i in range(600)],
            "close": [1.1002 + i * 0.0001 for i in range(600)],
            "volume": [1000 + i for i in range(600)],
        }
    )
    df_eurusd.to_csv(eurusd_dir / "eurusd.csv", index=False)

    # Create USDJPY (valid, 800 rows)
    usdjpy_dir = raw_path / "usdjpy"
    usdjpy_dir.mkdir()
    df_usdjpy = pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2020-01-01", periods=800, freq="1min", tz="UTC"
            ),
            "open": [110.00 + i * 0.01 for i in range(800)],
            "high": [110.05 + i * 0.01 for i in range(800)],
            "low": [109.95 + i * 0.01 for i in range(800)],
            "close": [110.02 + i * 0.01 for i in range(800)],
            "volume": [2000 + i for i in range(800)],
        }
    )
    df_usdjpy.to_csv(usdjpy_dir / "usdjpy.csv", index=False)

    # Create GBPUSD (insufficient rows - 100)
    gbpusd_dir = raw_path / "gbpusd"
    gbpusd_dir.mkdir()
    df_gbpusd = pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2020-01-01", periods=100, freq="1min", tz="UTC"
            ),
            "open": [1.3000] * 100,
            "high": [1.3005] * 100,
            "low": [1.2995] * 100,
            "close": [1.3002] * 100,
            "volume": [1500] * 100,
        }
    )
    df_gbpusd.to_csv(gbpusd_dir / "gbpusd.csv", index=False)

    # Create AUDUSD (schema mismatch - missing columns)
    audusd_dir = raw_path / "audusd"
    audusd_dir.mkdir()
    df_audusd = pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2020-01-01", periods=600, freq="1min", tz="UTC"
            ),
            "price": [0.7000] * 600,  # Wrong column name
        }
    )
    df_audusd.to_csv(audusd_dir / "audusd.csv", index=False)

    return raw_path, processed_path


class TestMultiSymbolBuild:
    """Integration tests for multi-symbol dataset building."""

    def test_build_all_creates_summary(self, multi_symbol_data):
        """Test that build_all creates build_summary.json."""
        raw_path, processed_path = multi_symbol_data

        summary = build_all_symbols(str(raw_path), str(processed_path))

        assert isinstance(summary, BuildSummary)

        # Check summary file created
        summary_file = processed_path / "build_summary.json"
        assert summary_file.exists()

    def test_build_all_processes_valid_symbols(self, multi_symbol_data):
        """Test that valid symbols are processed successfully."""
        raw_path, processed_path = multi_symbol_data

        summary = build_all_symbols(str(raw_path), str(processed_path))

        # Should process eurusd and usdjpy
        assert len(summary.symbols_processed) == 2
        assert "eurusd" in summary.symbols_processed
        assert "usdjpy" in summary.symbols_processed

    def test_build_all_skips_invalid_symbols(self, multi_symbol_data):
        """Test that invalid symbols are skipped with reasons."""
        raw_path, processed_path = multi_symbol_data

        summary = build_all_symbols(str(raw_path), str(processed_path))

        # Should skip gbpusd (insufficient) and audusd (schema mismatch)
        assert len(summary.symbols_skipped) == 2

        skipped_symbols = {s.symbol: s for s in summary.symbols_skipped}
        assert "gbpusd" in skipped_symbols
        assert "audusd" in skipped_symbols

        # Verify skip reasons
        assert skipped_symbols["gbpusd"].reason == SkipReason.INSUFFICIENT_ROWS
        assert skipped_symbols["audusd"].reason == SkipReason.SCHEMA_MISMATCH

    def test_build_all_correct_row_totals(self, multi_symbol_data):
        """Test that summary contains correct aggregated row counts."""
        raw_path, processed_path = multi_symbol_data

        summary = build_all_symbols(str(raw_path), str(processed_path))

        # eurusd: 600 rows, usdjpy: 800 rows = 1400 total
        assert summary.total_rows_processed == 1400

        # eurusd: 480 test, usdjpy: 640 test = 1120 total test
        assert summary.total_test_rows == 1120

        # eurusd: 120 validation, usdjpy: 160 validation = 280 total validation
        assert summary.total_validation_rows == 280

    def test_build_all_row_count_consistency(self, multi_symbol_data):
        """Test that test + validation = total rows."""
        raw_path, processed_path = multi_symbol_data

        summary = build_all_symbols(str(raw_path), str(processed_path))

        assert (
            summary.total_test_rows + summary.total_validation_rows
            == summary.total_rows_processed
        )

    def test_build_all_creates_output_directories(self, multi_symbol_data):
        """Test that output directories are created for all processed symbols."""
        raw_path, processed_path = multi_symbol_data

        build_all_symbols(str(raw_path), str(processed_path))

        # Check eurusd outputs
        eurusd_dir = processed_path / "eurusd"
        assert eurusd_dir.exists()
        assert (eurusd_dir / "test").exists()
        assert (eurusd_dir / "validate").exists()
        assert (eurusd_dir / "metadata.json").exists()

        # Check usdjpy outputs
        usdjpy_dir = processed_path / "usdjpy"
        assert usdjpy_dir.exists()
        assert (usdjpy_dir / "test").exists()
        assert (usdjpy_dir / "validate").exists()
        assert (usdjpy_dir / "metadata.json").exists()

        # Skipped symbols should not have outputs
        assert not (processed_path / "gbpusd" / "test").exists()
        assert not (processed_path / "audusd" / "test").exists()

    def test_build_all_duration_recorded(self, multi_symbol_data):
        """Test that build duration is recorded in summary."""
        raw_path, processed_path = multi_symbol_data

        summary = build_all_symbols(str(raw_path), str(processed_path))

        assert summary.duration_seconds > 0
        assert summary.duration_seconds < 60  # Should be fast for small datasets

    def test_build_all_timestamps_ordered(self, multi_symbol_data):
        """Test that build_completed_at >= build_timestamp."""
        raw_path, processed_path = multi_symbol_data

        summary = build_all_symbols(str(raw_path), str(processed_path))

        assert summary.build_completed_at >= summary.build_timestamp

    def test_build_all_summary_json_valid(self, multi_symbol_data):
        """Test that summary JSON file contains valid data."""
        raw_path, processed_path = multi_symbol_data

        build_all_symbols(str(raw_path), str(processed_path))

        summary_file = processed_path / "build_summary.json"
        with open(summary_file, encoding="utf-8") as f:
            summary_json = json.load(f)

        assert "build_timestamp" in summary_json
        assert "build_completed_at" in summary_json
        assert "symbols_processed" in summary_json
        assert "symbols_skipped" in summary_json
        assert "total_rows_processed" in summary_json
        assert "duration_seconds" in summary_json

        assert len(summary_json["symbols_processed"]) == 2
        assert len(summary_json["symbols_skipped"]) == 2

    def test_build_all_empty_directory(self, tmp_path):
        """Test build_all with no symbols."""
        raw_path = tmp_path / "raw"
        processed_path = tmp_path / "processed"
        raw_path.mkdir(parents=True)

        summary = build_all_symbols(str(raw_path), str(processed_path))

        assert len(summary.symbols_processed) == 0
        assert len(summary.symbols_skipped) == 0
        assert summary.total_rows_processed == 0

    def test_build_all_individual_metadata_files(self, multi_symbol_data):
        """Test that each processed symbol has valid metadata.json."""
        raw_path, processed_path = multi_symbol_data

        build_all_symbols(str(raw_path), str(processed_path))

        # Check eurusd metadata
        eurusd_metadata = processed_path / "eurusd" / "metadata.json"
        with open(eurusd_metadata, encoding="utf-8") as f:
            eurusd_data = json.load(f)
        assert eurusd_data["symbol"] == "eurusd"
        assert eurusd_data["total_rows"] == 600

        # Check usdjpy metadata
        usdjpy_metadata = processed_path / "usdjpy" / "metadata.json"
        with open(usdjpy_metadata, encoding="utf-8") as f:
            usdjpy_data = json.load(f)
        assert usdjpy_data["symbol"] == "usdjpy"
        assert usdjpy_data["total_rows"] == 800

    def test_build_all_partition_files_exist(self, multi_symbol_data):
        """Test that partition CSV files are created for all processed symbols."""
        raw_path, processed_path = multi_symbol_data

        build_all_symbols(str(raw_path), str(processed_path))

        # Check eurusd partitions
        assert (processed_path / "eurusd" / "test" / "eurusd_test.csv").exists()
        assert (processed_path / "eurusd" / "validate" / "eurusd_validate.csv").exists()

        # Check usdjpy partitions
        assert (processed_path / "usdjpy" / "test" / "usdjpy_test.csv").exists()
        assert (processed_path / "usdjpy" / "validate" / "usdjpy_validate.csv").exists()

    def test_build_all_no_silent_failures(self, multi_symbol_data):
        """Test that all skipped symbols have explicit reasons."""
        raw_path, processed_path = multi_symbol_data

        summary = build_all_symbols(str(raw_path), str(processed_path))

        for skipped in summary.symbols_skipped:
            assert skipped.reason is not None
            assert skipped.details is not None
            assert len(skipped.details) > 0
