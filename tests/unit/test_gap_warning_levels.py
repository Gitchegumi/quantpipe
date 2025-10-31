"""Unit tests for gap/overlap logging levels.

Feature: 004-timeseries-dataset
Task: T041 - Verify gap warnings are silent (debug) and overlap warnings explicit
Success Criteria:
- Gap detection uses logger.debug (silent by default)
- Overlap detection uses logger.warning (explicit/visible)
"""

# pylint: disable=unused-variable

import logging

import pandas as pd

from src.io.dataset_builder import detect_gaps_and_overlaps


class TestGapOverlapLogging:
    """Test that gap/overlap detection uses correct logging levels."""

    def test_gaps_logged_at_debug_level(self, caplog):
        """
        Verify gap detection uses DEBUG level (silent by default).

        Given: DataFrame with timestamp gaps
        When: detect_gaps_and_overlaps is called
        Then: Gap messages logged at DEBUG level only
        """
        # Create DataFrame with gap
        df = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    [
                        "2024-01-01 00:00:00",
                        "2024-01-01 00:01:00",
                        "2024-01-01 00:10:00",  # 9-minute gap
                        "2024-01-01 00:11:00",
                    ],
                    utc=True,
                )
            }
        )

        with caplog.at_level(logging.DEBUG):
            gap_count, overlap_count = detect_gaps_and_overlaps(df, "EURUSD")

        # Should detect gap
        assert gap_count > 0
        assert overlap_count == 0

        # Check that gap message is at DEBUG level
        gap_messages = [
            record for record in caplog.records if "temporal gaps" in record.message
        ]
        assert len(gap_messages) > 0
        assert all(record.levelname == "DEBUG" for record in gap_messages)

    def test_gaps_not_visible_at_info_level(self, caplog):
        """
        Verify gap detection is silent at INFO level.

        Given: DataFrame with timestamp gaps
        When: detect_gaps_and_overlaps called with INFO logging
        Then: No gap messages visible (silent)
        """
        df = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    [
                        "2024-01-01 00:00:00",
                        "2024-01-01 00:01:00",
                        "2024-01-01 00:10:00",  # Gap
                        "2024-01-01 00:11:00",
                    ],
                    utc=True,
                )
            }
        )

        with caplog.at_level(logging.INFO):
            gap_count, overlap_count = detect_gaps_and_overlaps(df, "EURUSD")

        # Gap detected but not logged at INFO
        assert gap_count > 0

        # No gap messages visible at INFO level
        gap_messages = [
            record for record in caplog.records if "temporal gaps" in record.message
        ]
        assert len(gap_messages) == 0

    def test_overlaps_logged_at_warning_level(self, caplog):
        """
        Verify overlap detection uses WARNING level (explicit/visible).

        Given: DataFrame with duplicate timestamps
        When: detect_gaps_and_overlaps is called
        Then: Overlap messages logged at WARNING level
        """
        # Create DataFrame with overlaps (duplicates)
        df = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    [
                        "2024-01-01 00:00:00",
                        "2024-01-01 00:01:00",
                        "2024-01-01 00:01:00",  # Duplicate
                        "2024-01-01 00:02:00",
                        "2024-01-01 00:02:00",  # Duplicate
                    ],
                    utc=True,
                )
            }
        )

        with caplog.at_level(logging.INFO):
            gap_count, overlap_count = detect_gaps_and_overlaps(df, "EURUSD")

        # Should detect overlaps
        assert overlap_count == 2
        # Note: gap_count may also be non-zero due to zero-delta duplicates

        # Check that overlap message is at WARNING level
        overlap_messages = [
            record
            for record in caplog.records
            if "overlapping timestamps" in record.message
        ]
        assert len(overlap_messages) > 0
        assert all(record.levelname == "WARNING" for record in overlap_messages)

    def test_overlaps_visible_at_info_level(self, caplog):
        """
        Verify overlap warnings are visible at INFO level.

        Given: DataFrame with duplicate timestamps
        When: detect_gaps_and_overlaps called with INFO logging
        Then: Overlap warnings are visible
        """
        df = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    [
                        "2024-01-01 00:00:00",
                        "2024-01-01 00:01:00",
                        "2024-01-01 00:01:00",  # Duplicate
                    ],
                    utc=True,
                )
            }
        )

        with caplog.at_level(logging.INFO):
            gap_count, overlap_count = detect_gaps_and_overlaps(df, "EURUSD")

        assert overlap_count == 1

        # Overlap messages visible at INFO level
        overlap_messages = [
            record
            for record in caplog.records
            if "overlapping timestamps" in record.message
        ]
        assert len(overlap_messages) > 0

    def test_no_gaps_or_overlaps_minimal_logging(self, caplog):
        """
        Verify clean data produces minimal logging.

        Given: DataFrame with no gaps or overlaps
        When: detect_gaps_and_overlaps is called
        Then: Minimal or no logging output
        """
        # Clean data - 1-minute intervals
        df = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    [
                        "2024-01-01 00:00:00",
                        "2024-01-01 00:01:00",
                        "2024-01-01 00:02:00",
                        "2024-01-01 00:03:00",
                    ],
                    utc=True,
                )
            }
        )

        with caplog.at_level(logging.DEBUG):
            gap_count, overlap_count = detect_gaps_and_overlaps(df, "EURUSD")

        assert gap_count == 0
        assert overlap_count == 0

        # Should have minimal logging (just debug statement)
        assert len(caplog.records) <= 1
