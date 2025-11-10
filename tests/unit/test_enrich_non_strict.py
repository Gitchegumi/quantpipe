"""Unit tests for non-strict mode enrichment - collects failures without aborting."""
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


def test_non_strict_mode_unknown_indicator_continues(core_dataframe):
    """Test that unknown indicator doesn't abort in non-strict mode."""
    result = enrich(
        core_dataframe, indicators=["nonexistent"], strict=False
    )

    # Should complete without exception
    assert result is not None
    assert "nonexistent" in result.failed_indicators
    assert len(result.indicators_applied) == 0


def test_non_strict_mode_mixed_valid_invalid(core_dataframe):
    """Test non-strict mode applies valid indicators and skips invalid ones."""
    result = enrich(
        core_dataframe,
        indicators=["ema20", "nonexistent", "atr14"],
        strict=False,
    )

    # Valid indicators should be applied
    assert "ema20" in result.indicators_applied
    assert "atr14" in result.indicators_applied

    # Invalid indicator should be in failed list
    assert "nonexistent" in result.failed_indicators

    # Verify columns
    assert "ema20" in result.enriched.columns
    assert "atr14" in result.enriched.columns


def test_non_strict_mode_collects_all_failures(core_dataframe):
    """Test that non-strict mode collects all failed indicators."""
    result = enrich(
        core_dataframe,
        indicators=["invalid1", "ema20", "invalid2", "atr14", "invalid3"],
        strict=False,
    )

    # All invalid indicators should be in failed list
    assert set(result.failed_indicators) == {"invalid1", "invalid2", "invalid3"}

    # All valid indicators should be applied
    assert set(result.indicators_applied) == {"ema20", "atr14"}


def test_non_strict_mode_all_invalid_returns_core_only(core_dataframe):
    """Test non-strict mode with all invalid indicators returns core DataFrame."""
    result = enrich(
        core_dataframe,
        indicators=["bad1", "bad2", "bad3"],
        strict=False,
    )

    # No indicators applied
    assert len(result.indicators_applied) == 0

    # All should be in failed list
    assert len(result.failed_indicators) == 3
    assert set(result.failed_indicators) == {"bad1", "bad2", "bad3"}

    # Should return core columns only
    assert set(result.enriched.columns) == set(core_dataframe.columns)


def test_non_strict_mode_all_valid_succeeds(core_dataframe):
    """Test non-strict mode with all valid indicators."""
    result = enrich(
        core_dataframe,
        indicators=["ema20", "ema50", "atr14"],
        strict=False,
    )

    # All should be applied
    assert len(result.indicators_applied) == 3
    assert set(result.indicators_applied) == {"ema20", "ema50", "atr14"}

    # None should fail
    assert len(result.failed_indicators) == 0


def test_non_strict_mode_empty_list_succeeds(core_dataframe):
    """Test non-strict mode with empty indicator list."""
    result = enrich(core_dataframe, indicators=[], strict=False)

    assert len(result.indicators_applied) == 0
    assert len(result.failed_indicators) == 0


def test_non_strict_mode_preserves_order_of_valid(core_dataframe):
    """Test that non-strict mode preserves order of valid indicators."""
    result = enrich(
        core_dataframe,
        indicators=["ema50", "invalid", "ema20", "atr14"],
        strict=False,
    )

    # Valid indicators should be applied in order
    assert result.indicators_applied == ["ema50", "ema20", "atr14"]
    assert result.failed_indicators == ["invalid"]


def test_non_strict_mode_partial_success_message(core_dataframe):
    """Test non-strict mode provides useful partial success information."""
    result = enrich(
        core_dataframe,
        indicators=["ema20", "fake1", "atr14", "fake2"],
        strict=False,
    )

    # Should have partial success
    assert len(result.indicators_applied) > 0
    assert len(result.failed_indicators) > 0

    # Verify counts
    assert len(result.indicators_applied) == 2  # ema20, atr14
    assert len(result.failed_indicators) == 2  # fake1, fake2


def test_non_strict_mode_single_valid(core_dataframe):
    """Test non-strict mode with single valid indicator."""
    result = enrich(core_dataframe, indicators=["ema20"], strict=False)

    assert result.indicators_applied == ["ema20"]
    assert len(result.failed_indicators) == 0


def test_non_strict_mode_single_invalid(core_dataframe):
    """Test non-strict mode with single invalid indicator."""
    result = enrich(
        core_dataframe, indicators=["invalid"], strict=False
    )

    assert len(result.indicators_applied) == 0
    assert result.failed_indicators == ["invalid"]


def test_non_strict_mode_runtime_measured(core_dataframe):
    """Test that runtime is measured even with failures in non-strict mode."""
    result = enrich(
        core_dataframe,
        indicators=["ema20", "invalid", "atr14"],
        strict=False,
    )

    # Runtime should be positive
    assert result.runtime_seconds > 0


def test_non_strict_continues_after_multiple_failures(core_dataframe):
    """Test non-strict mode continues even after encountering multiple failures."""
    result = enrich(
        core_dataframe,
        indicators=[
            "bad1",
            "ema20",
            "bad2",
            "bad3",
            "atr14",
            "bad4",
            "ema50",
        ],
        strict=False,
    )

    # Should have 3 valid
    assert len(result.indicators_applied) == 3
    assert set(result.indicators_applied) == {"ema20", "atr14", "ema50"}

    # Should have 4 failed
    assert len(result.failed_indicators) == 4
    assert set(result.failed_indicators) == {"bad1", "bad2", "bad3", "bad4"}


def test_non_strict_mode_no_exception_raised(core_dataframe):
    """Test that non-strict mode never raises exceptions for unknown indicators."""
    # Should not raise despite all being invalid
    result = enrich(
        core_dataframe,
        indicators=["x", "y", "z"],
        strict=False,
    )

    assert result is not None
    assert len(result.failed_indicators) == 3


def test_non_strict_mode_logs_warnings(core_dataframe, caplog):
    """Test that non-strict mode logs warnings for failed indicators."""
    import logging

    caplog.set_level(logging.WARNING)

    enrich(
        core_dataframe,
        indicators=["ema20", "invalid_indicator"],
        strict=False,
    )

    # Should have logged warning about unknown indicator
    assert any("invalid_indicator" in record.message for record in caplog.records)
    assert any("non-strict mode" in record.message for record in caplog.records)
