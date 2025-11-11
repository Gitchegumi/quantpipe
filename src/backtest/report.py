"""Performance report generation and aggregation.

This module consolidates scan and simulation metrics into a structured
PerformanceReport for reproducible benchmarking and performance tracking.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from src.backtest.batch_scan import ScanResult
from src.backtest.batch_simulation import SimulationResult
from src.models.performance_report import PerformanceReport


logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate comprehensive performance reports from scan and simulation results."""

    def __init__(
        self,
        manifest_path: str,
        manifest_sha256: str,
        deterministic_mode: bool = False,
    ):
        """Initialize report generator.

        Args:
            manifest_path: Relative path to dataset manifest file
            manifest_sha256: SHA-256 checksum of manifest file
            deterministic_mode: Whether run used deterministic configuration
        """
        self.manifest_path = manifest_path
        self.manifest_sha256 = manifest_sha256
        self.deterministic_mode = deterministic_mode

    def generate_report(
        self,
        scan_result: ScanResult,
        sim_result: SimulationResult,
        candle_count: int,
        equivalence_verified: bool = False,
        indicator_names: Optional[list[str]] = None,
        duplicate_timestamps_removed: int = 0,
        duplicate_first_ts: Optional[datetime] = None,
        duplicate_last_ts: Optional[datetime] = None,
        allocation_count_scan: Optional[int] = None,
        allocation_reduction_pct: Optional[float] = None,
    ) -> PerformanceReport:
        """Generate performance report from scan and simulation results.

        Args:
            scan_result: Result of batch scan operation
            sim_result: Result of batch simulation operation
            candle_count: Total number of candles processed
            equivalence_verified: Whether results match baseline
            indicator_names: Ordered list of indicator names used
            duplicate_timestamps_removed: Number of duplicate timestamps filtered
            duplicate_first_ts: First duplicate timestamp encountered
            duplicate_last_ts: Last duplicate timestamp encountered
            allocation_count_scan: Number of memory allocations during scan
            allocation_reduction_pct: Allocation reduction vs baseline

        Returns:
            PerformanceReport with aggregated metrics
        """
        # Calculate total progress overhead
        total_duration = (
            scan_result.scan_duration_sec + sim_result.simulation_duration_sec
        )
        scan_overhead = scan_result.progress_overhead_sec
        sim_overhead = (
            sim_result.simulation_duration_sec * sim_result.progress_overhead_pct / 100
        )
        total_overhead = scan_overhead + sim_overhead
        total_overhead_pct = (
            (total_overhead / total_duration * 100) if total_duration > 0 else 0.0
        )

        # Calculate peak memory (placeholder: use scan peak for now)
        # In production, this should aggregate across both phases
        peak_memory_mb = 0.0  # Placeholder: to be implemented with memory tracking

        # Calculate progress emission count
        progress_emission_count = 0  # Placeholder: sum of progress updates

        report = PerformanceReport(
            scan_duration_sec=scan_result.scan_duration_sec,
            simulation_duration_sec=sim_result.simulation_duration_sec,
            peak_memory_mb=peak_memory_mb,
            manifest_path=self.manifest_path,
            manifest_sha256=self.manifest_sha256,
            candle_count=candle_count,
            signal_count=scan_result.signal_count,
            trade_count=sim_result.trade_count,
            equivalence_verified=equivalence_verified,
            progress_emission_count=progress_emission_count,
            progress_overhead_pct=total_overhead_pct,
            indicator_names=indicator_names or [],
            deterministic_mode=self.deterministic_mode,
            allocation_count_scan=allocation_count_scan,
            allocation_reduction_pct=allocation_reduction_pct,
            duplicate_timestamps_removed=duplicate_timestamps_removed,
            duplicate_first_ts=duplicate_first_ts,
            duplicate_last_ts=duplicate_last_ts,
            created_at=datetime.now(timezone.utc),
        )

        logger.info(
            "Generated performance report: scan=%.2fs, sim=%.2fs, signals=%d, trades=%d",
            report.scan_duration_sec,
            report.simulation_duration_sec,
            report.signal_count,
            report.trade_count,
        )

        return report


def create_report(
    scan_result: ScanResult,
    sim_result: SimulationResult,
    candle_count: int,
    manifest_path: str,
    manifest_sha256: str,
    equivalence_verified: bool = False,
    indicator_names: Optional[list[str]] = None,
    deterministic_mode: bool = False,
    duplicate_timestamps_removed: int = 0,
    duplicate_first_ts: Optional[datetime] = None,
    duplicate_last_ts: Optional[datetime] = None,
    allocation_count_scan: Optional[int] = None,
    allocation_reduction_pct: Optional[float] = None,
) -> PerformanceReport:
    """Convenience function to create a performance report.

    Args:
        scan_result: Result of batch scan operation
        sim_result: Result of batch simulation operation
        candle_count: Total number of candles processed
        manifest_path: Relative path to dataset manifest file
        manifest_sha256: SHA-256 checksum of manifest file
        equivalence_verified: Whether results match baseline
        indicator_names: Ordered list of indicator names used
        deterministic_mode: Whether run used deterministic configuration
        duplicate_timestamps_removed: Number of duplicate timestamps filtered
        duplicate_first_ts: First duplicate timestamp encountered
        duplicate_last_ts: Last duplicate timestamp encountered
        allocation_count_scan: Number of memory allocations during scan
        allocation_reduction_pct: Allocation reduction vs baseline

    Returns:
        PerformanceReport with aggregated metrics
    """
    generator = ReportGenerator(
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha256,
        deterministic_mode=deterministic_mode,
    )

    return generator.generate_report(
        scan_result=scan_result,
        sim_result=sim_result,
        candle_count=candle_count,
        equivalence_verified=equivalence_verified,
        indicator_names=indicator_names,
        duplicate_timestamps_removed=duplicate_timestamps_removed,
        duplicate_first_ts=duplicate_first_ts,
        duplicate_last_ts=duplicate_last_ts,
        allocation_count_scan=allocation_count_scan,
        allocation_reduction_pct=allocation_reduction_pct,
    )
