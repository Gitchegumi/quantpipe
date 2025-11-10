"""Hash utilities for verifying dataset immutability.

This module provides utilities for computing deterministic hashes of DataFrames
to verify that core datasets remain unchanged during enrichment operations.
"""

import hashlib
from typing import List

import pandas as pd


def compute_dataframe_hash(df: pd.DataFrame, columns: List[str]) -> str:
    """Compute a deterministic hash of specified DataFrame columns.

    Args:
        df: The DataFrame to hash.
        columns: List of column names to include in the hash.

    Returns:
        str: Hexadecimal hash digest.

    Raises:
        ValueError: If any specified columns are missing from the DataFrame.
    """
    missing_columns = set(columns) - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing columns for hash: {missing_columns}")

    # Use to_csv for deterministic string representation
    # (more stable than to_string for large datasets)
    content = df[columns].to_csv(index=False)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def verify_immutability(
    df: pd.DataFrame, columns: List[str], expected_hash: str
) -> bool:
    """Verify that DataFrame columns match an expected hash.

    Args:
        df: The DataFrame to verify.
        columns: List of column names to check.
        expected_hash: The expected hash value.

    Returns:
        bool: True if hash matches, False otherwise.
    """
    current_hash = compute_dataframe_hash(df, columns)
    return current_hash == expected_hash
