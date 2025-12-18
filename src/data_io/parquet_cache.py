"""Parquet caching for CSV ingestion.

This module provides functionality to cache processed CSV data as Parquet files
to accelerate subsequent loads. It includes mechanisms for cache invalidation
based on source CSV modification times and content hashes.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Optional, Union

import pandas as pd
from polars import DataFrame as PolarsDataFrame
import polars as pl # Keep for pl.read_parquet, etc.


logger = logging.getLogger(__name__)

# Cache directory relative to project root
CACHE_DIR = Path(".parquet_cache")
CACHE_DIR.mkdir(exist_ok=True)


def _get_cache_path(csv_path: Path) -> Path:
    """Generate a unique cache path for a given CSV file."""
    # Use a hash of the absolute path to avoid name collisions and long paths
    path_hash = hashlib.sha256(str(csv_path.resolve()).encode()).hexdigest()
    return CACHE_DIR / f"{csv_path.stem}_{path_hash}.parquet"


def _get_csv_hash(csv_path: Path) -> str:
    """Compute SHA256 hash of a CSV file's content."""
    hasher = hashlib.sha256()
    with open(csv_path, "rb") as f:
        while chunk := f.read(8192):  # Read in 8KB chunks
            hasher.update(chunk)
    return hasher.hexdigest()


def _is_cache_valid(csv_path: Path, cache_path: Path) -> bool:
    """Check if the Parquet cache is valid (CSV not modified)."""
    if not cache_path.exists():
        return False

    try:
        # Read metadata from Parquet file
        # We store CSV hash and mtime in Parquet metadata
        # This requires pyarrow to be installed
        import pyarrow.parquet as pq

        metadata = pq.read_metadata(cache_path)
        file_metadata = metadata.metadata

        if file_metadata is None:
            logger.debug("Parquet metadata is empty for %s", cache_path)
            return False

        # Decode byte strings from metadata
        cached_csv_mtime = file_metadata.get(b"csv_mtime")
        cached_csv_hash = file_metadata.get(b"csv_hash")

        if cached_csv_mtime is None or cached_csv_hash is None:
            logger.debug("Missing csv_mtime or csv_hash in Parquet metadata for %s", cache_path)
            return False

        cached_csv_mtime = float(cached_csv_mtime.decode("utf-8"))
        cached_csv_hash = cached_csv_hash.decode("utf-8")

        # Compare with current CSV file
        current_csv_mtime = csv_path.stat().st_mtime
        current_csv_hash = _get_csv_hash(csv_path)

        if (
            abs(current_csv_mtime - cached_csv_mtime) < 0.001
            and current_csv_hash == cached_csv_hash
        ):
            logger.debug("Parquet cache for %s is valid.", csv_path)
            return True
        else:
            logger.debug(
                "Parquet cache for %s is invalid (mtime or hash mismatch).", csv_path
            )
            return False
    except Exception as e:  # pylint: disable=broad-except-caught
        logger.warning("Error validating Parquet cache for %s: %s", csv_path, e)
        return False


def load_with_cache(csv_path: Path, return_polars: bool = False) -> pd.DataFrame | PolarsDataFrame:
    """Load a CSV file, utilizing or creating a Parquet cache.

    Args:
        csv_path: Path to the input CSV file.
        return_polars: If True, return a Polars DataFrame.

    Returns:
        pd.DataFrame | PolarsDataFrame: Loaded DataFrame.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If the CSV file is empty or cannot be parsed.
        RuntimeError: If Parquet conversion or loading fails.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    cache_path = _get_cache_path(csv_path)

    if _is_cache_valid(csv_path, cache_path):
        logger.info("Loading from Parquet cache: %s", cache_path)
        try:
            if return_polars:
                return pl.read_parquet(cache_path)
            return pd.read_parquet(cache_path)
        except Exception as e:  # pylint: disable=broad-except-caught
            logger.warning("Failed to load Parquet cache, rebuilding: %s", e)
            # Fall through to rebuild cache
    else:
        logger.info("Parquet cache for %s not found or invalid, building...", csv_path)

    # Read CSV and save to Parquet cache
    try:
        if return_polars:
            df = pl.read_csv(csv_path)
        else:
            df = pd.read_csv(csv_path)

        if df.empty:
            raise ValueError(f"CSV file is empty: {csv_path}")

        # Store CSV mtime and hash in Parquet metadata
        csv_mtime = csv_path.stat().st_mtime
        csv_hash = _get_csv_hash(csv_path)

        # Convert to pyarrow table to write metadata
        import pyarrow as pa
        import pyarrow.parquet as pq

        if return_polars:
            table = df.to_arrow()
        else:
            table = pa.Table.from_pandas(df)

        metadata = table.schema.metadata
        if metadata is None:
            metadata = {}
        else:
            metadata = {k.decode("utf-8"): v.decode("utf-8") for k, v in metadata.items()}

        metadata["csv_mtime"] = str(csv_mtime)
        metadata["csv_hash"] = csv_hash

        # Encode metadata keys/values to bytes
        encoded_metadata = {k.encode("utf-8"): v.encode("utf-8") for k, v in metadata.items()}

        pq.write_table(table, cache_path, metadata_collector=[encoded_metadata])

        logger.info("Parquet cache built and saved to %s", cache_path)
        return df
    except Exception as e:  # pylint: disable=broad-except-caught
        raise RuntimeError(f"Failed to build Parquet cache for {csv_path}: {e}") from e


def clear_cache(csv_path: Optional[Path] = None) -> None:
    """Clear the Parquet cache.

    Args:
        csv_path: If provided, clear cache only for this specific CSV file.
                  If None, clear all Parquet caches.
    """
    if csv_path:
        cache_path = _get_cache_path(csv_path)
        if cache_path.exists():
            cache_path.unlink()
            logger.info("Cleared Parquet cache for %s", csv_path)
        else:
            logger.info("No Parquet cache found for %s", csv_path)
    else:
        for f in CACHE_DIR.glob("*.parquet"):
            f.unlink()
        logger.info("Cleared all Parquet caches in %s", CACHE_DIR)