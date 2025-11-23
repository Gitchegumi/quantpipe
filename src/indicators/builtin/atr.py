"""Average True Range (ATR) indicator implementation.

This module provides vectorized ATR computation using pandas operations
for efficient calculation of market volatility.
"""

import logging
from typing import Union

import pandas as pd
import polars as pl


logger = logging.getLogger(__name__)


def compute_atr(df: Union[pd.DataFrame, pl.DataFrame], period: int = 14) -> dict[str, Union[pd.Series, pl.Series]]:
    """Compute Average True Range (ATR).

    ATR measures market volatility by computing the average of true ranges
    over a specified period. True Range is the maximum of:
    1. Current High - Current Low
    2. Absolute(Current High - Previous Close)
    3. Absolute(Current Low - Previous Close)

    Uses pandas' rolling window or polars for vectorized computation.

    Args:
        df: DataFrame containing OHLCV data with 'high', 'low', 'close' columns.
        period: Number of periods for ATR calculation (default: 14).

    Returns:
        Dict[str, pd.Series]: Dictionary with single key 'atr{period}'
            mapping to the computed ATR series.

    Raises:
        KeyError: If required columns ('high', 'low', 'close') don't exist.
        ValueError: If period < 1.

    Example:
        >>> df = pd.DataFrame({
        ...     'high': [12, 13, 14, 15, 16],
        ...     'low': [10, 11, 12, 13, 14],
        ...     'close': [11, 12, 13, 14, 15]
        ... })
        >>> result = compute_atr(df, period=3)
        >>> 'atr3' in result
        True
    """
    if period < 1:
        raise ValueError(f"ATR period must be >= 1, got {period}")

    required_cols = ["high", "low", "close"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise KeyError(
            f"Missing required columns for ATR: {missing}. "
            f"Available: {list(df.columns)}"
        )

    if isinstance(df, pd.DataFrame):
        # Compute True Range components
        high_low = df["high"] - df["low"]
        high_prev_close = (df["high"] - df["close"].shift(1)).abs()
        low_prev_close = (df["low"] - df["close"].shift(1)).abs()

        # True Range is the maximum of the three components
        true_range = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(
            axis=1
        )

        # ATR is the moving average of True Range
        # Use exponential weighted moving average for smoothness
        atr_values = true_range.ewm(span=period, adjust=False).mean()
    elif isinstance(df, pl.DataFrame):
        high_low = df.select(pl.col("high") - pl.col("low")).to_series()
        high_prev_close = df.select((pl.col("high") - pl.col("close").shift(1)).abs()).to_series()
        low_prev_close = df.select((pl.col("low") - pl.col("close").shift(1)).abs()).to_series()

        true_range = pl.concat([high_low, high_prev_close, low_prev_close], how="horizontal").max(axis=1)

        atr_values = true_range.ewm_mean(span=period, adjust=False)
    else:
        raise TypeError(f"Unsupported DataFrame type: {type(df)}")


    indicator_name = f"atr{period}"
    logger.debug(
        "Computed %s: %d values (first %d will be NaN due to warmup)",
        indicator_name,
        len(atr_values),
        1,  # First value is NaN due to shift
    )

    return {indicator_name: atr_values}


def compute_atr_multiple(df: pd.DataFrame, periods: list[int]) -> dict[str, pd.Series]:
    """Compute multiple ATRs at once.

    Convenience function to compute several ATR periods simultaneously.

    Args:
        df: DataFrame containing OHLCV data.
        periods: List of periods to compute ATRs for.

    Returns:
        Dict[str, pd.Series]: Dictionary with keys 'atr{period}' for each
            requested period.

    Example:
        >>> df = pd.DataFrame({
        ...     'high': [12, 13, 14, 15, 16],
        ...     'low': [10, 11, 12, 13, 14],
        ...     'close': [11, 12, 13, 14, 15]
        ... })
        >>> result = compute_atr_multiple(df, periods=[3, 5])
        >>> sorted(result.keys())
        ['atr3', 'atr5']
    """
    result = {}
    for period in periods:
        atr_dict = compute_atr(df, period=period)
        result.update(atr_dict)

    logger.info("Computed %d ATRs: periods %s", len(periods), periods)

    return result
