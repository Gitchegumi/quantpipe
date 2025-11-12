"""CSV to Parquet conversion utilities for optimized data ingestion.

This module provides functionality to convert CSV market data files to Parquet format
with compression and checksum validation for improved I/O performance and integrity.
"""

import hashlib
import logging
from pathlib import Path

import polars as pl


logger = logging.getLogger(__name__)

# Required columns for OHLCV data
REQUIRED_COLUMNS = ["timestamp_utc", "open", "high", "low", "close"]


def convert_csv_to_parquet(
    csv_path: str,
    parquet_path: str,
    compression: str = "zstd",
    compression_level: int = 3,
) -> dict:
    """Convert CSV file to Parquet format with compression and checksum.

    Args:
        csv_path: Path to input CSV file
        parquet_path: Path to output Parquet file
        compression: Compression algorithm ('zstd', 'snappy', 'gzip', or 'none')
        compression_level: Compression level (1-22 for zstd, lower is faster)

    Returns:
        Dictionary containing:
            - parquet_path: Output file path
            - dataset_sha256: SHA-256 checksum of Parquet file
            - candle_count: Number of rows converted
            - schema_fingerprint: Hash of schema structure

    Raises:
        FileNotFoundError: If CSV file does not exist
        ValueError: If CSV format is invalid or required columns missing
    """
    logger.info("Converting CSV to Parquet: %s -> %s", csv_path, parquet_path)

    # Verify CSV file exists
    csv_file = Path(csv_path)
    if not csv_file.exists():
        msg = "CSV file not found: %s"
        logger.error(msg, csv_path)
        raise FileNotFoundError(msg % csv_path)

    # Read CSV using Polars (lazy for efficiency)
    try:
        df = pl.read_csv(
            csv_path,
            try_parse_dates=True,
            dtypes={"timestamp_utc": pl.Datetime},
        )
    except Exception as e:
        msg = "Failed to read CSV file: %s"
        logger.error(msg, str(e))
        raise ValueError(msg % str(e)) from e

    # Validate required columns
    missing_cols = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_cols:
        msg = "Missing required columns: %s"
        logger.error(msg, missing_cols)
        raise ValueError(msg % missing_cols)

    # Ensure output directory exists
    parquet_file = Path(parquet_path)
    parquet_file.parent.mkdir(parents=True, exist_ok=True)

    # Write to Parquet with compression
    df.write_parquet(
        parquet_path,
        compression=compression,
        compression_level=compression_level,
        statistics=True,
        use_pyarrow=True,
    )

    logger.info("Successfully wrote Parquet file: %s", parquet_path)

    # Compute schema fingerprint
    schema_fingerprint = compute_schema_fingerprint(df)

    # Compute file checksum
    dataset_sha256 = compute_file_checksum(parquet_path)

    # Get row count
    candle_count = len(df)

    logger.info(
        "Conversion complete: %d rows, checksum=%s",
        candle_count,
        dataset_sha256[:8],
    )

    return {
        "parquet_path": parquet_path,
        "dataset_sha256": dataset_sha256,
        "candle_count": candle_count,
        "schema_fingerprint": schema_fingerprint,
    }


def compute_schema_fingerprint(df: pl.DataFrame) -> str:
    """Compute deterministic fingerprint of DataFrame schema.

    Args:
        df: Polars DataFrame

    Returns:
        MD5 hash of schema structure (column names and types)
    """
    # Build schema string: "col1:type1,col2:type2,..."
    schema_parts = [f"{name}:{dtype}" for name, dtype in df.schema.items()]
    schema_str = ",".join(schema_parts)

    # Compute MD5 hash
    md5_hash = hashlib.md5(schema_str.encode("utf-8"), usedforsecurity=False)
    return md5_hash.hexdigest()


def compute_file_checksum(file_path: str) -> str:
    """Compute SHA-256 checksum of file.

    Args:
        file_path: Path to file

    Returns:
        SHA-256 checksum as hexadecimal string
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
