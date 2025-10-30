"""Time series dataset builder for test/validation split generation.

This module orchestrates the dataset building pipeline:
1. Discover symbols from raw data directories
2. Validate and merge raw CSV files per symbol
3. Perform deterministic 80/20 chronological split
4. Generate metadata and summary reports

Feature: 004-timeseries-dataset
Status: Phase 2 implementation (T006-T014)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..models.metadata import BuildSummary, MetadataRecord, SkipReason, SkippedSymbol

logger = logging.getLogger(__name__)

# Constants
REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}
MIN_ROWS_THRESHOLD = 500
SPLIT_RATIO = 0.8


def discover_symbols(raw_data_path: str) -> list[str]:
    """Scan raw data directory and enumerate symbol subdirectories.

    Args:
        raw_data_path: Path to price_data/raw/ directory

    Returns:
        List of symbol identifiers (subdirectory names)

    Implementation: T006
    """
    raw_path = Path(raw_data_path)

    if not raw_path.exists():
        logger.warning("Raw data path does not exist: %s", raw_data_path)
        return []

    # Find all subdirectories containing CSV files
    symbols = []
    for item in raw_path.iterdir():
        if item.is_dir():
            # Check if directory contains any CSV files
            csv_files = list(item.glob("*.csv"))
            if csv_files:
                symbols.append(item.name)
                logger.debug(
                    "Discovered symbol %s with %d CSV files", item.name, len(csv_files)
                )

    logger.info("Discovered %d symbols from %s", len(symbols), raw_data_path)
    return sorted(symbols)  # Deterministic ordering


def validate_schema(symbol: str, files: list[str]) -> bool:
    """Validate raw file schema consistency for a symbol.

    Args:
        symbol: Symbol identifier
        files: List of raw CSV file paths

    Returns:
        True if schema valid, False if mismatch detected

    Implementation: T007
    """
    if not files:
        logger.warning("No files provided for schema validation of symbol %s", symbol)
        return False

    reference_columns = None

    for file_path in files:
        try:
            # Read only header to check schema
            df_header = pd.read_csv(file_path, nrows=0)
            current_columns = set(df_header.columns.str.lower())

            # Check for required columns
            missing_columns = REQUIRED_COLUMNS - current_columns
            if missing_columns:
                logger.error(
                    "File %s for symbol %s missing required columns: %s",
                    file_path,
                    symbol,
                    missing_columns,
                )
                return False

            # Check consistency across files
            if reference_columns is None:
                reference_columns = current_columns
            elif current_columns != reference_columns:
                logger.error(
                    "Schema mismatch in symbol %s: %s has columns %s, expected %s",
                    symbol,
                    file_path,
                    current_columns,
                    reference_columns,
                )
                return False

        except Exception as e:
            logger.error(
                "Error reading file %s for symbol %s: %s", file_path, symbol, e
            )
            return False

    logger.debug(
        "Schema validation passed for symbol %s (%d files)", symbol, len(files)
    )
    return True


def detect_gaps_and_overlaps(df: pd.DataFrame, symbol: str) -> tuple[int, int]:
    """Detect temporal gaps and overlapping timestamps (T014 helper).

    Args:
        df: Sorted DataFrame with timestamp column
        symbol: Symbol identifier for logging

    Returns:
        Tuple of (gap_count, overlap_count)

    Notes:
        - Gaps are counted silently (no warnings per spec update)
        - Overlaps are logged as warnings
        - Gap detection based on median time delta deviation
    """
    if len(df) < 2:
        return 0, 0

    # Count overlaps (duplicates) - these are logged
    overlap_count = df["timestamp"].duplicated().sum()
    if overlap_count > 0:
        logger.warning("Symbol %s has %d overlapping timestamps", symbol, overlap_count)

    # Detect gaps based on expected cadence
    time_deltas = df["timestamp"].diff().dropna()
    if len(time_deltas) == 0:
        return 0, overlap_count

    # Use median delta as expected cadence
    median_delta = time_deltas.median()
    # Gaps are intervals > 1.5x median (conservative threshold)
    gap_threshold = median_delta * 1.5
    gap_count = (time_deltas > gap_threshold).sum()

    # Gaps counted silently per spec clarification
    logger.debug("Symbol %s has %d temporal gaps (silent)", symbol, gap_count)

    return int(gap_count), int(overlap_count)


def merge_and_sort(symbol: str, files: list[str]) -> tuple[pd.DataFrame, int, int]:
    """Merge raw files, sort chronologically, detect gaps/overlaps.

    Args:
        symbol: Symbol identifier
        files: List of raw CSV file paths

    Returns:
        Tuple of (merged_dataframe, gap_count, overlap_count)

    Implementation: T008
    """
    logger.info("Merging and sorting %d files for symbol %s", len(files), symbol)

    dataframes = []
    for file_path in files:
        try:
            df = pd.read_csv(file_path)
            # Normalize column names to lowercase
            df.columns = df.columns.str.lower()
            # Parse timestamp
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            dataframes.append(df)
            logger.debug("Loaded %d rows from %s", len(df), file_path)
        except Exception as e:
            logger.error(
                "Error loading file %s for symbol %s: %s", file_path, symbol, e
            )
            raise

    # Concatenate all dataframes
    merged = pd.concat(dataframes, ignore_index=True)
    logger.debug("Merged total %d rows for symbol %s", len(merged), symbol)

    # Detect gaps/overlaps before deduplication
    gap_count, overlap_count = detect_gaps_and_overlaps(merged, symbol)

    # Sort by timestamp
    merged = merged.sort_values("timestamp").reset_index(drop=True)

    # Deduplicate timestamps (keep first occurrence)
    if overlap_count > 0:
        pre_dedup_len = len(merged)
        merged = merged.drop_duplicates(subset=["timestamp"], keep="first").reset_index(
            drop=True
        )
        logger.debug(
            "Deduplicated %d overlapping rows for symbol %s",
            pre_dedup_len - len(merged),
            symbol,
        )

    logger.info(
        "Symbol %s: merged %d rows, %d gaps, %d overlaps",
        symbol,
        len(merged),
        gap_count,
        overlap_count,
    )

    return merged, gap_count, overlap_count


def partition_data(
    data: pd.DataFrame, split_ratio: float = 0.8
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Partition dataset into test (80%) and validation (20%) splits.

    Args:
        data: Merged and sorted DataFrame
        split_ratio: Test partition ratio (default 0.8)

    Returns:
        Tuple of (test_partition, validation_partition)

    Implementation: T009

    Notes:
        - Uses floor for test size ensuring deterministic split
        - Validation gets remainder (most recent data)
        - Formula: test_size = floor(n * split_ratio)
    """
    n = len(data)
    test_size = int(np.floor(n * split_ratio))

    test_partition = data.iloc[:test_size].copy()
    validation_partition = data.iloc[test_size:].copy()

    logger.info(
        "Partitioned data: %d total -> %d test (%.1f%%) + %d validation (%.1f%%)",
        n,
        test_size,
        (test_size / n * 100) if n > 0 else 0,
        len(validation_partition),
        (len(validation_partition) / n * 100) if n > 0 else 0,
    )

    return test_partition, validation_partition


def build_metadata(
    symbol: str,
    total_rows: int,
    test_rows: int,
    validation_rows: int,
    start_timestamp: datetime,
    end_timestamp: datetime,
    validation_start_timestamp: datetime,
    gap_count: int,
    overlap_count: int,
    source_files: list[str],
) -> MetadataRecord:
    """Generate per-symbol metadata record.

    Args:
        symbol: Symbol identifier
        total_rows: Total rows in merged dataset
        test_rows: Rows in test partition
        validation_rows: Rows in validation partition
        start_timestamp: Earliest timestamp
        end_timestamp: Latest timestamp
        validation_start_timestamp: First timestamp in validation partition
        gap_count: Number of detected gaps
        overlap_count: Number of overlapping timestamps
        source_files: List of source CSV file paths

    Returns:
        MetadataRecord pydantic model instance

    Implementation: T010
    """
    metadata = MetadataRecord(
        symbol=symbol,
        total_rows=total_rows,
        test_rows=test_rows,
        validation_rows=validation_rows,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        validation_start_timestamp=validation_start_timestamp,
        gap_count=gap_count,
        overlap_count=overlap_count,
        canonical_timezone="UTC",
        build_timestamp=datetime.now(timezone.utc),
        schema_version="v1",
        source_files=source_files,
    )

    logger.debug("Built metadata for symbol %s: %d rows", symbol, total_rows)
    return metadata


def build_summary(
    build_start: datetime,
    build_end: datetime,
    symbols_processed: list[str],
    symbols_skipped: list[SkippedSymbol],
    total_rows: int,
    total_test_rows: int,
    total_validation_rows: int,
) -> BuildSummary:
    """Generate consolidated build summary.

    Args:
        build_start: Build start timestamp
        build_end: Build completion timestamp
        symbols_processed: List of successfully processed symbols
        symbols_skipped: List of skipped symbols with reasons
        total_rows: Sum of all processed rows
        total_test_rows: Sum of test partition rows
        total_validation_rows: Sum of validation partition rows

    Returns:
        BuildSummary pydantic model instance

    Implementation: T011
    """
    duration = (build_end - build_start).total_seconds()

    summary = BuildSummary(
        build_timestamp=build_start,
        build_completed_at=build_end,
        symbols_processed=symbols_processed,
        symbols_skipped=symbols_skipped,
        total_rows_processed=total_rows,
        total_test_rows=total_test_rows,
        total_validation_rows=total_validation_rows,
        duration_seconds=duration,
    )

    logger.info(
        "Build summary: %d processed, %d skipped, %.2f seconds",
        len(symbols_processed),
        len(symbols_skipped),
        duration,
    )

    return summary


def write_outputs(
    symbol: str,
    test_partition: pd.DataFrame,
    validation_partition: pd.DataFrame,
    metadata: MetadataRecord,
    output_base: str,
) -> None:
    """Write CSV partitions and metadata JSON files.

    Args:
        symbol: Symbol identifier
        test_partition: Test partition DataFrame
        validation_partition: Validation partition DataFrame
        metadata: MetadataRecord model instance
        output_base: Base output directory path

    Implementation: T012
    """
    output_path = Path(output_base) / symbol
    test_path = output_path / "test"
    validate_path = output_path / "validate"

    # Create directories
    test_path.mkdir(parents=True, exist_ok=True)
    validate_path.mkdir(parents=True, exist_ok=True)

    # Write CSV partitions
    test_file = test_path / f"{symbol}_test.csv"
    validation_file = validate_path / f"{symbol}_validate.csv"

    test_partition.to_csv(test_file, index=False)
    validation_partition.to_csv(validation_file, index=False)

    logger.debug("Wrote test partition: %s (%d rows)", test_file, len(test_partition))
    logger.debug(
        "Wrote validation partition: %s (%d rows)",
        validation_file,
        len(validation_partition),
    )

    # Write metadata JSON
    metadata_file = output_path / "metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata.model_dump(mode="json"), f, indent=2, default=str)

    logger.info("Wrote outputs for symbol %s to %s", symbol, output_path)


def build_symbol_dataset(
    symbol: str, raw_path: str, output_path: str
) -> dict[str, Any]:
    """Build complete dataset for a single symbol (US1 integration).

    Args:
        symbol: Symbol identifier
        raw_path: Path to raw data directory
        output_path: Path to processed output directory

    Returns:
        Build result summary for this symbol with keys:
            - success: bool
            - symbol: str
            - metadata: MetadataRecord | None
            - skip_reason: SkipReason | None
            - error: str | None

    Implementation: T015
    """
    logger.info("Building dataset for symbol %s", symbol)

    symbol_raw_path = Path(raw_path) / symbol
    csv_files = list(symbol_raw_path.glob("*.csv"))

    if not csv_files:
        logger.warning("No CSV files found for symbol %s", symbol)
        return {
            "success": False,
            "symbol": symbol,
            "metadata": None,
            "skip_reason": SkipReason.READ_ERROR,
            "error": "No CSV files found",
        }

    file_paths = [str(f) for f in csv_files]

    # Validate schema
    if not validate_schema(symbol, file_paths):
        return {
            "success": False,
            "symbol": symbol,
            "metadata": None,
            "skip_reason": SkipReason.SCHEMA_MISMATCH,
            "error": "Schema validation failed",
        }

    try:
        # Merge and sort
        merged_df, gap_count, overlap_count = merge_and_sort(symbol, file_paths)

        # Check minimum rows threshold
        if len(merged_df) < MIN_ROWS_THRESHOLD:
            logger.warning(
                "Symbol %s has insufficient rows: %d < %d",
                symbol,
                len(merged_df),
                MIN_ROWS_THRESHOLD,
            )
            return {
                "success": False,
                "symbol": symbol,
                "metadata": None,
                "skip_reason": SkipReason.INSUFFICIENT_ROWS,
                "error": f"Only {len(merged_df)} rows, minimum {MIN_ROWS_THRESHOLD} required",
            }

        # Partition
        test_partition, validation_partition = partition_data(merged_df, SPLIT_RATIO)

        # Build metadata
        metadata = build_metadata(
            symbol=symbol,
            total_rows=len(merged_df),
            test_rows=len(test_partition),
            validation_rows=len(validation_partition),
            start_timestamp=merged_df["timestamp"].iloc[0].to_pydatetime(),
            end_timestamp=merged_df["timestamp"].iloc[-1].to_pydatetime(),
            validation_start_timestamp=validation_partition["timestamp"]
            .iloc[0]
            .to_pydatetime(),
            gap_count=gap_count,
            overlap_count=overlap_count,
            source_files=file_paths,
        )

        # Write outputs
        write_outputs(
            symbol, test_partition, validation_partition, metadata, output_path
        )

        logger.info("Successfully built dataset for symbol %s", symbol)
        return {
            "success": True,
            "symbol": symbol,
            "metadata": metadata,
            "skip_reason": None,
            "error": None,
        }

    except Exception as e:
        logger.error(
            "Error building dataset for symbol %s: %s", symbol, e, exc_info=True
        )
        return {
            "success": False,
            "symbol": symbol,
            "metadata": None,
            "skip_reason": SkipReason.READ_ERROR,
            "error": str(e),
        }


def build_all_symbols(
    raw_path: str, output_path: str, force: bool = False
) -> BuildSummary:
    """Build datasets for all discovered symbols (US2 orchestration).

    Args:
        raw_path: Path to raw data directory
        output_path: Path to processed output directory
        force: Force rebuild if True (currently ignored - future enhancement)

    Returns:
        Consolidated BuildSummary model instance

    Implementation: T022
    """
    build_start = datetime.now(timezone.utc)
    logger.info("Building datasets for all symbols (force=%s)", force)

    # Discover symbols
    symbols = discover_symbols(raw_path)

    if not symbols:
        logger.warning("No symbols discovered from %s", raw_path)
        build_end = datetime.now(timezone.utc)
        return build_summary(
            build_start=build_start,
            build_end=build_end,
            symbols_processed=[],
            symbols_skipped=[],
            total_rows=0,
            total_test_rows=0,
            total_validation_rows=0,
        )

    processed_symbols = []
    skipped_symbols = []
    total_rows = 0
    total_test_rows = 0
    total_validation_rows = 0

    # Process each symbol
    for symbol in symbols:
        result = build_symbol_dataset(symbol, raw_path, output_path)

        if result["success"]:
            processed_symbols.append(symbol)
            metadata = result["metadata"]
            total_rows += metadata.total_rows
            total_test_rows += metadata.test_rows
            total_validation_rows += metadata.validation_rows
        else:
            skipped_symbols.append(
                SkippedSymbol(
                    symbol=symbol,
                    reason=result["skip_reason"],
                    details=result["error"],
                )
            )

    build_end = datetime.now(timezone.utc)

    # Build consolidated summary
    summary = build_summary(
        build_start=build_start,
        build_end=build_end,
        symbols_processed=processed_symbols,
        symbols_skipped=skipped_symbols,
        total_rows=total_rows,
        total_test_rows=total_test_rows,
        total_validation_rows=total_validation_rows,
    )

    # Write summary to output directory
    summary_file = Path(output_path) / "build_summary.json"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary.model_dump(mode="json"), f, indent=2, default=str)

    logger.info("Wrote build summary to %s", summary_file)

    return summary
