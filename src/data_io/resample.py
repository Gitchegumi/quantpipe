"""OHLCV resampling for multi-timeframe backtesting.

This module provides functionality to resample 1-minute OHLCV data to higher
timeframes (e.g., 5m, 15m, 1h, 1d) using correct aggregation rules.

Aggregation Rules (FR-005):
- Open: first open in period
- High: max high in period
- Low: min low in period
- Close: last close in period
- Volume: sum of volume in period

Key Features:
- bar_complete column marks bars with missing constituent minutes (FR-007)
- Incomplete leading/trailing bars are dropped (per spec clarification)
- UTC boundary alignment (FR-006)

Performance Target:
- Resampling ≤5s for 6.9M rows using Polars vectorized operations
"""

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

import polars as pl


if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def resample_ohlcv(
    df: pl.DataFrame,
    target_minutes: int,
    timestamp_col: str = "timestamp_utc",
) -> pl.DataFrame:
    """Resample 1-minute OHLCV data to a higher timeframe.

    Uses Polars group_by_dynamic for efficient vectorized resampling with
    correct OHLCV aggregation. Bars are aligned to UTC minute boundaries.

    Args:
        df: Polars DataFrame with 1-minute OHLCV data.
            Required columns: timestamp_utc, open, high, low, close, volume
        target_minutes: Target timeframe in minutes (e.g., 15 for 15m, 60 for 1h).
        timestamp_col: Name of the timestamp column (default: 'timestamp_utc').

    Returns:
        Resampled DataFrame with columns:
        - timestamp_utc: Bar close timestamp (UTC aligned)
        - open, high, low, close, volume: Aggregated OHLCV values
        - bar_complete: True if all constituent 1-minute bars present (FR-007)

    Raises:
        ValueError: If required columns missing or target_minutes < 1.

    Examples:
        >>> df_15m = resample_ohlcv(df_1m, target_minutes=15)
        >>> df_1h = resample_ohlcv(df_1m, target_minutes=60)
    """
    if target_minutes < 1:
        raise ValueError(f"target_minutes must be >= 1, got {target_minutes}")

    # Validate required columns
    required_cols = {timestamp_col, "open", "high", "low", "close", "volume"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # If target is 1 minute, return original with bar_complete=True
    if target_minutes == 1:
        return df.with_columns(pl.lit(True).alias("bar_complete"))

    logger.info(
        "Resampling %d rows from 1m to %dm timeframe",
        len(df),
        target_minutes,
    )

    # Ensure timestamp column is datetime type
    if df[timestamp_col].dtype != pl.Datetime:
        df = df.with_columns(pl.col(timestamp_col).cast(pl.Datetime("us", "UTC")))

    # Use group_by_dynamic for time-based grouping
    # every: the interval for grouping
    # period: same as every (we want non-overlapping windows)
    # closed: 'left' means [start, end) intervals
    interval = f"{target_minutes}m"

    resampled = df.group_by_dynamic(
        timestamp_col,
        every=interval,
        period=interval,
        closed="left",
        label="right",  # Timestamp is at bar close
    ).agg(
        [
            pl.col("open").first().alias("open"),
            pl.col("high").max().alias("high"),
            pl.col("low").min().alias("low"),
            pl.col("close").last().alias("close"),
            pl.col("volume").sum().alias("volume"),
            pl.len().alias("_bar_count"),
        ]
    )

    # Add bar_complete flag (FR-007)
    # A bar is complete if it has exactly target_minutes constituent 1-minute bars
    resampled = resampled.with_columns(
        (pl.col("_bar_count") == target_minutes).alias("bar_complete")
    ).drop("_bar_count")

    # Drop incomplete leading/trailing bars (per spec clarification)
    resampled = _drop_incomplete_edge_bars(resampled)

    logger.info(
        "Resampled to %d bars (%dm timeframe)",
        len(resampled),
        target_minutes,
    )

    return resampled


def _drop_incomplete_edge_bars(df: pl.DataFrame) -> pl.DataFrame:
    """Drop incomplete bars at the start and end of the dataset.

    Per spec clarification: incomplete leading/trailing bars are always dropped
    (no override flag provided).

    Args:
        df: DataFrame with bar_complete column.

    Returns:
        DataFrame with incomplete edge bars removed.
    """
    if len(df) == 0:
        return df

    # Find first complete bar
    first_complete_idx = None
    bar_complete = df["bar_complete"].to_list()

    for i, complete in enumerate(bar_complete):
        if complete:
            first_complete_idx = i
            break

    if first_complete_idx is None:
        logger.warning("No complete bars found in resampled data")
        return df.clear()

    # Find last complete bar
    last_complete_idx = None
    for i in range(len(bar_complete) - 1, -1, -1):
        if bar_complete[i]:
            last_complete_idx = i
            break

    # Slice to keep only the range with complete edges
    if first_complete_idx > 0 or last_complete_idx < len(df) - 1:
        dropped_leading = first_complete_idx
        dropped_trailing = len(df) - 1 - last_complete_idx
        logger.debug(
            "Dropped %d incomplete leading bars, %d trailing bars",
            dropped_leading,
            dropped_trailing,
        )

    return df.slice(first_complete_idx, last_complete_idx - first_complete_idx + 1)
