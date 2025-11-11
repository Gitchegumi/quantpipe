"""Main ingestion pipeline for fast core data processing.

This module implements the high-performance ingestion pipeline that processes
raw OHLCV data through multiple stages: reading, sorting, deduplication,
cadence validation, gap filling, schema restriction, and optional downcasting.

The pipeline produces a normalized core dataset with performance metrics
and supports both columnar (DataFrame) and iterator output modes.

Core Pipeline Stages (FR-002):
1. Read -> Load raw CSV data
2. Sort -> Chronological ordering by timestamp
3. Deduplicate -> Remove duplicates (keep-first)
4. Validate Cadence -> Check for excessive missing intervals
5. Fill Gaps -> Synthesize missing candles
6. Restrict Schema -> Select core columns only
7. Downcast (optional) -> Optimize memory usage
8. Collect Metrics -> Gather performance statistics

Performance Target: ≤120s for 6.9M rows (SC-001), stretch goal ≤90s (SC-012)
"""

import logging
from dataclasses import dataclass
from typing import Union

import pandas as pd

from src.io.arrow_config import configure_arrow_backend, detect_backend
from src.io.cadence import (
    compute_cadence_deviation,
    compute_expected_intervals,
)
from src.io.downcast import downcast_float_columns
from src.io.duplicates import remove_duplicates
from src.io.gap_fill import fill_gaps_vectorized
from src.io.gaps import detect_gaps
from src.io.hash_utils import compute_dataframe_hash
from src.io.iterator_mode import DataFrameIteratorWrapper
from src.io.logging_constants import IngestionStage, MAX_PROGRESS_UPDATES
from src.io.perf_utils import PerformanceTimer, calculate_throughput
from src.io.progress import ProgressReporter
from src.io.schema import (
    CORE_COLUMNS,
    restrict_to_core_schema,
    validate_required_columns,
)
from src.io.timezone_validate import validate_utc_timezone

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

    data: Union[pd.DataFrame, DataFrameIteratorWrapper]
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
) -> IngestionResult:
    """Ingest and normalize raw OHLCV candle data.

    Implements the full ingestion pipeline with performance optimization
    and comprehensive metrics collection. Supports both columnar DataFrame
    and iterator output modes.

    Args:
        path: Path to raw CSV file containing OHLCV data.
        timeframe_minutes: Expected cadence in minutes (e.g., 1 for 1-minute).
        mode: Output mode, either 'columnar' or 'iterator'.
        downcast: If True, apply float64→float32 downcasting for memory savings.
        use_arrow: If True, attempt to use Arrow backend for acceleration.
        strict_cadence: If True, warn if deviation >50% (extreme gaps suggesting
            data quality issues). If False, no warnings. In both cases, gap filling
            proceeds normally. Historical FX data naturally has ~30% gaps (weekends).

    Returns:
        IngestionResult: Contains processed data, metrics, and metadata.

    Raises:
        FileNotFoundError: If input file does not exist.
        ValueError: If required columns missing, timestamps non-UTC,
            or cadence deviation exceeds tolerance.
        RuntimeError: If cadence validation fails with excessive gaps.

    Examples:
        >>> result = ingest_ohlcv_data(
        ...     "price_data/eurusd/eurusd_1m.csv",
        ...     timeframe_minutes=1,
        ...     mode="columnar"
        ... )
        >>> print(f"Processed {result.metrics.total_rows_output} rows")
        >>> print(f"Runtime: {result.metrics.runtime_seconds:.2f}s")
    """
    # Validate mode parameter
    if mode not in ("columnar", "iterator"):
        raise ValueError(f"Invalid mode: {mode}. Must be 'columnar' or 'iterator'.")

    # Initialize progress reporter (≤5 updates for entire pipeline)
    progress = ProgressReporter(total_stages=MAX_PROGRESS_UPDATES)

    # Configure Arrow backend if requested
    backend = "pandas"
    if use_arrow:
        try:
            configure_arrow_backend()
            backend = detect_backend()
            logger.info("Using acceleration backend: %s", backend)
        except (ImportError, ValueError, AttributeError) as exc:
            logger.warning("Arrow backend unavailable, using pandas: %s", exc)
            backend = "pandas"

    # Start performance timer
    with PerformanceTimer() as timer:
        # Stage 1: Read raw data
        progress.report_stage(IngestionStage.READ, f"Loading {path}")
        try:
            df = pd.read_csv(path)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Input file not found: {path}") from exc

        input_row_count = len(df)
        logger.info("Loaded %d raw rows", input_row_count)

        # Parse and validate timestamps
        if "timestamp" in df.columns:
            df["timestamp_utc"] = pd.to_datetime(df["timestamp"], utc=True)
        elif "timestamp_utc" not in df.columns:
            raise ValueError("Input must have 'timestamp' or 'timestamp_utc' column")

        validate_utc_timezone(df, "timestamp_utc")

        # Validate required columns present (after timestamp conversion)
        validate_required_columns(df)

        # Stage 2: Sort chronologically
        progress.report_stage(IngestionStage.PROCESS, "Sorting by timestamp")
        df = df.sort_values("timestamp_utc").reset_index(drop=True)
        logger.debug("Sorted %d rows chronologically", len(df))

        # Stage 3: Detect and remove duplicates
        df, duplicates_removed = remove_duplicates(df)
        if duplicates_removed > 0:
            logger.info("Removed %d duplicate rows", duplicates_removed)

        # Handle empty data early
        if len(df) == 0:
            logger.warning("Empty dataset after deduplication")
            # Add is_gap column for schema consistency
            df["is_gap"] = pd.Series(dtype=bool)
            # Restrict to core schema
            df = restrict_to_core_schema(df)
            output_row_count = 0
            gaps_inserted = 0
            downcast_applied = False
            core_hash = compute_dataframe_hash(df, CORE_COLUMNS)
        else:
            # Stage 4: Cadence analysis (informational only)
            # Note: FX data naturally has gaps (weekends, holidays, low liquidity)
            # This check just reports statistics - gap filling handles the actual gaps
            start_time = df["timestamp_utc"].iloc[0]
            end_time = df["timestamp_utc"].iloc[-1]
            expected_intervals = compute_expected_intervals(
                start_time, end_time, timeframe_minutes
            )
            actual_intervals = len(df)
            deviation = compute_cadence_deviation(actual_intervals, expected_intervals)

            logger.info(
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
                    "This may indicate a data quality issue. Gap filling will proceed.",
                    deviation,
                    missing,
                )

            # Stage 5: Gap detection and filling
            progress.report_stage(IngestionStage.GAP_FILL, "Filling gaps")
            gap_indices = detect_gaps(df, timeframe_minutes)
            gaps_inserted = len(gap_indices)

            if gaps_inserted > 0:
                df, gaps_inserted = fill_gaps_vectorized(df, timeframe_minutes)
                logger.info("Filled %d gaps with synthetic candles", gaps_inserted)
            else:
                # No gaps - add is_gap column with all False
                df["is_gap"] = False

            # Stage 6: Schema restriction
            progress.report_stage(IngestionStage.SCHEMA, "Restricting to core")
            df = restrict_to_core_schema(df)
            logger.debug("Restricted to core schema with %d columns", len(df.columns))

            # Stage 7: Optional downcasting
            downcast_applied = False
            if downcast:
                progress.report_stage(IngestionStage.FINALIZE, "Downcasting numerics")
                original_memory = df.memory_usage(deep=True).sum()
                df = downcast_float_columns(df)
                new_memory = df.memory_usage(deep=True).sum()
                memory_saved_pct = (
                    (original_memory - new_memory) / original_memory
                ) * 100
                logger.info("Downcast saved %.1f%% memory", memory_saved_pct)
                downcast_applied = True
            else:
                progress.report_stage(IngestionStage.FINALIZE, "Finalizing")

            # Store output count for metrics (before exiting context)
            output_row_count = len(df)

            # Compute core hash for immutability verification
            core_hash = compute_dataframe_hash(df, CORE_COLUMNS)

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

    # Log final summary
    logger.info(
        "Ingestion complete: %d rows in %.2fs (%.0f rows/min, backend=%s)",
        output_row_count,
        runtime_seconds,
        throughput,
        backend,
    )

    # Finalize progress bar
    progress.finish()

    # Return result with mode-specific data wrapper
    if mode == "iterator":
        # Wrap DataFrame in iterator for row-by-row consumption
        data = DataFrameIteratorWrapper(df)
    else:
        # Return DataFrame directly for columnar mode
        data = df

    return IngestionResult(data=data, metrics=metrics, mode=mode, core_hash=core_hash)
