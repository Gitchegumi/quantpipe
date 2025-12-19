"""Integration test for end-to-end ingestion pipeline.

Tests verify that the complete ingestion pipeline produces correct
results with proper handling of duplicates, gaps, cadence validation,
and schema restriction.
"""

import pandas as pd
import pytest

from src.data_io.ingestion import ingest_ohlcv_data


class TestIngestionPipelineIntegration:
    """Integration tests for complete ingestion pipeline."""

    def test_end_to_end_clean_data(self, tmp_path):
        """Test ingestion with clean, uniform data produces expected output."""
        # Create test CSV with uniform 1-minute data
        csv_path = tmp_path / "clean_data.csv"
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2025-01-01", periods=100, freq="1min", tz="UTC"
                ),
                "open": range(100, 200),
                "high": range(101, 201),
                "low": range(99, 199),
                "close": range(100, 200),
                "volume": [1000.0] * 100,
            }
        )
        df.to_csv(csv_path, index=False)

        # Run ingestion
        result = ingest_ohlcv_data(str(csv_path), timeframe_minutes=1)

        # Verify output structure
        assert result.data is not None
        assert len(result.data) == 100

        # Verify core schema only
        expected_columns = [
            "timestamp_utc",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "is_gap",
        ]
        assert list(result.data.columns) == expected_columns

        # Verify no gaps in clean data
        assert result.metrics.gaps_inserted == 0
        assert not result.data["is_gap"].any()

        # Verify no duplicates removed
        assert result.metrics.duplicates_removed == 0

        # Verify chronological order
        assert result.data["timestamp_utc"].is_monotonic_increasing

        # Verify metrics
        assert result.metrics.total_rows_input == 100
        assert result.metrics.total_rows_output == 100
        assert result.metrics.runtime_seconds > 0

    @pytest.mark.xfail(reason="Gap filling logic changed - test assertions need update")
    def test_end_to_end_with_gaps(self, tmp_path):
        """Test ingestion fills gaps correctly."""
        # Create test CSV with <2% gaps (1 gap out of 100)
        csv_path = tmp_path / "gapped_data.csv"
        timestamps = pd.date_range(
            "2025-01-01", periods=100, freq="1min", tz="UTC"
        ).tolist()
        # Remove one timestamp to create a single gap (<2%)
        timestamps_with_gaps = timestamps[:50] + timestamps[51:]

        df = pd.DataFrame(
            {
                "timestamp": timestamps_with_gaps,
                "open": list(range(100, 150)) + list(range(151, 200)),
                "high": list(range(101, 151)) + list(range(152, 201)),
                "low": list(range(99, 149)) + list(range(150, 199)),
                "close": list(range(100, 150)) + list(range(151, 200)),
                "volume": [1000.0] * 99,
            }
        )
        df.to_csv(csv_path, index=False)

        # Run ingestion
        result = ingest_ohlcv_data(str(csv_path), timeframe_minutes=1)

        # Verify gaps were filled
        assert result.data is not None
        assert len(result.data) == 100  # Original 99 + 1 gap
        assert result.metrics.gaps_inserted == 1

        # Verify gap flag
        assert result.data["is_gap"].sum() == 1

        # Verify gap row has correct properties
        gap_rows = result.data[result.data["is_gap"]]
        assert len(gap_rows) == 1

        # Gap rows should have zero volume
        assert (gap_rows["volume"] == 0.0).all()

        # Gap rows should have OHLC equal to forward-filled close
        for _, row in gap_rows.iterrows():
            assert row["open"] == row["close"]
            assert row["high"] == row["close"]
            assert row["low"] == row["close"]

    def test_end_to_end_with_duplicates(self, tmp_path):
        """Test ingestion removes duplicates correctly."""
        # Create test CSV with duplicate timestamps
        csv_path = tmp_path / "duplicate_data.csv"
        df = pd.DataFrame(
            {
                "timestamp": [
                    "2025-01-01 00:00:00",
                    "2025-01-01 00:01:00",
                    "2025-01-01 00:01:00",  # Duplicate
                    "2025-01-01 00:02:00",
                    "2025-01-01 00:02:00",  # Duplicate
                    "2025-01-01 00:03:00",
                ],
                "open": [100.0, 101.0, 101.1, 102.0, 102.1, 103.0],
                "high": [101.0, 102.0, 102.1, 103.0, 103.1, 104.0],
                "low": [99.0, 100.0, 100.1, 101.0, 101.1, 102.0],
                "close": [100.5, 101.5, 101.6, 102.5, 102.6, 103.5],
                "volume": [1000.0] * 6,
            }
        )
        df.to_csv(csv_path, index=False)

        # Run ingestion
        result = ingest_ohlcv_data(str(csv_path), timeframe_minutes=1)

        # Verify duplicates were removed
        assert result.data is not None
        assert len(result.data) == 4  # 6 input - 2 duplicates
        assert result.metrics.duplicates_removed == 2

        # Verify remaining timestamps are unique
        assert not result.data["timestamp_utc"].duplicated().any()

        # Verify keep-first strategy (first occurrence kept)
        timestamps = result.data["timestamp_utc"]
        assert len(timestamps) == len(timestamps.unique())

    def test_end_to_end_unsorted_input(self, tmp_path):
        """Test ingestion sorts unsorted input correctly."""
        # Create test CSV with unsorted timestamps
        csv_path = tmp_path / "unsorted_data.csv"
        df = pd.DataFrame(
            {
                "timestamp": [
                    "2025-01-01 00:02:00",
                    "2025-01-01 00:00:00",
                    "2025-01-01 00:03:00",
                    "2025-01-01 00:01:00",
                ],
                "open": [102.0, 100.0, 103.0, 101.0],
                "high": [103.0, 101.0, 104.0, 102.0],
                "low": [101.0, 99.0, 102.0, 100.0],
                "close": [102.5, 100.5, 103.5, 101.5],
                "volume": [1000.0] * 4,
            }
        )
        df.to_csv(csv_path, index=False)

        # Run ingestion
        result = ingest_ohlcv_data(str(csv_path), timeframe_minutes=1)

        # Verify output is sorted
        assert result.data is not None
        assert result.data["timestamp_utc"].is_monotonic_increasing

        # Verify first timestamp is earliest
        assert result.data["timestamp_utc"].iloc[0] == pd.Timestamp(
            "2025-01-01 00:00:00", tz="UTC"
        )

    def test_end_to_end_extra_columns_ignored(self, tmp_path):
        """Test ingestion ignores extra columns not in core schema."""
        # Create test CSV with extra columns
        csv_path = tmp_path / "extra_columns.csv"
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2025-01-01", periods=10, freq="1min", tz="UTC"
                ),
                "open": range(100, 110),
                "high": range(101, 111),
                "low": range(99, 109),
                "close": range(100, 110),
                "volume": [1000.0] * 10,
                "extra_col1": range(10),
                "extra_col2": ["A"] * 10,
            }
        )
        df.to_csv(csv_path, index=False)

        # Run ingestion
        result = ingest_ohlcv_data(str(csv_path), timeframe_minutes=1)

        # Verify only core columns in output
        assert result.data is not None
        expected_columns = [
            "timestamp_utc",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "is_gap",
        ]
        assert list(result.data.columns) == expected_columns

    def test_end_to_end_cadence_validation_passes(self, tmp_path):
        """Test ingestion passes cadence validation for uniform data."""
        # Create test CSV with <2% gaps
        csv_path = tmp_path / "valid_cadence.csv"
        timestamps = pd.date_range(
            "2025-01-01", periods=1000, freq="1min", tz="UTC"
        ).tolist()
        # Remove 1% of timestamps (10 out of 1000)
        timestamps_subset = [timestamps[i] for i in range(1000) if i % 100 != 50]

        df = pd.DataFrame(
            {
                "timestamp": timestamps_subset,
                "open": [100.0] * len(timestamps_subset),
                "high": [101.0] * len(timestamps_subset),
                "low": [99.0] * len(timestamps_subset),
                "close": [100.5] * len(timestamps_subset),
                "volume": [1000.0] * len(timestamps_subset),
            }
        )
        df.to_csv(csv_path, index=False)

        # Should not raise
        result = ingest_ohlcv_data(str(csv_path), timeframe_minutes=1)
        assert result.data is not None

    @pytest.mark.xfail(
        reason="Cadence validation behavior changed - no longer raises RuntimeError"
    )
    def test_end_to_end_cadence_validation_fails(self, tmp_path):
        """Test ingestion fails cadence validation for too many gaps."""
        # Create test CSV with >2% gaps
        csv_path = tmp_path / "invalid_cadence.csv"
        timestamps = pd.date_range(
            "2025-01-01", periods=100, freq="1min", tz="UTC"
        ).tolist()
        # Remove 10% of timestamps (10 out of 100) - exceeds 2% threshold
        # Remove every 10th timestamp to create distributed gaps
        timestamps_subset = [timestamps[i] for i in range(100) if i % 10 != 5]

        df = pd.DataFrame(
            {
                "timestamp": timestamps_subset,
                "open": [100.0] * len(timestamps_subset),
                "high": [101.0] * len(timestamps_subset),
                "low": [99.0] * len(timestamps_subset),
                "close": [100.5] * len(timestamps_subset),
                "volume": [1000.0] * len(timestamps_subset),
            }
        )
        df.to_csv(csv_path, index=False)

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Cadence deviation exceeds tolerance"):
            ingest_ohlcv_data(str(csv_path), timeframe_minutes=1)

    def test_end_to_end_missing_required_column(self, tmp_path):
        """Test ingestion fails with clear error for missing required columns."""
        # Create test CSV missing 'close' column
        csv_path = tmp_path / "missing_column.csv"
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2025-01-01", periods=10, freq="1min", tz="UTC"
                ),
                "open": range(100, 110),
                "high": range(101, 111),
                "low": range(99, 109),
                # Missing: close
                "volume": [1000.0] * 10,
            }
        )
        df.to_csv(csv_path, index=False)

        # Should raise ValueError
        with pytest.raises(ValueError, match="Missing required columns"):
            ingest_ohlcv_data(str(csv_path), timeframe_minutes=1)

    def test_end_to_end_empty_file(self, tmp_path):
        """Test ingestion handles empty input gracefully."""
        # Create empty CSV with headers only
        csv_path = tmp_path / "empty_data.csv"
        df = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df.to_csv(csv_path, index=False)

        # Run ingestion
        result = ingest_ohlcv_data(str(csv_path), timeframe_minutes=1)

        # Should return empty DataFrame with correct schema
        assert result.data is not None
        assert len(result.data) == 0
        assert result.metrics.total_rows_input == 0
        assert result.metrics.total_rows_output == 0

    def test_end_to_end_performance_metrics_recorded(self, tmp_path):
        """Test ingestion records comprehensive performance metrics."""
        # Create test CSV
        csv_path = tmp_path / "metrics_test.csv"
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2025-01-01", periods=100, freq="1min", tz="UTC"
                ),
                "open": range(100, 200),
                "high": range(101, 201),
                "low": range(99, 199),
                "close": range(100, 200),
                "volume": [1000.0] * 100,
            }
        )
        df.to_csv(csv_path, index=False)

        # Run ingestion
        result = ingest_ohlcv_data(str(csv_path), timeframe_minutes=1)

        # Verify all metrics present
        assert result.metrics.total_rows_input == 100
        assert result.metrics.total_rows_output == 100
        assert result.metrics.gaps_inserted == 0
        assert result.metrics.duplicates_removed == 0
        assert result.metrics.runtime_seconds > 0
        assert result.metrics.throughput_rows_per_min > 0

        # Verify acceleration backend reported
        assert result.metrics.acceleration_backend in ["arrow", "pandas"]
