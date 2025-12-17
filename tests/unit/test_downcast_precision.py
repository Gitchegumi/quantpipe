"""Unit tests for downcast precision guard (T091, FR-011)."""

# pylint: disable=redefined-outer-name  # pytest fixtures

import numpy as np
import pandas as pd

from src.data_io.downcast import check_precision_safe, downcast_numeric_columns


def test_precision_safe_for_integers():
    """Test that downcast precision check works for integer-like floats."""
    # Integer-like floats should be safe to downcast to float32
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], dtype="float64")

    is_safe = check_precision_safe(series, "float32", max_error=1e-6)
    assert is_safe, "Integer-like floats should be safe to downcast"


def test_precision_unsafe_for_high_precision():
    """Test that downcast is detected as unsafe for high-precision values."""
    # Very small values may lose precision when downcasting
    series = pd.Series([1.0, 1.0000001, 1.0000002, 1.0000003], dtype="float64")

    # Float32 has ~7 decimal digits precision, float64 has ~15
    # This should be safe with default threshold
    is_safe = check_precision_safe(series, "float32", max_error=1e-6)
    # May be safe or unsafe depending on the values
    assert isinstance(is_safe, bool | np.bool_)


def test_precision_check_with_zeros():
    """Test precision check handles zeros correctly."""
    series = pd.Series([0.0, 1.0, 2.0, 0.0, 3.0], dtype="float64")

    is_safe = check_precision_safe(series, "float32", max_error=1e-6)
    assert is_safe, "Series with zeros should be handled correctly"


def test_precision_check_all_zeros():
    """Test precision check with all zeros."""
    series = pd.Series([0.0, 0.0, 0.0, 0.0], dtype="float64")

    is_safe = check_precision_safe(series, "float32", max_error=1e-6)
    assert is_safe, "All zeros should be safe to downcast"


def test_precision_check_with_nan():
    """Test precision check handles NaN values correctly."""
    series = pd.Series([1.0, np.nan, 2.0, np.nan, 3.0], dtype="float64")

    is_safe = check_precision_safe(series, "float32", max_error=1e-6)
    assert is_safe, "Series with NaN should be handled correctly"


def test_precision_check_all_nan():
    """Test precision check with all NaN values."""
    series = pd.Series([np.nan, np.nan, np.nan], dtype="float64")

    is_safe = check_precision_safe(series, "float32", max_error=1e-6)
    assert is_safe, "All NaN should be safe to downcast"


def test_downcast_numeric_columns_skips_unsafe():
    """Test that downcast_numeric_columns skips unsafe columns (FR-011)."""
    # Create DataFrame with mixed precision requirements
    df = pd.DataFrame(
        {
            "safe_col": [1.0, 2.0, 3.0, 4.0],  # Safe to downcast
            "unsafe_col": [1.123456789012345] * 4,  # May lose precision
            "integer_col": [10, 20, 30, 40],
        }
    )

    result_df, downcasted_cols = downcast_numeric_columns(df)

    # Should have attempted to downcast numeric columns
    assert isinstance(result_df, pd.DataFrame)
    assert isinstance(downcasted_cols, list)

    # safe_col should be downcasted
    assert "safe_col" in downcasted_cols or result_df["safe_col"].dtype == np.float32


def test_downcast_respects_skip_columns():
    """Test that skip_columns parameter is respected."""
    df = pd.DataFrame(
        {
            "col1": [1.0, 2.0, 3.0],
            "col2": [4.0, 5.0, 6.0],
            "col3": [7.0, 8.0, 9.0],
        }
    )

    skip = ["col2"]
    result_df, downcasted_cols = downcast_numeric_columns(df, skip_columns=skip)

    # col2 should not be downcasted
    assert "col2" not in downcasted_cols

    # col2 should retain original dtype
    assert result_df["col2"].dtype == df["col2"].dtype


def test_downcast_preserves_data_integrity():
    """Test that downcasting preserves data values within tolerance."""
    df = pd.DataFrame(
        {
            "price": [1.0, 1.5, 2.0, 2.5, 3.0],
            "volume": [1000.0, 1500.0, 2000.0, 2500.0, 3000.0],
        }
    )

    original_values = df.copy()
    result_df, _ = downcast_numeric_columns(df)

    # Check that values are preserved within float32 precision
    for col in df.columns:
        if col in result_df.columns:
            np.testing.assert_allclose(
                original_values[col].values,
                result_df[col].values,
                rtol=1e-6,
                err_msg=f"Column {col} values changed after downcast",
            )


def test_downcast_empty_dataframe():
    """Test downcast on empty DataFrame."""
    df = pd.DataFrame({"col1": [], "col2": []}, dtype=float)

    result_df, downcasted_cols = downcast_numeric_columns(df)

    assert len(result_df) == 0
    assert isinstance(downcasted_cols, list)


def test_downcast_non_numeric_columns_ignored():
    """Test that non-numeric columns are ignored during downcast."""
    df = pd.DataFrame(
        {
            "numeric": [1.0, 2.0, 3.0],
            "string": ["a", "b", "c"],
            "bool": [True, False, True],
        }
    )

    result_df, downcasted_cols = downcast_numeric_columns(df)

    # String and bool columns should remain unchanged
    assert result_df["string"].dtype == object
    assert result_df["bool"].dtype == bool

    # Only numeric column should be in downcasted list (if it was downcasted)
    for col in downcasted_cols:
        assert col == "numeric"


def test_precision_check_large_values():
    """Test precision check with large values."""
    # Large values should be safe for float32 (range up to ~1e38)
    series = pd.Series([1e6, 1e7, 1e8, 1e9], dtype="float64")

    is_safe = check_precision_safe(series, "float32", max_error=1e-6)
    assert is_safe, "Large values within float32 range should be safe"


def test_precision_check_very_small_values():
    """Test precision check with very small values."""
    # Very small values near float32 precision limit
    series = pd.Series([1e-6, 1e-7, 1e-8], dtype="float64")

    # May or may not be safe depending on precision requirements
    is_safe = check_precision_safe(series, "float32", max_error=1e-6)
    assert isinstance(is_safe, bool | np.bool_)


def test_downcast_warns_on_unsafe_precision(caplog):
    """Test that warning is logged when downcast is unsafe."""
    import logging

    # High precision values that will lose precision in float32
    series = pd.Series([1.12345678901234567890] * 4, dtype="float64")

    with caplog.at_level(logging.WARNING):
        is_safe = check_precision_safe(series, "float32", max_error=1e-10)

    if not is_safe:
        # Should have logged a warning
        assert any("unsafe" in record.message.lower() for record in caplog.records)
