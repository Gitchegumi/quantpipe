"""Gap detection utilities.

This module provides utilities for detecting timestamp gaps in candle data
and preparing for gap filling operations.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Union

import pandas as pd
from polars import DataFrame as PolarsDataFrame
import polars as pl

logger = logging.getLogger(__name__)


def detect_gaps(
    df: pd.DataFrame | PolarsDataFrame, timeframe_minutes: int, is_polars: bool = False
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Detect timestamp gaps in candle data.

    Args:
        df: DataFrame with sorted 'timestamp_utc' column (Pandas or Polars).
        timeframe_minutes: Expected cadence in minutes.
        is_polars: If True, df is a Polars DataFrame.

    Returns:
        list: List of (gap_start, gap_end) tuples representing missing intervals.
    """
    if len(df) < 2:
        return []

    gaps = []
    expected_delta = timedelta(minutes=timeframe_minutes)

    if is_polars:
        timestamps = df["timestamp_utc"].to_numpy()
        for i in range(len(timestamps) - 1):
            current_ts = timestamps[i]
            next_ts = timestamps[i + 1]
            actual_delta = next_ts - current_ts

            if actual_delta > expected_delta:
                # Gap detected
                gap_start = current_ts + expected_delta
                gap_end = next_ts - expected_delta
                gaps.append((pd.Timestamp(current_ts + expected_delta), pd.Timestamp(next_ts - expected_delta)))
    else:
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
    start_time: pd.Timestamp | pl.datetime,
    end_time: pd.Timestamp | pl.datetime,
    timeframe_minutes: int,
    is_polars: bool = False,
) -> Union[pd.DatetimeIndex, pl.Series]:
    """Create a complete datetime index with uniform cadence.

    Args:
        start_time: Start timestamp.
        end_time: End timestamp.
        timeframe_minutes: Cadence in minutes.
        is_polars: If True, return a Polars Series.

    Returns:
        pd.DatetimeIndex | pl.Series: Complete index covering the time range.
    """
    if is_polars:
        return pl.datetime_range(
            start=start_time,
            end=end_time,
            interval=f"{timeframe_minutes}m",
            eager=True,
        ).alias("timestamp_utc")
    else:
        return pd.date_range(
            start=start_time,
            end=end_time,
            freq=f"{timeframe_minutes}min",
            tz="UTC",
        )


def reindex_with_gaps(
    df: pd.DataFrame | PolarsDataFrame, timeframe_minutes: int, is_polars: bool = False
) -> tuple[pd.DataFrame | PolarsDataFrame, int]:
    """Reindex DataFrame to include placeholder rows for gaps.

    Args:
        df: DataFrame with 'timestamp_utc' as index or column.
        timeframe_minutes: Expected cadence in minutes.
        is_polars: If True, df is a Polars DataFrame.

    Returns:
        tuple: (reindexed_df, count_gaps)
    """
    if is_polars:
        start_time = df["timestamp_utc"].min()
        end_time = df["timestamp_utc"].max()
        complete_index = create_complete_index(start_time, end_time, timeframe_minutes, is_polars=True)

        # Join with the complete index to find gaps
        reindexed_df = complete_index.to_frame().join(df, on="timestamp_utc", how="left")
        count_gaps = reindexed_df["open"].is_null().sum()
    else:
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
