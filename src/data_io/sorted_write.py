"""Sorted write enforcement for QuantPipe parquet partitions.

All parquet writes MUST use sorted columns (symbol, timestamp, strategy_id)
to enable zone map and bloom filter acceleration in DuckDB.

Sort order: (symbol ASC, timestamp ASC, strategy_id ASC)
"""

import logging
from typing import Optional, Sequence

import polars as pl

logger = logging.getLogger(__name__)

# Canonical sort key order
SORT_COLUMNS = ["symbol", "timestamp", "strategy_id"]
# Fallback sort columns when strategy_id not present
SORT_COLUMNS_FALLBACK = ["symbol", "timestamp"]
# Minimum columns required (must have at least timestamp)
REQUIRED_SORT_COLUMN = "timestamp"


class SortOrderViolationError(ValueError):
    """Raised when data is written out of sort order."""

    pass


def _resolve_sort_columns(df: pl.DataFrame, sort_cols: Optional[Sequence[str]]) -> list[str]:
    """Resolve which sort columns to use based on DataFrame schema.

    Args:
        df: DataFrame to inspect.
        sort_cols: Override sort columns, or None to auto-detect.

    Returns:
        List of column names to sort by.

    Raises:
        ValueError: If required column 'timestamp' is missing.
    """
    if sort_cols is not None:
        cols = list(sort_cols)
        missing = set(cols) - set(df.columns)
        if missing:
            raise ValueError(f"Override sort columns not in DataFrame: {missing}")
        return cols

    # Canonical: all three present
    if all(c in df.columns for c in SORT_COLUMNS):
        return SORT_COLUMNS.copy()

    # Fallback: symbol + timestamp (no strategy_id)
    if all(c in df.columns for c in SORT_COLUMNS_FALLBACK):
        logger.debug("strategy_id not present, falling back to %s", SORT_COLUMNS_FALLBACK)
        return SORT_COLUMNS_FALLBACK.copy()

    # Minimum viable: just timestamp
    if REQUIRED_SORT_COLUMN in df.columns:
        logger.warning(
            "Only '%s' available for sorting; symbol/strategy_id missing. "
            "This may degrade DuckDB query performance.",
            REQUIRED_SORT_COLUMN,
        )
        return [REQUIRED_SORT_COLUMN]

    raise ValueError(
        f"DataFrame must contain at least '{REQUIRED_SORT_COLUMN}' column for sorted write"
    )


def enforce_sorted_write(
    df: pl.DataFrame,
    sort_cols: Optional[Sequence[str]] = None,
    validate: bool = True,
) -> pl.DataFrame:
    """Sort DataFrame by canonical sort key and optionally validate result.

    Args:
        df: DataFrame to sort.
        sort_cols: Columns to sort by. Defaults to SORT_COLUMNS or SORT_COLUMNS_FALLBACK.
        validate: If True, verify sort order after sorting. Default True.

    Returns:
        Sorted DataFrame.

    Raises:
        SortOrderViolationError: If validation fails (should not happen after sort).
        ValueError: If required sort column missing.
    """
    cols = _resolve_sort_columns(df, sort_cols)

    logger.debug("Sorting DataFrame by %s (validate=%s)", cols, validate)

    sorted_df = df.sort(cols)

    if validate:
        if not validate_sort_order(sorted_df, cols):
            raise SortOrderViolationError(
                f"Sort validation failed after sorting by {cols}. "
                "This should not happen — please report this bug."
            )

    return sorted_df


def validate_sort_order(
    df: pl.DataFrame,
    sort_cols: Sequence[str],
) -> bool:
    """Check if DataFrame is already sorted by given columns.

    Args:
        df: DataFrame to check.
        sort_cols: Columns to check sort order for.

    Returns:
        True if sorted, False if not.
    """
    if len(df) <= 1:
        return True

    cols = list(sort_cols)
    for i in range(len(df) - 1):
        row_a = df.select(cols).row(i)
        row_b = df.select(cols).row(i + 1)
        if row_a > row_b:
            return False
    return True


def write_parquet_sorted(
    df: pl.DataFrame,
    path: str,
    compression: str = "zstd",
    compression_level: int = 3,
    sort_cols: Optional[Sequence[str]] = None,
    **kwargs,
) -> dict:
    """Sort DataFrame and write to parquet. Single entry point for all sorted writes.

    Args:
        df: DataFrame to write.
        path: Output parquet file path.
        compression: Compression algorithm.
        compression_level: Compression level.
        sort_cols: Override sort columns (default: SORT_COLUMNS or SORT_COLUMNS_FALLBACK).
        **kwargs: Passed to df.write_parquet().

    Returns:
        dict with keys: path, rows, sort_cols_used, was_presorted.
    """
    cols = _resolve_sort_columns(df, sort_cols)

    was_presorted = validate_sort_order(df, cols)

    if was_presorted:
        logger.debug("DataFrame already sorted by %s", cols)
    else:
        logger.debug("DataFrame not sorted by %s — sorting now", cols)

    sorted_df = df.sort(cols)

    # Validate post-sort (should always pass)
    if not validate_sort_order(sorted_df, cols):
        raise SortOrderViolationError(
            f"Post-sort validation failed for {cols}. Data may contain nulls or "
            "incomparable types."
        )

    sorted_df.write_parquet(
        path,
        compression=compression,
        compression_level=compression_level,
        statistics=True,
        use_pyarrow=True,
        **kwargs,
    )

    logger.info(
        "Wrote sorted parquet: %s | rows=%d | sort=%s | presorted=%s",
        path,
        len(df),
        cols,
        was_presorted,
    )

    return {
        "path": path,
        "rows": len(df),
        "sort_cols_used": cols,
        "was_presorted": was_presorted,
    }
