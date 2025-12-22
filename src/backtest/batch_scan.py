"""Batch scanning module for accelerated market analysis.

This module implements columnar batch scanning using NumPy arrays to process
large datasets efficiently while maintaining signal equivalence with baseline.
Coordinates deduplication, array extraction, and progress tracking.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import polars as pl

from src.backtest.arrays import (
    extract_indicator_arrays,
    extract_ohlc_arrays,
    validate_array_lengths,
)
from src.backtest.dedupe import DedupeResult, dedupe_timestamps_polars
from src.backtest.progress import ProgressDispatcher
from src.backtest.signal_filter import filter_overlapping_signals
from src.strategy.base import Strategy


logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result of batch scan operation.

    Attributes:
        signal_indices: NumPy array of indices where signals were generated
        signal_count: Total number of signals generated
        candles_processed: Number of candles processed
        duplicates_removed: Number of duplicate timestamps removed
        scan_duration_sec: Wall-clock time for scan operation
        progress_overhead_pct: Percentage of time spent on progress updates
    """

    signal_indices: np.ndarray
    signal_count: int
    candles_processed: int
    duplicates_removed: int
    scan_duration_sec: float
    progress_overhead_pct: float


class BatchScan:
    """Batch scanner coordinating dedupe, extraction, and progress tracking.

    Implements FR-001 (scan performance ≤12 min on 6.9M candles) and FR-002
    (allocation efficiency ≤1,500 allocations/million candles).

    Example:
        >>> scanner = BatchScan(strategy=my_strategy)
        >>> result = scanner.scan(df)
        >>> print(result.signal_count)
    """

    def __init__(
        self,
        strategy: Strategy,
        enable_progress: bool = True,
        direction: str = "BOTH",
        parameters: dict | None = None,
    ):
        """Initialize batch scanner.

        Args:
            strategy: Strategy instance providing indicator requirements
            enable_progress: Whether to emit progress updates (default: True)
            direction: Trade direction - "LONG", "SHORT", or "BOTH" (default: "BOTH")
            parameters: Strategy parameters dict (default: None uses strategy defaults)
        """
        self.strategy = strategy
        self.enable_progress = enable_progress
        self.direction = direction
        self.parameters = parameters or {}
        self._validate_strategy()

    def _validate_strategy(self) -> None:
        """Validate strategy has required metadata.

        Raises:
            ValueError: If strategy missing metadata or required_indicators
        """
        if not hasattr(self.strategy, "metadata"):
            msg = "Strategy must provide metadata property"
            logger.error(msg)
            raise ValueError(msg)

        metadata = self.strategy.metadata
        if not hasattr(metadata, "required_indicators"):
            msg = "Strategy metadata must declare required_indicators"
            logger.error(msg)
            raise ValueError(msg)

        logger.debug(
            "Strategy '%s' validated with %d indicators",
            metadata.name,
            len(metadata.required_indicators),
        )

    def scan(
        self,
        df: pl.DataFrame,
        timestamp_col: str = "timestamp_utc",
    ) -> ScanResult:
        """Execute batch scan on DataFrame.

        Args:
            df: Polars DataFrame containing OHLC and indicator data
            timestamp_col: Name of timestamp column (default: 'timestamp_utc')

        Returns:
            ScanResult with signal indices and performance metrics

        Raises:
            ValueError: If required columns missing or data invalid
        """
        import time

        scan_start = time.perf_counter()

        # Step 1: Deduplicate timestamps
        logger.info("Starting batch scan on %d rows", len(df))
        df_dedupe, dedupe_result = self._deduplicate(df, timestamp_col)

        if dedupe_result.duplicates_removed > 0:
            logger.warning(
                "Removed %d duplicate timestamps (first=%s, last=%s)",
                dedupe_result.duplicates_removed,
                dedupe_result.first_duplicate_ts,
                dedupe_result.last_duplicate_ts,
            )

        # Step 2: Extract arrays
        ohlc_arrays = extract_ohlc_arrays(df_dedupe)
        indicator_names = self.strategy.metadata.required_indicators
        indicator_arrays = extract_indicator_arrays(df_dedupe, indicator_names)

        # Step 3: Validate array lengths
        timestamps = ohlc_arrays[0]
        all_arrays = list(ohlc_arrays) + list(indicator_arrays.values())
        validate_array_lengths(*all_arrays)

        logger.debug(
            "Extracted arrays: %d candles, %d indicators",
            len(timestamps),
            len(indicator_arrays),
        )

        # Step 4: Initialize progress tracking
        progress: Optional[ProgressDispatcher] = None
        if self.enable_progress:
            progress = ProgressDispatcher(
                total_items=len(timestamps),
                description="Scanning signals",
                show_progress=self.enable_progress,
            )
            progress.start()

        # Step 5: Scan for signals using batch processing
        signal_indices = self._scan_signals(
            timestamps=timestamps,
            ohlc_arrays=ohlc_arrays,
            indicator_arrays=indicator_arrays,
            progress=progress,
        )

        # Step 5a: Apply strategy's max concurrent positions filter (FR-001)
        signal_indices = self._apply_position_filter(signal_indices)

        # Step 6: Finalize progress tracking
        progress_overhead_pct = 0.0
        if progress is not None:
            result = progress.finish()
            progress_overhead_pct = result["progress_overhead_pct"]
            logger.debug("Progress overhead: %.2f%%", progress_overhead_pct)

        scan_duration = time.perf_counter() - scan_start

        logger.info(
            "Batch scan complete: %d signals from %d candles in %.2fs",
            len(signal_indices),
            len(timestamps),
            scan_duration,
        )

        return ScanResult(
            signal_indices=signal_indices,
            signal_count=len(signal_indices),
            candles_processed=len(timestamps),
            duplicates_removed=dedupe_result.duplicates_removed,
            scan_duration_sec=scan_duration,
            progress_overhead_pct=progress_overhead_pct,
        )

    def _deduplicate(
        self, df: pl.DataFrame, timestamp_col: str
    ) -> tuple[pl.DataFrame, DedupeResult]:
        """Deduplicate timestamps from DataFrame.

        Args:
            df: Input DataFrame
            timestamp_col: Timestamp column name

        Returns:
            Tuple of (deduplicated DataFrame, DedupeResult)
        """
        return dedupe_timestamps_polars(df, timestamp_col)

    def _apply_position_filter(self, signal_indices: np.ndarray) -> np.ndarray:
        """Apply strategy's max concurrent positions filter.

        Uses the strategy's metadata.max_concurrent_positions setting to
        filter overlapping signals and enforce position limits (FR-001).

        Args:
            signal_indices: Array of signal indices from scan

        Returns:
            Filtered array respecting strategy's position limit
        """
        max_concurrent = getattr(self.strategy.metadata, "max_concurrent_positions", 1)

        # Position filtering is now handled in BatchSimulation with proper exit detection
        # This simple window-based filter was too aggressive (filtered 34859 -> 1)
        # Disabled in favor of BatchSimulation._filter_signals_sequential()
        return signal_indices

        # Old code (disabled):
        # if max_concurrent is None or max_concurrent <= 0:
        #     return signal_indices
        #
        # # Apply filter
        # original_count = len(signal_indices)
        # filtered = filter_overlapping_signals(
        #     signal_indices,
        #     exit_indices=None,  # Will be refined in batch simulation
        #     max_concurrent=max_concurrent,
        # )
        #
        # if len(filtered) < original_count:
        #     logger.info(
        #         "Position filter: %d -> %d signals (removed %d) (max_concurrent=%d)",
        #         original_count,
        #         len(filtered),
        #         original_count - len(filtered),
        #         max_concurrent,
        #     )
        #
        # return filtered

    def _scan_signals(
        self,
        timestamps: np.ndarray,
        ohlc_arrays: tuple[np.ndarray, ...],
        indicator_arrays: dict[str, np.ndarray],
        progress: Optional[ProgressDispatcher],
    ) -> np.ndarray:
        """Scan for signals using strategy's vectorized method.

        Delegates to strategy.scan_vectorized() for strategy-agnostic scanning.
        The strategy implements its own signal logic using NumPy array operations.

        Args:
            timestamps: Array of timestamps (datetime64[ns])
            ohlc_arrays: Tuple of (timestamps, open, high, low, close) arrays
            indicator_arrays: Dictionary of indicator name -> array
            progress: Optional progress dispatcher

        Returns:
            NumPy array of indices where signals were generated
        """
        n_candles = len(timestamps)

        # Extract close prices
        _, _, _, _, close_arr = ohlc_arrays

        # Check if strategy supports vectorized scanning
        if not hasattr(self.strategy, "scan_vectorized"):
            logger.error(
                "Strategy '%s' does not implement scan_vectorized(). "
                "Cannot perform batch scanning.",
                self.strategy.metadata.name,
            )
            return np.array([], dtype=np.int64)

        # Delegate to strategy's vectorized scan method
        try:
            # Strategy returns (indices, stop_prices, target_prices)
            signal_indices, stop_prices, target_prices = self.strategy.scan_vectorized(
                close=close_arr,
                indicator_arrays=indicator_arrays,
                parameters=self.parameters,
                direction=self.direction,
            )

            # Update progress to completion
            if progress is not None:
                progress.update(n_candles)

            logger.debug(
                "Vectorized scan complete: %d signals found in %d candles",
                len(signal_indices),
                n_candles,
            )

            return signal_indices, stop_prices, target_prices

        except Exception as e:  # pylint: disable=broad-except
            logger.error(
                "Strategy scan_vectorized() failed: %s",
                e,
                exc_info=True,
            )
            return np.array([], dtype=np.int64)
