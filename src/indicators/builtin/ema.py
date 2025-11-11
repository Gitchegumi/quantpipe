"""Exponential Moving Average (EMA) indicator implementation.

This module provides vectorized EMA computation using pandas' native
exponential weighted moving average functionality.
"""

import logging

import pandas as pd


logger = logging.getLogger(__name__)


def compute_ema(
    df: pd.DataFrame, period: int = 20, column: str = "close"
) -> dict[str, pd.Series]:
    """Compute Exponential Moving Average.

    Uses pandas' ewm() for vectorized computation. The smoothing factor
    alpha is computed as 2 / (period + 1) following standard EMA convention.

    Args:
        df: DataFrame containing OHLCV data.
        period: Number of periods for EMA calculation (default: 20).
        column: Column name to compute EMA on (default: 'close').

    Returns:
        Dict[str, pd.Series]: Dictionary with single key 'ema{period}'
            mapping to the computed EMA series.

    Raises:
        KeyError: If the specified column doesn't exist in df.
        ValueError: If period < 1.

    Example:
        >>> df = pd.DataFrame({'close': [10, 11, 12, 13, 14]})
        >>> result = compute_ema(df, period=3)
        >>> 'ema3' in result
        True
    """
    if period < 1:
        raise ValueError(f"EMA period must be >= 1, got {period}")

    if column not in df.columns:
        raise KeyError(
            f"Column '{column}' not found in DataFrame. "
            f"Available: {list(df.columns)}"
        )

    # Compute EMA using pandas ewm with span parameter
    # span = period ensures alpha = 2 / (period + 1)
    ema_values = df[column].ewm(span=period, adjust=False).mean()

    indicator_name = f"ema{period}"
    logger.debug(
        "Computed %s on column '%s': %d values",
        indicator_name,
        column,
        len(ema_values),
    )

    return {indicator_name: ema_values}


def compute_ema_multiple(
    df: pd.DataFrame, periods: list[int], column: str = "close"
) -> dict[str, pd.Series]:
    """Compute multiple EMAs at once.

    Convenience function to compute several EMA periods simultaneously.

    Args:
        df: DataFrame containing OHLCV data.
        periods: List of periods to compute EMAs for.
        column: Column name to compute EMAs on (default: 'close').

    Returns:
        Dict[str, pd.Series]: Dictionary with keys 'ema{period}' for each
            requested period.

    Example:
        >>> df = pd.DataFrame({'close': [10, 11, 12, 13, 14]})
        >>> result = compute_ema_multiple(df, periods=[3, 5])
        >>> sorted(result.keys())
        ['ema3', 'ema5']
    """
    result = {}
    for period in periods:
        ema_dict = compute_ema(df, period=period, column=column)
        result.update(ema_dict)

    logger.info(
        "Computed %d EMAs on column '%s': periods %s",
        len(periods),
        column,
        periods,
    )

    return result
