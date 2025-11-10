"""Unit tests for schema restriction and column order in ingestion pipeline.

Tests verify that schema restriction correctly selects only core columns
and maintains the specified column order.
"""

import pandas as pd
import pytest

from src.io.schema import (
    CORE_COLUMNS,
    restrict_to_core_schema,
    validate_required_columns,
)


class TestSchemaRestrictionAndOrder:
    """Test suite for schema restriction and column ordering."""

    def test_core_columns_defined(self):
        """Test that CORE_COLUMNS constant is properly defined."""
        assert CORE_COLUMNS is not None
        assert len(CORE_COLUMNS) == 7
        assert "timestamp_utc" in CORE_COLUMNS
        assert "open" in CORE_COLUMNS
        assert "high" in CORE_COLUMNS
        assert "low" in CORE_COLUMNS
        assert "close" in CORE_COLUMNS
        assert "volume" in CORE_COLUMNS
        assert "is_gap" in CORE_COLUMNS

    def test_restrict_to_core_removes_extra_columns(self):
        """Test that extra columns are removed during restriction."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.date_range(
                    "2025-01-01", periods=3, freq="1min", tz="UTC"
                ),
                "open": [1.0, 1.1, 1.2],
                "high": [1.05, 1.15, 1.25],
                "low": [0.95, 1.05, 1.15],
                "close": [1.01, 1.11, 1.21],
                "volume": [100.0, 110.0, 120.0],
                "is_gap": [False, False, False],
                "extra_column1": [1, 2, 3],
                "extra_column2": ["a", "b", "c"],
            }
        )

        result = restrict_to_core_schema(df)

        # Should have exactly core columns
        assert set(result.columns) == set(CORE_COLUMNS)
        assert len(result.columns) == 7

        # Extra columns should be gone
        assert "extra_column1" not in result.columns
        assert "extra_column2" not in result.columns

    def test_core_column_order_preserved(self):
        """Test that core columns maintain specified order."""
        df = pd.DataFrame(
            {
                "volume": [100.0, 110.0],
                "close": [1.01, 1.11],
                "timestamp_utc": pd.date_range(
                    "2025-01-01", periods=2, freq="1min", tz="UTC"
                ),
                "open": [1.0, 1.1],
                "is_gap": [False, False],
                "low": [0.95, 1.05],
                "high": [1.05, 1.15],
            }
        )

        result = restrict_to_core_schema(df)

        # Columns should be in CORE_COLUMNS order
        assert list(result.columns) == CORE_COLUMNS

    def test_core_columns_only_unchanged(self):
        """Test that dataframe with only core columns is unchanged."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.date_range(
                    "2025-01-01", periods=3, freq="1min", tz="UTC"
                ),
                "open": [1.0, 1.1, 1.2],
                "high": [1.05, 1.15, 1.25],
                "low": [0.95, 1.05, 1.15],
                "close": [1.01, 1.11, 1.21],
                "volume": [100.0, 110.0, 120.0],
                "is_gap": [False, False, False],
            }
        )

        result = restrict_to_core_schema(df)

        # Should be identical (except potentially column order)
        assert len(result) == len(df)
        assert set(result.columns) == set(df.columns)

    def test_missing_core_column_raises_error(self):
        """Test that missing core column raises ValueError."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.date_range(
                    "2025-01-01", periods=2, freq="1min", tz="UTC"
                ),
                "open": [1.0, 1.1],
                "high": [1.05, 1.15],
                "low": [0.95, 1.05],
                "close": [1.01, 1.11],
                # Missing: volume and is_gap
            }
        )

        with pytest.raises(ValueError, match="Missing core columns"):
            restrict_to_core_schema(df)

    def test_validate_required_columns_passes(self):
        """Test that validation passes with all required columns."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(["2025-01-01"], utc=True),
                "open": [1.0],
                "high": [1.05],
                "low": [0.95],
                "close": [1.01],
                "volume": [100.0],
            }
        )

        # Should not raise
        validate_required_columns(df)

    def test_validate_required_columns_fails(self):
        """Test that validation fails with missing required columns."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(["2025-01-01"], utc=True),
                "open": [1.0],
                # Missing: high, low, close, volume
            }
        )

        with pytest.raises(ValueError, match="Missing required columns"):
            validate_required_columns(df)

    def test_data_values_preserved_after_restriction(self):
        """Test that data values are preserved during restriction."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.date_range(
                    "2025-01-01", periods=3, freq="1min", tz="UTC"
                ),
                "open": [1.0, 1.1, 1.2],
                "high": [1.05, 1.15, 1.25],
                "low": [0.95, 1.05, 1.15],
                "close": [1.01, 1.11, 1.21],
                "volume": [100.0, 110.0, 120.0],
                "is_gap": [False, False, True],
                "extra": [99, 88, 77],
            }
        )

        result = restrict_to_core_schema(df)

        # Values should be unchanged
        assert (result["open"] == df["open"]).all()
        assert (result["close"] == df["close"]).all()
        assert (result["is_gap"] == df["is_gap"]).all()

    def test_schema_restriction_with_many_extra_columns(self):
        """Test restriction with many extraneous columns."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.date_range(
                    "2025-01-01", periods=2, freq="1min", tz="UTC"
                ),
                "open": [1.0, 1.1],
                "high": [1.05, 1.15],
                "low": [0.95, 1.05],
                "close": [1.01, 1.11],
                "volume": [100.0, 110.0],
                "is_gap": [False, False],
                "indicator1": [1, 2],
                "indicator2": [3, 4],
                "indicator3": [5, 6],
                "indicator4": [7, 8],
                "indicator5": [9, 10],
            }
        )

        result = restrict_to_core_schema(df)

        # Should have exactly 7 columns
        assert len(result.columns) == 7

        # All core columns present
        for col in CORE_COLUMNS:
            assert col in result.columns

    def test_schema_restriction_preserves_row_count(self):
        """Test that row count is preserved during restriction."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.date_range(
                    "2025-01-01", periods=100, freq="1min", tz="UTC"
                ),
                "open": range(100),
                "high": range(100),
                "low": range(100),
                "close": range(100),
                "volume": range(100),
                "is_gap": [False] * 100,
                "extra1": range(100),
                "extra2": range(100),
            }
        )

        result = restrict_to_core_schema(df)

        assert len(result) == len(df)
        assert len(result) == 100

    def test_column_order_matches_spec(self):
        """Test that column order matches specification exactly."""
        df = pd.DataFrame(
            {
                "is_gap": [False],
                "volume": [100.0],
                "close": [1.01],
                "low": [0.95],
                "high": [1.05],
                "open": [1.0],
                "timestamp_utc": pd.to_datetime(["2025-01-01"], utc=True),
            }
        )

        result = restrict_to_core_schema(df)

        # Order should be: timestamp_utc, open, high, low, close, volume, is_gap
        expected_order = [
            "timestamp_utc",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "is_gap",
        ]
        assert list(result.columns) == expected_order

    def test_schema_restriction_with_empty_dataframe(self):
        """Test restriction works with empty dataframe."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime([], utc=True),
                "open": [],
                "high": [],
                "low": [],
                "close": [],
                "volume": [],
                "is_gap": [],
                "extra": [],
            }
        )

        result = restrict_to_core_schema(df)

        assert len(result) == 0
        assert set(result.columns) == set(CORE_COLUMNS)

    def test_schema_restriction_maintains_dtypes(self):
        """Test that data types are preserved during restriction."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.date_range(
                    "2025-01-01", periods=2, freq="1min", tz="UTC"
                ),
                "open": pd.Series([1.0, 1.1], dtype="float64"),
                "high": pd.Series([1.05, 1.15], dtype="float64"),
                "low": pd.Series([0.95, 1.05], dtype="float64"),
                "close": pd.Series([1.01, 1.11], dtype="float64"),
                "volume": pd.Series([100.0, 110.0], dtype="float64"),
                "is_gap": pd.Series([False, False], dtype="bool"),
                "extra": [1, 2],
            }
        )

        result = restrict_to_core_schema(df)

        # Dtypes should be preserved
        assert result["open"].dtype == "float64"
        assert result["is_gap"].dtype == "bool"
        assert pd.api.types.is_datetime64tz_dtype(result["timestamp_utc"])

    def test_error_message_lists_missing_columns(self):
        """Test that error message includes list of missing columns."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.date_range(
                    "2025-01-01", periods=2, freq="1min", tz="UTC"
                ),
                "open": [1.0, 1.1],
                # Missing: high, low, close, volume, is_gap
            }
        )

        with pytest.raises(ValueError) as exc_info:
            restrict_to_core_schema(df)

        error_msg = str(exc_info.value)
        # Should mention missing columns
        assert "high" in error_msg or "Missing" in error_msg

    def test_schema_restriction_idempotent(self):
        """Test that applying restriction twice has no effect."""
        df = pd.DataFrame(
            {
                "timestamp_utc": pd.date_range(
                    "2025-01-01", periods=2, freq="1min", tz="UTC"
                ),
                "open": [1.0, 1.1],
                "high": [1.05, 1.15],
                "low": [0.95, 1.05],
                "close": [1.01, 1.11],
                "volume": [100.0, 110.0],
                "is_gap": [False, False],
                "extra": [1, 2],
            }
        )

        result1 = restrict_to_core_schema(df)
        result2 = restrict_to_core_schema(result1)

        # Should be identical
        assert list(result1.columns) == list(result2.columns)
        assert len(result1) == len(result2)
        assert (result1 == result2).all().all()
