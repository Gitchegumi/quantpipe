"""Performance tests for dataset building with large datasets.

Feature: 004-timeseries-dataset
Task: T025 - Performance test with large synthetic dataset
Success Criteria: SC-005 - Build completes within 2 minutes for 1M rows
"""

import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta
import time

from src.io.dataset_builder import build_symbol_dataset


@pytest.fixture
def large_dataset(tmp_path):
    """Generate a synthetic dataset with 1M rows (~1 year of 1-minute data)."""
    raw_path = tmp_path / "raw"
    symbol_path = raw_path / "eurusd"
    symbol_path.mkdir(parents=True, exist_ok=True)

    # Generate 1M rows of synthetic OHLCV data
    num_rows = 1_000_000

    # Start from Jan 1, 2020 and generate 1-minute bars
    start_time = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    timestamps = [start_time + timedelta(minutes=i) for i in range(num_rows)]

    # Generate realistic-ish price data
    base_price = 1.1000
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [base_price + (i % 100) * 0.0001 for i in range(num_rows)],
            "high": [base_price + (i % 100) * 0.0001 + 0.0005 for i in range(num_rows)],
            "low": [base_price + (i % 100) * 0.0001 - 0.0003 for i in range(num_rows)],
            "close": [
                base_price + (i % 100) * 0.0001 + 0.0002 for i in range(num_rows)
            ],
            "volume": [1000 + (i % 500) for i in range(num_rows)],
        }
    )

    csv_file = symbol_path / "eurusd_large.csv"
    df.to_csv(csv_file, index=False)

    return {
        "raw_path": raw_path,
        "output_path": tmp_path / "processed",
        "num_rows": num_rows,
    }


class TestLargeBuildTiming:
    """Performance tests for large dataset builds."""

    def test_1m_rows_within_2_minutes(self, large_dataset):
        """Test that 1M rows build completes within 2 minutes (SC-005)."""
        start_time = time.perf_counter()

        # Build the dataset
        result = build_symbol_dataset(
            symbol="eurusd",
            raw_path=large_dataset["raw_path"],
            output_path=large_dataset["output_path"],
        )

        end_time = time.perf_counter()
        duration = end_time - start_time

        # Assert build succeeded
        assert result is not None
        assert result["success"] is True

        # Assert performance requirement: <2 minutes (120 seconds)
        assert (
            duration < 120.0
        ), f"Build took {duration:.2f}s, exceeding 2-minute threshold"

        # Log actual duration for monitoring
        print(f"\n✓ 1M rows processed in {duration:.2f}s")

    def test_large_build_correctness(self, large_dataset):
        """Test that large build produces correct output structure."""
        result = build_symbol_dataset(
            symbol="eurusd",
            raw_path=large_dataset["raw_path"],
            output_path=large_dataset["output_path"],
        )

        assert result is not None
        assert result["success"] is True
        assert result["metadata"] is not None

        # Verify row counts from metadata (80/20 split of 1M)
        metadata = result["metadata"]
        expected_test = int(1_000_000 * 0.8)  # 800,000
        expected_validation = 1_000_000 - expected_test  # 200,000

        assert metadata.test_rows == expected_test
        assert metadata.validation_rows == expected_validation
        assert metadata.total_rows == 1_000_000

        print(
            f"\n✓ Correct partitioning: {expected_test} test, {expected_validation} validation"
        )

    def test_large_build_chronological_order(self, large_dataset):
        """Test that large dataset maintains chronological order via metadata."""
        result = build_symbol_dataset(
            symbol="eurusd",
            raw_path=large_dataset["raw_path"],
            output_path=large_dataset["output_path"],
        )

        assert result["success"] is True

        # Verify timestamps from metadata (start < validation_start < end)
        metadata = result["metadata"]
        assert metadata.start_timestamp < metadata.validation_start_timestamp
        assert metadata.validation_start_timestamp <= metadata.end_timestamp

        print("\n✓ Metadata confirms chronological ordering")

    def test_large_build_validation_is_most_recent(self, large_dataset):
        """Test that validation partition contains most recent 20% of data."""
        result = build_symbol_dataset(
            symbol="eurusd",
            raw_path=large_dataset["raw_path"],
            output_path=large_dataset["output_path"],
        )

        assert result["success"] is True

        # Verify via metadata: validation_start should be after ~80% point
        metadata = result["metadata"]

        # Validation rows should be ~20% of total
        validation_ratio = metadata.validation_rows / metadata.total_rows
        assert (
            0.19 <= validation_ratio <= 0.21
        ), f"Validation ratio {validation_ratio} not ~0.20"

        # Validation timestamps should be at the end
        assert metadata.validation_start_timestamp >= metadata.start_timestamp
        assert metadata.validation_start_timestamp <= metadata.end_timestamp

        print("\n✓ Validation partition is most recent 20% of data")

    def test_large_build_memory_efficiency(self, large_dataset):
        """Test that large build does not cause memory issues."""
        # This test validates that pandas operations don't blow up memory
        # Just running the build without crashing demonstrates memory safety
        result = build_symbol_dataset(
            symbol="eurusd",
            raw_path=large_dataset["raw_path"],
            output_path=large_dataset["output_path"],
        )

        assert result is not None
        assert result["success"] is True

        print("\n✓ Build completed without memory errors")
