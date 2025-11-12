"""Parquet caching for optimized data loading.

This module provides CSV→Parquet conversion and caching to eliminate
repeated CSV parsing overhead. Converted Parquet files are validated
via checksums and automatically invalidated when source changes.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import polars as pl


logger = logging.getLogger(__name__)


@dataclass
class CacheMetadata:
    """Metadata for cached Parquet file.

    Attributes:
        source_path: Original CSV file path
        source_checksum: SHA-256 checksum of source CSV
        parquet_path: Path to cached Parquet file
        row_count: Number of rows in cached file
        created_at: ISO timestamp of cache creation
    """

    source_path: str
    source_checksum: str
    parquet_path: str
    row_count: int
    created_at: str


def calculate_file_checksum(file_path: Path) -> str:
    """Calculate SHA-256 checksum of file.

    Args:
        file_path: Path to file

    Returns:
        Hex-encoded SHA-256 checksum
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_cache_path(csv_path: Path) -> Path:
    """Get Parquet cache path for CSV file.

    Args:
        csv_path: Path to source CSV file

    Returns:
        Path to cached Parquet file (same directory, .parquet extension)
    """
    return csv_path.with_suffix(".parquet")


def get_metadata_path(csv_path: Path) -> Path:
    """Get cache metadata path for CSV file.

    Args:
        csv_path: Path to source CSV file

    Returns:
        Path to cache metadata JSON file
    """
    return csv_path.with_suffix(".parquet.meta")


def is_cache_valid(csv_path: Path) -> bool:
    """Check if Parquet cache is valid for CSV file.

    Args:
        csv_path: Path to source CSV file

    Returns:
        True if cache exists and checksums match
    """
    parquet_path = get_cache_path(csv_path)
    meta_path = get_metadata_path(csv_path)

    if not parquet_path.exists() or not meta_path.exists():
        logger.debug("Cache miss: files not found for %s", csv_path)
        return False

    try:
        # Load metadata
        with open(meta_path, encoding="utf-8") as f:
            meta_dict = json.load(f)
        metadata = CacheMetadata(**meta_dict)

        # Calculate current CSV checksum
        current_checksum = calculate_file_checksum(csv_path)

        if metadata.source_checksum != current_checksum:
            logger.info(
                "Cache invalid: checksum mismatch for %s (expected=%s, actual=%s)",
                csv_path,
                metadata.source_checksum[:8],
                current_checksum[:8],
            )
            return False

        logger.debug("Cache valid for %s", csv_path)
        return True

    except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
        logger.warning("Cache metadata corrupt for %s: %s", csv_path, e)
        return False


def convert_csv_to_parquet(
    csv_path: Path, compression: str = "zstd"
) -> tuple[Path, CacheMetadata]:
    """Convert CSV to Parquet with caching metadata.

    Args:
        csv_path: Path to source CSV file
        compression: Parquet compression codec (default: zstd)

    Returns:
        Tuple of (parquet_path, metadata)
    """
    from datetime import UTC, datetime

    logger.info("Converting CSV to Parquet: %s", csv_path)

    # Calculate source checksum
    source_checksum = calculate_file_checksum(csv_path)

    # Read CSV with Polars (faster than pandas)
    df = pl.read_csv(csv_path)
    row_count = len(df)

    # Write Parquet with compression
    parquet_path = get_cache_path(csv_path)
    df.write_parquet(parquet_path, compression=compression)

    logger.info(
        "Converted %d rows to Parquet (%s): %s",
        row_count,
        compression,
        parquet_path,
    )

    # Create metadata
    metadata = CacheMetadata(
        source_path=str(csv_path),
        source_checksum=source_checksum,
        parquet_path=str(parquet_path),
        row_count=row_count,
        created_at=datetime.now(UTC).isoformat(),
    )

    # Write metadata
    meta_path = get_metadata_path(csv_path)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "source_path": metadata.source_path,
                "source_checksum": metadata.source_checksum,
                "parquet_path": metadata.parquet_path,
                "row_count": metadata.row_count,
                "created_at": metadata.created_at,
            },
            f,
            indent=2,
        )

    logger.debug("Wrote cache metadata: %s", meta_path)
    return parquet_path, metadata


def load_from_cache(csv_path: Path) -> Optional[pl.DataFrame]:
    """Load DataFrame from Parquet cache if valid.

    Args:
        csv_path: Path to source CSV file

    Returns:
        DataFrame if cache valid, None otherwise
    """
    if not is_cache_valid(csv_path):
        return None

    parquet_path = get_cache_path(csv_path)
    logger.info("Loading from Parquet cache: %s", parquet_path)

    try:
        df = pl.read_parquet(parquet_path)
        logger.info("Loaded %d rows from cache", len(df))
        return df
    except Exception as e:
        logger.warning("Failed to load cache %s: %s", parquet_path, e)
        return None


def load_with_cache(csv_path: Path) -> pl.DataFrame:
    """Load DataFrame with automatic Parquet caching.

    Checks cache validity, loads from cache if valid, otherwise
    converts CSV to Parquet and caches for future use.

    Args:
        csv_path: Path to source CSV file

    Returns:
        Polars DataFrame
    """
    csv_path = Path(csv_path)

    # Try loading from cache
    df = load_from_cache(csv_path)
    if df is not None:
        return df

    # Cache miss or invalid - convert and cache
    logger.info("Cache miss - converting CSV to Parquet")
    parquet_path, _ = convert_csv_to_parquet(csv_path)  # metadata not needed here

    # Load from newly created Parquet
    df = pl.read_parquet(parquet_path)
    logger.info("Cached and loaded %d rows", len(df))
    return df


def invalidate_cache(csv_path: Path) -> None:
    """Invalidate Parquet cache for CSV file.

    Removes cached Parquet file and metadata.

    Args:
        csv_path: Path to source CSV file
    """
    parquet_path = get_cache_path(csv_path)
    meta_path = get_metadata_path(csv_path)

    removed = []
    if parquet_path.exists():
        parquet_path.unlink()
        removed.append(str(parquet_path))

    if meta_path.exists():
        meta_path.unlink()
        removed.append(str(meta_path))

    if removed:
        logger.info("Invalidated cache: %s", ", ".join(removed))
    else:
        logger.debug("No cache to invalidate for %s", csv_path)
