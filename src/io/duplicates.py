"""Duplicate detection and resolution utilities.

This module provides utilities for detecting and resolving duplicate
timestamps in candle data using a keep-first strategy.
"""

from __future__ import annotations

import logging

import pandas as pd
from polars import DataFrame as PolarsDataFrame

logger = logging.getLogger(__name__)


def get_duplicate_mask(
    df: pd.DataFrame | PolarsDataFrame, is_polars: bool = False
) -> pd.Series | pl.Series:
    """Get boolean mask indicating which rows are duplicates.

    Args:
        df: DataFrame with 'timestamp_utc' column (Pandas or Polars).
        is_polars: If True, df is a Polars DataFrame.

    Returns:
        pd.Series | pl.Series: Boolean mask where True indicates a duplicate row.
    """
    if is_polars:
        return df["timestamp_utc"].is_duplicated()
    return df["timestamp_utc"].duplicated(keep="first")


def detect_duplicates(
    df: pd.DataFrame | PolarsDataFrame, is_polars: bool = False
) -> pd.DataFrame | PolarsDataFrame:
    """Detect duplicate timestamps in candle data.

    Args:
        df: DataFrame with 'timestamp_utc' column (Pandas or Polars).
        is_polars: If True, df is a Polars DataFrame.

    Returns:
        pd.DataFrame | PolarsDataFrame: Subset of rows that are duplicates (not the first occurrence).
    """
    duplicate_mask = get_duplicate_mask(df, is_polars)
    if is_polars:
        return df.filter(duplicate_mask)
    return df[duplicate_mask]


def remove_duplicates(
    df: pd.DataFrame | PolarsDataFrame, is_polars: bool = False
) -> tuple[pd.DataFrame | PolarsDataFrame, int]:
    """Remove duplicate timestamps, keeping the first occurrence.

    Args:
        df: DataFrame with 'timestamp_utc' column (Pandas or Polars).
        is_polars: If True, df is a Polars DataFrame.

    Returns:
        tuple: (cleaned_df, count_removed)
    """
    duplicates = detect_duplicates(df, is_polars)
    count_removed = len(duplicates)

    if count_removed > 0:
        logger.warning(
            "Removing %d duplicate timestamps (keeping first occurrence)",
            count_removed,
        )
        # Log sample of removed timestamps for audit
        sample_size = min(5, count_removed)
        if is_polars:
            sample_timestamps = duplicates["timestamp_utc"].head(sample_size).to_list()
        else:
            sample_timestamps = duplicates["timestamp_utc"].head(sample_size).tolist()
        logger.debug("Sample duplicate timestamps removed: %s", sample_timestamps)

    if is_polars:
        cleaned_df = df.unique(subset=["timestamp_utc"], keep="first")
    else:
        cleaned_df = df.drop_duplicates(subset=["timestamp_utc"], keep="first")
    return cleaned_df, count_removed
