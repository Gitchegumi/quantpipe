"""Stochastic RSI indicator - vectorized DataFrame implementation."""

import logging

import pandas as pd


logger = logging.getLogger(__name__)


def compute_rsi(df: pd.DataFrame, period: int = 14, column: str = "close") -> pd.Series:
    """Compute Relative Strength Index."""
    delta = df[column].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_stoch_rsi(
    df: pd.DataFrame,
    rsi_period: int = 14,
    stoch_period: int = 14,
    column: str = "close",
) -> dict[str, pd.Series]:
    """Compute Stochastic RSI."""
    if rsi_period < 1:
        raise ValueError(f"RSI period must be >= 1, got {rsi_period}")
    if stoch_period < 1:
        raise ValueError(f"Stochastic period must be >= 1, got {stoch_period}")
    if column not in df.columns:
        raise KeyError(f"Column not found: {column}")

    rsi = compute_rsi(df, period=rsi_period, column=column)
    rsi_min = rsi.rolling(window=stoch_period).min()
    rsi_max = rsi.rolling(window=stoch_period).max()
    stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min)
    stoch_rsi = stoch_rsi.fillna(0.5)

    logger.debug("Computed stoch_rsi")
    return {"stoch_rsi": stoch_rsi}
