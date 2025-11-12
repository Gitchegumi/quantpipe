"""Allocation profiling harness for scan performance benchmarking.

This script captures memory allocation counts during scan operations
to establish baselines and measure optimization effectiveness
(FR-002, FR-014).

Usage:
    python scripts/ci/profile_scan_allocations.py \
        --dataset <path> --mode <baseline|optimized>

Features:
- Captures tracemalloc snapshots during scan
- Computes allocation count per million candles
- Emits JSON report with allocation metrics
- Compares baseline vs optimized runs

Output:
    allocation_profile.json with fields:
    - mode: "baseline" or "optimized"
    - total_allocations: total allocation count
    - candles_processed: number of candles
    - allocations_per_million: normalized allocation rate
    - peak_memory_mb: peak memory usage
    - timestamp: profile capture time
"""
# pylint: disable=unused-variable
# Justification:
# - unused-variable: result variable used for scan side effects

import argparse
import json
import logging
import sys
import tracemalloc
from datetime import UTC, datetime
from pathlib import Path

import polars as pl


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backtest.batch_scan import BatchScan


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_mock_strategy():
    """Create mock strategy for profiling."""

    class MockMetadata:
        """Mock strategy metadata."""

        name = "profile_strategy"
        version = "1.0.0"
        required_indicators = ["ema20", "ema50", "atr14"]

    class MockStrategy:
        """Mock strategy for allocation profiling."""

        @property
        def metadata(self):
            """Return mock metadata."""
            return MockMetadata()

        def generate_signals(self, candles, parameters):  # pylint: disable=unused-argument
            """Mock signal generation.
            
            Args:
                candles: Input candles (unused - rule-based generation)
                parameters: Strategy parameters (unused - no parameter dependency)
            """
            # Simple rule: signal every 100th candle
            return list(range(0, len(candles), 100))

    return MockStrategy()


def profile_scan_allocations(dataset_path: str, mode: str) -> dict:
    """Profile memory allocations during scan operation.

    Args:
        dataset_path: Path to Parquet dataset file
        mode: "baseline" or "optimized"

    Returns:
        Dictionary with allocation profile metrics
    """
    logger.info("Loading dataset: %s", dataset_path)
    df = pl.read_parquet(dataset_path)
    candles_processed = len(df)

    logger.info(
        "Starting allocation profiling for %d candles (mode=%s)",
        candles_processed,
        mode,
    )

    # Start tracemalloc
    tracemalloc.start()

    # Create scanner and run scan
    strategy = create_mock_strategy()
    scanner = BatchScan(strategy=strategy, enable_progress=False)

    logger.info("Running scan...")
    result = scanner.scan(df)

    # Capture allocation snapshot
    snapshot = tracemalloc.take_snapshot()
    current_memory, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Calculate allocation statistics
    total_allocations = len(snapshot.statistics("lineno"))
    allocations_per_million = (total_allocations / candles_processed) * 1_000_000
    peak_memory_mb = peak_memory / (1024 * 1024)

    logger.info("Scan completed: %d signals generated", result.signal_count)
    logger.info("Total allocations: %d", total_allocations)
    logger.info("Allocations per million candles: %.0f", allocations_per_million)
    logger.info("Peak memory: %.2f MB", peak_memory_mb)

    # Build profile report
    return {
        "mode": mode,
        "total_allocations": total_allocations,
        "candles_processed": candles_processed,
        "allocations_per_million": round(allocations_per_million, 2),
        "peak_memory_mb": round(peak_memory_mb, 2),
        "signal_count": result.signal_count,
        "scan_duration_sec": round(result.scan_duration_sec, 3),
        "timestamp": datetime.now(UTC).isoformat(),
    }



def main():
    """Main entry point for allocation profiling script."""
    parser = argparse.ArgumentParser(
        description="Profile memory allocations during scan operations"
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to Parquet dataset file",
    )
    parser.add_argument(
        "--mode",
        choices=["baseline", "optimized"],
        required=True,
        help="Profiling mode: baseline or optimized",
    )
    parser.add_argument(
        "--output",
        default="allocation_profile.json",
        help="Output JSON file path (default: allocation_profile.json)",
    )

    args = parser.parse_args()

    # Validate dataset exists
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        logger.error("Dataset file not found: %s", args.dataset)
        sys.exit(1)

    # Run profiling
    try:
        profile = profile_scan_allocations(str(dataset_path), args.mode)

        # Write output
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)

        logger.info("Profile saved to: %s", output_path)

        # If this is an optimized run, check for existing baseline and compute reduction
        if args.mode == "optimized":
            baseline_path = output_path.parent / "allocation_profile_baseline.json"
            if baseline_path.exists():
                with open(baseline_path, encoding="utf-8") as f:
                    baseline = json.load(f)

                baseline_allocations = baseline["allocations_per_million"]
                optimized_allocations = profile["allocations_per_million"]
                reduction_pct = (
                    (baseline_allocations - optimized_allocations)
                    / baseline_allocations
                    * 100
                )

                logger.info(
                    "Allocation reduction: %.1f%% (baseline: %.0f, optimized: %.0f)",
                    reduction_pct,
                    baseline_allocations,
                    optimized_allocations,
                )

                # Add reduction to profile
                profile["baseline_allocations_per_million"] = baseline_allocations
                profile["allocation_reduction_pct"] = round(reduction_pct, 2)

                # Rewrite output with reduction
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(profile, f, indent=2)

    except Exception as e:  # pylint: disable=broad-exception-caught
        # Broad exception acceptable: top-level error handler for CLI script
        logger.error("Profiling failed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
