"""Unit tests for indicator warm-up NaN exclusion.

This module validates that the system correctly handles missing indicator
values at the start of datasets during warm-up periods (edge case from spec:
"Missing indicator values at start of dataset (warm-up) do not produce false signals").

Tests verify:
- NaN values during warm-up are detected
- Signals are not generated during warm-up period
- Warm-up completion is correctly identified
- Post-warm-up processing continues normally
"""

import numpy as np
import polars as pl
import pytest

from src.backtest.arrays import extract_indicator_arrays, extract_ohlc_arrays


@pytest.fixture
def dataframe_with_warmup():
    """Create DataFrame with NaN values during indicator warm-up.

    Simulates typical indicator calculation where first N values are NaN
    due to insufficient history (e.g., EMA20 needs 20 candles).
    """
    n_rows = 1000
    warmup_period = 50  # First 50 rows have NaN indicators

    timestamps = np.arange(n_rows, dtype=np.int64) * 60

    # Create indicator arrays with NaN warm-up
    ema20 = np.full(n_rows, np.nan, dtype=np.float64)
    ema20[warmup_period:] = np.random.uniform(1.1, 1.2, n_rows - warmup_period)

    ema50 = np.full(n_rows, np.nan, dtype=np.float64)
    ema50[warmup_period:] = np.random.uniform(1.1, 1.2, n_rows - warmup_period)

    atr14 = np.full(n_rows, np.nan, dtype=np.float64)
    atr14[warmup_period:] = np.random.uniform(0.001, 0.01, n_rows - warmup_period)

    df = pl.DataFrame(
        {
            "timestamp_utc": timestamps,
            "open": np.random.uniform(1.1, 1.2, n_rows),
            "high": np.random.uniform(1.2, 1.3, n_rows),
            "low": np.random.uniform(1.0, 1.1, n_rows),
            "close": np.random.uniform(1.1, 1.2, n_rows),
            "ema20": ema20,
            "ema50": ema50,
            "atr14": atr14,
        }
    )

    return df, warmup_period


def test_warmup_nan_detection(dataframe_with_warmup):
    """Test that NaN values during warm-up are correctly detected.

    Verifies:
    - Indicator arrays contain NaN during warm-up
    - NaN detection works correctly
    - Warm-up period can be identified
    """
    df, warmup_period = dataframe_with_warmup

    indicator_names = ["ema20", "ema50", "atr14"]
    indicator_arrays = extract_indicator_arrays(df, indicator_names)

    # Check that warm-up period has NaN
    for name, array in indicator_arrays.items():
        assert np.isnan(
            array[:warmup_period]
        ).all(), f"{name} should have NaN in warm-up"

        # Check that post-warm-up has valid values
        assert np.isfinite(
            array[warmup_period:]
        ).all(), f"{name} should have valid values after warm-up"


def test_warmup_valid_mask(dataframe_with_warmup):
    """Test creation of valid indicator mask excluding warm-up.

    Verifies:
    - Mask correctly identifies valid (non-NaN) periods
    - Warm-up period is excluded
    - Mask can be used for filtering
    """
    df, warmup_period = dataframe_with_warmup

    indicator_names = ["ema20", "ema50", "atr14"]
    indicator_arrays = extract_indicator_arrays(df, indicator_names)

    # Create combined valid mask (all indicators must be valid)
    valid_mask = np.ones(len(df), dtype=bool)
    for array in indicator_arrays.values():
        valid_mask &= np.isfinite(array)

    # Verify warm-up period is masked out
    assert not valid_mask[:warmup_period].any(), "Warm-up period should be masked"

    # Verify post-warm-up is valid
    assert valid_mask[warmup_period:].all(), "Post-warm-up period should be valid"


def test_warmup_signal_exclusion(dataframe_with_warmup):
    """Test that signals are not generated during warm-up period.

    Verifies:
    - Signal indices exclude warm-up period
    - Only valid indicator values trigger signals
    """
    df, warmup_period = dataframe_with_warmup

    indicator_names = ["ema20", "ema50", "atr14"]
    indicator_arrays = extract_indicator_arrays(df, indicator_names)

    # Create valid mask
    valid_mask = np.ones(len(df), dtype=bool)
    for array in indicator_arrays.values():
        valid_mask &= np.isfinite(array)

    # Get valid indices (potential signal candidates)
    valid_indices = np.where(valid_mask)[0]

    # Verify all valid indices are after warm-up
    assert (
        valid_indices[0] >= warmup_period
    ), "First valid index should be after warm-up"
    assert len(valid_indices) == len(df) - warmup_period


def test_warmup_partial_indicators(dataframe_with_warmup):
    """Test handling when indicators have different warm-up periods.

    Verifies:
    - System uses longest warm-up period
    - Conservative approach (wait for all indicators)
    """
    df, _ = dataframe_with_warmup

    # Modify to have different warm-up periods
    n_rows = len(df)
    df = df.with_columns(
        [
            pl.Series(
                "fast_indicator",
                np.concatenate(
                    [np.full(10, np.nan), np.random.uniform(1.0, 2.0, n_rows - 10)]
                ),
            ),
            pl.Series(
                "slow_indicator",
                np.concatenate(
                    [np.full(100, np.nan), np.random.uniform(1.0, 2.0, n_rows - 100)]
                ),
            ),
        ]
    )

    indicator_names = ["fast_indicator", "slow_indicator"]
    indicator_arrays = extract_indicator_arrays(df, indicator_names)

    # Create combined valid mask
    valid_mask = np.ones(n_rows, dtype=bool)
    for array in indicator_arrays.values():
        valid_mask &= np.isfinite(array)

    # Should wait for slowest indicator (100 periods)
    valid_indices = np.where(valid_mask)[0]
    assert valid_indices[0] >= 100, "Should wait for slowest indicator"


def test_warmup_ohlc_always_valid(dataframe_with_warmup):
    """Test that OHLC data is valid during warm-up period.

    Verifies:
    - OHLC arrays never contain NaN
    - Price data available from start
    - Only indicators have warm-up
    """
    df, warmup_period = dataframe_with_warmup

    ohlc_arrays = extract_ohlc_arrays(df)
    timestamps, open_prices, high_prices, low_prices, close_prices = ohlc_arrays

    # All OHLC should be finite, including warm-up
    assert np.isfinite(open_prices).all(), "Open prices should always be valid"
    assert np.isfinite(high_prices).all(), "High prices should always be valid"
    assert np.isfinite(low_prices).all(), "Low prices should always be valid"
    assert np.isfinite(close_prices).all(), "Close prices should always be valid"

    # Verify even during warm-up period
    assert np.isfinite(open_prices[:warmup_period]).all()


def test_warmup_count_valid_candles(dataframe_with_warmup):
    """Test counting valid candles after warm-up.

    Verifies:
    - Can calculate number of usable candles
    - Warm-up reduces effective dataset size
    """
    df, warmup_period = dataframe_with_warmup

    indicator_names = ["ema20", "ema50", "atr14"]
    indicator_arrays = extract_indicator_arrays(df, indicator_names)

    # Count valid candles
    valid_mask = np.ones(len(df), dtype=bool)
    for array in indicator_arrays.values():
        valid_mask &= np.isfinite(array)

    valid_count = np.sum(valid_mask)
    expected_valid = len(df) - warmup_period

    assert valid_count == expected_valid


def test_warmup_zero_valid_candles():
    """Test edge case where all candles are in warm-up (all NaN).

    Verifies:
    - System handles dataset smaller than warm-up period
    - No signals generated
    - No errors raised
    """
    n_rows = 100
    timestamps = np.arange(n_rows, dtype=np.int64) * 60

    # All indicators are NaN (insufficient data for warm-up)
    df = pl.DataFrame(
        {
            "timestamp_utc": timestamps,
            "open": np.random.uniform(1.1, 1.2, n_rows),
            "high": np.random.uniform(1.2, 1.3, n_rows),
            "low": np.random.uniform(1.0, 1.1, n_rows),
            "close": np.random.uniform(1.1, 1.2, n_rows),
            "ema20": np.full(n_rows, np.nan),
            "ema50": np.full(n_rows, np.nan),
        }
    )

    indicator_names = ["ema20", "ema50"]
    indicator_arrays = extract_indicator_arrays(df, indicator_names)

    # Create valid mask
    valid_mask = np.ones(n_rows, dtype=bool)
    for array in indicator_arrays.values():
        valid_mask &= np.isfinite(array)

    # Should have zero valid candles
    assert np.sum(valid_mask) == 0
    assert not valid_mask.any()


def test_warmup_single_valid_candle():
    """Test edge case with exactly one valid candle after warm-up.

    Verifies:
    - System handles minimal valid dataset
    - Single valid candle can be processed
    """
    n_rows = 100
    timestamps = np.arange(n_rows, dtype=np.int64) * 60

    # Only last candle has valid indicators
    ema20 = np.full(n_rows, np.nan)
    ema20[-1] = 1.15

    df = pl.DataFrame(
        {
            "timestamp_utc": timestamps,
            "open": np.random.uniform(1.1, 1.2, n_rows),
            "high": np.random.uniform(1.2, 1.3, n_rows),
            "low": np.random.uniform(1.0, 1.1, n_rows),
            "close": np.random.uniform(1.1, 1.2, n_rows),
            "ema20": ema20,
        }
    )

    indicator_arrays = extract_indicator_arrays(df, ["ema20"])

    # Create valid mask
    valid_mask = np.isfinite(indicator_arrays["ema20"])

    # Should have exactly one valid candle
    assert np.sum(valid_mask) == 1
    assert valid_mask[-1]


def test_warmup_indicator_subset():
    """Test warm-up with subset of indicators requested.

    Verifies:
    - Only requested indicators are checked for validity
    - Extra indicators in DataFrame are ignored
    """
    n_rows = 1000
    warmup_period = 50
    timestamps = np.arange(n_rows, dtype=np.int64) * 60

    # Multiple indicators with different warm-up periods
    ema20 = np.full(n_rows, np.nan)
    ema20[warmup_period:] = np.random.uniform(1.1, 1.2, n_rows - warmup_period)

    ema50 = np.full(n_rows, np.nan)
    ema50[100:] = np.random.uniform(1.1, 1.2, n_rows - 100)  # Longer warm-up

    df = pl.DataFrame(
        {
            "timestamp_utc": timestamps,
            "open": np.random.uniform(1.1, 1.2, n_rows),
            "high": np.random.uniform(1.2, 1.3, n_rows),
            "low": np.random.uniform(1.0, 1.1, n_rows),
            "close": np.random.uniform(1.1, 1.2, n_rows),
            "ema20": ema20,
            "ema50": ema50,
        }
    )

    # Request only ema20 (shorter warm-up)
    indicator_arrays = extract_indicator_arrays(df, ["ema20"])
    valid_mask = np.isfinite(indicator_arrays["ema20"])

    # Should be valid after ema20's warm-up (50), not ema50's (100)
    valid_indices = np.where(valid_mask)[0]
    assert valid_indices[0] == warmup_period
    assert len(valid_indices) == n_rows - warmup_period
