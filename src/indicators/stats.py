"""
Statistical indicators module using Polars.

This module provides common statistical functions like Z-score, rolling mean,
and rolling standard deviation, optimized for vectorized execution.
"""

import polars as pl


def calculate_rolling_mean(
    df: pl.DataFrame,
    period: int,
    column: str = "close",
    output_col: str | None = None,
) -> pl.DataFrame:
    """
    Calculate rolling mean (Simple Moving Average).

    Args:
        df: Input DataFrame.
        period: Window size.
        column: Input column name.
        output_col: Optional output column name (default: mean_{period}).

    Returns:
        DataFrame with appended mean column.
    """
    out_name = output_col or f"mean_{period}"
    return df.with_columns(
        pl.col(column).rolling_mean(window_size=period).alias(out_name)
    )


def calculate_rolling_std(
    df: pl.DataFrame,
    period: int,
    column: str = "close",
    output_col: str | None = None,
) -> pl.DataFrame:
    """
    Calculate rolling standard deviation.

    Args:
        df: Input DataFrame.
        period: Window size.
        column: Input column name.
        output_col: Optional output column name (default: std_{period}).

    Returns:
        DataFrame with appended std column.
    """
    out_name = output_col or f"std_{period}"
    return df.with_columns(
        pl.col(column).rolling_std(window_size=period).alias(out_name)
    )


def calculate_zscore(
    df: pl.DataFrame,
    period: int,
    column: str = "close",
    output_col: str | None = None,
) -> pl.DataFrame:
    """
    Calculate rolling Z-score.

    Z = (Value - Mean) / StdDev

    Args:
        df: Input DataFrame.
        period: Window size for mean and std dev.
        column: Input column name.
        output_col: Optional output column name (default: zscore_{period}).

    Returns:
        DataFrame with appended z-score column.
    """
    mean_col = pl.col(column).rolling_mean(window_size=period)
    std_col = pl.col(column).rolling_std(window_size=period)

    # Avoid division by zero
    z_score = (pl.col(column) - mean_col) / std_col

    out_name = output_col or f"zscore_{period}"
    return df.with_columns(z_score.fill_nan(0.0).alias(out_name))
