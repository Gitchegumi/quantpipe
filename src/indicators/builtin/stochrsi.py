"""Stochastic RSI indicator - vectorized DataFrame implementation."""

import logging
from typing import Union

import pandas as pd
import polars as pl


logger = logging.getLogger(__name__)


def compute_rsi(df: Union[pd.DataFrame, pl.DataFrame], period: int = 14, column: str = "close") -> Union[pd.Series, pl.Series]:
    """Compute Relative Strength Index."""
    if isinstance(df, pd.DataFrame):
        delta = df[column].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    elif isinstance(df, pl.DataFrame):
        delta = df.select(pl.col(column).diff().alias("delta")).to_series()
        gain = delta.map_elements(lambda x: x if x > 0 else 0).rolling_mean(window_size=period)
        loss = delta.map_elements(lambda x: -x if x < 0 else 0).rolling_mean(window_size=period)
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    else:
        raise TypeError(f"Unsupported DataFrame type: {type(df)}")


def compute_stoch_rsi(
    df: Union[pd.DataFrame, pl.DataFrame],
    rsi_period: int = 14,
    stoch_period: int = 14,
    column: str = "close",
) -> dict[str, Union[pd.Series, pl.Series]]:
    """Compute Stochastic RSI."""
    if rsi_period < 1:
        raise ValueError(f"RSI period must be >= 1, got {rsi_period}")
    if stoch_period < 1:
        raise ValueError(f"Stochastic period must be >= 1, got {stoch_period}")
    if column not in df.columns:
        raise KeyError(f"Column not found: {column}")

    rsi = compute_rsi(df, period=rsi_period, column=column)
    
    if isinstance(df, pd.DataFrame):
        rsi_min = rsi.rolling(window=stoch_period).min()
        rsi_max = rsi.rolling(window=stoch_period).max()
        stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min)
        stoch_rsi = stoch_rsi.fillna(0.5)
    elif isinstance(df, pl.DataFrame):
        rsi_min = rsi.rolling_min(window_size=stoch_period)
        rsi_max = rsi.rolling_max(window_size=stoch_period)
        stoch_rsi = ((rsi - rsi_min) / (rsi_max - rsi_min)).fill_nan(0.5)
    else:
        raise TypeError(f"Unsupported DataFrame type: {type(df)}")

    logger.debug("Computed stoch_rsi")
    return {"stoch_rsi": stoch_rsi}
