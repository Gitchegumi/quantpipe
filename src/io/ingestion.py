"""
Streaming data ingestion for market candles.

This module provides an iterator-based approach to loading and enriching market
data from CSV files. It yields fully-populated Candle objects with computed
technical indicators and validates timestamp continuity.

The ingestion process:
1. Reads raw OHLCV data from CSV
2. Computes EMA, ATR, RSI, Stochastic RSI indicators
3. Detects timestamp gaps (per FR-019)
4. Yields Candle objects one at a time
"""

import logging
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from ..indicators.basic import atr, ema, rsi
from ..models.core import Candle
from ..models.exceptions import DataIntegrityError

logger = logging.getLogger(__name__)


def _compute_stochastic_rsi(
    rsi_values: NDArray[np.float64], period: int = 14
) -> NDArray[np.float64]:
    """
    Compute Stochastic RSI from RSI values.

    Stochastic RSI = (RSI - min(RSI, period)) / (max(RSI, period) - min(RSI, period))

    Args:
        rsi_values: Array of RSI values (0-100).
        period: Lookback period for min/max calculation.

    Returns:
        Array of Stochastic RSI values (0-1 range), NaN for insufficient data.

    Examples:
        >>> rsi_vals = np.array([30, 40, 50, 60, 70])
        >>> stoch = _compute_stochastic_rsi(rsi_vals, period=3)
        >>> stoch[-1]  # Most recent value
        1.0
    """
    result = np.full_like(rsi_values, np.nan)

    for i in range(period - 1, len(rsi_values)):
        window = rsi_values[i - period + 1 : i + 1]
        if np.any(np.isnan(window)):
            continue

        min_rsi = np.min(window)
        max_rsi = np.max(window)

        # Avoid division by zero
        if max_rsi - min_rsi == 0:
            result[i] = 0.5  # Neutral value when RSI is flat
        else:
            result[i] = (rsi_values[i] - min_rsi) / (max_rsi - min_rsi)

    return result


def ingest_candles(
    csv_path: Path,
    ema_fast: int = 20,
    ema_slow: int = 50,
    atr_period: int = 14,
    rsi_period: int = 14,
    stoch_rsi_period: int = 14,
    expected_timeframe_minutes: int = 5,
    allow_gaps: bool = False,
) -> Iterator[Candle]:
    """
    Load candles from CSV and yield Candle objects with computed indicators.

    Reads OHLCV data, computes technical indicators, validates timestamp
    continuity, and yields fully-enriched Candle objects.

    CSV Format:
        timestamp_utc, open, high, low, close, volume
        2025-01-01 00:00:00, 1.1000, 1.1010, 1.0990, 1.1005, 1000

    Args:
        csv_path: Path to CSV file with OHLCV data.
        ema_fast: Fast EMA period (default 20).
        ema_slow: Slow EMA period (default 50).
        atr_period: ATR period (default 14).
        rsi_period: RSI period (default 14).
        stoch_rsi_period: Stochastic RSI period (default 14).
        expected_timeframe_minutes: Expected candle interval in minutes (default 5).
        allow_gaps: If True, log gaps but don't raise errors (default False).

    Yields:
        Candle objects with computed indicators.

    Raises:
        DataIntegrityError: If CSV is malformed, has invalid OHLC, or timestamp gaps.
        FileNotFoundError: If csv_path does not exist.

    Examples:
        >>> from pathlib import Path
        >>> csv_path = Path("data/EURUSD_M5.csv")
        >>> for candle in ingest_candles(csv_path, ema_fast=20, ema_slow=50):
        ...     print(f"Close: {candle.close}, EMA20: {candle.ema20}")
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    logger.info(f"Starting ingestion from {csv_path}")

    # Read CSV
    try:
        df = pd.read_csv(
            csv_path,
            parse_dates=["timestamp_utc"],
            date_format="%Y-%m-%d %H:%M:%S",
        )
    except Exception as e:
        raise DataIntegrityError(
            f"Failed to parse CSV: {csv_path}",
            context={"error": str(e)},
        ) from e

    # Validate required columns
    required_cols = ["timestamp_utc", "open", "high", "low", "close", "volume"]
    missing_cols = set(required_cols) - set(df.columns)
    if missing_cols:
        raise DataIntegrityError(
            "Missing required columns",
            context={"missing": list(missing_cols), "file": str(csv_path)},
        )

    # Sort by timestamp
    df = df.sort_values("timestamp_utc").reset_index(drop=True)

    # Validate OHLC relationships
    invalid_ohlc = (df["high"] < df["low"]) | (df["high"] < df["close"]) | (df["low"] > df["close"])
    if invalid_ohlc.any():
        first_invalid_idx = invalid_ohlc.idxmax()
        raise DataIntegrityError(
            "Invalid OHLC relationship detected",
            context={
                "row": int(first_invalid_idx),
                "timestamp": str(df.loc[first_invalid_idx, "timestamp_utc"]),
                "high": float(df.loc[first_invalid_idx, "high"]),
                "low": float(df.loc[first_invalid_idx, "low"]),
            },
        )

    # Extract arrays for indicator computation
    close_prices = df["close"].to_numpy(dtype=np.float64)
    high_prices = df["high"].to_numpy(dtype=np.float64)
    low_prices = df["low"].to_numpy(dtype=np.float64)

    # Compute indicators (vectorized)
    ema20_values = ema(close_prices, ema_fast)
    ema50_values = ema(close_prices, ema_slow)
    atr_values = atr(high_prices, low_prices, close_prices, atr_period)
    rsi_values = rsi(close_prices, rsi_period)
    stoch_rsi_values = _compute_stochastic_rsi(rsi_values, stoch_rsi_period)

    # Validate timestamp continuity and yield candles
    expected_delta = timedelta(minutes=expected_timeframe_minutes)
    prev_timestamp: datetime | None = None

    for idx, row in df.iterrows():
        current_timestamp = row["timestamp_utc"]

        # Check for timestamp gaps (FR-019)
        if prev_timestamp is not None:
            actual_delta = current_timestamp - prev_timestamp
            if actual_delta > expected_delta:
                gap_minutes = actual_delta.total_seconds() / 60
                if allow_gaps:
                    logger.warning(
                        f"Timestamp gap detected (allowing): expected {expected_timeframe_minutes}m, "
                        f"actual {gap_minutes:.1f}m at {current_timestamp}"
                    )
                else:
                    raise DataIntegrityError(
                        "Timestamp gap detected",
                    context={
                        "expected_minutes": expected_timeframe_minutes,
                        "actual_minutes": actual_delta.total_seconds() / 60,
                        "previous_timestamp": str(prev_timestamp),
                        "current_timestamp": str(current_timestamp),
                    },
                )

        # Yield Candle object
        candle = Candle(
            timestamp_utc=current_timestamp,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
            ema20=float(ema20_values[idx]),
            ema50=float(ema50_values[idx]),
            atr=float(atr_values[idx]),
            rsi=float(rsi_values[idx]),
            stoch_rsi=float(stoch_rsi_values[idx]),
        )

        yield candle
        prev_timestamp = current_timestamp

    logger.info(f"Ingestion complete: {len(df)} candles processed from {csv_path}")
