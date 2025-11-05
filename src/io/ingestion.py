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

# pylint: disable=unused-variable

import logging
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

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
    fill_gaps: bool = True,
    show_progress: bool = False,
) -> Iterator[Candle]:
    """
    Load candles from CSV and yield Candle objects with computed indicators.

    Reads OHLCV data, computes technical indicators, validates timestamp
    continuity, and yields fully-enriched Candle objects. When fill_gaps=True,
    creates synthetic candles to fill timestamp gaps by carrying forward the
    previous close price.

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
        fill_gaps: If True, create synthetic candles to fill gaps (default True).
        show_progress: If True, display progress bar during ingestion (default False).

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

    logger.info("Starting ingestion from %s", csv_path)

    # Read CSV
    try:
        df = pd.read_csv(csv_path)

        # Accept both 'timestamp' and 'timestamp_utc' column names
        timestamp_col = None
        if "timestamp_utc" in df.columns:
            timestamp_col = "timestamp_utc"
        elif "timestamp" in df.columns:
            timestamp_col = "timestamp"
            # Rename to timestamp_utc for internal consistency
            df = df.rename(columns={"timestamp": "timestamp_utc"})
        else:
            raise KeyError(
                "No timestamp column found (expected 'timestamp' or 'timestamp_utc')"
            )

        # Convert timestamp column to datetime if it's not already
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp_utc"]):
            df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
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
    invalid_ohlc = (
        (df["high"] < df["low"])
        | (df["high"] < df["close"])
        | (df["low"] > df["close"])
    )
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
    prev_candle: Candle | None = None
    total_candles = len(df)
    gap_count = 0
    filled_count = 0

    # Create progress bar if requested
    if show_progress:
        gap_label = "filled" if fill_gaps else "gaps"
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn(f"• {{task.fields[gaps]}} {gap_label}"),
        )
        progress.start()
        task = progress.add_task(
            f"Ingesting {total_candles:,} candles",
            total=total_candles,
            gaps=0,
        )

    for idx, row in df.iterrows():
        current_timestamp = row["timestamp_utc"]

        # Check for timestamp gaps (FR-019)
        if prev_timestamp is not None and prev_candle is not None:
            actual_delta = current_timestamp - prev_timestamp
            if actual_delta > expected_delta:
                gap_minutes = actual_delta.total_seconds() / 60
                gap_count += 1

                if fill_gaps:
                    # Fill the gap with synthetic candles
                    num_missing = int(
                        (actual_delta - expected_delta).total_seconds()
                        / 60
                        / expected_timeframe_minutes
                    )
                    filled_count += num_missing

                    # Create synthetic candles carrying forward the previous close
                    fill_timestamp = prev_timestamp
                    for _ in range(num_missing):
                        fill_timestamp = fill_timestamp + expected_delta

                        # Create synthetic candle with previous close price
                        # All prices = previous close, volume = 0, indicators = NaN
                        gap_candle = Candle(
                            timestamp_utc=fill_timestamp,
                            open=prev_candle.close,
                            high=prev_candle.close,
                            low=prev_candle.close,
                            close=prev_candle.close,
                            volume=0.0,
                            ema20=np.nan,
                            ema50=np.nan,
                            atr=np.nan,
                            rsi=np.nan,
                            stoch_rsi=None,
                            is_gap=True,
                        )

                        if show_progress:
                            progress.update(task, gaps=filled_count)

                        yield gap_candle

                    logger.debug(
                        "Filled %d candles for gap: expected %dm, actual %.1fm at %s",
                        num_missing,
                        expected_timeframe_minutes,
                        gap_minutes,
                        current_timestamp,
                    )
                elif allow_gaps:
                    # Gaps are expected in forex data - log at DEBUG level (silent)
                    logger.debug(
                        "Timestamp gap detected (allowing): \
expected %dm, actual %.1fm at %s",
                        expected_timeframe_minutes,
                        gap_minutes,
                        current_timestamp,
                    )
                else:
                    if show_progress:
                        progress.stop()
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
            is_gap=False,
        )

        if show_progress:
            progress.update(
                task, advance=1, gaps=filled_count if fill_gaps else gap_count
            )

        yield candle
        prev_timestamp = current_timestamp
        prev_candle = candle

    if show_progress:
        progress.stop()

    if fill_gaps:
        logger.info(
            "Ingestion complete: %d candles processed, %d gaps filled",
            total_candles,
            filled_count,
        )
    else:
        logger.info(
            "Ingestion complete: %d candles processed, %d gaps detected",
            total_candles,
            gap_count,
        )
