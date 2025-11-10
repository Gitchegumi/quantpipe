"""Cadence interval computation utilities.

This module provides utilities for computing expected cadence intervals
and validating that the dataset meets cadence uniformity requirements.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def compute_expected_intervals(
    start_time: pd.Timestamp,
    end_time: pd.Timestamp,
    timeframe_minutes: int,
) -> int:
    """Compute expected number of intervals for a uniform cadence.

    Args:
        start_time: Start timestamp (UTC).
        end_time: End timestamp (UTC).
        timeframe_minutes: Cadence in minutes (e.g., 1 for 1-minute bars).

    Returns:
        int: Expected number of intervals.
    """
    delta = end_time - start_time
    total_minutes = delta.total_seconds() / 60.0
    return int(total_minutes / timeframe_minutes) + 1


def compute_cadence_deviation(
    actual_count: int,
    expected_count: int,
) -> float:
    """Compute cadence deviation percentage.

    Args:
        actual_count: Actual number of intervals observed.
        expected_count: Expected number of intervals.

    Returns:
        float: Deviation percentage (0.0 to 100.0).
    """
    if expected_count == 0:
        return 0.0
    missing = expected_count - actual_count
    return abs(missing / expected_count) * 100.0


def validate_cadence_uniformity(
    df: pd.DataFrame,
    timeframe_minutes: int,
    tolerance_percent: float = 2.0,
) -> tuple[int, int, float]:
    """Validate that dataset meets cadence uniformity requirements.

    Args:
        df: DataFrame with 'timestamp_utc' column.
        timeframe_minutes: Expected cadence in minutes.
        tolerance_percent: Maximum allowed deviation percentage.

    Returns:
        tuple: (actual_count, expected_count, deviation_percent)

    Raises:
        RuntimeError: If cadence deviation exceeds tolerance.
    """
    if len(df) == 0:
        return 0, 0, 0.0

    start_time = df["timestamp_utc"].iloc[0]
    end_time = df["timestamp_utc"].iloc[-1]

    actual_count = len(df)
    expected_count = compute_expected_intervals(
        start_time, end_time, timeframe_minutes
    )
    deviation = compute_cadence_deviation(actual_count, expected_count)

    if deviation > tolerance_percent:
        raise RuntimeError(
            f"Cadence deviation exceeds tolerance: {deviation:.2f}% "
            f"(max: {tolerance_percent:.2f}%)"
        )

    logger.info(
        "Cadence validation passed: %d/%d intervals, %.2f%% deviation",
        actual_count,
        expected_count,
        deviation,
    )

    return actual_count, expected_count, deviation


def compute_cadence_minutes(timestamps: pd.Series) -> int:
    """Compute the median cadence in minutes from timestamps.

    Args:
        timestamps: Series of UTC timestamps.

    Returns:
        int: Median cadence in minutes.
    """
    if len(timestamps) < 2:
        return 1  # Default to 1 minute if insufficient data

    time_diffs = timestamps.diff()[1:]  # Skip first NaT
    median_diff = time_diffs.median()
    return int(median_diff.total_seconds() / 60)


def validate_cadence(
    timestamps: pd.Series | pd.DatetimeIndex, expected_minutes: int, tolerance: float = 0.02
) -> None:
    """Validate that timestamps meet cadence uniformity requirements.

    Args:
        timestamps: Series or DatetimeIndex of UTC timestamps.
        expected_minutes: Expected cadence in minutes.
        tolerance: Maximum allowed deviation as fraction (e.g., 0.02 for 2%).

    Raises:
        RuntimeError: If cadence deviation exceeds tolerance.
    """
    if len(timestamps) < 2:
        return  # Not enough data to validate

    # Convert to Series if DatetimeIndex
    if isinstance(timestamps, pd.DatetimeIndex):
        timestamps = pd.Series(timestamps)

    start_time = timestamps.iloc[0]
    end_time = timestamps.iloc[-1]

    actual_count = len(timestamps)
    expected_count = compute_expected_intervals(
        start_time, end_time, expected_minutes
    )
    deviation_percent = compute_cadence_deviation(actual_count, expected_count)
    tolerance_percent = tolerance * 100.0

    if deviation_percent > tolerance_percent:
        raise RuntimeError(
            f"Cadence deviation exceeds tolerance: {deviation_percent:.2f}% "
            f"(expected ≤{tolerance_percent:.2f}%). "
            f"Missing {expected_count - actual_count} intervals."
        )
