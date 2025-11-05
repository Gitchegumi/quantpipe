"""Performance tests for data loading and slicing operations (T060, SC-003).

Tests validate that data loading + fraction slicing for ≥10M rows completes
within 60 seconds wall-clock time.
"""

# pylint: disable=unused-variable

import time
from pathlib import Path
import pandas as pd
import pytest


class TestLoadSliceSpeed:
    """Performance test suite for data loading and slicing."""

    def test_load_slice_10m_rows_under_60_seconds(self, tmp_path):
        """Data loading + slicing for 10M rows completes in ≤60s (SC-003, T060)."""
        # T060: Validate SC-003 - load + slice timing for large datasets

        # Create synthetic 10M row dataset
        num_rows = 10_000_000
        print(f"\nGenerating {num_rows:,} row synthetic dataset...")

        # Generate synthetic OHLC data
        import numpy as np

        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=num_rows, freq="1min")

        # Efficient generation using numpy arrays
        base_price = 1.1000
        price_changes = np.random.randn(num_rows) * 0.0001
        closes = base_price + np.cumsum(price_changes)

        # Generate OHLC from closes
        highs = closes + np.abs(np.random.randn(num_rows) * 0.0001)
        lows = closes - np.abs(np.random.randn(num_rows) * 0.0001)
        opens = np.roll(closes, 1)
        opens[0] = base_price

        df = pd.DataFrame(
            {
                "timestamp": dates,
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
            }
        )

        # Write to CSV
        csv_path = tmp_path / "large_dataset.csv"
        print(f"Writing to {csv_path}...")
        df.to_csv(csv_path, index=False)

        # T060: Time the load + slice operation
        start_time = time.perf_counter()

        # Load dataset
        loaded_df = pd.read_csv(csv_path)

        # Slice to fraction (e.g., 25%)
        fraction = 0.25
        slice_size = int(len(loaded_df) * fraction)
        sliced_df = loaded_df.iloc[:slice_size]

        end_time = time.perf_counter()
        elapsed = end_time - start_time

        print(f"Loaded {len(loaded_df):,} rows in {elapsed:.2f}s")
        print(f"Sliced to {len(sliced_df):,} rows (fraction={fraction})")

        # SC-003: Assert load + slice time ≤ 60 seconds
        assert (
            elapsed <= 60.0
        ), f"Load + slice time {elapsed:.2f}s exceeds 60s threshold (SC-003)"

        # Verify data integrity
        assert len(sliced_df) == slice_size
        assert "close" in sliced_df.columns
        assert sliced_df["close"].notna().all()

    def test_load_slice_scaling(self, tmp_path):
        """Load + slice time scales sub-linearly with dataset size (T060)."""
        # T060: Validate that loading performance doesn't degrade unexpectedly

        import numpy as np

        sizes = [100_000, 500_000, 1_000_000]
        times = []

        for size in sizes:
            # Generate synthetic data
            np.random.seed(42)
            dates = pd.date_range("2020-01-01", periods=size, freq="1min")

            df = pd.DataFrame(
                {
                    "timestamp": dates,
                    "open": 1.1 + np.random.randn(size) * 0.0001,
                    "high": 1.1 + np.random.randn(size) * 0.0001,
                    "low": 1.1 + np.random.randn(size) * 0.0001,
                    "close": 1.1 + np.random.randn(size) * 0.0001,
                }
            )

            csv_path = tmp_path / f"dataset_{size}.csv"
            df.to_csv(csv_path, index=False)

            # Time load + slice
            start = time.perf_counter()
            loaded = pd.read_csv(csv_path)
            sliced = loaded.iloc[: int(len(loaded) * 0.25)]
            end = time.perf_counter()

            elapsed = end - start
            times.append(elapsed)
            print(f"\n{size:,} rows: {elapsed:.3f}s")

        # Verify sub-linear scaling (time ratio < row ratio)
        # Going from 100k to 1M rows (10× increase)
        row_ratio = sizes[-1] / sizes[0]  # 10×
        time_ratio = times[-1] / times[0]

        print(f"\nRow ratio: {row_ratio:.1f}×")
        print(f"Time ratio: {time_ratio:.2f}×")

        # Assert sub-linear scaling (time ratio should be < row ratio)
        # Pandas read_csv scales roughly O(n log n) to O(n)
        assert time_ratio < row_ratio, (
            f"Load time scaling {time_ratio:.2f}× is not sub-linear "
            f"for {row_ratio:.1f}× row increase"
        )

    @pytest.mark.skip(reason="Requires production dataset - optional validation")
    def test_load_slice_production_dataset(self):
        """Load + slice production 6.9M row dataset under 60s (SC-003)."""
        # This test would run against actual production data
        # Skip by default since it requires large files

        production_file = Path("price_data/processed/eurusd/full/eurusd_2020_2025.csv")

        if not production_file.exists():
            pytest.skip(f"Production file not found: {production_file}")

        start = time.perf_counter()
        df = pd.read_csv(production_file)
        sliced = df.iloc[: int(len(df) * 0.25)]
        end = time.perf_counter()

        elapsed = end - start
        print(f"\nProduction dataset: {len(df):,} rows")
        print(f"Load + slice time: {elapsed:.2f}s")

        assert elapsed <= 60.0, f"Production load time {elapsed:.2f}s exceeds 60s"
