"""Unit tests for duplicate handling determinism in ingestion pipeline.

Tests verify that duplicate detection and removal is deterministic,
always keeping the first occurrence and producing identical results
across repeated runs.
"""

import hashlib

import pandas as pd

from src.io.duplicates import get_duplicate_mask


class TestDuplicateHandlingDeterministic:
    """Test suite for duplicate detection and removal determinism."""

    def test_no_duplicates_returns_empty_mask(self):
        """Test that data without duplicates returns all-False mask."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        "2025-01-01 00:01:00",
                        "2025-01-01 00:02:00",
                    ],
                    utc=True,
                )
            }
        )

        mask = get_duplicate_mask(df)

        assert mask.sum() == 0
        assert (~mask).all()

    def test_keeps_first_occurrence(self):
        """Test that duplicate detection keeps first occurrence."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        "2025-01-01 00:01:00",
                        "2025-01-01 00:01:00",  # Duplicate
                        "2025-01-01 00:02:00",
                    ],
                    utc=True,
                ),
                "value": [1, 2, 3, 4],
            }
        )

        mask = get_duplicate_mask(df)

        # Exactly 1 duplicate
        assert mask.sum() == 1

        # Duplicate is at index 2
        assert mask[2]

        # First occurrence at index 1 is not marked
        assert not mask[1]

        # After filtering, first occurrence value should remain
        result = df[~mask]
        first_occurrence = result[
            result["timestamp_utc"] == pd.Timestamp("2025-01-01 00:01:00", tz="UTC")
        ]
        assert first_occurrence["value"].iloc[0] == 2

    def test_multiple_duplicates_same_timestamp(self):
        """Test handling of multiple duplicates at same timestamp."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        "2025-01-01 00:01:00",
                        "2025-01-01 00:01:00",  # Duplicate 1
                        "2025-01-01 00:01:00",  # Duplicate 2
                        "2025-01-01 00:02:00",
                    ],
                    utc=True,
                ),
                "value": [1, 2, 3, 4, 5],
            }
        )

        mask = get_duplicate_mask(df)

        # Exactly 2 duplicates
        assert mask.sum() == 2

        # Duplicates are at indices 2 and 3
        assert mask[2] and mask[3]

        # First occurrence at index 1 is not marked
        assert not mask[1]

    def test_deterministic_across_runs(self):
        """Test that duplicate detection is deterministic across multiple runs."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        "2025-01-01 00:01:00",
                        "2025-01-01 00:01:00",
                        "2025-01-01 00:02:00",
                        "2025-01-01 00:02:00",
                        "2025-01-01 00:03:00",
                    ],
                    utc=True,
                )
            }
        )

        # Run detection multiple times
        results = [get_duplicate_mask(df) for _ in range(5)]

        # All results should be identical
        for result in results[1:]:
            assert (result == results[0]).all()

    def test_dataset_hash_deterministic_after_deduplication(self):
        """Test that deduplicated dataset hash is identical across runs."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        "2025-01-01 00:01:00",
                        "2025-01-01 00:01:00",  # Duplicate
                        "2025-01-01 00:02:00",
                    ],
                    utc=True,
                ),
                "open": [1.0, 1.1, 1.15, 1.2],
                "close": [1.01, 1.11, 1.16, 1.21],
            }
        )

        # Compute hash multiple times
        hashes = []
        for _ in range(3):
            mask = get_duplicate_mask(df)
            result = df[~mask].reset_index(drop=True)

            # Compute hash of result
            data_bytes = result.to_csv(index=False).encode("utf-8")
            hash_value = hashlib.sha256(data_bytes).hexdigest()
            hashes.append(hash_value)

        # All hashes should be identical
        assert len(set(hashes)) == 1

    def test_duplicate_removal_preserves_order(self):
        """Test that duplicate removal maintains row order."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        "2025-01-01 00:01:00",
                        "2025-01-01 00:01:00",  # Duplicate
                        "2025-01-01 00:02:00",
                        "2025-01-01 00:03:00",
                    ],
                    utc=True,
                ),
                "sequence": [1, 2, 99, 3, 4],
            }
        )

        mask = get_duplicate_mask(df)
        result = df[~mask]

        # Sequence should be preserved (excluding duplicate)
        expected_sequence = [1, 2, 3, 4]
        assert result["sequence"].tolist() == expected_sequence

    def test_duplicates_at_start_and_end(self):
        """Test duplicate handling at dataset boundaries."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        "2025-01-01 00:00:00",  # Duplicate at start
                        "2025-01-01 00:01:00",
                        "2025-01-01 00:02:00",
                        "2025-01-01 00:02:00",  # Duplicate at end
                    ],
                    utc=True,
                )
            }
        )

        mask = get_duplicate_mask(df)

        # Exactly 2 duplicates
        assert mask.sum() == 2

        # Duplicates at indices 1 and 4
        assert mask[1] and mask[4]

        # First occurrences preserved
        assert not mask[0] and not mask[3]

    def test_all_duplicates_scenario(self):
        """Test scenario where all rows after first are duplicates."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    ["2025-01-01 00:00:00"] * 5, utc=True
                ),
                "value": [1, 2, 3, 4, 5],
            }
        )

        mask = get_duplicate_mask(df)

        # 4 duplicates (all except first)
        assert mask.sum() == 4

        # Only first occurrence kept
        result = df[~mask]
        assert len(result) == 1
        assert result["value"].iloc[0] == 1

    def test_duplicate_count_logged_correctly(self):
        """Test that duplicate count matches mask sum."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        "2025-01-01 00:01:00",
                        "2025-01-01 00:01:00",
                        "2025-01-01 00:01:00",
                        "2025-01-01 00:02:00",
                        "2025-01-01 00:02:00",
                    ],
                    utc=True,
                )
            }
        )

        mask = get_duplicate_mask(df)
        duplicate_count = mask.sum()

        # Should detect exactly 3 duplicates
        assert duplicate_count == 3

    def test_empty_dataframe_no_duplicates(self):
        """Test that empty dataframe returns empty mask."""
        df = pd.DataFrame({"timestamp_utc": pd.to_datetime([], utc=True)})

        mask = get_duplicate_mask(df)

        assert len(mask) == 0

    def test_single_row_no_duplicates(self):
        """Test that single-row dataframe has no duplicates."""
        df = pd.DataFrame(
            {"timestamp_utc": pd.to_datetime(["2025-01-01 00:00:00"], utc=True)}
        )

        mask = get_duplicate_mask(df)

        assert mask.sum() == 0

    def test_large_dataset_determinism(self):
        """Test determinism with large dataset containing duplicates."""
        # Create dataset with 10,000 rows
        timestamps = pd.date_range(
            "2025-01-01", periods=5000, freq="1min", tz="UTC"
        ).tolist()

        # Duplicate some timestamps
        timestamps = timestamps + timestamps[:1000]  # Add 1000 duplicates

        df = pd.DataFrame({"timestamp_utc": timestamps})

        # Run multiple times
        hashes = []
        for _ in range(3):
            mask = get_duplicate_mask(df)
            result = df[~mask].reset_index(drop=True)

            # Hash the result
            data_bytes = result["timestamp_utc"].astype(str).sum().encode()
            hash_value = hashlib.sha256(data_bytes).hexdigest()
            hashes.append(hash_value)

        # All hashes identical
        assert len(set(hashes)) == 1

    def test_duplicate_detection_with_unsorted_data(self):
        """Test that duplicate detection works correctly on unsorted data."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    [
                        "2025-01-01 00:02:00",
                        "2025-01-01 00:00:00",
                        "2025-01-01 00:01:00",
                        "2025-01-01 00:01:00",  # Duplicate
                        "2025-01-01 00:00:00",  # Duplicate
                    ],
                    utc=True,
                ),
                "value": [1, 2, 3, 4, 5],
            }
        )

        mask = get_duplicate_mask(df)

        # Should detect 2 duplicates
        assert mask.sum() == 2

        # Duplicates should be at indices 3 and 4 (first occurrences at 1 and 2)
        assert mask[3] and mask[4]
        assert not mask[1] and not mask[2]

