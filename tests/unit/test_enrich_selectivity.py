"""Unit tests for enrichment selectivity - only requested columns added."""
# pylint: disable=redefined-outer-name  # pytest fixtures

import pandas as pd
import pytest

from src.indicators.enrich import enrich


@pytest.fixture
def core_dataframe():
    """Create a sample core DataFrame for testing."""
    return pd.DataFrame(
        {
            "timestamp_utc": pd.date_range("2024-01-01", periods=100, freq="1min"),
            "open": range(100, 200),
            "high": range(101, 201),
            "low": range(99, 199),
            "close": range(100, 200),
            "volume": [1000] * 100,
            "is_gap": [False] * 100,
        }
    )


@pytest.fixture(autouse=True)
def cleanup_registry():
    """Clean up registry after each test."""
    yield
    # Note: Built-in indicators will be auto-registered, which is OK


def test_no_indicators_returns_only_core(core_dataframe):
    """Test that requesting no indicators returns only core columns."""
    result = enrich(core_dataframe, indicators=[], strict=True)

    # Should have same columns as input
    assert set(result.enriched.columns) == set(core_dataframe.columns)
    assert len(result.indicators_applied) == 0
    assert len(result.failed_indicators) == 0


def test_single_indicator_adds_only_one_column(core_dataframe):
    """Test that requesting one indicator adds only that column."""
    result = enrich(core_dataframe, indicators=["ema20"], strict=True)

    # Should have core columns plus ema20
    expected_columns = set(core_dataframe.columns) | {"ema20"}
    assert set(result.enriched.columns) == expected_columns

    assert "ema20" in result.indicators_applied
    assert len(result.indicators_applied) == 1
    assert len(result.failed_indicators) == 0


def test_multiple_indicators_adds_all_requested_columns(core_dataframe):
    """Test that requesting multiple indicators adds all of them."""
    result = enrich(
        core_dataframe, indicators=["ema20", "ema50", "atr14"], strict=True
    )

    # Should have core columns plus requested indicators
    expected_columns = set(core_dataframe.columns) | {"ema20", "ema50", "atr14"}
    assert set(result.enriched.columns) == expected_columns

    assert set(result.indicators_applied) == {"ema20", "ema50", "atr14"}
    assert len(result.failed_indicators) == 0


def test_no_unrequested_columns_added(core_dataframe):
    """Test that no unrequested indicator columns are added."""
    result = enrich(core_dataframe, indicators=["ema20"], strict=True)

    # Should NOT have ema50, atr14, or stoch_rsi
    assert "ema50" not in result.enriched.columns
    assert "atr14" not in result.enriched.columns
    assert "stoch_rsi" not in result.enriched.columns

    # Only ema20 should be in applied
    assert result.indicators_applied == ["ema20"]


def test_core_columns_unchanged_count(core_dataframe):
    """Test that core columns count doesn't change."""
    original_core_count = len(core_dataframe.columns)

    result = enrich(core_dataframe, indicators=["ema20", "atr14"], strict=True)

    # Core columns should still be present
    for col in core_dataframe.columns:
        assert col in result.enriched.columns

    # Total columns should be core + indicators
    expected_total = original_core_count + 2  # ema20, atr14
    assert len(result.enriched.columns) == expected_total


def test_indicator_order_does_not_add_extras(core_dataframe):
    """Test that indicator computation order doesn't add extra columns."""
    # Request in different order
    result1 = enrich(
        core_dataframe, indicators=["ema20", "atr14"], strict=True
    )
    result2 = enrich(
        core_dataframe, indicators=["atr14", "ema20"], strict=True
    )

    # Both should have exactly same columns (order may differ)
    assert set(result1.enriched.columns) == set(result2.enriched.columns)

    # Both should have exactly 2 indicators applied
    assert len(result1.indicators_applied) == 2
    assert len(result2.indicators_applied) == 2


def test_partial_request_subset(core_dataframe):
    """Test requesting subset of available indicators."""
    # Request only 1 of 4 available built-ins
    result = enrich(core_dataframe, indicators=["stoch_rsi"], strict=True)

    # Should only have stoch_rsi, not ema20/ema50/atr14
    assert "stoch_rsi" in result.enriched.columns
    assert "ema20" not in result.enriched.columns
    assert "ema50" not in result.enriched.columns
    assert "atr14" not in result.enriched.columns

    assert result.indicators_applied == ["stoch_rsi"]


def test_empty_request_with_strict_mode(core_dataframe):
    """Test empty indicator request in strict mode."""
    result = enrich(core_dataframe, indicators=[], strict=True)

    # Should return core columns only
    assert set(result.enriched.columns) == set(core_dataframe.columns)
    assert len(result.indicators_applied) == 0


def test_empty_request_with_non_strict_mode(core_dataframe):
    """Test empty indicator request in non-strict mode."""
    result = enrich(core_dataframe, indicators=[], strict=False)

    # Should return core columns only
    assert set(result.enriched.columns) == set(core_dataframe.columns)
    assert len(result.indicators_applied) == 0
    assert len(result.failed_indicators) == 0


def test_selectivity_with_params(core_dataframe):
    """Test that custom params don't cause extra columns."""
    params = {"ema20": {"period": 20, "column": "close"}}

    result = enrich(
        core_dataframe, indicators=["ema20"], params=params, strict=True
    )

    # Should still only add ema20
    expected_columns = set(core_dataframe.columns) | {"ema20"}
    assert set(result.enriched.columns) == expected_columns
    assert result.indicators_applied == ["ema20"]


def test_core_reference_dataframe_unchanged(core_dataframe):
    """Test that core reference DataFrame is not modified."""
    original_columns = set(core_dataframe.columns)
    original_shape = core_dataframe.shape

    result = enrich(core_dataframe, indicators=["ema20"], strict=True)

    # Original DataFrame should be unchanged
    assert set(core_dataframe.columns) == original_columns
    assert core_dataframe.shape == original_shape

    # But enriched should have additional column
    assert "ema20" not in core_dataframe.columns
    assert "ema20" in result.enriched.columns
