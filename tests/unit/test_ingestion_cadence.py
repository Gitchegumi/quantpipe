"""Unit tests for cadence validation errors in ingestion pipeline.

Tests verify that cadence validation correctly detects excessive gaps
and raises appropriate errors when deviation exceeds 2% tolerance.
"""

import pandas as pd
import pytest

from src.data_io.cadence import (
    compute_cadence_minutes,
    validate_cadence,
)


class TestCadenceValidationErrors:
    """Test suite for cadence validation error conditions."""

    def test_perfect_cadence_passes(self):
        """Test that perfectly uniform cadence passes validation."""
        timestamps = pd.date_range("2025-01-01", periods=100, freq="1min", tz="UTC")

        # Should not raise
        validate_cadence(timestamps, expected_minutes=1, tolerance=0.02)

    def test_within_tolerance_passes(self):
        """Test that cadence within 2% tolerance passes."""
        # 1000 rows, remove 19 (1.9% missing) - should pass
        timestamps = pd.date_range("2025-01-01", periods=1000, freq="1min", tz="UTC")
        keep_mask = [True] * 1000
        for i in range(100, 119):  # Remove 19 rows
            keep_mask[i] = False

        timestamps = timestamps[keep_mask]

        # Should not raise
        validate_cadence(timestamps, expected_minutes=1, tolerance=0.02)

    def test_exceeds_tolerance_raises_error(self):
        """Test that cadence exceeding 2% tolerance raises RuntimeError."""
        # 1000 rows, remove 21 (2.1% missing) - should fail
        timestamps = pd.date_range("2025-01-01", periods=1000, freq="1min", tz="UTC")
        keep_mask = [True] * 1000
        for i in range(100, 121):  # Remove 21 rows
            keep_mask[i] = False

        timestamps = timestamps[keep_mask]

        with pytest.raises(RuntimeError, match="Cadence deviation exceeds tolerance"):
            validate_cadence(timestamps, expected_minutes=1, tolerance=0.02)

    def test_error_message_includes_deviation_percent(self):
        """Test that error message includes deviation percentage."""
        timestamps = pd.date_range("2025-01-01", periods=100, freq="1min", tz="UTC")
        keep_mask = [True] * 100
        for i in range(50, 60):
            keep_mask[i] = False  # Remove 10 rows (10% missing)

        timestamps = timestamps[keep_mask]

        with pytest.raises(RuntimeError) as exc_info:
            validate_cadence(timestamps, expected_minutes=1, tolerance=0.02)

        error_msg = str(exc_info.value)
        assert "deviation" in error_msg.lower()
        # Should contain a percentage value
        assert "%" in error_msg

    def test_error_includes_expected_and_actual_counts(self):
        """Test that error message includes expected and actual interval counts."""
        timestamps = pd.date_range("2025-01-01", periods=100, freq="1min", tz="UTC")
        keep_mask = [True] * 100
        for i in range(10, 20):
            keep_mask[i] = False  # Remove 10 rows

        timestamps = timestamps[keep_mask]

        with pytest.raises(RuntimeError) as exc_info:
            validate_cadence(timestamps, expected_minutes=1, tolerance=0.02)

        error_msg = str(exc_info.value)
        # Error should communicate the gap
        assert "expected" in error_msg.lower() or "missing" in error_msg.lower()

    def test_large_gap_raises_error(self):
        """Test that a large single gap raises validation error."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        "2025-01-01 00:01:00",
                        # Large gap: 50 minutes missing
                        "2025-01-01 00:52:00",
                        "2025-01-01 00:53:00",
                    ],
                    utc=True,
                )
            }
        )

        with pytest.raises(RuntimeError):
            validate_cadence(df["timestamp_utc"], expected_minutes=1, tolerance=0.02)

    def test_many_small_gaps_raise_error(self):
        """Test that many small gaps can accumulate to exceed tolerance."""
        timestamps = pd.date_range("2025-01-01", periods=200, freq="1min", tz="UTC")

        # Remove every 10th row (20 rows total = 10% missing)
        keep_mask = [i % 10 != 0 for i in range(200)]
        timestamps = timestamps[keep_mask]

        with pytest.raises(RuntimeError):
            validate_cadence(timestamps, expected_minutes=1, tolerance=0.02)

    def test_zero_tolerance_still_allows_zero_gaps(self):
        """Test that zero tolerance passes when no gaps exist."""
        timestamps = pd.date_range("2025-01-01", periods=50, freq="1min", tz="UTC")

        # Should not raise even with zero tolerance
        validate_cadence(timestamps, expected_minutes=1, tolerance=0.0)

    def test_exactly_at_threshold_passes(self):
        """Test that deviation exactly at 2% threshold passes."""
        # Create dataset where exactly 2% are missing
        timestamps = pd.date_range("2025-01-01", periods=5000, freq="1min", tz="UTC")
        keep_mask = [True] * 5000

        # Remove exactly 100 rows (2.0%)
        for i in range(100, 200):
            keep_mask[i] = False

        timestamps = timestamps[keep_mask]

        # Should not raise (at threshold)
        validate_cadence(timestamps, expected_minutes=1, tolerance=0.02)

    def test_just_over_threshold_raises(self):
        """Test that deviation just over 2% threshold raises error."""
        # Create dataset where 2.1% are missing
        timestamps = pd.date_range("2025-01-01", periods=5000, freq="1min", tz="UTC")
        keep_mask = [True] * 5000

        # Remove 105 rows (2.1%)
        for i in range(100, 205):
            keep_mask[i] = False

        timestamps = timestamps[keep_mask]

        with pytest.raises(RuntimeError):
            validate_cadence(timestamps, expected_minutes=1, tolerance=0.02)

    def test_cadence_validation_with_5_minute_timeframe(self):
        """Test validation works with different timeframes."""
        timestamps = pd.date_range("2025-01-01", periods=1000, freq="5min", tz="UTC")
        keep_mask = [True] * 1000

        # Remove 25 rows (2.5% missing) - should fail
        for i in range(100, 125):
            keep_mask[i] = False

        timestamps = timestamps[keep_mask]

        with pytest.raises(RuntimeError):
            validate_cadence(timestamps, expected_minutes=5, tolerance=0.02)

    def test_detected_cadence_matches_expected(self):
        """Test that detected cadence matches expected for valid data."""
        timestamps = pd.date_range("2025-01-01", periods=100, freq="1min", tz="UTC")

        detected = compute_cadence_minutes(timestamps)
        assert detected == 1

        # Validation should pass when detected matches expected
        validate_cadence(timestamps, expected_minutes=detected, tolerance=0.02)

    def test_validation_with_very_small_dataset(self):
        """Test validation behavior with minimal data points."""
        # Only 3 timestamps
        timestamps = pd.to_datetime(
            [
                "2025-01-01 00:00:00",
                "2025-01-01 00:01:00",
                "2025-01-01 00:02:00",
            ],
            utc=True,
        )

        # Should pass with perfect cadence
        validate_cadence(timestamps, expected_minutes=1, tolerance=0.02)

    def test_validation_fails_with_single_large_gap_in_small_dataset(self):
        """Test that single gap in small dataset can exceed tolerance."""
        # Only 4 timestamps with one large gap
        timestamps = pd.to_datetime(
            [
                "2025-01-01 00:00:00",
                "2025-01-01 00:01:00",
                "2025-01-01 00:10:00",  # 8-minute gap (8 rows missing)
                "2025-01-01 00:11:00",
            ],
            utc=True,
        )

        # Expected 11 intervals, have only 3 = ~73% missing
        with pytest.raises(RuntimeError):
            validate_cadence(timestamps, expected_minutes=1, tolerance=0.02)

    def test_tolerance_parameter_respected(self):
        """Test that custom tolerance values are respected."""
        timestamps = pd.date_range("2025-01-01", periods=1000, freq="1min", tz="UTC")
        keep_mask = [True] * 1000
        for i in range(100, 150):
            keep_mask[i] = False  # Remove 50 rows (5% missing)

        timestamps = timestamps[keep_mask]

        # Should fail with 2% tolerance
        with pytest.raises(RuntimeError):
            validate_cadence(timestamps, expected_minutes=1, tolerance=0.02)

        # Should pass with 10% tolerance
        validate_cadence(timestamps, expected_minutes=1, tolerance=0.10)

    def test_error_raised_before_gap_filling(self):
        """Test that validation error occurs before gap filling."""
        # This simulates the ingestion pipeline order:
        # validation happens before gap fill

        timestamps = pd.date_range("2025-01-01", periods=100, freq="1min", tz="UTC")
        keep_mask = [True] * 100
        for i in range(50, 60):
            keep_mask[i] = False  # 10% missing

        timestamps = timestamps[keep_mask]

        # Validation should fail immediately
        with pytest.raises(RuntimeError):
            validate_cadence(timestamps, expected_minutes=1, tolerance=0.02)

        # Gap filling would never occur due to early failure
