"""Schema enforcement and column restriction utilities.

This module provides utilities for enforcing the core OHLCV schema
and restricting output to only required columns.
"""

import logging
from typing import Union

import pandas as pd
from polars import DataFrame as PolarsDataFrame

logger = logging.getLogger(__name__)

# Core schema columns (FR-001)
CORE_COLUMNS = [
    "timestamp_utc",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "is_gap",
]

# Required input columns (before gap filling adds is_gap)
REQUIRED_INPUT_COLUMNS = [
    "timestamp_utc",
    "open",
    "high",
    "low",
    "close",
    "volume",
]


def validate_required_columns(df: Union[pd.DataFrame, PolarsDataFrame]) -> None:
    """Validate that all required columns are present.

    Args:
        df: DataFrame to validate (Pandas or Polars).

    Raises:
        ValueError: If any required columns are missing.
    """
    if isinstance(df, PolarsDataFrame):
        missing_columns = set(REQUIRED_INPUT_COLUMNS) - set(df.columns)
    else:
        missing_columns = set(REQUIRED_INPUT_COLUMNS) - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(sorted(missing_columns))}"
        )

    logger.debug("Required columns validation passed")


def restrict_to_core_schema(df: Union[pd.DataFrame, PolarsDataFrame], is_polars: bool = False) -> Union[pd.DataFrame, PolarsDataFrame]:
    """Restrict DataFrame to core schema columns only.

    Args:
        df: DataFrame to restrict (Pandas or Polars).
        is_polars: If True, df is a Polars DataFrame.

    Returns:
        pd.DataFrame | pl.DataFrame: DataFrame with only core columns.

    Raises:
        ValueError: If any core columns are missing.
    """
    missing_columns = set(CORE_COLUMNS) - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing core columns for restriction: "
            f"{', '.join(sorted(missing_columns))}"
        )

    # Select only core columns in the specified order
    if is_polars:
        restricted_df = df.select(CORE_COLUMNS)
    else:
        restricted_df = df[CORE_COLUMNS].copy()

    logger.debug(
        "Restricted to core schema: %d columns -> %d columns",
        len(df.columns),
        len(CORE_COLUMNS),
    )

    return restricted_df
