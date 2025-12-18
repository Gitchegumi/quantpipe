"""Unit tests for enrichment immutability - core hash unchanged after enrichment."""

# pylint: disable=redefined-outer-name  # pytest fixtures

import pandas as pd
import pytest

from src.indicators.enrich import enrich
from src.data_io.hash_utils import compute_dataframe_hash


CORE_COLUMNS = ["timestamp_utc", "open", "high", "low", "close", "volume", "is_gap"]


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


def test_core_columns_unchanged_after_enrichment(core_dataframe):
    """Test that core columns remain unchanged after enrichment."""
    # Compute hash before enrichment
    hash_before = compute_dataframe_hash(core_dataframe, CORE_COLUMNS)

    result = enrich(core_dataframe, indicators=["ema20"], strict=True)

    # Compute hash after enrichment (from enriched DataFrame)
    hash_after = compute_dataframe_hash(result.enriched, CORE_COLUMNS)

    # Hashes should match
    assert hash_before == hash_after


def test_core_values_unchanged_after_multiple_indicators(core_dataframe):
    """Test core columns unchanged after applying multiple indicators."""
    hash_before = compute_dataframe_hash(core_dataframe, CORE_COLUMNS)

    result = enrich(
        core_dataframe,
        indicators=["ema20", "ema50", "atr14", "stoch_rsi"],
        strict=True,
    )

    hash_after = compute_dataframe_hash(result.enriched, CORE_COLUMNS)
    assert hash_before == hash_after


def test_original_dataframe_not_modified(core_dataframe):
    """Test that original input DataFrame is never modified."""
    # Store original values
    original_close = core_dataframe["close"].copy()
    original_shape = core_dataframe.shape
    original_columns = set(core_dataframe.columns)

    result = enrich(core_dataframe, indicators=["ema20", "atr14"], strict=True)

    # Original DataFrame should be unchanged
    assert core_dataframe.shape == original_shape
    assert set(core_dataframe.columns) == original_columns
    assert (core_dataframe["close"] == original_close).all()

    # Result should have new columns
    assert "ema20" not in core_dataframe.columns
    assert "ema20" in result.enriched.columns


def test_immutability_with_no_indicators(core_dataframe):
    """Test immutability when no indicators requested."""
    hash_before = compute_dataframe_hash(core_dataframe, CORE_COLUMNS)

    result = enrich(core_dataframe, indicators=[], strict=True)

    hash_after = compute_dataframe_hash(result.enriched, CORE_COLUMNS)
    assert hash_before == hash_after


def test_immutability_in_non_strict_mode(core_dataframe):
    """Test that immutability is maintained in non-strict mode."""
    hash_before = compute_dataframe_hash(core_dataframe, CORE_COLUMNS)

    result = enrich(
        core_dataframe,
        indicators=["ema20", "invalid", "atr14"],
        strict=False,
    )

    hash_after = compute_dataframe_hash(result.enriched, CORE_COLUMNS)
    assert hash_before == hash_after


def test_core_reference_in_result_unchanged(core_dataframe):
    """Test that result.core reference points to unchanged DataFrame."""
    hash_before = compute_dataframe_hash(core_dataframe, CORE_COLUMNS)

    result = enrich(core_dataframe, indicators=["ema20"], strict=True)

    # result.core should reference the original core DataFrame
    hash_core_ref = compute_dataframe_hash(result.core, CORE_COLUMNS)
    assert hash_before == hash_core_ref


def test_enriched_dataframe_is_copy_not_reference(core_dataframe):
    """Test that enriched DataFrame is a copy, not a reference to original."""
    result = enrich(core_dataframe, indicators=["ema20"], strict=True)

    # Modify enriched DataFrame
    result.enriched.loc[0, "ema20"] = 999999

    # Original should be unchanged
    assert "ema20" not in core_dataframe.columns

    # Core reference in result should be unchanged
    assert result.core.equals(core_dataframe)


def test_immutability_with_params(core_dataframe):
    """Test immutability when using custom parameters."""
    hash_before = compute_dataframe_hash(core_dataframe, CORE_COLUMNS)

    params = {"ema20": {"period": 20, "column": "close"}}
    result = enrich(core_dataframe, indicators=["ema20"], params=params, strict=True)

    hash_after = compute_dataframe_hash(result.enriched, CORE_COLUMNS)
    assert hash_before == hash_after


def test_core_timestamp_unchanged(core_dataframe):
    """Test that timestamp column specifically remains unchanged."""
    original_timestamps = core_dataframe["timestamp_utc"].copy()

    result = enrich(core_dataframe, indicators=["ema20", "atr14"], strict=True)

    # Timestamps in enriched should match original
    assert (result.enriched["timestamp_utc"] == original_timestamps).all()

    # Original should also be unchanged
    assert (core_dataframe["timestamp_utc"] == original_timestamps).all()


def test_core_ohlcv_values_unchanged(core_dataframe):
    """Test that OHLCV values remain unchanged after enrichment."""
    original_open = core_dataframe["open"].copy()
    original_high = core_dataframe["high"].copy()
    original_low = core_dataframe["low"].copy()
    original_close = core_dataframe["close"].copy()
    original_volume = core_dataframe["volume"].copy()

    result = enrich(
        core_dataframe, indicators=["ema20", "atr14", "stoch_rsi"], strict=True
    )

    # All OHLCV should be unchanged in enriched
    assert (result.enriched["open"] == original_open).all()
    assert (result.enriched["high"] == original_high).all()
    assert (result.enriched["low"] == original_low).all()
    assert (result.enriched["close"] == original_close).all()
    assert (result.enriched["volume"] == original_volume).all()


def test_is_gap_column_unchanged(core_dataframe):
    """Test that is_gap column remains unchanged after enrichment."""
    original_is_gap = core_dataframe["is_gap"].copy()

    result = enrich(core_dataframe, indicators=["ema20"], strict=True)

    # is_gap should be unchanged
    assert (result.enriched["is_gap"] == original_is_gap).all()


def test_immutability_multiple_sequential_enrichments(core_dataframe):
    """Test immutability across multiple sequential enrichment calls."""
    hash_original = compute_dataframe_hash(core_dataframe, CORE_COLUMNS)

    # First enrichment
    result1 = enrich(core_dataframe, indicators=["ema20"], strict=True)
    hash_after_1 = compute_dataframe_hash(result1.enriched, CORE_COLUMNS)

    # Second enrichment on original
    result2 = enrich(core_dataframe, indicators=["atr14"], strict=True)
    hash_after_2 = compute_dataframe_hash(result2.enriched, CORE_COLUMNS)

    # All hashes should match
    assert hash_original == hash_after_1
    assert hash_original == hash_after_2


def test_immutability_verification_detects_violation():
    """Test that immutability violation is detected if core mutated."""
    # This is a theoretical test - actual implementation should never allow this
    # But we verify the guard would detect it if it happened

    df = pd.DataFrame(
        {
            "timestamp_utc": pd.date_range("2024-01-01", periods=10, freq="1min"),
            "open": range(10),
            "high": range(10),
            "low": range(10),
            "close": range(10),
            "volume": [100] * 10,
            "is_gap": [False] * 10,
        }
    )

    hash_before = compute_dataframe_hash(df, CORE_COLUMNS)

    # Manually mutate core (simulating a bug)
    df.loc[0, "close"] = 999

    hash_after = compute_dataframe_hash(df, CORE_COLUMNS)

    # Hashes should differ (violation detected)
    assert hash_before != hash_after
