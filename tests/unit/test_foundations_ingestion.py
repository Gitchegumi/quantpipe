"""Unit tests for foundational ingestion utilities.

Tests for cadence, duplicates, gaps, gap filling, downcast, progress,
schema, timezone validation, and hash utilities.
"""

import numpy as np
import pandas as pd
import pytest

from src.data_io import cadence, duplicates, gaps, gap_fill, downcast, progress
from src.data_io import schema, timezone_validate, hash_utils
from src.data_io.logging_constants import IngestionStage


class TestCadence:
    """Tests for cadence computation and validation."""

    def test_compute_expected_intervals(self):
        """Test expected interval computation."""
        start = pd.Timestamp("2024-01-01 00:00:00", tz="UTC")
        end = pd.Timestamp("2024-01-01 01:00:00", tz="UTC")

        result = cadence.compute_expected_intervals(start, end, 1)
        assert result == 61  # 60 minutes + 1

    def test_compute_cadence_deviation(self):
        """Test cadence deviation calculation."""
        deviation = cadence.compute_cadence_deviation(
            actual_count=98, expected_count=100
        )
        assert abs(deviation - 2.0) < 0.01

    def test_validate_cadence_uniformity_pass(self):
        """Test cadence validation passes within tolerance."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.date_range(
                    "2024-01-01", periods=100, freq="1min", tz="UTC"
                ),
                "close": np.arange(100),
            }
        )

        actual, _expected, dev = cadence.validate_cadence_uniformity(
            df, 1, tolerance_percent=2.0
        )
        assert actual == 100
        assert dev < 2.0

    def test_validate_cadence_uniformity_fail(self):
        """Test cadence validation fails when deviation exceeds tolerance."""
        # Create timestamps with a gap to ensure deviation
        # 0..44 (45 mins), then skip 5 mins, then 50..94 (45 mins)
        # Expected: 95 mins (0..94) -> 95 points
        # Actual: 90 points
        # Deviation: 5/95 ~= 5.2% > 1.0%
        timestamps = list(
            pd.date_range("2024-01-01 00:00", periods=45, freq="1min", tz="UTC")
        )
        timestamps += list(
            pd.date_range("2024-01-01 00:50", periods=45, freq="1min", tz="UTC")
        )

        df = pd.DataFrame(
            {
                "timestamp_utc": timestamps,
                "close": np.arange(90),
            }
        )

        with pytest.raises(RuntimeError, match="Cadence deviation exceeds tolerance"):
            cadence.validate_cadence_uniformity(df, 1, tolerance_percent=1.0)


class TestDuplicates:
    """Tests for duplicate detection and removal."""

    def test_detect_duplicates(self):
        """Test duplicate detection."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    ["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-03"], utc=True
                ),
                "close": [1, 2, 3, 4],
            }
        )

        dupes = duplicates.detect_duplicates(df)
        assert len(dupes) == 1
        assert dupes.iloc[0]["close"] == 3

    def test_remove_duplicates(self):
        """Test duplicate removal keeps first occurrence."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    ["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-03"], utc=True
                ),
                "close": [1, 2, 3, 4],
            }
        )

        cleaned, count = duplicates.remove_duplicates(df)
        assert count == 1
        assert len(cleaned) == 3
        ts_filter = cleaned["timestamp_utc"] == pd.Timestamp("2024-01-02", tz="UTC")
        assert cleaned[ts_filter]["close"].iloc[0] == 2


class TestGaps:
    """Tests for gap detection."""

    def test_detect_gaps(self):
        """Test gap detection finds missing intervals."""
        timestamps = [
            "2024-01-01 00:00",
            "2024-01-01 00:01",
            "2024-01-01 00:04",  # Gap: 00:02, 00:03 missing
            "2024-01-01 00:05",
        ]
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(timestamps, utc=True),
                "close": [1, 2, 3, 4],
            }
        )

        gaps_found = gaps.detect_gaps(df, timeframe_minutes=1)
        assert len(gaps_found) == 1

    def test_create_complete_index(self):
        """Test complete index creation."""
        start = pd.Timestamp("2024-01-01 00:00", tz="UTC")
        end = pd.Timestamp("2024-01-01 00:05", tz="UTC")

        index = gaps.create_complete_index(start, end, timeframe_minutes=1)
        assert len(index) == 6


class TestGapFill:
    """Tests for gap filling."""

    def test_synthesize_gap_values(self):
        """Test gap value synthesis."""
        df = pd.DataFrame(
            {
                "open": [1.0, np.nan, 3.0],
                "high": [1.1, np.nan, 3.1],
                "low": [0.9, np.nan, 2.9],
                "close": [1.0, np.nan, 3.0],
                "volume": [100.0, np.nan, 300.0],
            }
        )

        filled = gap_fill.synthesize_gap_values(df)
        assert filled.loc[1, "is_gap"]
        assert filled.loc[1, "close"] == 1.0  # Forward-filled
        assert filled.loc[1, "volume"] == 0.0


class TestDowncast:
    """Tests for numeric downcasting."""

    def test_check_precision_safe(self):
        """Test precision safety check."""
        series = pd.Series([1.0, 2.0, 3.0], dtype="float64")
        assert downcast.check_precision_safe(series, "float32")

    def test_downcast_numeric_columns(self):
        """Test downcasting numeric columns."""
        df = pd.DataFrame(
            {
                "close": pd.Series([1.0, 2.0, 3.0], dtype="float64"),
                "volume": pd.Series([100.0, 200.0, 300.0], dtype="float64"),
            }
        )

        downcasted, cols = downcast.downcast_numeric_columns(df)
        assert "close" in cols
        assert downcasted["close"].dtype == "float32"


class TestProgress:
    """Tests for progress reporting."""

    def test_progress_reporter_api(self):
        """Test progress reporter API."""
        # Test with show_progress=False to avoid UI side effects
        reporter = progress.ProgressReporter(show_progress=False)

        # Should not raise
        reporter.start_stage(IngestionStage.READ, "Testing")
        reporter.update_progress(1)
        reporter.finish()

        # Verify state
        assert reporter._started is False


class TestSchema:
    """Tests for schema enforcement."""

    def test_validate_required_columns_pass(self):
        """Test required columns validation passes."""
        df = pd.DataFrame(
            {
                "timestamp_utc": [],
                "open": [],
                "high": [],
                "low": [],
                "close": [],
                "volume": [],
            }
        )

        schema.validate_required_columns(df)  # Should not raise

    def test_validate_required_columns_fail(self):
        """Test required columns validation fails."""
        df = pd.DataFrame(
            {
                "timestamp_utc": [],
                "close": [],
            }
        )

        with pytest.raises(ValueError, match="Missing required columns"):
            schema.validate_required_columns(df)

    def test_restrict_to_core_schema(self):
        """Test core schema restriction."""
        df = pd.DataFrame(
            {
                "timestamp_utc": [1, 2, 3],
                "open": [1, 2, 3],
                "high": [1, 2, 3],
                "low": [1, 2, 3],
                "close": [1, 2, 3],
                "volume": [1, 2, 3],
                "is_gap": [False, False, False],
                "extra_col": [1, 2, 3],
            }
        )

        restricted = schema.restrict_to_core_schema(df)
        assert list(restricted.columns) == schema.CORE_COLUMNS
        assert "extra_col" not in restricted.columns


class TestTimezoneValidate:
    """Tests for timezone validation."""

    def test_validate_utc_timezone_pass(self):
        """Test UTC validation passes."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.date_range(
                    "2024-01-01", periods=5, freq="1min", tz="UTC"
                ),
            }
        )

        timezone_validate.validate_utc_timezone(df)  # Should not raise

    def test_validate_utc_timezone_fail_naive(self):
        """Test UTC validation fails on naive timestamps."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.date_range("2024-01-01", periods=5, freq="1min"),
            }
        )

        with pytest.raises(ValueError, match="timezone-naive"):
            timezone_validate.validate_utc_timezone(df)

    def test_validate_utc_timezone_fail_wrong_tz(self):
        """Test UTC validation fails on non-UTC timezone."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.date_range(
                    "2024-01-01", periods=5, freq="1min", tz="US/Eastern"
                ),
            }
        )

        with pytest.raises(ValueError, match="timezone is"):
            timezone_validate.validate_utc_timezone(df)


class TestHashUtils:
    """Tests for hash utilities."""

    def test_compute_dataframe_hash(self):
        """Test DataFrame hash computation."""
        df = pd.DataFrame(
            {
                "col1": [1, 2, 3],
                "col2": [4, 5, 6],
            }
        )

        hash1 = hash_utils.compute_dataframe_hash(df, ["col1", "col2"])
        hash2 = hash_utils.compute_dataframe_hash(df, ["col1", "col2"])
        assert hash1 == hash2  # Deterministic

    def test_verify_immutability_pass(self):
        """Test immutability verification passes."""
        df = pd.DataFrame(
            {
                "col1": [1, 2, 3],
            }
        )

        expected_hash = hash_utils.compute_dataframe_hash(df, ["col1"])
        assert hash_utils.verify_immutability(df, ["col1"], expected_hash)

    def test_verify_immutability_fail(self):
        """Test immutability verification fails on mutation."""
        df = pd.DataFrame(
            {
                "col1": [1, 2, 3],
            }
        )

        expected_hash = hash_utils.compute_dataframe_hash(df, ["col1"])
        df.loc[0, "col1"] = 999

        assert not hash_utils.verify_immutability(df, ["col1"], expected_hash)
