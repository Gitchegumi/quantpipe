"""Performance profiling and benchmark artifact generation.

This module provides phase timing instrumentation, hotspot extraction via
cProfile, and benchmark record writing for tracking performance metrics
across backtest runs.

Success criteria: SC-007 (100% runs), SC-008 (≥10 hotspots), SC-009 (memory ratio).
"""

from typing import Dict, Any, Optional
import json
import time
from pathlib import Path


class ProfilingContext:
    """Context manager for tracking phase timings.
    
    Usage:
        with ProfilingContext() as profiler:
            profiler.start_phase("ingest")
            # ... data loading ...
            profiler.end_phase("ingest")
    """
    
    def __init__(self):
        """Initialize profiling context."""
        self._phase_times: Dict[str, float] = {}
        self._current_phase: Optional[str] = None
        self._phase_start: Optional[float] = None
    
    def __enter__(self):
        """Enter profiling context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit profiling context."""
        if self._current_phase:
            self.end_phase(self._current_phase)
    
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


def write_benchmark_record(
    output_path: Path,
    dataset_rows: int,
    trades_simulated: int,
    phase_times: Dict[str, float],
    wall_clock_total: float,
    memory_peak_mb: float,
    memory_ratio: float,
    **kwargs
) -> None:
    """Write benchmark record to JSON file.
    
    Args:
        output_path: Path to write benchmark JSON.
        dataset_rows: Number of dataset rows processed.
        trades_simulated: Number of trades simulated.
        phase_times: Dictionary of phase name -> duration (seconds).
        wall_clock_total: Total wall-clock time (seconds).
        memory_peak_mb: Peak memory usage in MB.
        memory_ratio: peak_bytes / raw_dataset_bytes.
        **kwargs: Additional metadata fields (e.g., fraction, parallel_efficiency).
    """
    record = {
        "dataset_rows": dataset_rows,
        "trades_simulated": trades_simulated,
        "phase_times": phase_times,
        "wall_clock_total": wall_clock_total,
        "memory_peak_mb": memory_peak_mb,
        "memory_ratio": memory_ratio,
        **kwargs
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
