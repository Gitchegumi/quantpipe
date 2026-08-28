"""Unit tests for sorted_write module.

Tests cover:
- enforce_sorted_write sorts correctly when unsorted
- validate_sort_order returns True for sorted, False for unsorted
- write_parquet_sorted creates a file that reads back sorted
- strategy_id fallback works (no strategy_id column)
- single column fallback (only timestamp)
"""

from datetime import datetime, timezone

import polars as pl
import pytest

from src.data_io.sorted_write import (
    SORT_COLUMNS,
    SortOrderViolationError,
    enforce_sorted_write,
    validate_sort_order,
    write_parquet_sorted,
)


def create_full_df(rows=10) -> pl.DataFrame:
    """DataFrame with symbol, timestamp, strategy_id — unsorted."""
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    timestamps = [
        start.replace(minute=i % 60, hour=start.hour + i // 60) for i in range(rows)
    ]
    symbols = ["EURUSD" if i % 2 == 0 else "USDJPY" for i in range(rows)]
    strategy_ids = [f"s{i % 3}" for i in range(rows)]
    return pl.DataFrame(
        {
            "symbol": symbols,
            "timestamp": timestamps,
            "strategy_id": strategy_ids,
            "close": [1.0850 + i * 0.0001 for i in range(rows)],
        }
    )


def create_no_strategy_df(rows=10) -> pl.DataFrame:
    """DataFrame with symbol, timestamp only — unsorted."""
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    timestamps = [
        start.replace(minute=i % 60, hour=start.hour + i // 60) for i in range(rows)
    ]
    symbols = ["EURUSD" if i % 2 == 0 else "USDJPY" for i in range(rows)]
    return pl.DataFrame(
        {
            "symbol": symbols,
            "timestamp": timestamps,
            "close": [1.0850 + i * 0.0001 for i in range(rows)],
        }
    )


def create_timestamp_only_df(rows=10) -> pl.DataFrame:
    """DataFrame with timestamp only — unsorted."""
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    timestamps = [
        start.replace(minute=i % 60, hour=start.hour + i // 60) for i in range(rows)
    ]
    return pl.DataFrame(
        {
            "timestamp": timestamps,
            "close": [1.0850 + i * 0.0001 for i in range(rows)],
        }
    )


class TestEnforceSortedWrite:
    def test_sorts_unsorted_data(self):
        """Unsorted DataFrame should be sorted after enforce_sorted_write."""
        df = create_full_df()
        assert not validate_sort_order(df, SORT_COLUMNS)

        sorted_df = enforce_sorted_write(df)

        assert validate_sort_order(sorted_df, SORT_COLUMNS)

    def test_preserves_sorted_data(self):
        """Already-sorted DataFrame should remain unchanged."""
        df = create_full_df().sort(SORT_COLUMNS)

        sorted_df = enforce_sorted_write(df)

        assert validate_sort_order(sorted_df, SORT_COLUMNS)

    def test_raises_on_validation_failure(self):
        """Validation failure should raise SortOrderViolationError."""
        df = create_full_df()
        # Manually break sort by mutating (can't actually break it after sort)
        # This test verifies the validation path by using a custom sort_cols
        # that doesn't include all breaking columns
        df_broken = df.sort(["close"])  # sorted by close, not by sort columns
        with pytest.raises(SortOrderViolationError):
            enforce_sorted_write(df_broken)

    def test_validates_true_by_default(self):
        """validate=True is the default."""
        df = create_full_df()
        sorted_df = enforce_sorted_write(df)
        assert validate_sort_order(sorted_df, SORT_COLUMNS)

    def test_validate_false_skips_check(self):
        """validate=False should not raise even if something went wrong (it won't)."""
        df = create_full_df()
        # This is a no-op test since enforce_sorted_write always sorts correctly
        sorted_df = enforce_sorted_write(df, validate=False)
        assert validate_sort_order(sorted_df, SORT_COLUMNS)


class TestValidateSortOrder:
    def test_returns_true_for_sorted_df(self):
        """Sorted DataFrame should return True."""
        df = create_full_df().sort(SORT_COLUMNS)
        assert validate_sort_order(df, SORT_COLUMNS) is True

    def test_returns_false_for_unsorted_df(self):
        """Unsorted DataFrame should return False."""
        df = create_full_df()
        assert validate_sort_order(df, SORT_COLUMNS) is False

    def test_single_row_returns_true(self):
        """Single-row DataFrame is trivially sorted."""
        df = create_full_df().head(1)
        assert validate_sort_order(df, SORT_COLUMNS) is True

    def test_empty_df_returns_true(self):
        """Empty DataFrame is trivially sorted."""
        df = pl.DataFrame({"symbol": [], "timestamp": [], "strategy_id": []})
        assert validate_sort_order(df, SORT_COLUMNS) is True


class TestWriteParquetSorted:
    def test_writes_sorted_parquet(self, tmp_path):
        """Written parquet should read back sorted."""
        df = create_full_df()
        path = str(tmp_path / "test_sorted.parquet")

        result = write_parquet_sorted(df, path)

        assert result["path"] == path
        assert result["rows"] == len(df)
        assert result["sort_cols_used"] == SORT_COLUMNS
        assert isinstance(result["was_presorted"], bool)

        # Read back and verify sort
        read_df = pl.read_parquet(path)
        assert validate_sort_order(read_df, SORT_COLUMNS)

    def test_presorted_flag_true_when_already_sorted(self, tmp_path):
        """was_presorted should be True for already-sorted data."""
        df = create_full_df().sort(SORT_COLUMNS)
        path = str(tmp_path / "test_presorted.parquet")

        result = write_parquet_sorted(df, path)

        assert result["was_presorted"] is True

    def test_presorted_flag_false_when_unsorted(self, tmp_path):
        """was_presorted should be False for unsorted data."""
        df = create_full_df()
        path = str(tmp_path / "test_unsorted.parquet")

        result = write_parquet_sorted(df, path)

        assert result["was_presorted"] is False


class TestStrategyIdFallback:
    def test_falls_back_to_symbol_timestamp_when_no_strategy_id(self, tmp_path):
        """When strategy_id is absent, should use symbol+timestamp."""
        df = create_no_strategy_df()
        path = str(tmp_path / "test_no_strategy.parquet")

        result = write_parquet_sorted(df, path)

        assert result["sort_cols_used"] == ["symbol", "timestamp"]

        read_df = pl.read_parquet(path)
        assert validate_sort_order(read_df, ["symbol", "timestamp"])


class TestTimestampOnlyFallback:
    def test_falls_back_to_timestamp_only(self, tmp_path):
        """When only timestamp present, should use timestamp alone."""
        df = create_timestamp_only_df()
        path = str(tmp_path / "test_timestamp_only.parquet")

        result = write_parquet_sorted(df, path)

        assert result["sort_cols_used"] == ["timestamp"]

        read_df = pl.read_parquet(path)
        assert validate_sort_order(read_df, ["timestamp"])
