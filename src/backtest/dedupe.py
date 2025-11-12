"""Duplicate timestamp handling utilities for data deduplication.

This module provides utilities for detecting and removing duplicate timestamps
from time series data while maintaining deterministic behavior and audit trails.
"""

import logging
from datetime import datetime
from typing import Optional

import numpy as np
import polars as pl


logger = logging.getLogger(__name__)


class DedupeResult:
    """Result of deduplication operation with audit information.

    Attributes:
        original_count: Number of rows before deduplication
        deduplicated_count: Number of rows after deduplication
        duplicates_removed: Number of duplicate rows removed
        first_duplicate_ts: First duplicate timestamp encountered (if any)
        last_duplicate_ts: Last duplicate timestamp encountered (if any)
        indices_kept: NumPy array of indices that were kept
    """

    def __init__(
        self,
        original_count: int,
        deduplicated_count: int,
        duplicates_removed: int,
        first_duplicate_ts: Optional[datetime] = None,
        last_duplicate_ts: Optional[datetime] = None,
        indices_kept: Optional[np.ndarray] = None,
    ):
        """Initialize dedupe result.

        Args:
            original_count: Number of rows before deduplication
            deduplicated_count: Number of rows after deduplication
            duplicates_removed: Number of duplicate rows removed
            first_duplicate_ts: First duplicate timestamp (optional)
            last_duplicate_ts: Last duplicate timestamp (optional)
            indices_kept: Array of indices kept (optional)
        """
        self.original_count = original_count
        self.deduplicated_count = deduplicated_count
        self.duplicates_removed = duplicates_removed
        self.first_duplicate_ts = first_duplicate_ts
        self.last_duplicate_ts = last_duplicate_ts
        self.indices_kept = indices_kept

    def __repr__(self) -> str:
        """String representation of dedupe result."""
        return (
            f"DedupeResult(original={self.original_count}, "
            f"deduplicated={self.deduplicated_count}, "
            f"removed={self.duplicates_removed})"
        )


def dedupe_timestamps_polars(
    df: pl.DataFrame, timestamp_col: str = "timestamp_utc"
) -> tuple[pl.DataFrame, DedupeResult]:
    """Remove duplicate timestamps from Polars DataFrame, keeping first occurrence.

    Args:
        df: Polars DataFrame containing time series data
        timestamp_col: Name of timestamp column (default: 'timestamp_utc')

    Returns:
        Tuple of (deduplicated DataFrame, DedupeResult)

    Raises:
        ValueError: If timestamp column does not exist
    """
    if timestamp_col not in df.columns:
        msg = "Timestamp column '%s' not found in DataFrame"
        logger.error(msg, timestamp_col)
        raise ValueError(msg % timestamp_col)

    original_count = len(df)

    # Find duplicate timestamps (keeping first occurrence)
    is_duplicate = df[timestamp_col].is_duplicated()

    # Track first and last duplicate timestamps
    first_duplicate_ts = None
    last_duplicate_ts = None

    if is_duplicate.any():
        # Get duplicate timestamps
        dup_timestamps = df.filter(is_duplicate)[timestamp_col]
        if len(dup_timestamps) > 0:
            first_duplicate_ts = dup_timestamps[0]
            last_duplicate_ts = dup_timestamps[-1]

        logger.warning(
            "Found %d duplicate timestamps (first: %s, last: %s)",
            is_duplicate.sum(),
            first_duplicate_ts,
            last_duplicate_ts,
        )

    # Remove duplicates (keep='first' is default behavior)
    df_deduped = df.unique(subset=[timestamp_col], keep="first", maintain_order=True)

    deduplicated_count = len(df_deduped)
    duplicates_removed = original_count - deduplicated_count

    result = DedupeResult(
        original_count=original_count,
        deduplicated_count=deduplicated_count,
        duplicates_removed=duplicates_removed,
        first_duplicate_ts=first_duplicate_ts,
        last_duplicate_ts=last_duplicate_ts,
    )

    logger.info(
        "Deduplication complete: %d rows -> %d rows (%d removed)",
        original_count,
        deduplicated_count,
        duplicates_removed,
    )

    return df_deduped, result


def dedupe_timestamps_numpy(
    timestamps: np.ndarray,
) -> tuple[np.ndarray, DedupeResult]:
    """Remove duplicate timestamps from NumPy array, keeping first occurrence.

    Args:
        timestamps: NumPy array of timestamps (datetime64 or numeric)

    Returns:
        Tuple of (unique indices to keep, DedupeResult)

    Note:
        Returns indices rather than values to allow coordinated filtering
        of multiple parallel arrays (timestamps, prices, indicators, etc.)
    """
    original_count = len(timestamps)

    # Find first occurrence of each unique timestamp
    _, unique_indices = np.unique(timestamps, return_index=True)

    # Sort indices to maintain original order
    unique_indices = np.sort(unique_indices)

    deduplicated_count = len(unique_indices)
    duplicates_removed = original_count - deduplicated_count

    # Track first and last duplicate timestamps if any exist
    first_duplicate_ts = None
    last_duplicate_ts = None

    if duplicates_removed > 0:
        # Find duplicate indices (not in unique_indices)
        all_indices = np.arange(original_count)
        duplicate_mask = ~np.isin(all_indices, unique_indices)
        duplicate_indices = all_indices[duplicate_mask]

        if len(duplicate_indices) > 0:
            first_duplicate_ts = timestamps[duplicate_indices[0]]
            last_duplicate_ts = timestamps[duplicate_indices[-1]]

        logger.warning(
            "Found %d duplicate timestamps (first index: %d, last index: %d)",
            duplicates_removed,
            duplicate_indices[0] if len(duplicate_indices) > 0 else -1,
            duplicate_indices[-1] if len(duplicate_indices) > 0 else -1,
        )

    result = DedupeResult(
        original_count=original_count,
        deduplicated_count=deduplicated_count,
        duplicates_removed=duplicates_removed,
        first_duplicate_ts=first_duplicate_ts,
        last_duplicate_ts=last_duplicate_ts,
        indices_kept=unique_indices,
    )

    logger.info(
        "Deduplication complete: %d timestamps -> %d unique (%d removed)",
        original_count,
        deduplicated_count,
        duplicates_removed,
    )

    return unique_indices, result
