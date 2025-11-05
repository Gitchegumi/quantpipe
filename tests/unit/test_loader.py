"""Unit tests for column-limited typed loader (T057, FR-003)."""

# pylint: disable=unused-import

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.backtest.loader import (
    OPTIONAL_COLUMNS,
    REQUIRED_COLUMNS,
    load_candles_memory_efficient,
    load_candles_typed,
)


class TestLoadCandlesTyped:
    """Unit tests for load_candles_typed function."""

    def test_load_all_required_columns(self):
        """Load CSV with all required columns (T057, FR-003)."""
        # Create temporary CSV with required columns
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_path = Path(f.name)
            f.write("timestamp_utc,open,high,low,close\n")
            f.write("2020-01-01 00:00:00,1.1000,1.1010,1.0990,1.1005\n")
            f.write("2020-01-01 00:01:00,1.1005,1.1015,1.0995,1.1010\n")

        try:
            df = load_candles_typed(csv_path)

            # Validate all required columns present
            assert set(df.columns) == set(REQUIRED_COLUMNS.keys())

            # Validate dtypes
            assert df["timestamp_utc"].dtype == "datetime64[ns]"
            assert df["open"].dtype == "float64"
            assert df["high"].dtype == "float64"
            assert df["low"].dtype == "float64"
            assert df["close"].dtype == "float64"

            # Validate data
            assert len(df) == 2
            assert df.loc[0, "close"] == 1.1005
        finally:
            csv_path.unlink()

    def test_load_subset_of_columns(self):
        """Load only specified columns for memory efficiency (T057, FR-003)."""
        # Create temporary CSV
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_path = Path(f.name)
            f.write("timestamp_utc,open,high,low,close\n")
            f.write("2020-01-01 00:00:00,1.1000,1.1010,1.0990,1.1005\n")

        try:
            # Load only timestamp + close
            df = load_candles_typed(csv_path, columns=["timestamp_utc", "close"])

            # Validate only requested columns present
            assert list(df.columns) == ["timestamp_utc", "close"]

            # Validate dtypes
            assert df["timestamp_utc"].dtype == "datetime64[ns]"
            assert df["close"].dtype == "float64"

            # Validate data
            assert df.loc[0, "close"] == 1.1005
        finally:
            csv_path.unlink()

    def test_timestamp_column_alias(self):
        """Handle 'timestamp' as alias for 'timestamp_utc' (T057)."""
        # Create CSV with 'timestamp' instead of 'timestamp_utc'
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_path = Path(f.name)
            f.write("timestamp,open,high,low,close\n")
            f.write("2020-01-01 00:00:00,1.1000,1.1010,1.0990,1.1005\n")

        try:
            df = load_candles_typed(csv_path)

            # Should rename to standard column
            assert "timestamp_utc" in df.columns
            assert "timestamp" not in df.columns

            # Validate dtype
            assert df["timestamp_utc"].dtype == "datetime64[ns]"
        finally:
            csv_path.unlink()

    def test_strict_validation_rejects_unexpected_columns(self):
        """Strict mode rejects CSVs with unexpected columns (T057, FR-003)."""
        # Create CSV with unexpected column
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_path = Path(f.name)
            f.write("timestamp_utc,open,high,low,close,unexpected_column\n")
            f.write("2020-01-01 00:00:00,1.1000,1.1010,1.0990,1.1005,99\n")

        try:
            with pytest.raises(
                ValueError, match="unexpected columns.*unexpected_column"
            ):
                load_candles_typed(csv_path, validate_strict=True)
        finally:
            csv_path.unlink()

    def test_strict_validation_disabled(self):
        """Non-strict mode allows unexpected columns (T057)."""
        # Create CSV with unexpected column
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_path = Path(f.name)
            f.write("timestamp_utc,open,high,low,close,unexpected_column\n")
            f.write("2020-01-01 00:00:00,1.1000,1.1010,1.0990,1.1005,99\n")

        try:
            # Should succeed with validate_strict=False
            df = load_candles_typed(csv_path, validate_strict=False)

            # Loaded only required columns
            assert set(df.columns) == set(REQUIRED_COLUMNS.keys())
        finally:
            csv_path.unlink()

    def test_optional_columns_allowed(self):
        """Optional columns (volume, tick_volume) are allowed (T057, FR-003)."""
        # Create CSV with optional volume column
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_path = Path(f.name)
            f.write("timestamp_utc,open,high,low,close,volume\n")
            f.write("2020-01-01 00:00:00,1.1000,1.1010,1.0990,1.1005,1000.0\n")

        try:
            # Should succeed (volume is optional)
            df = load_candles_typed(csv_path, validate_strict=True)

            # Volume not loaded by default
            assert "volume" not in df.columns

            # Load with volume explicitly requested
            df_with_volume = load_candles_typed(
                csv_path, columns=["timestamp_utc", "close", "volume"]
            )

            assert "volume" in df_with_volume.columns
            assert df_with_volume["volume"].dtype == "float64"
            assert df_with_volume.loc[0, "volume"] == 1000.0
        finally:
            csv_path.unlink()

    def test_unknown_column_requested(self):
        """Requesting unknown column raises ValueError (T057, FR-003)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_path = Path(f.name)
            f.write("timestamp_utc,open,high,low,close\n")
            f.write("2020-01-01 00:00:00,1.1000,1.1010,1.0990,1.1005\n")

        try:
            with pytest.raises(ValueError, match="Unknown column 'invalid_col'"):
                load_candles_typed(csv_path, columns=["timestamp_utc", "invalid_col"])
        finally:
            csv_path.unlink()

    def test_file_not_found(self):
        """Missing CSV file raises FileNotFoundError (T057)."""
        with pytest.raises(FileNotFoundError, match="CSV file not found"):
            load_candles_typed("nonexistent_file.csv")


class TestLoadCandlesMemoryEfficient:
    """Unit tests for load_candles_memory_efficient function."""

    def test_load_in_chunks(self):
        """Load large dataset in chunks (T057, SC-003)."""
        # Create temporary CSV with 10k rows
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_path = Path(f.name)
            f.write("timestamp_utc,open,high,low,close\n")

            # Write 10k rows (use valid timestamps - increment minutes)
            base_time = pd.Timestamp("2020-01-01 00:00:00")
            for i in range(10_000):
                timestamp = base_time + pd.Timedelta(minutes=i)
                price = 1.1 + i * 0.0001
                f.write(
                    f"{timestamp},{price},{price + 0.001},{price - 0.001},{price}\n"
                )

        try:
            # Load in 1000-row chunks
            df = load_candles_memory_efficient(csv_path, chunksize=1000)

            # Validate full dataset loaded
            assert len(df) == 10_000

            # Validate dtypes
            assert df["timestamp_utc"].dtype == "datetime64[ns]"
            assert df["close"].dtype == "float64"

            # Validate data integrity
            assert df.loc[0, "close"] == pytest.approx(1.1, rel=1e-6)
            assert df.loc[9999, "close"] == pytest.approx(1.1 + 9999 * 0.0001, rel=1e-6)
        finally:
            csv_path.unlink(missing_ok=True)

    def test_chunk_size_larger_than_dataset(self):
        """Chunksize larger than dataset still works (T057)."""
        # Create small CSV
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_path = Path(f.name)
            f.write("timestamp_utc,open,high,low,close\n")
            f.write("2020-01-01 00:00:00,1.1000,1.1010,1.0990,1.1005\n")

        try:
            # Load with large chunksize
            df = load_candles_memory_efficient(csv_path, chunksize=10_000_000)

            # Should still load correctly
            assert len(df) == 1
            assert df.loc[0, "close"] == 1.1005
        finally:
            csv_path.unlink()

    def test_timestamp_alias_in_chunks(self):
        """Handle 'timestamp' alias when loading in chunks (T057)."""
        # Create CSV with 'timestamp' instead of 'timestamp_utc'
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_path = Path(f.name)
            f.write("timestamp,open,high,low,close\n")

            # Use valid timestamps
            base_time = pd.Timestamp("2020-01-01 00:00:00")
            for i in range(100):
                timestamp = base_time + pd.Timedelta(minutes=i)
                f.write(f"{timestamp},1.1,1.11,1.09,1.10\n")

        try:
            df = load_candles_memory_efficient(csv_path, chunksize=50)

            # Should rename to standard column
            assert "timestamp_utc" in df.columns
            assert "timestamp" not in df.columns

            # Validate data
            assert len(df) == 100
        finally:
            csv_path.unlink(missing_ok=True)
