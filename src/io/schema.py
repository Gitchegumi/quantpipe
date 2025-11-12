"""Schema enforcement and column restriction utilities.

This module provides utilities for enforcing the core OHLCV schema
and restricting output to only required columns.
"""

import logging

import pandas as pd

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


def validate_required_columns(df: pd.DataFrame) -> None:
    """Validate that all required columns are present.

    Args:
        df: DataFrame to validate.

    Raises:
        ValueError: If any required columns are missing.
    """
    missing_columns = set(REQUIRED_INPUT_COLUMNS) - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(sorted(missing_columns))}"
        )

    logger.debug("Required columns validation passed")


def restrict_to_core_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Restrict DataFrame to core schema columns only.

    Args:
        df: DataFrame to restrict.

    Returns:
        pd.DataFrame: DataFrame with only core columns.

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
    restricted_df = df[CORE_COLUMNS].copy()

    logger.debug(
        "Restricted to core schema: %d columns -> %d columns",
        len(df.columns),
        len(CORE_COLUMNS),
    )

    return restricted_df
