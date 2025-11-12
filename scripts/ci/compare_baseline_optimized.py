"""Performance comparison script for baseline vs optimized backtest paths.

This script compares execution time, memory usage, and throughput between
the legacy baseline path and the optimized BatchScan/BatchSimulation path
to measure actual speedup achieved by Feature 010 optimizations.

Usage:
    python scripts/ci/compare_baseline_optimized.py \\
        --data path/to/data.csv \\
        --direction LONG \\
        --data-frac 0.01

Requirements:
    - Both baseline and optimized paths functional
    - PerformanceReport emission enabled
    - Sufficient data for meaningful comparison

Performance Targets (Feature 010):
    - Scan: ≥50% speedup (FR-001: ≤12 min on 6.9M candles)
    - Simulation: ≥55% speedup (FR-001: ≤8 min on ~84,938 trades)
    - Memory: ≥30% reduction (FR-005)
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional


logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)-8s %(message)s"
)
logger = logging.getLogger(__name__)


def run_backtest(
    data_path: str,
    direction: str,
    data_frac: float,
    emit_perf_report: bool = False,
    use_legacy: bool = False,
) -> tuple[float, Optional[Path]]:
    """Run a single backtest and return duration and performance report path.

    Args:
        data_path: Path to price data CSV
        direction: Direction mode (LONG, SHORT, BOTH)
        data_frac: Data fraction to use
        emit_perf_report: Whether to emit PerformanceReport
        use_legacy: Force legacy Candle-based path (placeholder for future)

    Returns:
        Tuple of (duration_seconds, report_path)
    """
    cmd = [
        "poetry",
        "run",
        "python",
        "-m",
        "src.cli.run_backtest",
        "--data",
        data_path,
        "--direction",
        direction,
        "--data-frac",
        str(data_frac),
    ]

    if emit_perf_report:
        cmd.append("--emit-perf-report")

    logger.info("Running backtest: %s", " ".join(cmd))

    start_time = datetime.now(UTC)
    # Use echo to provide portion index input
    result = subprocess.run(
        ["powershell", "-Command", f"echo 1 | {' '.join(cmd)}"],
        capture_output=True,
        text=True,
        check=False,
    )
    end_time = datetime.now(UTC)

    if result.returncode != 0:
        logger.error("Backtest failed with exit code %d", result.returncode)
        logger.error("STDERR: %s", result.stderr)
        raise RuntimeError(f"Backtest failed: {result.stderr}")

    duration = (end_time - start_time).total_seconds()

    # Extract performance report path if emitted
    report_path = None
    if emit_perf_report:
        for line in result.stdout.split("\\n"):
            if "Performance report:" in line:
                # Extract path from line like "Performance report: results/..."
                report_path = Path(line.split("Performance report:")[-1].strip())
                break

    return duration, report_path


def load_performance_report(report_path: Path) -> dict:
    """Load PerformanceReport JSON.

    Args:
        report_path: Path to performance report JSON

    Returns:
        Dictionary with report data
    """
    with open(report_path, encoding="utf-8") as f:
        return json.load(f)


def calculate_speedup(baseline_duration: float, optimized_duration: float) -> float:
    """Calculate speedup percentage.

    Args:
        baseline_duration: Baseline execution time (seconds)
        optimized_duration: Optimized execution time (seconds)

    Returns:
        Speedup percentage (e.g., 50.0 for 50% faster)
    """
    if baseline_duration == 0:
        return 0.0
    return ((baseline_duration - optimized_duration) / baseline_duration) * 100.0


def main():
    """Main comparison script."""
    parser = argparse.ArgumentParser(
        description="Compare baseline vs optimized backtest performance"
    )
    parser.add_argument(
        "--data", required=True, help="Path to price data CSV file"
    )
    parser.add_argument(
        "--direction",
        required=True,
        choices=["LONG", "SHORT", "BOTH"],
        help="Direction mode for backtest",
    )
    parser.add_argument(
        "--data-frac",
        type=float,
        default=0.01,
        help="Data fraction to use (default: 0.01)",
    )
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help="Run baseline only (skip optimized)",
    )
    parser.add_argument(
        "--optimized-only",
        action="store_true",
        help="Run optimized only (skip baseline)",
    )

    args = parser.parse_args()

    logger.info("Starting performance comparison")
    logger.info("Data: %s", args.data)
    logger.info("Direction: %s", args.direction)
    logger.info("Data fraction: %.2f", args.data_frac)

    results = {}

    # Run baseline (legacy Candle-based path)
    # NOTE: Currently we don't have a way to force legacy path,
    # so this comparison is placeheld for when that becomes available
    if not args.optimized_only:
        logger.info("Running BASELINE backtest...")
        logger.warning(
            "Baseline comparison not yet implemented - "
            "requires mechanism to force legacy Candle path"
        )
        # Placeholder: baseline_duration, baseline_report = run_backtest(...)
        # results["baseline"] = {...}

    # Run optimized (BatchScan/BatchSimulation path)
    if not args.baseline_only:
        logger.info("Running OPTIMIZED backtest...")
        optimized_duration, optimized_report = run_backtest(
            data_path=args.data,
            direction=args.direction,
            data_frac=args.data_frac,
            emit_perf_report=True,
            use_legacy=False,
        )

        logger.info("Optimized backtest completed in %.2fs", optimized_duration)

        if optimized_report and optimized_report.exists():
            opt_data = load_performance_report(optimized_report)
            results["optimized"] = {
                "duration": optimized_duration,
                "scan_duration": opt_data.get("scan_duration_sec", 0.0),
                "simulation_duration": opt_data.get("simulation_duration_sec", 0.0),
                "peak_memory_mb": opt_data.get("peak_memory_mb", 0.0),
                "candle_count": opt_data.get("candle_count", 0),
                "signal_count": opt_data.get("signal_count", 0),
                "trade_count": opt_data.get("trade_count", 0),
            }
        else:
            logger.warning("No performance report found for optimized run")
            results["optimized"] = {"duration": optimized_duration}

    # Calculate and display comparison
    print("\\n" + "=" * 60)
    print("PERFORMANCE COMPARISON RESULTS")
    print("=" * 60)

    if "baseline" in results and "optimized" in results:
        baseline_dur = results["baseline"]["duration"]
        optimized_dur = results["optimized"]["duration"]
        speedup = calculate_speedup(baseline_dur, optimized_dur)

        print(f"\\nBaseline duration:  {baseline_dur:.2f}s")
        print(f"Optimized duration: {optimized_dur:.2f}s")
        print(f"Speedup:            {speedup:+.1f}%")
        print(f"Target:             ≥50.0% (FR-001)")

        if speedup >= 50.0:
            print("\\n✓ TARGET MET")
        else:
            print("\\n✗ TARGET NOT MET")
    elif "optimized" in results:
        print("\\nOptimized Results:")
        print(f"  Duration:       {results['optimized']['duration']:.2f}s")
        if "candle_count" in results["optimized"]:
            print(f"  Candles:        {results['optimized']['candle_count']:,}")
            print(f"  Signals:        {results['optimized']['signal_count']:,}")
            print(f"  Trades:         {results['optimized']['trade_count']:,}")
        print("\\n(Baseline comparison pending legacy path isolation)")
    else:
        print("\\nNo results to display")

    print("=" * 60)

    # Write results to JSON
    output_path = Path("results/performance_comparison.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "data_path": args.data,
                "direction": args.direction,
                "data_frac": args.data_frac,
                "results": results,
            },
            f,
            indent=2,
        )
    logger.info("Comparison results written to %s", output_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
