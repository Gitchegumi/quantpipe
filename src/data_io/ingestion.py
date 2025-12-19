"""Main ingestion pipeline for fast core data processing.

This module implements the high-performance ingestion pipeline that processes
raw OHLCV data through multiple stages: reading, sorting, deduplication,
cadence validation, gap filling, schema restriction, and optional downcasting.

The pipeline produces a normalized core dataset with performance metrics
and supports both columnar (DataFrame) and iterator output modes.

Core Pipeline Stages (FR-002):
1. Read -> Load raw CSV data (with Parquet caching)
2. Sort -> Chronological ordering by timestamp
3. Deduplicate -> Remove duplicates (keep-first)
4. Validate Cadence -> Check for excessive missing intervals
5. Fill Gaps -> Synthesize missing candles
6. Restrict Schema -> Select core columns only
7. Downcast (optional) -> Optimize memory usage
8. Collect Metrics -> Gather performance statistics

Performance Target: ≤120s for 6.9M rows (SC-001), stretch goal ≤90s (SC-012)
Parquet caching reduces subsequent loads to ≤15s
"""

# pylint: disable=unused-import


import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Union, TYPE_CHECKING

import pandas as pd
import polars as pl
from polars import DataFrame as PolarsDataFrame

from src.data_io.arrow_config import configure_arrow_backend
from src.data_io.cadence import (
    compute_cadence_deviation,
    compute_expected_intervals,
)
from src.data_io.downcast import downcast_float_columns
from src.data_io.duplicates import remove_duplicates
from src.data_io.gap_fill import fill_gaps_vectorized
from src.data_io.gaps import detect_gaps
from src.data_io.hash_utils import compute_dataframe_hash
from src.data_io.iterator_mode import DataFrameIteratorWrapper
from src.data_io.logging_constants import IngestionStage
from src.data_io.parquet_cache import load_with_cache
from src.data_io.perf_utils import PerformanceTimer, calculate_throughput
from src.data_io.progress import ProgressReporter
from src.data_io.schema import (
    CORE_COLUMNS,
    restrict_to_core_schema,
    validate_required_columns,
)
from src.data_io.timezone_validate import validate_utc_timezone


if TYPE_CHECKING:
    pass  # import polars as pl is no longer needed here


logger = logging.getLogger(__name__)


@dataclass
class IngestionMetrics:
    """Performance and processing metrics for ingestion pipeline.

    Attributes:
        total_rows_input: Number of rows in raw input.
        total_rows_output: Number of rows after processing.
        gaps_inserted: Count of synthetic gap rows added.
        duplicates_removed: Count of duplicate rows removed.
        runtime_seconds: Total wall-clock time for ingestion.
        throughput_rows_per_min: Processing throughput.
        acceleration_backend: Backend used (arrow or pandas).
        downcast_applied: Whether numeric downcasting was applied.
        stretch_runtime_candidate: True if runtime ≤90s (stretch goal).
    """

    total_rows_input: int
    total_rows_output: int
    gaps_inserted: int
    duplicates_removed: int
    runtime_seconds: float
    throughput_rows_per_min: float
    acceleration_backend: str
    downcast_applied: bool
    stretch_runtime_candidate: bool


@dataclass
class IngestionResult:
    """Result of ingestion pipeline execution.

    Attributes:
        data: Core dataset (DataFrame for columnar, iterator wrapper for iterator mode).
        metrics: Performance and processing metrics.
        mode: Output mode (columnar or iterator).
        core_hash: SHA256 hash of core columns for immutability verification.
    """

    data: pd.DataFrame | PolarsDataFrame | DataFrameIteratorWrapper
    metrics: IngestionMetrics
    mode: str
    core_hash: str


def ingest_ohlcv_data(
    path: str,
    timeframe_minutes: int,
    mode: str = "columnar",
    downcast: bool = False,
    use_arrow: bool = True,
    strict_cadence: bool = True,
    use_parquet_cache: bool = True,
    fill_gaps: bool = False,
    return_polars: bool = False,
) -> IngestionResult:

    try:
        # Ingest and normalize raw OHLCV candle data.
        # Implements the full ingestion pipeline with performance optimization
        # and comprehensive metrics collection. Supports both columnar DataFrame
        # and iterator output modes. Automatically caches CSV→Parquet for faster
        # subsequent loads.
        # Args:
        #     path: Path to raw CSV file containing OHLCV data.
        #     timeframe_minutes: Expected cadence in minutes (e.g., 1 for 1-minute).
        #     mode: Output mode, either 'columnar' or 'iterator'.
        #     downcast: If True, apply float64→float32 downcasting for memory savings.
        #     use_arrow: If True, attempt to use Arrow backend for acceleration.
        #     strict_cadence: If True, warn if deviation >50% (extreme gaps suggesting
        #         data quality issues). If False, no warnings. Historical FX data
        #         naturally has ~30% gaps (weekends).
        #     use_parquet_cache: If True, use Parquet caching to skip CSV parsing on
        #         subsequent loads (default: True for 10-15x speedup).
        #     fill_gaps: If True, fill timestamp gaps with synthetic candles
        #         (forward-fill close prices). If False (default), preserve gaps as they
        #         represent actual market closures (weekends, holidays). When False,
        #         is_gap column is still added but all values are False.
        #         **Note**: Gap filling during ingestion is generally NOT recommended
        #         as it creates synthetic price data that never occurred. The primary
        #         use case for gap filling is during **resampling to higher
        #         timeframes** (e.g., 1-min → 5-min → 1-hour), which will be
        #         implemented in a future specification. For raw ingestion, gaps should
        #         be preserved to maintain data integrity.
        # Returns:
        #     IngestionResult: Contains processed data, metrics, and metadata.
        # Raises:
        #     FileNotFoundError: If input file does not exist.
        #     ValueError: If required columns missing, timestamps non-UTC,
        #         or cadence deviation exceeds tolerance.
        #     RuntimeError: If cadence validation fails with excessive gaps.
        # Examples:
        #     >>> result = ingest_ohlcv_data(
        #     ...     "price_data/eurusd/eurusd_1m.csv",
        #     ...     timeframe_minutes=1,
        #     ...     mode="columnar"
        #     ... )
        #     >>> print(f"Processed {result.metrics.total_rows_output} rows")
        #     >>> print(f"Runtime: {result.metrics.runtime_seconds:.2f}s")

        # Validate mode parameter

        if mode not in ("columnar", "iterator"):

            raise ValueError(f"Invalid mode: {mode}. Must be 'columnar' or 'iterator'.")

        # Initialize progress reporter

        progress = ProgressReporter(show_progress=True)

        # Configure Arrow backend if requested

        backend = "pandas"

        dtype_backend = None  # Use pandas default (numpy)

        if use_arrow:

            try:

                backend = configure_arrow_backend()

                if backend == "arrow":

                    dtype_backend = "pyarrow"

                logger.info("Using acceleration backend: %s", backend)

            except (ImportError, ValueError, AttributeError) as exc:

                logger.warning("Arrow backend unavailable, using pandas: %s", exc)

                backend = "pandas"

        # Start performance timer

        with PerformanceTimer() as timer:

            df = None  # Initialize df to None

            input_row_count = 0  # Initialize input_row_count to 0

            output_row_count = 0  # Initialize output_row_count to 0

            gaps_inserted = 0  # Initialize gaps_inserted to 0

            duplicates_removed = 0  # Initialize duplicates_removed to 0

            downcast_applied = False  # Initialize downcast_applied to False

            core_hash = ""  # Initialize core_hash to empty string

            # Stage 1: Read raw data with progress tracking (or load from Parquet cache)

            csv_path = Path(path)

            # Check if input is already Parquet

            if csv_path.suffix.lower() == ".parquet":

                logger.info("Loading Parquet file directly: %s", csv_path)

                try:

                    df = pl.read_parquet(csv_path)

                    input_row_count = len(df)

                    logger.info("✓ Loaded %d rows from Parquet file", input_row_count)

                except Exception as exc:

                    raise RuntimeError(f"Failed to load Parquet file: {exc}") from exc

                if not return_polars and isinstance(df, pl.DataFrame):
                    print(
                        f"DEBUG INGEST: Converting Polars to Pandas. Cols: {df.columns}"
                    )
                    df = df.to_pandas()
                    print(f"DEBUG INGEST: Converted. Cols: {df.columns}")

            # Try Parquet cache for CSV files

            elif use_parquet_cache:

                try:

                    df = load_with_cache(csv_path, return_polars=return_polars)

                    input_row_count = len(df)

                    logger.info("✓ Loaded %d rows from Parquet cache", input_row_count)

                except (FileNotFoundError, ValueError, RuntimeError, OSError) as exc:

                    logger.warning(
                        "Parquet cache load failed, falling back to CSV: %s", exc
                    )

                    df = None

            else:

                df = None

            # Fallback to CSV parsing if cache disabled or failed

            if df is None:

                # First pass: count total lines for progress bar

                try:

                    with open(path, encoding="utf-8") as f:

                        total_lines = sum(1 for _ in f) - 1  # Subtract header

                except FileNotFoundError as exc:

                    raise FileNotFoundError(f"Input file not found: {path}") from exc

                progress.start_stage(
                    IngestionStage.READ, f"Reading {path}", total=total_lines
                )

                if return_polars:

                    # Read CSV directly into Polars DataFrame

                    df = pl.read_csv(
                        path, has_header=True
                    )  # Assuming header for Polars

                    input_row_count = len(df)

                    progress.update_progress(advance=input_row_count)

                else:

                    # Read CSV in chunks with progress tracking (Pandas)

                    chunk_size = 100_000  # 100k rows per chunk

                    chunks = []

                    try:

                        read_kwargs = {"chunksize": chunk_size}

                        if dtype_backend:

                            read_kwargs["dtype_backend"] = dtype_backend

                        for chunk in pd.read_csv(path, **read_kwargs):

                            chunks.append(chunk)

                            progress.update_progress(advance=len(chunk))

                        df = pd.concat(chunks, ignore_index=True)

                    except (
                        pd.errors.ParserError,
                        pd.errors.EmptyDataError,
                        ValueError,
                    ) as exc:

                        raise RuntimeError(f"Error reading CSV: {exc}") from exc

                    input_row_count = len(df)

                    logger.info("Loaded %d raw rows from CSV", input_row_count)

                    if df is None:
                        # If all loading attempts failed, create an empty DataFrame
                        if return_polars:
                            df = pl.DataFrame()
                        else:

                            df = pd.DataFrame()
                            logger.warning(
                                "No data loaded, proceeding with empty DataFrame."
                            )

            # Parse and validate timestamps
            if return_polars:
                if "timestamp" in df.columns:
                    df = df.with_columns(
                        pl.col("timestamp")
                        .str.to_datetime(format="%Y-%m-%d %H:%M:%S%z")
                        .alias("timestamp_utc")
                    )
                elif "timestamp_utc" in df.columns:
                    # timestamp_utc exists but may be string from CSV - convert it
                    if df["timestamp_utc"].dtype == pl.Utf8:
                        df = df.with_columns(
                            pl.col("timestamp_utc")
                            .str.to_datetime(format="%Y-%m-%d %H:%M:%S")
                            .dt.replace_time_zone("UTC")
                        )
                else:
                    raise ValueError(
                        "Input must have 'timestamp' or 'timestamp_utc' column"
                    )
                # Polars handles UTC automatically with time_unit="ns"
            else:
                if "timestamp" in df.columns:
                    df["timestamp_utc"] = pd.to_datetime(df["timestamp"], utc=True)
                elif "timestamp_utc" in df.columns:
                    # timestamp_utc exists but may be string from CSV - convert it
                    if not pd.api.types.is_datetime64_any_dtype(df["timestamp_utc"]):
                        df["timestamp_utc"] = pd.to_datetime(
                            df["timestamp_utc"], utc=True
                        )
                else:
                    raise ValueError(
                        "Input must have 'timestamp' or 'timestamp_utc' column"
                    )
                validate_utc_timezone(df, "timestamp_utc")

            # Validate required columns present (after timestamp conversion)

            validate_required_columns(df)

            # Stage 2: Sort chronologically (atomic operation - indeterminate)

            progress.start_stage(
                IngestionStage.PROCESS, f"Sorting {len(df):,} rows by timestamp"
            )

            if return_polars:

                df = df.sort("timestamp_utc")

            else:

                df = df.sort_values("timestamp_utc").reset_index(drop=True)

            logger.debug("Sorted %d rows chronologically", len(df))

            # Stage 3: Detect and remove duplicates

            df, duplicates_removed = remove_duplicates(df, is_polars=return_polars)

            if duplicates_removed > 0:

                logger.info("Removed %d duplicate rows", duplicates_removed)

            # Handle empty data early

            if len(df) == 0:

                logger.warning("Empty dataset after deduplication")

                # Add is_gap column for schema consistency

                if return_polars:

                    df = df.with_columns(
                        pl.Series("is_gap", [False] * len(df), dtype=pl.Boolean)
                    )

                else:

                    df["is_gap"] = pd.Series(dtype=bool)

                # Restrict to core schema

                df = restrict_to_core_schema(df, is_polars=return_polars)

                output_row_count = 0

                gaps_inserted = 0

                downcast_applied = False

                core_hash = compute_dataframe_hash(
                    df, CORE_COLUMNS, is_polars=return_polars
                )

            else:

                # Stage 4: Cadence analysis (informational only)
                # Note: FX data naturally has gaps (weekends, holidays, low liquidity)
                # This check just reports statistics - gap filling handles the
                # actual gaps

                if return_polars:

                    start_time = df["timestamp_utc"].head(1).item()

                    end_time = df["timestamp_utc"].tail(1).item()

                else:

                    start_time = df["timestamp_utc"].iloc[0]

                    end_time = df["timestamp_utc"].iloc[-1]

                expected_intervals = compute_expected_intervals(
                    start_time, end_time, timeframe_minutes
                )

                actual_intervals = len(df)

                deviation = compute_cadence_deviation(
                    actual_intervals, expected_intervals
                )

                logger.debug(
                    "Cadence analysis: %d intervals present, %d expected (%.1f%% complete)",
                    actual_intervals,
                    expected_intervals,
                    100.0 - deviation,
                )

                # Only warn if deviation is extreme (suggests data quality issue)

                if deviation > 50.0 and strict_cadence:

                    missing = expected_intervals - actual_intervals

                    logger.warning(
                        "Large data gap detected: %.1f%% missing (%d intervals). "
                        "Enable fill_gaps=True if you want to fill these during resampling.",
                        deviation,
                        missing,
                    )

                # Stage 5: Optional gap detection and filling

                # Only detect gaps if we're going to fill them (for resampling use case)

                gaps_inserted = 0  # Initialize for metrics

                if fill_gaps:

                    progress.start_stage(
                        IngestionStage.GAP_FILL,
                        f"Detecting and filling gaps in {len(df):,} rows",
                    )

                    gap_indices = detect_gaps(
                        df, timeframe_minutes, is_polars=return_polars
                    )

                    gaps_detected = len(gap_indices)

                    if gaps_detected > 0:

                        logger.info(
                            "Detected %d gaps in timestamp sequence", gaps_detected
                        )

                        # Fill gaps with synthetic candles

                        df, gaps_inserted = fill_gaps_vectorized(
                            df, timeframe_minutes, is_polars=return_polars
                        )

                        logger.info(
                            "Filled %d gaps with synthetic candles", gaps_inserted
                        )

                    else:

                        # No gaps detected - add is_gap column with all False

                        if return_polars:

                            df = df.with_columns(
                                pl.Series("is_gap", [False] * len(df), dtype=pl.Boolean)
                            )

                        else:

                            df["is_gap"] = False

                else:

                    # Skip gap detection entirely - just add is_gap column with all False

                    # Gap detection is expensive and unnecessary if we're not filling

                    if return_polars:

                        df = df.with_columns(
                            pl.Series("is_gap", [False] * len(df), dtype=pl.Boolean)
                        )

                    else:

                        df["is_gap"] = False

                    logger.debug(
                        "Skipping gap detection (fill_gaps=False) - preserving original data"
                    )

                # Stage 6: Schema restriction (atomic operation - indeterminate)

                progress.start_stage(
                    IngestionStage.SCHEMA,
                    f"Restricting {len(df):,} rows to core schema",
                )

                df = restrict_to_core_schema(df, is_polars=return_polars)

                logger.debug(
                    "Restricted to core schema with %d columns", len(df.columns)
                )

                # Stage 7: Optional downcasting (atomic - indeterminate)

                downcast_applied = False

                if (
                    downcast and not return_polars
                ):  # Downcasting only for Pandas for now

                    progress.start_stage(
                        IngestionStage.FINALIZE,
                        f"Downcasting {len(df):,} rows to float32",
                    )

                    original_memory = df.memory_usage(deep=True).sum()

                    df = downcast_float_columns(df)

                    new_memory = df.memory_usage(deep=True).sum()

                    memory_saved_pct = (
                        (original_memory - new_memory) / original_memory
                    ) * 100

                    logger.info("Downcast saved %.1f%% memory", memory_saved_pct)

                    downcast_applied = True

                else:

                    progress.start_stage(IngestionStage.FINALIZE, "Finalizing")

                # Store output count for metrics (before exiting context)

                output_row_count = len(df)

                # Compute core hash for immutability verification

                core_hash = compute_dataframe_hash(
                    df, CORE_COLUMNS, is_polars=return_polars
                )

        # Timer context has exited - now we can access elapsed time

        runtime_seconds = timer.elapsed

        throughput = calculate_throughput(output_row_count, runtime_seconds)

        stretch_candidate = runtime_seconds <= 90.0

        # Assemble metrics

        metrics = IngestionMetrics(
            total_rows_input=input_row_count,
            total_rows_output=output_row_count,
            gaps_inserted=gaps_inserted,
            duplicates_removed=duplicates_removed,
            runtime_seconds=runtime_seconds,
            throughput_rows_per_min=throughput,
            acceleration_backend=backend,
            downcast_applied=downcast_applied,
            stretch_runtime_candidate=stretch_candidate,
        )

        # Finalize progress bar

        progress.finish()

        # Log final summary

        logger.info(
            "Ingestion complete: %d rows in %.2fs (% .0f rows/min, backend=%s)",
            output_row_count,
            runtime_seconds,
            throughput,
            backend,
        )

        # Return result with mode-specific data wrapper

        if mode == "iterator":

            # Wrap DataFrame in iterator for row-by-row consumption

            data = DataFrameIteratorWrapper(df)

        else:

            # Return DataFrame directly for columnar mode

            data = df

        return IngestionResult(
            data=data, metrics=metrics, mode=mode, core_hash=core_hash
        )

    except Exception as e:

        logger.error("Unhandled exception in ingest_ohlcv_data: %s", e, exc_info=True)

        raise  # Re-raise the exception to propagate it
