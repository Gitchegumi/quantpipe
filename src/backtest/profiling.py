"""Performance profiling and benchmark artifact generation.

This module provides phase timing instrumentation, hotspot extraction via
cProfile, and benchmark record writing for tracking performance metrics
across backtest runs.

Success criteria: SC-007 (100% runs), SC-008 (≥10 hotspots), SC-009 (memory ratio).
"""

# pylint: disable=unused-import

from typing import Dict, Any, Optional, List
import json
import time
import cProfile
import pstats
from pathlib import Path


class ProfilingContext:
    """Context manager for tracking phase timings and cProfile hotspots.

    Usage:
        with ProfilingContext() as profiler:
            profiler.start_phase("ingest")
            # ... data loading ...
            profiler.end_phase("ingest")
            
            # Get hotspots
            hotspots = profiler.get_hotspots(n=10)
    """

    def __init__(self, enable_cprofile: bool = True):
        """Initialize profiling context.
        
        Args:
            enable_cprofile: If True, enable cProfile hotspot extraction.
        """
        self._phase_times: Dict[str, float] = {}
        self._current_phase: Optional[str] = None
        self._phase_start: Optional[float] = None
        self._enable_cprofile = enable_cprofile
        self._profiler: Optional[cProfile.Profile] = None

    def __enter__(self):
        """Enter profiling context and start cProfile if enabled."""
        if self._enable_cprofile:
            self._profiler = cProfile.Profile()
            self._profiler.enable()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit profiling context and stop cProfile."""
        if self._current_phase:
            self.end_phase(self._current_phase)
        if self._profiler:
            self._profiler.disable()

    def start_phase(self, phase_name: str) -> None:
        """Start timing a phase.

        Args:
            phase_name: Name of the phase (e.g., "ingest", "scan", "simulate").
        """
        if self._current_phase:
            self.end_phase(self._current_phase)
        self._current_phase = phase_name
        self._phase_start = time.perf_counter()

    def end_phase(self, phase_name: str) -> None:
        """End timing a phase and record duration.

        Args:
            phase_name: Name of the phase being ended.
        """
        if self._phase_start is not None:
            duration = time.perf_counter() - self._phase_start
            self._phase_times[phase_name] = duration
            self._current_phase = None
            self._phase_start = None

    def get_phase_times(self) -> Dict[str, float]:
        """Retrieve recorded phase timings.

        Returns:
            Dictionary mapping phase names to durations in seconds.
        """
        return self._phase_times.copy()

    def get_hotspots(self, n: int = 10) -> List[Dict[str, Any]]:
        """Extract top N hotspots from cProfile data.
        
        Args:
            n: Number of top hotspots to return (default 10).
            
        Returns:
            List of dictionaries with hotspot data:
                - function: Function name
                - filename: Source file
                - lineno: Line number
                - ncalls: Number of calls
                - tottime: Total time in function (excluding subcalls)
                - cumtime: Cumulative time (including subcalls)
                - percall_tot: Time per call (tottime/ncalls)
                - percall_cum: Time per call (cumtime/ncalls)
        """
        if not self._profiler:
            return []
        
        # Create stats object
        stats = pstats.Stats(self._profiler)
        stats.strip_dirs()
        stats.sort_stats('cumulative')
        
        # Extract hotspot data
        hotspots = []
        for func, (_, nc, tt, ct, _) in list(stats.stats.items())[:n]:
            filename, lineno, func_name = func
            hotspots.append({
                "function": func_name,
                "filename": filename,
                "lineno": lineno,
                "ncalls": nc,
                "tottime": tt,
                "cumtime": ct,
                "percall_tot": tt / nc if nc > 0 else 0.0,
                "percall_cum": ct / nc if nc > 0 else 0.0,
            })
        
        return hotspots


def write_benchmark_record(
    output_path: Path,
    dataset_rows: int,
    trades_simulated: int,
    phase_times: Dict[str, float],
    wall_clock_total: float,
    memory_peak_mb: float,
    memory_ratio: float,
    **kwargs,
) -> None:
    """Write benchmark record to JSON file.

    Args:
        output_path: Path to write benchmark JSON.
        dataset_rows: Number of dataset rows processed.
        trades_simulated: Number of trades simulated.
        phase_times: Dictionary of phase name -> duration (seconds).
                     Common phases: "ingest", "scan", "simulate".
        wall_clock_total: Total wall-clock time (seconds).
        memory_peak_mb: Peak memory usage in MB.
        memory_ratio: peak_bytes / raw_dataset_bytes.
        **kwargs: Additional metadata fields. Common fields:
                 - fraction (float): Dataset fraction used (0.0-1.0)
                 - parallel_efficiency (float): Parallel speedup / num_workers (0.0-1.0)
                 - hotspots (List[Dict]): cProfile hotspot data
                 - custom fields as needed
    
    Examples:
        >>> write_benchmark_record(
        ...     output_path=Path("benchmark.json"),
        ...     dataset_rows=1000000,
        ...     trades_simulated=500,
        ...     phase_times={"ingest": 10.0, "scan": 30.0, "simulate": 15.0},
        ...     wall_clock_total=55.0,
        ...     memory_peak_mb=512.0,
        ...     memory_ratio=1.3,
        ...     parallel_efficiency=0.85,
        ...     fraction=0.5,
        ... )
    """
    record = {
        "dataset_rows": dataset_rows,
        "trades_simulated": trades_simulated,
        "phase_times": phase_times,
        "wall_clock_total": wall_clock_total,
        "memory_peak_mb": memory_peak_mb,
        "memory_ratio": memory_ratio,
        **kwargs,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
