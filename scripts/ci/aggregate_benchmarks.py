"""Benchmark aggregation utility for CI/CD pipelines.

Aggregates multiple benchmark JSON files from results/ directory and produces
summary statistics (mean, median, min, max) for phase timings, trade counts,
and memory metrics.

Usage:
    python scripts/ci/aggregate_benchmarks.py [--pattern GLOB] [--output FILE]

Examples:
    # Aggregate all benchmarks
    python scripts/ci/aggregate_benchmarks.py

    # Aggregate specific pattern
    python scripts/ci/aggregate_benchmarks.py --pattern "benchmark_*_long_*.json"

    # Write to custom output
    python scripts/ci/aggregate_benchmarks.py --output summary.json

References:
    - Phase 6 T050 (Polish & Cross-Cutting)
    - docs/performance.md (benchmark JSON schema)
"""

# pylint: disable=line-too-long

import argparse
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def load_benchmarks(pattern: str = "benchmark_*.json") -> list[dict[str, Any]]:
    """Load all benchmark files matching pattern.

    Args:
        pattern: Glob pattern for benchmark files (default: benchmark_*.json)
                Can be absolute path pattern or relative to results/ directory.

    Returns:
        List of benchmark dictionaries
    """
    # Check if pattern contains directory separators (absolute or relative path)
    pattern_path = Path(pattern)

    if pattern_path.is_absolute() or (
        len(pattern_path.parts) > 1 and pattern_path.parts[0] != "results"
    ):
        # Absolute path or path with directory: glob from parent directory
        parent_dir = pattern_path.parent
        glob_pattern = pattern_path.name

        if not parent_dir.exists():
            return []

        benchmarks = []
        for filepath in parent_dir.glob(glob_pattern):
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                    benchmarks.append(data)
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Failed to load {filepath}: {e}")
        return benchmarks
    else:
        # Relative pattern: use results/ directory
        results_dir = Path("results")
        if not results_dir.exists():
            return []

        benchmarks = []
        for filepath in results_dir.glob(pattern):
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                    benchmarks.append(data)
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Failed to load {filepath}: {e}")

        return benchmarks


def aggregate_phase_times(
    benchmarks: list[dict[str, Any]],
) -> dict[str, dict[str, float]]:
    """Aggregate phase timing statistics.

    Args:
        benchmarks: List of benchmark dictionaries

    Returns:
        Dictionary with phase names as keys, stats as values
        Example: {"ingest": {"mean": 1.23, "median": 1.20, ...}, ...}
    """
    # Collect phase times grouped by phase name
    phase_data: dict[str, list[float]] = {}

    for benchmark in benchmarks:
        phase_times_dict = benchmark.get("phase_times", {})

        # phase_times is a dict: {"ingest": 1.5, "scan": 2.0, ...}
        if isinstance(phase_times_dict, dict):
            for phase_name, duration in phase_times_dict.items():
                if phase_name not in phase_data:
                    phase_data[phase_name] = []
                phase_data[phase_name].append(duration)

    # Calculate statistics for each phase
    stats = {}
    for phase_name, durations in phase_data.items():
        if durations:
            stats[phase_name] = {
                "mean": statistics.mean(durations),
                "median": statistics.median(durations),
                "min": min(durations),
                "max": max(durations),
                "count": len(durations),
            }

    return stats


def aggregate_trade_counts(benchmarks: list[dict[str, Any]]) -> dict[str, float]:
    """Aggregate trade count statistics.

    Args:
        benchmarks: List of benchmark dictionaries

    Returns:
        Dictionary with trade count statistics
    """
    trade_counts = [b.get("trades", 0) for b in benchmarks if "trades" in b]

    if not trade_counts:
        return {}

    return {
        "mean": statistics.mean(trade_counts),
        "median": statistics.median(trade_counts),
        "min": min(trade_counts),
        "max": max(trade_counts),
        "count": len(trade_counts),
    }


def aggregate_memory_metrics(benchmarks: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate memory usage statistics.

    Args:
        benchmarks: List of benchmark dictionaries

    Returns:
        Dictionary with memory statistics and threshold violation counts
    """
    memory_ratios = []
    threshold_violations = 0

    for benchmark in benchmarks:
        ratio = benchmark.get("memory_ratio")
        if ratio is not None:
            memory_ratios.append(ratio)

        if benchmark.get("memory_threshold_exceeded", False):
            threshold_violations += 1

    if not memory_ratios:
        return {}

    return {
        "ratio_mean": statistics.mean(memory_ratios),
        "ratio_median": statistics.median(memory_ratios),
        "ratio_min": min(memory_ratios),
        "ratio_max": max(memory_ratios),
        "threshold_violations": threshold_violations,
        "total_runs": len(benchmarks),
    }


def aggregate_benchmarks(pattern: str = "benchmark_*.json") -> dict[str, Any]:
    """Aggregate all benchmark files into summary statistics.

    Args:
        pattern: Glob pattern for benchmark files

    Returns:
        Aggregated summary dictionary
    """
    benchmarks = load_benchmarks(pattern)

    if not benchmarks:
        return {
            "error": "No benchmark files found",
            "pattern": pattern,
            "timestamp": datetime.now().isoformat(),
        }

    summary = {
        "summary_timestamp": datetime.now().isoformat(),
        "benchmark_count": len(benchmarks),
        "phase_times": aggregate_phase_times(benchmarks),
        "trade_counts": aggregate_trade_counts(benchmarks),
        "memory_metrics": aggregate_memory_metrics(benchmarks),
    }

    # T049: Add Spec 010 scan/simulation specific metrics
    scan_durations = [
        b.get("phase_times", {}).get("scan", 0)
        for b in benchmarks
        if "phase_times" in b and "scan" in b.get("phase_times", {})
    ]
    sim_durations = [
        b.get("phase_times", {}).get("simulate", 0)
        for b in benchmarks
        if "phase_times" in b and "simulate" in b.get("phase_times", {})
    ]

    if scan_durations:
        summary["scan_performance"] = {
            "mean": statistics.mean(scan_durations),
            "median": statistics.median(scan_durations),
            "min": min(scan_durations),
            "max": max(scan_durations),
            "target": 720.0,  # SCAN_MAX_SECONDS from Spec 010
            "target_met": all(d <= 720.0 for d in scan_durations),
        }

    if sim_durations:
        summary["simulation_performance"] = {
            "mean": statistics.mean(sim_durations),
            "median": statistics.median(sim_durations),
            "min": min(sim_durations),
            "max": max(sim_durations),
            "target": 480.0,  # SIM_MAX_SECONDS from Spec 010
            "target_met": all(d <= 480.0 for d in sim_durations),
        }

    # Calculate overall speedup if baseline is available
    for benchmark in benchmarks:
        if "baseline_runtime" in benchmark:
            baseline = benchmark["baseline_runtime"]
            current = benchmark.get("wall_clock_total", 0)
            if baseline > 0:
                speedup = baseline / current
                if "speedup_metrics" not in summary:
                    summary["speedup_metrics"] = []
                summary["speedup_metrics"].append(speedup)

    if "speedup_metrics" in summary and summary["speedup_metrics"]:
        summary["speedup_summary"] = {
            "mean_speedup": statistics.mean(summary["speedup_metrics"]),
            "median_speedup": statistics.median(summary["speedup_metrics"]),
            "min_speedup": min(summary["speedup_metrics"]),
            "max_speedup": max(summary["speedup_metrics"]),
        }
        del summary["speedup_metrics"]  # Remove raw list, keep summary only

    return summary


def main() -> None:
    """Main entry point for benchmark aggregation."""
    parser = argparse.ArgumentParser(
        description="Aggregate benchmark JSON files into summary statistics"
    )
    parser.add_argument(
        "--pattern",
        default="benchmark_*.json",
        help="Glob pattern for benchmark files (default: benchmark_*.json)",
    )
    parser.add_argument(
        "--output",
        default="results/benchmark_summary.json",
        help="Output file path (default: results/benchmark_summary.json)",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit with error code if benchmarks fail success criteria (T071, FR-014)",
    )
    parser.add_argument(
        "--runtime-threshold",
        type=float,
        default=1200.0,
        help="Maximum runtime in seconds (default: 1200s = 20 min, SC-001)",
    )
    parser.add_argument(
        "--memory-threshold",
        type=float,
        default=1.5,
        help="Maximum memory ratio multiplier (default: 1.5, SC-009)",
    )
    parser.add_argument(
        "--scan-threshold",
        type=float,
        default=720.0,
        help="Maximum scan duration in seconds (default: 720s, Spec 010)",
    )
    parser.add_argument(
        "--simulation-threshold",
        type=float,
        default=480.0,
        help="Maximum simulation duration in seconds (default: 480s, Spec 010)",
    )

    args = parser.parse_args()

    # Aggregate benchmarks
    summary = aggregate_benchmarks(args.pattern)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Benchmark summary written to {output_path}")
    print(f"Aggregated {summary.get('benchmark_count', 0)} benchmark files")

    # T071: CI gate regression check (FR-014)
    if args.fail_on_regression:
        benchmarks = load_benchmarks(args.pattern)
        failures = []

        for benchmark in benchmarks:
            # Check success_criteria_passed flag if present (new schema)
            if "success_criteria_passed" in benchmark:
                if not benchmark["success_criteria_passed"]:
                    failures.append(
                        f"Benchmark failed success criteria: "
                        f"runtime_passed={benchmark.get('runtime_passed')}, "
                        f"memory_passed={benchmark.get('memory_passed')}, "
                        f"hotspot_count_passed={benchmark.get('hotspot_count_passed')}, "
                        f"parallel_efficiency_passed={benchmark.get('parallel_efficiency_passed')}"
                    )
            else:
                # Fallback: manual threshold checks for older schema
                runtime = benchmark.get("wall_clock_total", 0)
                memory_ratio = benchmark.get("memory_ratio", 0)

                if runtime > args.runtime_threshold:
                    failures.append(
                        f"Runtime exceeds threshold: {runtime:.1f}s > {args.runtime_threshold}s (SC-001)"
                    )

                if memory_ratio > args.memory_threshold:
                    failures.append(
                        f"Memory ratio exceeds threshold: {memory_ratio:.2f}× > {args.memory_threshold}× (SC-009)"
                    )

            # T049: Check Spec 010 scan/simulation targets
            phase_times = benchmark.get("phase_times", {})
            scan_time = phase_times.get("scan", 0)
            sim_time = phase_times.get("simulate", 0)

            if scan_time > args.scan_threshold:
                failures.append(
                    f"Scan duration exceeds threshold: {scan_time:.1f}s > {args.scan_threshold}s (Spec 010)"
                )

            if sim_time > args.simulation_threshold:
                failures.append(
                    f"Simulation duration exceeds threshold: {sim_time:.1f}s > {args.simulation_threshold}s (Spec 010)"
                )

        if failures:
            print("\n[FAIL] BENCHMARK REGRESSION DETECTED:")
            for failure in failures:
                print(f"  - {failure}")
            sys.exit(1)  # Fail CI pipeline
        else:
            print("\n[PASS] All benchmarks passed success criteria")

    # T049: Print Spec 010 summary if available
    if "scan_performance" in summary or "simulation_performance" in summary:
        print("\n=== Spec 010 Performance Summary ===")
        if "scan_performance" in summary:
            scan_perf = summary["scan_performance"]
            print(
                f"Scan: mean={scan_perf['mean']:.1f}s, "
                f"median={scan_perf['median']:.1f}s, "
                f"target={scan_perf['target']:.1f}s, "
                f"met={scan_perf['target_met']}"
            )
        if "simulation_performance" in summary:
            sim_perf = summary["simulation_performance"]
            print(
                f"Simulation: mean={sim_perf['mean']:.1f}s, "
                f"median={sim_perf['median']:.1f}s, "
                f"target={sim_perf['target']:.1f}s, "
                f"met={sim_perf['target_met']}"
            )
        if "speedup_summary" in summary:
            speedup = summary["speedup_summary"]
            print(
                f"Speedup: mean={speedup['mean_speedup']:.2f}×, "
                f"median={speedup['median_speedup']:.2f}×"
            )


if __name__ == "__main__":
    main()
