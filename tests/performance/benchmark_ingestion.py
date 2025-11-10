"""Performance benchmarks for ingestion operations.

This module provides performance benchmarking for the ingestion pipeline,
measuring runtime, throughput, and memory usage against baseline targets.
"""

import json
import logging
from pathlib import Path

import pytest

from src.io.ingestion import ingest_ohlcv_data


logger = logging.getLogger(__name__)

# Baseline dataset reference
BASELINE_DATASET_PATH = Path("price_data/raw/eurusd/eurusd_2024.csv")
BASELINE_ROW_COUNT = 6_900_000  # Approximate 6.9M rows
BASELINE_TARGET_SECONDS = 120  # SC-001
STRETCH_TARGET_SECONDS = 90  # SC-012


@pytest.mark.performance()
@pytest.mark.skipif(
    not BASELINE_DATASET_PATH.exists(),
    reason="Baseline dataset not available",
)
def test_ingestion_baseline_performance():
    """Test that ingestion meets baseline performance target (≤120s).

    SC-001: Ingest 6.9M-row baseline dataset in ≤120 seconds.
    """
    logger.info("Starting baseline performance benchmark")
    logger.info("Dataset: %s", BASELINE_DATASET_PATH)
    logger.info("Target: ≤%d seconds", BASELINE_TARGET_SECONDS)

    # Run ingestion
    result = ingest_ohlcv_data(str(BASELINE_DATASET_PATH), timeframe_minutes=1)

    # Extract metrics
    runtime = result.metrics.runtime_seconds
    throughput = result.metrics.throughput_rows_per_min
    rows_output = result.metrics.total_rows_output
    backend = result.metrics.acceleration_backend

    logger.info("Ingestion complete:")
    logger.info("  Runtime: %.2f seconds", runtime)
    logger.info("  Throughput: %.0f rows/min", throughput)
    logger.info("  Rows output: %d", rows_output)
    logger.info("  Backend: %s", backend)
    logger.info("  Gaps inserted: %d", result.metrics.gaps_inserted)
    logger.info("  Duplicates removed: %d", result.metrics.duplicates_removed)

    # Save benchmark results
    results_path = Path("results/benchmark_summary.json")
    results_path.parent.mkdir(parents=True, exist_ok=True)

    benchmark_data = {
        "test": "ingestion_baseline",
        "runtime_seconds": runtime,
        "throughput_rows_per_min": throughput,
        "rows_output": rows_output,
        "acceleration_backend": backend,
        "gaps_inserted": result.metrics.gaps_inserted,
        "duplicates_removed": result.metrics.duplicates_removed,
        "target_seconds": BASELINE_TARGET_SECONDS,
        "passed": runtime <= BASELINE_TARGET_SECONDS,
        "stretch_candidate": result.metrics.stretch_runtime_candidate,
    }

    with results_path.open("w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2)

    logger.info("Benchmark results saved to %s", results_path)

    # Assert performance target met
    assert (
        runtime <= BASELINE_TARGET_SECONDS
    ), f"Ingestion took {runtime:.2f}s, exceeds target of {BASELINE_TARGET_SECONDS}s"

    # Log if stretch target achieved
    if runtime <= STRETCH_TARGET_SECONDS:
        logger.info(
            "✓ Stretch target achieved: %.2f ≤ %d seconds",
            runtime,
            STRETCH_TARGET_SECONDS,
        )


@pytest.mark.performance()
def test_ingestion_stretch_performance():
    """Test that ingestion achieves stretch target (≤90s) if possible.

    SC-012: Aspirational stretch goal for optimized ingestion.
    """
    # Will be implemented in Phase 6 (T094)
    pytest.skip("Stretch performance test to be implemented in Phase 6")
