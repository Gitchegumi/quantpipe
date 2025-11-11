"""Columnar array extraction utilities for NumPy conversions.

This module provides utilities for extracting columnar data from Polars DataFrames
and converting to NumPy arrays for efficient numerical processing.
"""

import logging
from typing import Optional

import numpy as np
import polars as pl


logger = logging.getLogger(__name__)


def extract_ohlc_arrays(
    df: pl.DataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Extract OHLC + timestamp arrays from Polars DataFrame.

    Args:
        df: Polars DataFrame containing OHLC data

    Returns:
        Tuple of (timestamps, open, high, low, close) as NumPy arrays

    Raises:
        ValueError: If required columns are missing
    """
    required_cols = ["timestamp_utc", "open", "high", "low", "close"]
    missing_cols = set(required_cols) - set(df.columns)

    if missing_cols:
        msg = "Missing required columns: %s"
        logger.error(msg, missing_cols)
        raise ValueError(msg % str(missing_cols))

    # Extract arrays (single pass, zero-copy where possible)
    timestamps = df["timestamp_utc"].to_numpy()
    open_prices = df["open"].to_numpy(dtype=np.float64)
    high_prices = df["high"].to_numpy(dtype=np.float64)
    low_prices = df["low"].to_numpy(dtype=np.float64)
    close_prices = df["close"].to_numpy(dtype=np.float64)

    logger.debug(
        "Extracted OHLC arrays: %d rows, dtype=%s",
        len(timestamps),
        open_prices.dtype,
    )

    return timestamps, open_prices, high_prices, low_prices, close_prices


def extract_indicator_arrays(
    df: pl.DataFrame, indicator_names: list[str]
) -> dict[str, np.ndarray]:
    """Extract indicator columns as NumPy arrays.

    Args:
        df: Polars DataFrame containing indicator columns
        indicator_names: List of indicator column names to extract

    Returns:
        Dictionary mapping indicator names to NumPy arrays

    Raises:
        ValueError: If any indicator column is missing
    """
    missing_cols = set(indicator_names) - set(df.columns)

    if missing_cols:
        msg = "Missing indicator columns: %s"
        logger.error(msg, missing_cols)
        raise ValueError(msg % str(missing_cols))

    # Extract all indicator arrays
    indicator_arrays = {}
    for name in indicator_names:
        indicator_arrays[name] = df[name].to_numpy(dtype=np.float64)

    logger.debug(
        "Extracted %d indicator arrays with %d rows each",
        len(indicator_names),
        len(df),
    )

    return indicator_arrays


def extract_column_array(
    df: pl.DataFrame, column_name: str, dtype: Optional[np.dtype] = None
) -> np.ndarray:
    """Extract a single column as NumPy array with optional dtype conversion.

    Args:
        df: Polars DataFrame
        column_name: Name of column to extract
        dtype: Optional NumPy dtype for conversion (default: infer from data)

    Returns:
        NumPy array of column values

    Raises:
        ValueError: If column does not exist
    """
    if column_name not in df.columns:
        msg = "Column '%s' not found in DataFrame"
        logger.error(msg, column_name)
        raise ValueError(msg % column_name)

    # Extract array with optional dtype conversion
    if dtype is not None:
        arr = df[column_name].to_numpy(dtype=dtype)
    else:
        arr = df[column_name].to_numpy()

    logger.debug(
        "Extracted column '%s': %d values, dtype=%s",
        column_name,
        len(arr),
        arr.dtype,
    )

    return arr


def create_price_lookup_arrays(
    timestamps: np.ndarray,
    open_prices: np.ndarray,
    high_prices: np.ndarray,
    low_prices: np.ndarray,
    close_prices: np.ndarray,
) -> dict:
    """Create optimized lookup structures for price data.

    Args:
        timestamps: Array of timestamps
        open_prices: Array of open prices
        high_prices: Array of high prices
        low_prices: Array of low prices
        close_prices: Array of close prices

    Returns:
        Dictionary containing:
            - ts_to_index: Dictionary mapping timestamps to indices (O(1) lookup)
            - price_arrays: Dictionary of price arrays by name
            - index_range: Tuple of (start_index, end_index)
    """
    # Create timestamp-to-index lookup (O(1) access)
    ts_to_index = {ts: idx for idx, ts in enumerate(timestamps)}

    # Bundle price arrays for convenient access
    price_arrays = {
        "open": open_prices,
        "high": high_prices,
        "low": low_prices,
        "close": close_prices,
    }

    # Store index range for bounds checking
    index_range = (0, len(timestamps) - 1)

    logger.debug(
        "Created price lookup structures: %d timestamps, index range=[%d, %d]",
        len(ts_to_index),
        index_range[0],
        index_range[1],
    )

    return {
        "ts_to_index": ts_to_index,
        "price_arrays": price_arrays,
        "index_range": index_range,
    }


def validate_array_lengths(*arrays: np.ndarray) -> bool:
    """Validate that all arrays have the same length.

    Args:
        *arrays: Variable number of NumPy arrays to validate

    Returns:
        True if all arrays have same length

    Raises:
        ValueError: If arrays have different lengths
    """
    if len(arrays) == 0:
        return True

    first_len = len(arrays[0])

    for i, arr in enumerate(arrays[1:], start=1):
        if len(arr) != first_len:
            msg = "Array length mismatch: array[0]=%d, array[%d]=%d"
            logger.error(msg, first_len, i, len(arr))
            raise ValueError(msg % (first_len, i, len(arr)))

    logger.debug(
        "Array length validation passed: %d arrays of length %d", len(arrays), first_len
    )

    return True
