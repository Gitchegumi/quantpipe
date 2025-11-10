"""Duplicate detection and resolution utilities.

This module provides utilities for detecting and resolving duplicate
timestamps in candle data using a keep-first strategy.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def detect_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Detect duplicate timestamps in candle data.

    Args:
        df: DataFrame with 'timestamp_utc' column.

    Returns:
        pd.DataFrame: Subset of rows that are duplicates (not the first occurrence).
    """
    duplicate_mask = df["timestamp_utc"].duplicated(keep="first")
    return df[duplicate_mask]


def remove_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Remove duplicate timestamps, keeping the first occurrence.

    Args:
        df: DataFrame with 'timestamp_utc' column.

    Returns:
        tuple: (cleaned_df, count_removed)
    """
    duplicates = detect_duplicates(df)
    count_removed = len(duplicates)

    if count_removed > 0:
        logger.warning(
            "Removing %d duplicate timestamps (keeping first occurrence)",
            count_removed,
        )
        # Log sample of removed timestamps for audit
        sample_size = min(5, count_removed)
        sample_timestamps = duplicates["timestamp_utc"].head(sample_size).tolist()
        logger.debug("Sample duplicate timestamps removed: %s", sample_timestamps)

    cleaned_df = df.drop_duplicates(subset=["timestamp_utc"], keep="first")
    return cleaned_df, count_removed
