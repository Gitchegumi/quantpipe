"""
Unit tests for path construction logic.

Tests cover:
- Single pair path construction
- Multi-pair path construction
- Parquet preferred over CSV fallback

Feature: 013-multi-symbol-backtest
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestPathConstruction:
    """Tests for dataset path construction (US2)."""

    def test_path_construction_single_pair(self, tmp_path: Path):
        """T012: Verify path construction for single pair.

        Given a single pair with valid Parquet file,
        When construct_data_paths() is called,
        Then it returns a list with one (pair, path) tuple.
        """
        from src.cli.run_backtest import construct_data_paths

        # Setup: Create test directory structure
        pair_dir = tmp_path / "eurusd" / "test"
        pair_dir.mkdir(parents=True)
        parquet_file = pair_dir / "eurusd_test.parquet"
        parquet_file.write_bytes(b"mock_parquet_data")

        # Execute
        result = construct_data_paths(
            pairs=["EURUSD"],
            dataset="test",
            base_dir=tmp_path,
        )

        # Verify
        assert len(result) == 1
        assert result[0][0] == "EURUSD"
        assert result[0][1] == parquet_file

    def test_path_construction_multi_pair(self, tmp_path: Path):
        """T013: Verify path construction for multiple pairs.

        Given multiple pairs with valid data files,
        When construct_data_paths() is called with multiple pairs,
        Then it returns a list with all (pair, path) tuples.
        """
        from src.cli.run_backtest import construct_data_paths

        # Setup: Create test directory structure for both pairs
        eurusd_dir = tmp_path / "eurusd" / "test"
        eurusd_dir.mkdir(parents=True)
        eurusd_file = eurusd_dir / "eurusd_test.parquet"
        eurusd_file.write_bytes(b"mock_eurusd_data")

        usdjpy_dir = tmp_path / "usdjpy" / "test"
        usdjpy_dir.mkdir(parents=True)
        usdjpy_file = usdjpy_dir / "usdjpy_test.parquet"
        usdjpy_file.write_bytes(b"mock_usdjpy_data")

        # Execute
        result = construct_data_paths(
            pairs=["EURUSD", "USDJPY"],
            dataset="test",
            base_dir=tmp_path,
        )

        # Verify
        assert len(result) == 2

        # Check both pairs are present (order may vary)
        pairs = [r[0] for r in result]
        assert "EURUSD" in pairs
        assert "USDJPY" in pairs

        # Check paths are correct
        paths_by_pair = {r[0]: r[1] for r in result}
        assert paths_by_pair["EURUSD"] == eurusd_file
        assert paths_by_pair["USDJPY"] == usdjpy_file

    def test_path_parquet_preferred_over_csv(self, tmp_path: Path):
        """T014: Verify Parquet files are preferred over CSV.

        Given a pair with both Parquet and CSV files,
        When construct_data_paths() is called,
        Then it returns the Parquet path, not CSV.
        """
        from src.cli.run_backtest import construct_data_paths

        # Setup: Create both Parquet and CSV files
        pair_dir = tmp_path / "eurusd" / "test"
        pair_dir.mkdir(parents=True)

        parquet_file = pair_dir / "eurusd_test.parquet"
        parquet_file.write_bytes(b"mock_parquet_data")

        csv_file = pair_dir / "eurusd_test.csv"
        csv_file.write_text("timestamp,open,high,low,close\n")

        # Execute
        result = construct_data_paths(
            pairs=["EURUSD"],
            dataset="test",
            base_dir=tmp_path,
        )

        # Verify: Parquet path returned, not CSV
        assert len(result) == 1
        assert result[0][1] == parquet_file
        assert result[0][1].suffix == ".parquet"

    def test_path_csv_fallback_when_no_parquet(self, tmp_path: Path):
        """Verify CSV is used when Parquet doesn't exist.

        Given a pair with only CSV file (no Parquet),
        When construct_data_paths() is called,
        Then it returns the CSV path as fallback.
        """
        from src.cli.run_backtest import construct_data_paths

        # Setup: Create only CSV file
        pair_dir = tmp_path / "eurusd" / "test"
        pair_dir.mkdir(parents=True)

        csv_file = pair_dir / "eurusd_test.csv"
        csv_file.write_text("timestamp,open,high,low,close\n")

        # Execute
        result = construct_data_paths(
            pairs=["EURUSD"],
            dataset="test",
            base_dir=tmp_path,
        )

        # Verify: CSV path returned as fallback
        assert len(result) == 1
        assert result[0][1] == csv_file
        assert result[0][1].suffix == ".csv"

    def test_path_missing_pair_skipped(self, tmp_path: Path):
        """Verify missing pairs are skipped with warning.

        Given two pairs where only one has data,
        When construct_data_paths() is called,
        Then it returns only the valid pair and skips missing.
        """
        from src.cli.run_backtest import construct_data_paths

        # Setup: Create data for only one pair
        eurusd_dir = tmp_path / "eurusd" / "test"
        eurusd_dir.mkdir(parents=True)
        eurusd_file = eurusd_dir / "eurusd_test.parquet"
        eurusd_file.write_bytes(b"mock_eurusd_data")

        # USDJPY directory doesn't exist

        # Execute
        result = construct_data_paths(
            pairs=["EURUSD", "USDJPY"],
            dataset="test",
            base_dir=tmp_path,
        )

        # Verify: Only EURUSD returned
        assert len(result) == 1
        assert result[0][0] == "EURUSD"

    def test_path_all_missing_exits(self, tmp_path: Path):
        """Verify sys.exit is called when all pairs missing.

        Given pairs with no data files,
        When construct_data_paths() is called,
        Then it calls sys.exit(1).
        """
        from src.cli.run_backtest import construct_data_paths

        # Execute & Verify
        with pytest.raises(SystemExit) as exc_info:
            construct_data_paths(
                pairs=["NONEXISTENT"],
                dataset="test",
                base_dir=tmp_path,
            )
        assert exc_info.value.code == 1
