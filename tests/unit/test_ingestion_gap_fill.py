"""Unit tests for gap synthesis correctness in ingestion pipeline.

Tests verify that gap filling produces the correct number of synthetic
rows, with proper forward-fill logic and gap flagging.
"""

import pandas as pd

from src.data_io.gap_fill import fill_gaps_vectorized


class TestGapSynthesisCorrectness:
    """Test suite for gap synthesis accuracy."""

    def test_no_gaps_returns_unchanged(self):
        """Test that data without gaps is returned unchanged."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.date_range(
                    "2025-01-01", periods=5, freq="1min", tz="UTC"
                ),
                "open": [1.0, 1.1, 1.2, 1.3, 1.4],
                "high": [1.05, 1.15, 1.25, 1.35, 1.45],
                "low": [0.95, 1.05, 1.15, 1.25, 1.35],
                "close": [1.01, 1.11, 1.21, 1.31, 1.41],
                "volume": [100.0, 110.0, 120.0, 130.0, 140.0],
            }
        )

        result, _ = fill_gaps_vectorized(df, timeframe_minutes=1)

        # Should have is_gap column
        assert "is_gap" in result.columns

        # All rows should be non-gaps
        assert result["is_gap"].sum() == 0

        # Row count should be unchanged
        assert len(result) == len(df)

    def test_single_gap_filled_correctly(self):
        """Test that a single missing interval is filled correctly."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        "2025-01-01 00:01:00",
                        # Missing: 2025-01-01 00:02:00
                        "2025-01-01 00:03:00",
                    ],
                    utc=True,
                ),
                "open": [1.0, 1.1, 1.3],
                "high": [1.05, 1.15, 1.35],
                "low": [0.95, 1.05, 1.25],
                "close": [1.01, 1.11, 1.31],
                "volume": [100.0, 110.0, 130.0],
            }
        )

        result, _ = fill_gaps_vectorized(df, timeframe_minutes=1)

        # Should have 4 rows now (3 original + 1 gap)
        assert len(result) == 4

        # Exactly 1 gap row
        assert result["is_gap"].sum() == 1

        # Gap row should be at index 2
        gap_row = result[result["is_gap"]].iloc[0]
        assert gap_row["timestamp_utc"] == pd.Timestamp("2025-01-01 00:02:00", tz="UTC")

        # Gap row OHLC should match previous close
        assert gap_row["open"] == 1.11
        assert gap_row["high"] == 1.11
        assert gap_row["low"] == 1.11
        assert gap_row["close"] == 1.11

        # Gap row volume should be 0
        assert gap_row["volume"] == 0.0

    def test_multiple_consecutive_gaps(self):
        """Test filling multiple consecutive missing intervals."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        # Missing: 00:01:00, 00:02:00, 00:03:00
                        "2025-01-01 00:04:00",
                    ],
                    utc=True,
                ),
                "open": [1.0, 1.4],
                "high": [1.05, 1.45],
                "low": [0.95, 1.35],
                "close": [1.01, 1.41],
                "volume": [100.0, 140.0],
            }
        )

        result, _ = fill_gaps_vectorized(df, timeframe_minutes=1)

        # Should have 5 rows (2 original + 3 gaps)
        assert len(result) == 5

        # Exactly 3 gap rows
        assert result["is_gap"].sum() == 3

        # All gap rows should have OHLC = 1.01 (forward-filled from first close)
        gap_rows = result[result["is_gap"]]
        assert (gap_rows["open"] == 1.01).all()
        assert (gap_rows["high"] == 1.01).all()
        assert (gap_rows["low"] == 1.01).all()
        assert (gap_rows["close"] == 1.01).all()

        # All gap volumes should be 0
        assert (gap_rows["volume"] == 0.0).all()

    def test_gap_count_matches_detected_gaps(self):
        """Test that number of filled gaps matches gap detection."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        "2025-01-01 00:01:00",
                        "2025-01-01 00:04:00",  # 2 gaps
                        "2025-01-01 00:05:00",
                        "2025-01-01 00:08:00",  # 2 gaps
                    ],
                    utc=True,
                ),
                "open": [1.0, 1.1, 1.4, 1.5, 1.8],
                "high": [1.05, 1.15, 1.45, 1.55, 1.85],
                "low": [0.95, 1.05, 1.35, 1.45, 1.75],
                "close": [1.01, 1.11, 1.41, 1.51, 1.81],
                "volume": [100.0, 110.0, 140.0, 150.0, 180.0],
            }
        )

        # Fill gaps
        result, gap_count = fill_gaps_vectorized(df, timeframe_minutes=1)

        # Gap count in result should match returned count
        actual_gap_count = result["is_gap"].sum()
        assert actual_gap_count == gap_count
        assert actual_gap_count == 4  # 2 + 2 gaps

    def test_gap_fill_preserves_chronological_order(self):
        """Test that filled gaps maintain chronological timestamp order."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        "2025-01-01 00:05:00",
                        "2025-01-01 00:10:00",
                    ],
                    utc=True,
                ),
                "open": [1.0, 1.5, 2.0],
                "high": [1.05, 1.55, 2.05],
                "low": [0.95, 1.45, 1.95],
                "close": [1.01, 1.51, 2.01],
                "volume": [100.0, 150.0, 200.0],
            }
        )

        result, _ = fill_gaps_vectorized(df, timeframe_minutes=1)

        # Timestamps should be sorted
        assert result["timestamp_utc"].is_monotonic_increasing

        # Should have continuous 1-minute intervals
        time_diffs = result["timestamp_utc"].diff()[1:]
        expected_diff = pd.Timedelta(minutes=1)
        assert (time_diffs == expected_diff).all()

    def test_gap_fill_with_5_minute_timeframe(self):
        """Test gap filling works with different timeframes."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        # Missing: 00:05:00
                        "2025-01-01 00:10:00",
                    ],
                    utc=True,
                ),
                "open": [1.0, 1.2],
                "high": [1.05, 1.25],
                "low": [0.95, 1.15],
                "close": [1.01, 1.21],
                "volume": [100.0, 120.0],
            }
        )

        result, _ = fill_gaps_vectorized(df, timeframe_minutes=5)

        # Should have 3 rows (2 original + 1 gap)
        assert len(result) == 3

        # Exactly 1 gap
        assert result["is_gap"].sum() == 1

        # Gap should be at 00:05:00
        gap_row = result[result["is_gap"]].iloc[0]
        assert gap_row["timestamp_utc"] == pd.Timestamp("2025-01-01 00:05:00", tz="UTC")

    def test_gap_fill_zero_tolerance(self):
        """Test that gap filling has zero tolerance for missing intervals."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        "2025-01-01 00:02:00",  # 1 minute gap
                    ],
                    utc=True,
                ),
                "open": [1.0, 1.2],
                "high": [1.05, 1.25],
                "low": [0.95, 1.15],
                "close": [1.01, 1.21],
                "volume": [100.0, 120.0],
            }
        )

        result, _ = fill_gaps_vectorized(df, timeframe_minutes=1)

        # Must fill the gap with zero tolerance
        assert result["is_gap"].sum() == 1

    def test_original_rows_not_flagged_as_gaps(self):
        """Test that original data rows are never flagged as gaps."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        "2025-01-01 00:03:00",
                        "2025-01-01 00:06:00",
                    ],
                    utc=True,
                ),
                "open": [1.0, 1.3, 1.6],
                "high": [1.05, 1.35, 1.65],
                "low": [0.95, 1.25, 1.55],
                "close": [1.01, 1.31, 1.61],
                "volume": [100.0, 130.0, 160.0],
            }
        )

        result, _ = fill_gaps_vectorized(df, timeframe_minutes=1)

        # Original timestamps should not be flagged
        original_timestamps = df["timestamp_utc"].tolist()
        for ts in original_timestamps:
            row = result[result["timestamp_utc"] == ts]
            assert len(row) == 1  # Should find exactly one row
            assert not row["is_gap"].values[0]  # Should not be a gap

    def test_gap_fill_large_dataset_performance(self):
        """Test that gap filling scales efficiently with large datasets."""
        # Create dataset with 10,000 rows and scattered gaps
        timestamps = pd.date_range("2025-01-01", periods=10000, freq="1min", tz="UTC")

        # Remove some rows to create gaps
        keep_mask = pd.Series([True] * 10000)
        keep_mask[100:105] = False  # 5-row gap
        keep_mask[1000:1010] = False  # 10-row gap
        keep_mask[5000] = False  # 1-row gap

        timestamps = timestamps[keep_mask]

        df = pd.DataFrame(
            {
                "timestamp_utc": timestamps,
                "open": 1.0,
                "high": 1.05,
                "low": 0.95,
                "close": 1.01,
                "volume": 100.0,
            }
        )

        result, _ = fill_gaps_vectorized(df, timeframe_minutes=1)

        # Should fill all gaps
        expected_total = 10000
        assert len(result) == expected_total

        # Should have exactly 16 gaps (5 + 10 + 1)
        assert result["is_gap"].sum() == 16
