"""Unit tests for dataset partitioning logic.

Feature: 004-timeseries-dataset
Task: T018 - Test partition size logic
"""

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta, timezone

from src.io.dataset_builder import partition_data, SPLIT_RATIO


class TestPartitionLogic:
    """Test deterministic 80/20 partitioning with floor-based split."""

    def test_partition_exact_split(self):
        """Test partition with rows divisible by split ratio."""
        # 1000 rows -> 800 test, 200 validation
        df = self._create_sample_df(1000)
        test, validation = partition_data(df, SPLIT_RATIO)

        assert len(test) == 800
        assert len(validation) == 200
        assert len(test) + len(validation) == len(df)

    def test_partition_floor_rounding(self):
        """Test that partition uses floor for test size."""
        # 601 rows -> floor(601 * 0.8) = floor(480.8) = 480 test, 121 validation
        df = self._create_sample_df(601)
        test, validation = partition_data(df, SPLIT_RATIO)

        assert len(test) == 480  # floor(480.8)
        assert len(validation) == 121
        assert len(test) + len(validation) == 601

    def test_partition_minimum_threshold(self):
        """Test partition with exactly minimum rows (500)."""
        df = self._create_sample_df(500)
        test, validation = partition_data(df, SPLIT_RATIO)

        assert len(test) == 400  # floor(500 * 0.8)
        assert len(validation) == 100
        assert len(test) + len(validation) == 500

    def test_partition_just_above_threshold(self):
        """Test partition with 501 rows (just above minimum)."""
        df = self._create_sample_df(501)
        test, validation = partition_data(df, SPLIT_RATIO)

        assert len(test) == 400  # floor(501 * 0.8) = floor(400.8)
        assert len(validation) == 101

    def test_partition_preserves_chronological_order(self):
        """Test that partitions maintain chronological order."""
        df = self._create_sample_df(600)
        test, validation = partition_data(df, SPLIT_RATIO)

        # Test partition should have earlier timestamps
        assert test["timestamp"].iloc[0] < validation["timestamp"].iloc[0]
        assert test["timestamp"].iloc[-1] < validation["timestamp"].iloc[0]

        # Within each partition, timestamps should be increasing
        assert test["timestamp"].is_monotonic_increasing
        assert validation["timestamp"].is_monotonic_increasing

    def test_validation_is_most_recent(self):
        """Test that validation partition contains the most recent data."""
        df = self._create_sample_df(600)
        test, validation = partition_data(df, SPLIT_RATIO)

        # Last timestamp in original data should be in validation
        assert validation["timestamp"].iloc[-1] == df["timestamp"].iloc[-1]

        # First timestamp should be in test
        assert test["timestamp"].iloc[0] == df["timestamp"].iloc[0]

    def test_partition_contiguity(self):
        """Test that partitions are contiguous without gaps."""
        df = self._create_sample_df(600)
        test, validation = partition_data(df, SPLIT_RATIO)

        # The last row of test + 1 should be the first row of validation
        combined = pd.concat([test, validation], ignore_index=True)
        pd.testing.assert_frame_equal(combined, df)

    def test_partition_no_overlap(self):
        """Test that test and validation partitions don't overlap."""
        df = self._create_sample_df(600)
        test, validation = partition_data(df, SPLIT_RATIO)

        test_timestamps = set(test["timestamp"])
        validation_timestamps = set(validation["timestamp"])

        assert len(test_timestamps & validation_timestamps) == 0

    def test_partition_large_dataset(self):
        """Test partition with large dataset (1M rows)."""
        df = self._create_sample_df(1_000_000)
        test, validation = partition_data(df, SPLIT_RATIO)

        assert len(test) == 800_000
        assert len(validation) == 200_000

    def test_partition_custom_ratio(self):
        """Test partition with custom split ratio."""
        df = self._create_sample_df(1000)
        test, validation = partition_data(df, split_ratio=0.7)

        assert len(test) == 700  # floor(1000 * 0.7)
        assert len(validation) == 300

    def test_partition_edge_case_99_rows(self):
        """Test partition behavior with small dataset."""
        df = self._create_sample_df(99)
        test, validation = partition_data(df, SPLIT_RATIO)

        assert len(test) == 79  # floor(99 * 0.8)
        assert len(validation) == 20

    @staticmethod
    def _create_sample_df(n_rows: int) -> pd.DataFrame:
        """Create sample DataFrame with chronological timestamps.
        
        Args:
            n_rows: Number of rows to create
            
        Returns:
            DataFrame with timestamp and OHLCV columns
        """
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        timestamps = [start + timedelta(minutes=i) for i in range(n_rows)]

        return pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": np.random.uniform(1.1, 1.2, n_rows),
                "high": np.random.uniform(1.1, 1.2, n_rows),
                "low": np.random.uniform(1.1, 1.2, n_rows),
                "close": np.random.uniform(1.1, 1.2, n_rows),
                "volume": np.random.randint(1000, 2000, n_rows),
            }
        )
