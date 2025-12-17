"""Parquet data loading utilities using Polars LazyFrame.

This module provides optimized data loading functionality using Polars LazyFrame
for efficient memory usage and query optimization through lazy evaluation.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

import polars as pl


logger = logging.getLogger(__name__)


def load_parquet_lazy(
    parquet_path: str,
    columns: Optional[list[str]] = None,
    predicate: Optional[pl.Expr] = None,
) -> pl.LazyFrame:
    """Load Parquet file as Polars LazyFrame with optional column selection.

    Uses lazy evaluation to enable query optimization and predicate pushdown.

    Args:
        parquet_path: Path to Parquet file
        columns: Optional list of columns to load (projection pushdown)
        predicate: Optional filter expression (predicate pushdown)

    Returns:
        Polars LazyFrame for deferred execution

    Raises:
        FileNotFoundError: If Parquet file does not exist
        ValueError: If specified columns do not exist in schema
    """
    logger.info("Loading Parquet file (lazy): %s", parquet_path)

    # Verify file exists
    parquet_file = Path(parquet_path)
    if not parquet_file.exists():
        msg = "Parquet file not found: %s"
        logger.error(msg, parquet_path)
        raise FileNotFoundError(msg % parquet_path)

    # Start with scan (lazy operation)
    lf = pl.scan_parquet(parquet_path)

    # Apply column selection (projection pushdown)
    if columns is not None:
        try:
            lf = lf.select(columns)
        except Exception as e:
            msg = "Invalid columns specified: %s"
            logger.error(msg, str(e))
            raise ValueError(msg % str(e)) from e

    # Apply predicate filter (predicate pushdown)
    if predicate is not None:
        lf = lf.filter(predicate)

    logger.debug(
        "LazyFrame created with %d column(s) and predicate=%s",
        len(columns) if columns else 0,
        predicate is not None,
    )

    return lf


def load_parquet_eager(
    parquet_path: str, columns: Optional[list[str]] = None
) -> pl.DataFrame:
    """Load Parquet file as Polars DataFrame (eager evaluation).

    Use for small datasets or when immediate materialization is required.

    Args:
        parquet_path: Path to Parquet file
        columns: Optional list of columns to load

    Returns:
        Polars DataFrame

    Raises:
        FileNotFoundError: If Parquet file does not exist
        ValueError: If specified columns do not exist in schema
    """
    logger.info("Loading Parquet file (eager): %s", parquet_path)

    # Verify file exists
    parquet_file = Path(parquet_path)
    if not parquet_file.exists():
        msg = "Parquet file not found: %s"
        logger.error(msg, parquet_path)
        raise FileNotFoundError(msg % parquet_path)

    # Read Parquet file directly (eager operation)
    try:
        df = pl.read_parquet(parquet_path, columns=columns)
    except Exception as e:
        msg = "Failed to read Parquet file: %s"
        logger.error(msg, str(e))
        raise ValueError(msg % str(e)) from e

    logger.info(
        "Loaded DataFrame with %d rows and %d columns", len(df), len(df.columns)
    )

    return df


def get_schema_fingerprint(parquet_path: str) -> str:
    """Extract schema fingerprint from Parquet file metadata.

    Args:
        parquet_path: Path to Parquet file

    Returns:
        Schema fingerprint string (MD5 hash of column names and types)

    Raises:
        FileNotFoundError: If Parquet file does not exist
    """
    # Verify file exists
    parquet_file = Path(parquet_path)
    if not parquet_file.exists():
        msg = "Parquet file not found: %s"
        logger.error(msg, parquet_path)
        raise FileNotFoundError(msg % parquet_path)

    # Read schema without loading data (very fast)
    lf = pl.scan_parquet(parquet_path)
    schema = lf.collect_schema()

    # Build schema string: "col1:type1,col2:type2,..."
    schema_parts = [f"{name}:{dtype}" for name, dtype in schema.items()]
    schema_str = ",".join(schema_parts)

    # Compute MD5 hash
    md5_hash = hashlib.md5(schema_str.encode("utf-8"), usedforsecurity=False)
    fingerprint = md5_hash.hexdigest()

    logger.debug("Schema fingerprint for %s: %s", parquet_path, fingerprint[:8])

    return fingerprint
