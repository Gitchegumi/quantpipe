"""Performance report model for benchmark tracking and reproducibility.

This module defines the PerformanceReport pydantic model used to capture
comprehensive performance metrics, dataset provenance, and equivalence validation
results for scan and simulation operations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PerformanceReport(BaseModel):
    """Comprehensive performance report for scan and simulation benchmarking.

    Captures timing metrics, memory usage, dataset provenance, progress tracking,
    and equivalence validation results to enable reproducible benchmarking and
    performance regression detection.

    Attributes:
        scan_duration_sec: Wall-clock time for scan phase (seconds)
        simulation_duration_sec: Wall-clock time for simulation phase (seconds)
        peak_memory_mb: Peak memory usage during execution (megabytes)
        manifest_path: Relative path to dataset manifest file
        manifest_sha256: SHA-256 checksum of manifest file
        candle_count: Total number of candles processed
        signal_count: Number of trade signals generated
        trade_count: Number of trades executed in simulation
        equivalence_verified: Whether results match baseline (True/False)
        progress_emission_count: Number of progress updates emitted
        progress_overhead_pct: Progress tracking overhead as % of total time
        indicator_names: Ordered list of indicator names used
        deterministic_mode: Whether run used deterministic configuration
        allocation_count_scan: Number of memory allocations during scan
        allocation_reduction_pct: % reduction in allocations vs baseline
        duplicate_timestamps_removed: Number of duplicate timestamps filtered
        duplicate_first_ts: First duplicate timestamp encountered (if any)
        duplicate_last_ts: Last duplicate timestamp encountered (if any)
        created_at: Report creation timestamp (UTC)
    """

    scan_duration_sec: float = Field(..., ge=0, description="Scan wall-clock time")
    simulation_duration_sec: float = Field(
        ..., ge=0, description="Simulation wall-clock time"
    )
    peak_memory_mb: float = Field(..., ge=0, description="Peak memory usage (MB)")
    manifest_path: str = Field(..., description="Relative path to manifest")
    manifest_sha256: str = Field(
        ..., min_length=64, max_length=64, description="Manifest SHA-256 checksum"
    )
    candle_count: int = Field(..., gt=0, description="Total candles processed")
    signal_count: int = Field(..., ge=0, description="Signals generated")
    trade_count: int = Field(..., ge=0, description="Trades executed")
    equivalence_verified: bool = Field(..., description="Baseline match confirmed")
    progress_emission_count: int = Field(
        ..., ge=0, description="Progress updates emitted"
    )
    progress_overhead_pct: Optional[float] = Field(
        default=None, ge=0, le=100, description="Progress overhead % of total time"
    )
    indicator_names: list[str] = Field(
        default_factory=list, description="Ordered indicator names"
    )
    deterministic_mode: bool = Field(
        default=False, description="Deterministic configuration used"
    )
    allocation_count_scan: Optional[int] = Field(
        default=None, ge=0, description="Memory allocations during scan"
    )
    allocation_reduction_pct: Optional[float] = Field(
        default=None, ge=0, le=100, description="Allocation reduction vs baseline"
    )
    duplicate_timestamps_removed: int = Field(
        default=0, ge=0, description="Duplicate timestamps filtered"
    )
    duplicate_first_ts: Optional[datetime] = Field(
        default=None, description="First duplicate timestamp"
    )
    duplicate_last_ts: Optional[datetime] = Field(
        default=None, description="Last duplicate timestamp"
    )
    created_at: datetime = Field(..., description="Report creation time (UTC)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "scan_duration_sec": 721.4,
                "simulation_duration_sec": 467.2,
                "peak_memory_mb": 1530.2,
                "manifest_path": "price_data/processed/eurusd/manifest.json",
                "manifest_sha256": "a" * 64,
                "candle_count": 6900000,
                "signal_count": 12345,
                "trade_count": 84938,
                "equivalence_verified": True,
                "progress_emission_count": 420,
                "progress_overhead_pct": 0.8,
                "indicator_names": ["ema_fast", "ema_slow", "atr"],
                "deterministic_mode": True,
                "allocation_count_scan": 156000,
                "allocation_reduction_pct": 72.5,
                "duplicate_timestamps_removed": 0,
                "duplicate_first_ts": None,
                "duplicate_last_ts": None,
                "created_at": "2025-11-11T12:00:00Z",
            }
        }
    )
