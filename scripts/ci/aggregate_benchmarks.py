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

import argparse
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any


def load_benchmarks(pattern: str = "benchmark_*.json") -> list[dict[str, Any]]:
    """Load all benchmark files matching pattern.

    Args:
        pattern: Glob pattern for benchmark files (default: benchmark_*.json)

    Returns:
        List of benchmark dictionaries
    """
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
        for phase in benchmark.get("phase_times", []):
            phase_name = phase.get("phase")
            duration = phase.get("duration_seconds")

            if phase_name and duration is not None:
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


if __name__ == "__main__":
    main()
