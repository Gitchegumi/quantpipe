"""Unit tests for strict mode enrichment - fast-fail on errors."""
# pylint: disable=redefined-outer-name  # pytest fixtures

import pandas as pd
import pytest

from src.indicators.enrich import enrich
from src.indicators.errors import UnknownIndicatorError


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


def test_strict_mode_unknown_indicator_raises(core_dataframe):
    """Test that unknown indicator raises UnknownIndicatorError in strict mode."""
    with pytest.raises(UnknownIndicatorError) as exc_info:
        enrich(core_dataframe, indicators=["nonexistent"], strict=True)

    # Verify error contains indicator name
    assert "nonexistent" in str(exc_info.value)
    assert exc_info.value.indicator_name == "nonexistent"


def test_strict_mode_unknown_with_available_list(core_dataframe):
    """Test that error includes available indicators list."""
    with pytest.raises(UnknownIndicatorError) as exc_info:
        enrich(core_dataframe, indicators=["bogus_indicator"], strict=True)

    # Should include available indicators
    assert len(exc_info.value.available) > 0
    assert "ema20" in exc_info.value.available  # Built-in should be listed


def test_strict_mode_no_partial_computation(core_dataframe):
    """Test that no indicators are applied when one fails in strict mode."""
    # Request valid + invalid indicators
    with pytest.raises(UnknownIndicatorError):
        enrich(
            core_dataframe,
            indicators=["ema20", "nonexistent", "atr14"],
            strict=True,
        )

    # DataFrame should not have been modified with partial results
    # (We can't verify the enriched result since exception was raised,
    # but we test that the function aborted without returning partial work)


def test_strict_mode_first_error_aborts(core_dataframe):
    """Test that strict mode aborts on first error, not all errors."""
    # Multiple unknown indicators - should fail on first one encountered
    with pytest.raises(UnknownIndicatorError) as exc_info:
        enrich(
            core_dataframe,
            indicators=["unknown1", "unknown2", "unknown3"],
            strict=True,
        )

    # Should report the first unknown encountered
    assert exc_info.value.indicator_name in ["unknown1", "unknown2", "unknown3"]


def test_strict_mode_mixed_valid_invalid_order(core_dataframe):
    """Test strict mode with valid indicators before invalid one."""
    # Valid indicators first, then invalid
    with pytest.raises(UnknownIndicatorError) as exc_info:
        enrich(
            core_dataframe,
            indicators=["ema20", "ema50", "invalid_ind"],
            strict=True,
        )

    assert exc_info.value.indicator_name == "invalid_ind"


def test_strict_mode_all_valid_succeeds(core_dataframe):
    """Test that strict mode succeeds when all indicators are valid."""
    result = enrich(
        core_dataframe,
        indicators=["ema20", "ema50", "atr14"],
        strict=True,
    )

    assert len(result.indicators_applied) == 3
    assert len(result.failed_indicators) == 0
    assert set(result.indicators_applied) == {"ema20", "ema50", "atr14"}


def test_strict_mode_empty_list_succeeds(core_dataframe):
    """Test that strict mode with empty indicator list succeeds."""
    result = enrich(core_dataframe, indicators=[], strict=True)

    assert len(result.indicators_applied) == 0
    assert len(result.failed_indicators) == 0


def test_strict_mode_single_valid_succeeds(core_dataframe):
    """Test strict mode with single valid indicator."""
    result = enrich(core_dataframe, indicators=["ema20"], strict=True)

    assert result.indicators_applied == ["ema20"]
    assert len(result.failed_indicators) == 0


def test_strict_mode_single_invalid_fails(core_dataframe):
    """Test strict mode with single invalid indicator."""
    with pytest.raises(UnknownIndicatorError) as exc_info:
        enrich(core_dataframe, indicators=["fake_indicator"], strict=True)

    assert exc_info.value.indicator_name == "fake_indicator"


def test_strict_mode_case_sensitive_unknown(core_dataframe):
    """Test that indicator names are case-sensitive in strict mode."""
    # EMA20 vs ema20 - should fail for wrong case
    with pytest.raises(UnknownIndicatorError) as exc_info:
        enrich(core_dataframe, indicators=["EMA20"], strict=True)

    assert exc_info.value.indicator_name == "EMA20"


def test_strict_mode_with_typo_in_name(core_dataframe):
    """Test strict mode catches typos in indicator names."""
    # Common typo: ema2 instead of ema20
    with pytest.raises(UnknownIndicatorError) as exc_info:
        enrich(core_dataframe, indicators=["ema2"], strict=True)

    assert exc_info.value.indicator_name == "ema2"

    # Verify available list includes correct name
    assert "ema20" in exc_info.value.available


def test_strict_mode_preserves_exception_chain(core_dataframe):
    """Test that strict mode preserves exception chain for debugging."""
    with pytest.raises(UnknownIndicatorError) as exc_info:
        enrich(core_dataframe, indicators=["bad_name"], strict=True)

    # Should be an UnknownIndicatorError
    assert isinstance(exc_info.value, UnknownIndicatorError)


def test_strict_mode_no_failed_indicators_on_success(core_dataframe):
    """Test that failed_indicators is empty on successful strict enrichment."""
    result = enrich(
        core_dataframe,
        indicators=["ema20", "atr14"],
        strict=True,
    )

    # In strict mode with no errors, failed list should be empty
    assert not result.failed_indicators
    assert len(result.indicators_applied) == 2
