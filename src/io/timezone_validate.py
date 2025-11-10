"""Timezone validation utilities.

This module provides utilities for validating that timestamps are in UTC,
rejecting non-UTC timestamps as required by FR-014.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def validate_utc_timezone(
    df: pd.DataFrame, timestamp_col: str = "timestamp_utc"
) -> None:
    """Validate that all timestamps are in UTC timezone.

    Args:
        df: DataFrame with timestamp column.
        timestamp_col: Name of the timestamp column.

    Raises:
        ValueError: If timestamps are not UTC or timezone-naive.
    """
    if timestamp_col not in df.columns:
        raise ValueError(f"Timestamp column '{timestamp_col}' not found")

    timestamps = df[timestamp_col]

    # Check if timestamps are timezone-aware
    if timestamps.dt.tz is None:
        raise ValueError(
            "Non-UTC timestamps detected: timestamps are timezone-naive. "
            "Expected UTC timezone."
        )

    # Check if timezone is UTC
    if str(timestamps.dt.tz) != "UTC":
        raise ValueError(
            f"Non-UTC timestamps detected: timezone is {timestamps.dt.tz}. "
            f"Expected UTC."
        )

    logger.debug("UTC timezone validation passed")


def ensure_utc_timezone(series: pd.Series) -> pd.Series:
    """Ensure a timestamp series is UTC-aware.

    Args:
        series: Timestamp series.

    Returns:
        pd.Series: UTC-aware timestamp series.

    Raises:
        ValueError: If series has non-UTC timezone.
    """
    if series.dt.tz is None:
        # Assume UTC if naive
        logger.warning("Timezone-naive timestamps detected, assuming UTC")
        return series.dt.tz_localize("UTC")

    if str(series.dt.tz) != "UTC":
        raise ValueError(
            f"Cannot convert non-UTC timezone {series.dt.tz} to UTC automatically"
        )

    return series
