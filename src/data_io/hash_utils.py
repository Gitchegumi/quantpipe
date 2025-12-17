"""Hash utilities for verifying dataset immutability.

This module provides utilities for computing deterministic hashes of DataFrames
to verify that core datasets remain unchanged during enrichment operations.
"""
from __future__ import annotations

import hashlib
from typing import List, Union

import pandas as pd
from polars import DataFrame as PolarsDataFrame


def compute_dataframe_hash(df: pd.DataFrame | PolarsDataFrame, columns: List[str], is_polars: bool = False) -> str:
    """Compute a deterministic hash of specified DataFrame columns.

    Args:
        df: The DataFrame to hash (Pandas or Polars).
        columns: List of column names to include in the hash.
        is_polars: If True, df is a Polars DataFrame.

    Returns:
        str: Hexadecimal hash digest.

    Raises:
        ValueError: If any specified columns are missing from the DataFrame.
    """
    if is_polars:
        missing_columns = set(columns) - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing columns for hash: {missing_columns}")
        content = df.select(columns).write_csv(separator=',').encode("utf-8")
    else:
        missing_columns = set(columns) - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing columns for hash: {missing_columns}")
        content = df[columns].to_csv(index=False).encode("utf-8")

    return hashlib.sha256(content).hexdigest()


def verify_immutability(
    df: pd.DataFrame | PolarsDataFrame, columns: List[str], expected_hash: str, is_polars: bool = False
) -> bool:
    """Verify that DataFrame columns match an expected hash.

    Args:
        df: The DataFrame to verify (Pandas or Polars).
        columns: List of column names to check.
        expected_hash: The expected hash value.
        is_polars: If True, df is a Polars DataFrame.

    Returns:
        bool: True if hash matches, False otherwise.
    """
    current_hash = compute_dataframe_hash(df, columns, is_polars)
    return current_hash == expected_hash
