"""Disk caching for resampled OHLCV data.

This module provides caching functionality to avoid recomputing resampled
data on repeated backtest runs with the same parameters.

Cache Location (per spec clarification):
- .time_cache/ directory in project root

Cache Key Components (FR-011):
- instrument: Trading pair (e.g., 'EURUSD')
- timeframe: Target timeframe in minutes (e.g., 15)
- date_range: Start and end dates of the data
- data_version: Hash of source data for invalidation

Cache File Format:
- Parquet files for fast I/O and good compression
- Filename: {instrument}_{tf}m_{start}_{end}_{hash8}.parquet

Telemetry (FR-014):
- Cache hits/misses logged at INFO level
- Resample time recorded for performance monitoring
"""

import hashlib
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl


if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Cache directory relative to project root
CACHE_DIR = Path(".time_cache")


def get_cache_path(
    instrument: str,
    tf_minutes: int,
    start_date: str,
    end_date: str,
    data_hash: str,
) -> Path:
    """Generate cache file path for resampled data.

    Args:
        instrument: Trading pair (e.g., 'EURUSD').
        tf_minutes: Target timeframe in minutes.
        start_date: Start date string (YYYYMMDD format).
        end_date: End date string (YYYYMMDD format).
        data_hash: First 8 chars of source data hash.

    Returns:
        Path to cache file.
    """
    filename = f"{instrument.upper()}_{tf_minutes}m_{start_date}_{end_date}_{data_hash[:8]}.parquet"
    return CACHE_DIR / filename


def compute_data_hash(df: pl.DataFrame, timestamp_col: str = "timestamp_utc") -> str:
    """Compute a hash of the source data for cache invalidation.

    Uses first/last timestamps and row count for fast hashing.

    Args:
        df: Source DataFrame.
        timestamp_col: Name of timestamp column.

    Returns:
        SHA256 hash (first 16 chars).
    """
    if len(df) == 0:
        return "empty_data_hash"

    first_ts = str(df[timestamp_col].head(1).item())
    last_ts = str(df[timestamp_col].tail(1).item())
    row_count = len(df)

    hash_input = f"{first_ts}_{last_ts}_{row_count}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


def load_cached_resample(cache_path: Path) -> pl.DataFrame | None:
    """Load resampled data from cache.

    Args:
        cache_path: Path to cache file.

    Returns:
        DataFrame if cache hit, None if cache miss.
    """
    if not cache_path.exists():
        return None

    try:
        df = pl.read_parquet(cache_path)
        logger.info("Resample cache hit: %s", cache_path.name)
        return df
    except Exception as exc:
        logger.warning("Failed to load cache file %s: %s", cache_path, exc)
        return None


def save_cached_resample(df: pl.DataFrame, cache_path: Path) -> None:
    """Save resampled data to cache.

    Args:
        df: Resampled DataFrame.
        cache_path: Path to save cache file.
    """
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(cache_path)
        logger.info("Resample cache saved: %s", cache_path.name)
    except Exception as exc:
        logger.warning("Failed to save cache file %s: %s", cache_path, exc)


def resample_with_cache(
    df: pl.DataFrame,
    instrument: str,
    tf_minutes: int,
    resample_fn: Callable[[pl.DataFrame, int], pl.DataFrame],
    timestamp_col: str = "timestamp_utc",
) -> pl.DataFrame:
    """Resample data with disk caching.

    Checks cache first, computes and saves if cache miss.

    Args:
        df: Source 1-minute OHLCV DataFrame.
        instrument: Trading pair (e.g., 'EURUSD').
        tf_minutes: Target timeframe in minutes.
        resample_fn: Resampling function to call on cache miss.
        timestamp_col: Name of timestamp column.

    Returns:
        Resampled DataFrame.
    """
    # If 1m, no caching needed
    if tf_minutes == 1:
        return resample_fn(df, tf_minutes)

    # Compute cache key components
    if len(df) == 0:
        return resample_fn(df, tf_minutes)

    first_ts = df[timestamp_col].head(1).item()
    last_ts = df[timestamp_col].tail(1).item()

    start_date = (
        first_ts.strftime("%Y%m%d")
        if hasattr(first_ts, "strftime")
        else str(first_ts)[:10].replace("-", "")
    )
    end_date = (
        last_ts.strftime("%Y%m%d")
        if hasattr(last_ts, "strftime")
        else str(last_ts)[:10].replace("-", "")
    )
    data_hash = compute_data_hash(df, timestamp_col)

    cache_path = get_cache_path(instrument, tf_minutes, start_date, end_date, data_hash)

    # Try cache
    cached_df = load_cached_resample(cache_path)
    if cached_df is not None:
        return cached_df

    # Cache miss - resample and save
    logger.info(
        "Resample cache miss: computing %dm resample for %s", tf_minutes, instrument
    )
    start_time = time.perf_counter()

    resampled_df = resample_fn(df, tf_minutes)

    elapsed = time.perf_counter() - start_time
    logger.info("Resample time: %.2fs (%d bars)", elapsed, len(resampled_df))

    # Save to cache
    save_cached_resample(resampled_df, cache_path)

    return resampled_df
