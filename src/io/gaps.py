"""Gap detection utilities.

This module provides utilities for detecting timestamp gaps in candle data
and preparing for gap filling operations.
"""

import logging
from datetime import timedelta

import pandas as pd

logger = logging.getLogger(__name__)


def detect_gaps(
    df: pd.DataFrame, timeframe_minutes: int
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Detect timestamp gaps in candle data.

    Args:
        df: DataFrame with sorted 'timestamp_utc' column.
        timeframe_minutes: Expected cadence in minutes.

    Returns:
        list: List of (gap_start, gap_end) tuples representing missing intervals.
    """
    if len(df) < 2:
        return []

    gaps = []
    expected_delta = timedelta(minutes=timeframe_minutes)

    for i in range(len(df) - 1):
        current_ts = df["timestamp_utc"].iloc[i]
        next_ts = df["timestamp_utc"].iloc[i + 1]
        actual_delta = next_ts - current_ts

        if actual_delta > expected_delta:
            # Gap detected
            gap_start = current_ts + expected_delta
            gap_end = next_ts - expected_delta
            gaps.append((gap_start, gap_end))

    if gaps:
        logger.info("Detected %d gaps in timestamp sequence", len(gaps))

    return gaps


def create_complete_index(
    start_time: pd.Timestamp,
    end_time: pd.Timestamp,
    timeframe_minutes: int,
) -> pd.DatetimeIndex:
    """Create a complete datetime index with uniform cadence.

    Args:
        start_time: Start timestamp.
        end_time: End timestamp.
        timeframe_minutes: Cadence in minutes.

    Returns:
        pd.DatetimeIndex: Complete index covering the time range.
    """
    return pd.date_range(
        start=start_time,
        end=end_time,
        freq=f"{timeframe_minutes}min",
        tz="UTC",
    )


def reindex_with_gaps(
    df: pd.DataFrame, timeframe_minutes: int
) -> tuple[pd.DataFrame, int]:
    """Reindex DataFrame to include placeholder rows for gaps.

    Args:
        df: DataFrame with 'timestamp_utc' as index or column.
        timeframe_minutes: Expected cadence in minutes.

    Returns:
        tuple: (reindexed_df, count_gaps)
    """
    # Ensure timestamp_utc is the index
    if "timestamp_utc" in df.columns:
        df = df.set_index("timestamp_utc")

    start_time = df.index[0]
    end_time = df.index[-1]

    complete_index = create_complete_index(start_time, end_time, timeframe_minutes)
    reindexed_df = df.reindex(complete_index)

    count_gaps = reindexed_df.isna().any(axis=1).sum()

    logger.info("Reindexed DataFrame: added %d gap placeholder rows", count_gaps)

    return reindexed_df, count_gaps
