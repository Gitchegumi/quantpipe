"""
This module provides a vectorized rolling window implementation using Polars.
"""

import polars as pl


def calculate_ema(
    df: pl.DataFrame, period: int, column: str = "close", output_col: str | None = None
) -> pl.DataFrame:
    """
    Calculate Exponential Moving Average (EMA).

    Args:
        df: Input DataFrame.
        period: EMA period.
        column: Column to calculate EMA on.
        output_col: Optional name for output column.
    """
    out_name = output_col or f"ema{period}"
    return df.with_columns(
        pl.col(column).ewm_mean(span=period, adjust=False).alias(out_name)
    )


def calculate_atr(
    df: pl.DataFrame, period: int, output_col: str | None = None
) -> pl.DataFrame:
    """
    Calculate Average True Range (ATR).

    Args:
        df: Input DataFrame with high, low, close columns.
        period: ATR period.
        output_col: Optional output column name.

    Returns:
        DataFrame with new column `atr{period}`.
    """
    # Calculate True Range
    # TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
    # In Polars, we can calculate these 3 components and take the max

    prev_close = pl.col("close").shift(1)
    tr1 = pl.col("high") - pl.col("low")
    tr2 = (pl.col("high") - prev_close).abs()
    tr3 = (pl.col("low") - prev_close).abs()

    # We need to handle the first row where prev_close is null.
    # Standard ATR definition usually takes high-low for the first period.
    # Polars max_horizontal ignores nulls, so if prev_close is null, tr2/tr3 are null.

    tr = pl.max_horizontal(tr1, tr2, tr3).alias("tr")

    # ATR is EMA of TR
    # Note: Some implementations use RMA (Wilder's Smoothing), which is
    # ewm(alpha=1/period).
    # The existing basic.py uses standard EMA (alpha=2/(period+1)).
    # We will stick to standard EMA to match basic.py unless specified otherwise.

    out_name = output_col or f"atr{period}"
    return (
        df.with_columns(tr)
        .with_columns(pl.col("tr").ewm_mean(span=period, adjust=False).alias(out_name))
        .drop("tr")
    )


def calculate_rsi(
    df: pl.DataFrame, period: int, column: str = "close", output_col: str | None = None
) -> pl.DataFrame:
    """
    Calculate Relative Strength Index (RSI).

    Args:
        df: Input DataFrame.
        period: RSI period.
        column: Column to calculate RSI on.
        output_col: Optional output name.

    Returns:
        DataFrame with new column `rsi`.
    """
    delta = pl.col(column).diff()
    gain = delta.clip(lower_bound=0)
    loss = delta.clip(upper_bound=0).abs()

    # Use standard EMA for avg_gain/avg_loss as per basic.py
    avg_gain = gain.ewm_mean(span=period, adjust=False)
    avg_loss = loss.ewm_mean(span=period, adjust=False)

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # Handle division by zero (if avg_loss is 0, RSI is 100)
    rsi = pl.when(avg_loss == 0).then(100).otherwise(rsi)

    out_name = output_col or "rsi"
    return df.with_columns(rsi.alias(out_name))


def calculate_stoch_rsi(
    df: pl.DataFrame,
    period: int = 14,
    rsi_col: str = "rsi",
    output_col: str | None = None,
) -> pl.DataFrame:
    """
    Calculate Stochastic RSI.

    Args:
        df: Input DataFrame with RSI column.
        period: Lookback period.
        rsi_col: Name of the RSI column.
        output_col: Optional output name.

    Returns:
        DataFrame with new column `stoch_rsi`.
    """
    rsi = pl.col(rsi_col)
    rsi_min = rsi.rolling_min(window_size=period)
    rsi_max = rsi.rolling_max(window_size=period)

    stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min)

    # Handle division by zero (flat RSI) -> 0.5
    stoch_rsi = pl.when(rsi_max == rsi_min).then(0.5).otherwise(stoch_rsi)

    out_name = output_col or "stoch_rsi"
    return df.with_columns(stoch_rsi.alias(out_name))
