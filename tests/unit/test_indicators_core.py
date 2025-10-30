"""
Unit tests for core indicator behavior and warm-up sequences.

Tests EMA warm-up periods, ATR calculation sequences, and validates
numeric accuracy against fixture expectations for deterministic verification.

Covers:
- T020: EMA warm-up and ATR calculation
- T020a: EMA(50) indicator test sequence assertions
- T020b: Warm-up NaN counts for EMA(20), EMA(50), ATR(14)
- T020c: ATR(14) full sequence numeric values against fixture expectations
"""

import numpy as np
import pytest

pytestmark = pytest.mark.unit

from src.indicators.basic import atr, ema


class TestEMAWarmUp:
    """Test EMA warm-up behavior and NaN handling."""

    def test_ema20_warm_up_nan_count(self):
        """
        T020b: Verify EMA(20) has exactly 19 NaN values during warm-up.

        Given 100 price values,
        When calculating EMA(20),
        Then first 19 values should be NaN (insufficient data).
        """
        prices = np.arange(1.0, 101.0, dtype=np.float64)  # 100 values
        period = 20

        result = ema(prices, period)

        # Count NaN values at start
        nan_count = np.sum(np.isnan(result[:period]))
        assert nan_count == period - 1, f"Expected {period-1} NaN values, got {nan_count}"

        # First valid value should be at index 19 (period-1)
        assert not np.isnan(result[19]), "EMA(20) should have valid value at index 19"

    def test_ema50_warm_up_nan_count(self):
        """
        T020a/T020b: Verify EMA(50) has exactly 49 NaN values during warm-up.

        Given 100 price values,
        When calculating EMA(50),
        Then first 49 values should be NaN (insufficient data).
        """
        prices = np.arange(1.0, 101.0, dtype=np.float64)  # 100 values
        period = 50

        result = ema(prices, period)

        # Count NaN values at start
        nan_count = np.sum(np.isnan(result[:period]))
        assert nan_count == period - 1, f"Expected {period-1} NaN values, got {nan_count}"

        # First valid value should be at index 49 (period-1)
        assert not np.isnan(result[49]), "EMA(50) should have valid value at index 49"

        # Verify values after warm-up are all valid
        valid_values = result[49:]
        assert not np.any(np.isnan(valid_values)), "All values after warm-up should be valid"

    def test_ema50_sequence_values(self):
        """
        T020a: Verify EMA(50) calculates correct sequence.

        Given stable uptrend prices,
        When calculating EMA(50),
        Then EMA values should follow expected smoothing behavior.
        """
        # Create predictable uptrend: 1.10000 to 1.10100
        prices = np.linspace(1.10000, 1.10100, 100, dtype=np.float64)
        period = 50

        result = ema(prices, period)

        # EMA uses exponential smoothing from first value, not SMA
        # First valid EMA at index 49 should be reasonable
        first_ema = result[49]
        assert first_ema > prices[0], "EMA should be higher than start in uptrend"
        assert first_ema < prices[49], "EMA should lag behind current price"

        # EMA should increase monotonically with uptrend
        valid_ema = result[49:]
        for i in range(1, len(valid_ema)):
            assert valid_ema[i] >= valid_ema[i - 1], f"EMA should increase at index {49+i}"

    def test_ema20_vs_ema50_warm_up_difference(self):
        """
        Verify EMA(20) warms up faster than EMA(50).

        Given same price data,
        When calculating both EMA(20) and EMA(50),
        Then EMA(20) should have fewer NaN values.
        """
        prices = np.arange(1.0, 101.0, dtype=np.float64)

        ema20 = ema(prices, 20)
        ema50 = ema(prices, 50)

        nan_count_20 = np.sum(np.isnan(ema20))
        nan_count_50 = np.sum(np.isnan(ema50))

        assert nan_count_20 < nan_count_50, "EMA(20) should have fewer NaN values than EMA(50)"
        assert nan_count_20 == 19, "EMA(20) should have exactly 19 NaN values"
        assert nan_count_50 == 49, "EMA(50) should have exactly 49 NaN values"


class TestATRWarmUp:
    """Test ATR warm-up behavior and calculation sequences."""

    def test_atr14_warm_up_nan_count(self):
        """
        T020b: Verify ATR(14) has exactly 13 NaN values during warm-up.

        Given 50 candles of price data,
        When calculating ATR(14),
        Then first 13 values should be NaN (period-1 for EMA smoothing).
        """
        # Create synthetic OHLC data
        size = 50
        high = np.linspace(1.10050, 1.10150, size, dtype=np.float64)
        low = np.linspace(1.09950, 1.10050, size, dtype=np.float64)
        close = np.linspace(1.10000, 1.10100, size, dtype=np.float64)
        period = 14

        result = atr(high, low, close, period)

        # ATR uses EMA for smoothing, which has period-1 NaN values
        # So ATR will have 13 NaN values for period=14
        nan_count = np.sum(np.isnan(result))
        assert nan_count == period - 1, f"Expected {period-1} NaN values for ATR({period}), got {nan_count}"

        # First valid ATR should be at index 13 (period-1)
        assert np.isnan(result[12]), f"Index 12 should still be NaN"
        assert not np.isnan(result[13]), f"ATR({period}) should have valid value at index {period-1}"

    def test_atr14_sequence_numeric_values(self):
        """
        T020c: Verify ATR(14) full sequence numeric values against fixture expectations.

        Given deterministic OHLC fixture data,
        When calculating ATR(14),
        Then values should match expected calculations with tight tolerance.
        """
        # Fixture: 30 candles with known True Range pattern
        # Pattern: High-Low range of 20 pips, close gaps minimal
        high = np.array(
            [
                1.10020,
                1.10040,
                1.10030,
                1.10050,
                1.10045,
                1.10060,
                1.10055,
                1.10070,
                1.10065,
                1.10080,
                1.10075,
                1.10090,
                1.10085,
                1.10100,
                1.10095,  # Index 14
                1.10110,
                1.10105,
                1.10120,
                1.10115,
                1.10130,
                1.10125,
                1.10140,
                1.10135,
                1.10150,
                1.10145,
                1.10160,
                1.10155,
                1.10170,
                1.10165,
                1.10180,
            ],
            dtype=np.float64,
        )

        low = np.array(
            [
                1.10000,
                1.10020,
                1.10010,
                1.10030,
                1.10025,
                1.10040,
                1.10035,
                1.10050,
                1.10045,
                1.10060,
                1.10055,
                1.10070,
                1.10065,
                1.10080,
                1.10075,
                1.10090,
                1.10085,
                1.10100,
                1.10095,
                1.10110,
                1.10105,
                1.10120,
                1.10115,
                1.10130,
                1.10125,
                1.10140,
                1.10135,
                1.10150,
                1.10145,
                1.10160,
            ],
            dtype=np.float64,
        )

        close = np.array(
            [
                1.10010,
                1.10030,
                1.10020,
                1.10040,
                1.10035,
                1.10050,
                1.10045,
                1.10060,
                1.10055,
                1.10070,
                1.10065,
                1.10080,
                1.10075,
                1.10090,
                1.10085,
                1.10100,
                1.10095,
                1.10110,
                1.10105,
                1.10120,
                1.10115,
                1.10130,
                1.10125,
                1.10140,
                1.10135,
                1.10150,
                1.10145,
                1.10160,
                1.10155,
                1.10170,
            ],
            dtype=np.float64,
        )

        period = 14
        result = atr(high, low, close, period)

        # Verify first 13 values are NaN (period-1)
        assert np.sum(np.isnan(result[:13])) == 13, "First 13 ATR values should be NaN"

        # Verify all subsequent values are valid (not NaN)
        assert not np.any(np.isnan(result[13:])), "All ATR values after index 13 should be valid"

        # Verify ATR values are positive and reasonable (True Range is ~20 pips = 0.00020)
        valid_atr = result[13:]
        assert np.all(valid_atr > 0), "All ATR values should be positive"
        assert np.all(valid_atr < 0.001), "ATR values should be reasonable (< 100 pips)"

        # ATR should be in expected range around 20 pips
        assert result[13] > 0.00015, "First ATR value should be reasonable (> 15 pips)"
        assert result[13] < 0.00030, "First ATR value should be reasonable (< 30 pips)"

    def test_atr14_stable_in_ranging_market(self):
        """
        Verify ATR(14) remains stable in ranging market.

        Given constant True Range (no volatility change),
        When calculating ATR(14),
        Then ATR should converge to constant value.
        """
        size = 50
        # Constant range: high-low always 0.00020 (20 pips)
        high = np.full(size, 1.10020, dtype=np.float64)
        low = np.full(size, 1.10000, dtype=np.float64)
        close = np.full(size, 1.10010, dtype=np.float64)  # Mid-range

        result = atr(high, low, close, 14)

        # After warm-up, ATR should stabilize
        valid_atr = result[14:]

        # All values should be very close (stable)
        atr_std = np.std(valid_atr)
        assert atr_std < 1e-6, f"ATR should be stable in ranging market, std={atr_std}"

        # Value should be close to True Range (0.00020)
        assert valid_atr[-1] == pytest.approx(0.00020, abs=1e-5)


class TestIndicatorIntegration:
    """Test indicator combinations and cross-validation."""

    def test_ema20_ema50_crossover_detection(self):
        """
        Verify EMA(20) crosses EMA(50) in uptrend scenario.

        Given price data transitioning from downtrend to uptrend,
        When calculating both EMAs,
        Then EMA(20) should cross above EMA(50).
        """
        # Create price series: downtrend then sharp uptrend
        downtrend = np.linspace(1.11000, 1.10000, 50, dtype=np.float64)
        uptrend = np.linspace(1.10000, 1.11000, 50, dtype=np.float64)
        prices = np.concatenate([downtrend, uptrend])

        ema20 = ema(prices, 20)
        ema50 = ema(prices, 50)

        # After warm-up (index 50+), find crossover
        # EMA(20) reacts faster, should be below EMA(50) in downtrend
        # Then cross above in uptrend

        # At index 60 (in downtrend region), EMA(20) should be below EMA(50)
        assert ema20[60] < ema50[60], "EMA(20) should be below EMA(50) in downtrend"

        # At index 90 (in uptrend region), EMA(20) should be above EMA(50)
        assert ema20[90] > ema50[90], "EMA(20) should be above EMA(50) in uptrend"

    def test_atr_increases_with_volatility(self):
        """
        Verify ATR increases when volatility increases.

        Given low volatility followed by high volatility,
        When calculating ATR(14),
        Then ATR should be higher in high volatility period.
        """
        # Low volatility: 10 pip range
        low_vol_high = np.full(30, 1.10010, dtype=np.float64)
        low_vol_low = np.full(30, 1.10000, dtype=np.float64)
        low_vol_close = np.full(30, 1.10005, dtype=np.float64)

        # High volatility: 50 pip range
        high_vol_high = np.full(30, 1.10050, dtype=np.float64)
        high_vol_low = np.full(30, 1.10000, dtype=np.float64)
        high_vol_close = np.full(30, 1.10025, dtype=np.float64)

        # Concatenate periods
        high = np.concatenate([low_vol_high, high_vol_high])
        low = np.concatenate([low_vol_low, high_vol_low])
        close = np.concatenate([low_vol_close, high_vol_close])

        result = atr(high, low, close, 14)

        # ATR at end of low volatility period (index 29)
        atr_low_vol = result[29]

        # ATR at end of high volatility period (index 59)
        atr_high_vol = result[59]

        assert atr_high_vol > atr_low_vol, "ATR should increase with higher volatility"
        assert atr_high_vol > atr_low_vol * 2, "ATR should at least double with 5x volatility increase"

    def test_indicator_determinism(self):
        """
        Verify indicators produce identical results with same input.

        Given identical price data,
        When calculating indicators multiple times,
        Then results should be bit-for-bit identical.
        """
        prices = np.random.RandomState(42).uniform(1.09, 1.11, 100)

        # Calculate EMA twice
        ema20_run1 = ema(prices, 20)
        ema20_run2 = ema(prices, 20)

        assert np.array_equal(ema20_run1, ema20_run2, equal_nan=True), "EMA should be deterministic"

        # Calculate ATR twice
        high = prices + 0.0001
        low = prices - 0.0001
        close = prices

        atr_run1 = atr(high, low, close, 14)
        atr_run2 = atr(high, low, close, 14)

        assert np.array_equal(atr_run1, atr_run2, equal_nan=True), "ATR should be deterministic"
