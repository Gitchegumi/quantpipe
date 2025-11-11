"""Stretch runtime artifact recorder for CI/CD pipelines.

Tracks stretch runtime metric (≤90s goal) for ingestion performance monitoring.
Reads latest benchmark results and updates/creates JSON artifact with baseline,
stretch target, and latest runtime measurements.

Usage:
    python scripts/ci/record_stretch_runtime.py [--input FILE] [--output FILE]

Examples:
    # Use default paths
    python scripts/ci/record_stretch_runtime.py

    # Custom benchmark input
    python scripts/ci/record_stretch_runtime.py \\
        --input results/benchmarks/ingestion_run_20241106.json

    # Custom artifact output
    python scripts/ci/record_stretch_runtime.py \\
        --output results/stretch_runtime.json

Artifact Schema (FR-027):
    {
        "baseline_seconds": 150.0,     # Original runtime before optimization
        "stretch_target_seconds": 90.0, # Target goal (≤90s)
        "latest_seconds": 120.5,       # Most recent measured runtime
        "updated_at": "2024-11-06T13:45:00Z"
    }

References:
    - FR-027: System SHOULD track stretch runtime metric (≤90s)
    - NFR-009: Benchmark artifacts stored under results/benchmarks/
    - Phase 6 T094 (Remediation Additions)
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def find_latest_benchmark(benchmark_dir: Path) -> Path | None:
    """Find the most recently created benchmark JSON file.

    Args:
        benchmark_dir: Directory containing benchmark files

    Returns:
        Path to latest benchmark file, or None if directory empty
    """
    benchmark_files = list(benchmark_dir.glob("ingestion_run_*.json"))
    if not benchmark_files:
        return None
    # Sort by modification time (most recent first)
    return max(benchmark_files, key=lambda p: p.stat().st_mtime)


def extract_runtime_from_benchmark(benchmark_path: Path) -> float:
    """Extract total runtime from benchmark JSON file.

    Args:
        benchmark_path: Path to benchmark JSON file

    Returns:
        Total runtime in seconds

    Raises:
        ValueError: If benchmark JSON format invalid or runtime missing
    """
    try:
        with benchmark_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Check for runtime_seconds field (FR-016 format)
        if "runtime_seconds" in data:
            return float(data["runtime_seconds"])

        # Fallback: check for phases array (legacy format)
        if "phases" in data and isinstance(data["phases"], list):
            total = sum(phase.get("duration_seconds", 0.0) for phase in data["phases"])
            if total > 0:
                return total

        msg = "No runtime data found in benchmark"
        raise ValueError(msg)

    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        msg = f"Invalid benchmark format: {benchmark_path.name} - {e!s}"
        raise ValueError(msg) from e



def load_stretch_artifact(artifact_path: Path) -> dict[str, Any]:
    """Load existing stretch runtime artifact or create default.

    Args:
        artifact_path: Path to stretch runtime JSON artifact

    Returns:
        Dictionary with baseline_seconds, stretch_target_seconds, latest_seconds
    """
    if artifact_path.exists():
        try:
            with artifact_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(
                f"Warning: Could not load existing artifact "
                f"({artifact_path.name}), creating new: {e!s}",
                file=sys.stderr,
            )


    # Default artifact (FR-027 schema)
    return {
        "baseline_seconds": None,  # Set on first run
        "stretch_target_seconds": 90.0,  # Per FR-027 (≤90s goal)
        "latest_seconds": None,
    }


def update_stretch_artifact(
    artifact: dict[str, Any], latest_runtime: float
) -> dict[str, Any]:
    """Update stretch runtime artifact with latest measurement.

    Args:
        artifact: Existing artifact dictionary
        latest_runtime: Latest runtime measurement in seconds

    Returns:
        Updated artifact dictionary
    """
    # Set baseline on first run (if not already set)
    if artifact["baseline_seconds"] is None:
        artifact["baseline_seconds"] = latest_runtime

    # Update latest runtime
    artifact["latest_seconds"] = latest_runtime

    # Add timestamp
    artifact["updated_at"] = datetime.now(UTC).isoformat()

    return artifact


def save_stretch_artifact(artifact_path: Path, artifact: dict[str, Any]) -> None:
    """Save stretch runtime artifact to JSON file.

    Args:
        artifact_path: Path to output artifact file
        artifact: Artifact dictionary to save
    """
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with artifact_path.open("w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2)
    print(f"Stretch runtime artifact updated: {artifact_path}")


def main(argv: list[str] | None = None) -> int:
    """Main entry point for stretch runtime recorder.

    Args:
        argv: Command-line arguments (default: sys.argv)

    Returns:
        Exit code (0 = success, non-zero = error)
    """
    parser = argparse.ArgumentParser(
        description="Record stretch runtime metric artifact (FR-027)"
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Path to benchmark JSON file (default: latest in results/benchmarks/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/stretch_runtime.json"),
        help="Path to stretch runtime artifact (default: results/stretch_runtime.json)",
    )

    args = parser.parse_args(argv)

    # Find input benchmark file
    if args.input:
        benchmark_path = args.input
        if not benchmark_path.exists():
            print(f"Error: Benchmark file not found: {benchmark_path}", file=sys.stderr)
            return 1
    else:
        # Find latest benchmark in results/benchmarks/
        benchmark_dir = Path("results/benchmarks")
        if not benchmark_dir.exists():
            print(
                f"Error: Benchmark directory not found: {benchmark_dir}",
                file=sys.stderr,
            )
            return 1
        benchmark_path = find_latest_benchmark(benchmark_dir)
        if benchmark_path is None:
            print(
                f"Error: No benchmark files found in {benchmark_dir}",
                file=sys.stderr,
            )
            return 1
        print(f"Using latest benchmark: {benchmark_path.name}")

    # Extract runtime from benchmark
    try:
        latest_runtime = extract_runtime_from_benchmark(benchmark_path)
        print(f"Latest runtime: {latest_runtime:.2f} seconds")
    except ValueError as e:
        print(f"Error: {e!s}", file=sys.stderr)
        return 1

    # Load existing artifact or create new
    artifact = load_stretch_artifact(args.output)

    # Update artifact with latest measurement
    artifact = update_stretch_artifact(artifact, latest_runtime)

    # Display summary
    print("\nStretch Runtime Summary:")
    baseline_str = (
        f"{artifact['baseline_seconds']:.2f}"
        if artifact["baseline_seconds"] is not None
        else "N/A"
    )
    print(f"  Baseline: {baseline_str} seconds")
    print(f"  Target: {artifact['stretch_target_seconds']:.2f} seconds")
    print(f"  Latest: {artifact['latest_seconds']:.2f} seconds")


    if artifact["baseline_seconds"] is not None:
        improvement = artifact["baseline_seconds"] - artifact["latest_seconds"]
        improvement_pct = (improvement / artifact["baseline_seconds"]) * 100
        print(f"  Improvement: {improvement:.2f} seconds ({improvement_pct:.1f}%)")

        if artifact["latest_seconds"] <= artifact["stretch_target_seconds"]:
            print("  ✓ Stretch target met!")
        else:
            remaining = artifact["latest_seconds"] - artifact["stretch_target_seconds"]
            print(f"  ⚠ {remaining:.2f} seconds above stretch target")

    # Save artifact
    try:
        save_stretch_artifact(args.output, artifact)
        return 0
    except OSError as e:
        print(f"Error: Could not save artifact: {e!s}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
