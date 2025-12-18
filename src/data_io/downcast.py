"""Numeric downcast utilities with precision safety checks.

This module provides utilities for downcasting numeric columns to save memory
while ensuring precision requirements are met.
"""

import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def check_precision_safe(
    series: pd.Series, target_dtype: str, max_error: float = 1e-6
) -> bool:
    """Check if downcasting is safe without losing precision.

    Args:
        series: Series to check.
        target_dtype: Target dtype (e.g., 'float32').
        max_error: Maximum allowed relative error.

    Returns:
        bool: True if downcast is safe, False otherwise.
    """
    if series.isna().all():
        return True

    # Cast to target dtype and back
    downcasted = series.astype(target_dtype).astype(series.dtype)

    # Compute relative error
    non_zero = series != 0
    if non_zero.sum() == 0:
        return True

    relative_error = np.abs(
        (series[non_zero] - downcasted[non_zero]) / series[non_zero]
    )
    max_rel_error = relative_error.max()

    is_safe = max_rel_error < max_error

    if not is_safe:
        logger.warning(
            "Downcast unsafe for column: max relative error %.2e exceeds %.2e",
            max_rel_error,
            max_error,
        )

    return is_safe


def downcast_numeric_columns(
    df: pd.DataFrame, skip_columns: list[str] = None
) -> tuple[pd.DataFrame, list[str]]:
    """Downcast numeric columns to reduce memory usage.

    Converts float64 to float32 where precision is safe.

    Args:
        df: DataFrame with numeric columns.
        skip_columns: Optional list of columns to skip.

    Returns:
        tuple: (downcasted_df, list of downcasted column names)
    """
    if skip_columns is None:
        skip_columns = []

    downcasted_columns = []

    for col in df.select_dtypes(include=["float64"]).columns:
        if col in skip_columns:
            continue

        if check_precision_safe(df[col], "float32"):
            df[col] = df[col].astype("float32")
            downcasted_columns.append(col)
            logger.debug("Downcasted column '%s' to float32", col)

    if downcasted_columns:
        logger.info("Downcasted %d columns to float32", len(downcasted_columns))

    return df, downcasted_columns


def downcast_float_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Downcast float64 columns to float32 where safe (convenience wrapper).

    Args:
        df: DataFrame with numeric columns.

    Returns:
        pd.DataFrame: DataFrame with downcasted columns.
    """
    result, _ = downcast_numeric_columns(df)
    return result



# Alias for backward compatibility
try_downcast_float_columns = downcast_float_columns
