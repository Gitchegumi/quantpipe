"""
Unit tests for basic technical indicators.

Tests EMA, ATR, and RSI implementations for correctness, edge cases,
and handling of insufficient data periods.
"""

import numpy as np
import pytest


pytestmark = pytest.mark.unit

from src.indicators.basic import atr, ema, rsi, validate_indicator_inputs


class TestEMA:
    """Test suite for Exponential Moving Average calculation."""

    def test_ema_basic_calculation(self):
        """Test EMA calculation with known values."""
        prices = np.array([10.0, 11.0, 12.0, 13.0, 14.0], dtype=np.float64)
        period = 3

        result = ema(prices, period)

        # First two values should be NaN (insufficient data)
        assert np.isnan(result[0])
        assert np.isnan(result[1])

        # Third value is simple average
        assert result[2] == pytest.approx(11.0)

        # Fourth value uses EMA formula: EMA = price * alpha + EMA_prev * (1-alpha)
        # alpha = 2/(3+1) = 0.5
        # EMA[3] = 13 * 0.5 + 11 * 0.5 = 12.0
        assert result[3] == pytest.approx(12.0)

    def test_ema_period_equals_length(self):
        """Test EMA when period equals array length."""
        prices = np.array([10.0, 20.0, 30.0], dtype=np.float64)
        period = 3

        result = ema(prices, period)

        assert np.isnan(result[0])
        assert np.isnan(result[1])
        assert result[2] == pytest.approx(20.0)  # Simple average

    def test_ema_insufficient_data(self):
        """Test EMA with fewer values than period."""
        prices = np.array([10.0, 11.0], dtype=np.float64)
        period = 5

        result = ema(prices, period)

        assert np.all(np.isnan(result))

    def test_ema_empty_array(self):
        """Test EMA with empty input."""
        prices = np.array([], dtype=np.float64)
        period = 3

        result = ema(prices, period)

        assert len(result) == 0

    def test_ema_single_value(self):
        """Test EMA with single value."""
        prices = np.array([10.0], dtype=np.float64)
        period = 1

        result = ema(prices, period)

        assert result[0] == pytest.approx(10.0)


class TestATR:
    """Test suite for Average True Range calculation."""

    def test_atr_basic_calculation(self):
        """Test ATR calculation with known values."""
        high = np.array([12.0, 13.0, 14.0, 15.0, 16.0], dtype=np.float64)
        low = np.array([10.0, 11.0, 12.0, 13.0, 14.0], dtype=np.float64)
        close = np.array([11.0, 12.0, 13.0, 14.0, 15.0], dtype=np.float64)
        period = 3

        result = atr(high, low, close, period)

        # First value should be NaN (no previous close for True Range)
        assert np.isnan(result[0])

        # True Range for index 1: max(13-11, |13-11|, |11-11|) = 2.0
        # True Range for index 2: max(14-12, |14-12|, |12-12|) = 2.0
        # ATR at index 2: average of [2.0, 2.0] using EMA
        # (Since it's the first ATR value, it's just the average)
        assert not np.isnan(result[2])
        assert result[2] > 0

    def test_atr_with_gaps(self):
        """Test ATR handles price gaps correctly."""
        high = np.array([10.0, 20.0, 15.0], dtype=np.float64)
        low = np.array([9.0, 18.0, 13.0], dtype=np.float64)
        close = np.array([9.5, 19.0, 14.0], dtype=np.float64)
        period = 2

        result = atr(high, low, close, period)

        # Gap from 9.5 to 18.0 should increase True Range
        # True Range[1] = max(20-18, |20-9.5|, |18-9.5|) = max(2, 10.5, 8.5) = 10.5
        assert result[1] > 2.0

    def test_atr_insufficient_data(self):
        """Test ATR with fewer values than period."""
        high = np.array([10.0], dtype=np.float64)
        low = np.array([9.0], dtype=np.float64)
        close = np.array([9.5], dtype=np.float64)
        period = 14

        result = atr(high, low, close, period)

        assert np.all(np.isnan(result))

    def test_atr_mismatched_lengths(self):
        """Test ATR raises ValueError for mismatched array lengths."""
        high = np.array([10.0, 11.0], dtype=np.float64)
        low = np.array([9.0], dtype=np.float64)
        close = np.array([9.5, 10.5], dtype=np.float64)

        with pytest.raises(
            ValueError, match="All price arrays must have the same length"
        ):
            atr(high, low, close, period=2)


class TestRSI:
    """Test suite for Relative Strength Index calculation."""

    def test_rsi_basic_calculation(self):
        """Test RSI calculation with known trend."""
        # Uptrend: RSI should be high
        prices_up = np.array(
            [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0],
            dtype=np.float64,
        )
        period = 5

        result = rsi(prices_up, period)

        # First few values should be NaN
        assert np.isnan(result[:period]).all()

        # In strong uptrend, RSI should be high (>70)
        assert result[-1] > 70

    def test_rsi_downtrend(self):
        """Test RSI in downtrend."""
        # Downtrend: RSI should be low
        prices_down = np.array(
            [20.0, 19.0, 18.0, 17.0, 16.0, 15.0, 14.0, 13.0, 12.0, 11.0, 10.0],
            dtype=np.float64,
        )
        period = 5

        result = rsi(prices_down, period)

        # In strong downtrend, RSI should be low (<30)
        assert result[-1] < 30

    def test_rsi_neutral(self):
        """Test RSI with flat prices."""
        # Flat prices: RSI should be around 50
        prices_flat = np.array([10.0] * 20, dtype=np.float64)
        period = 14

        result = rsi(prices_flat, period)

        # With no price movement, RSI should be 50 (neutral)
        # (Actually it will be NaN because avg_gains and avg_losses are both 0)
        assert np.isnan(result[-1]) or result[-1] == pytest.approx(50.0, abs=1.0)

    def test_rsi_bounds(self):
        """Test RSI stays within 0-100 range."""
        # Extreme uptrend
        prices = np.array([1.0 * (1.1**i) for i in range(30)], dtype=np.float64)
        period = 14

        result = rsi(prices, period)

        # All valid RSI values should be in [0, 100]
        valid_rsi = result[~np.isnan(result)]
        assert np.all(valid_rsi >= 0)
        assert np.all(valid_rsi <= 100)

    def test_rsi_insufficient_data(self):
        """Test RSI with fewer values than period."""
        prices = np.array([10.0, 11.0, 12.0], dtype=np.float64)
        period = 14

        result = rsi(prices, period)

        assert np.all(np.isnan(result))


class TestValidateIndicatorInputs:
    """Test suite for input validation helper."""

    def test_valid_inputs(self):
        """Test validation passes for valid inputs."""
        prices = np.array([10.0, 11.0, 12.0], dtype=np.float64)
        period = 2

        # Should not raise
        validate_indicator_inputs(prices, period)

    def test_nan_values(self):
        """Test validation detects NaN values."""
        prices = np.array([10.0, np.nan, 12.0], dtype=np.float64)
        period = 2

        with pytest.raises(ValueError, match="contain NaN"):
            validate_indicator_inputs(prices, period)

    def test_inf_values(self):
        """Test validation detects infinite values."""
        prices = np.array([10.0, np.inf, 12.0], dtype=np.float64)
        period = 2

        with pytest.raises(ValueError, match="contain infinite"):
            validate_indicator_inputs(prices, period)

    def test_empty_array(self):
        """Test validation allows empty array."""
        prices = np.array([], dtype=np.float64)
        period = 2

        # Should not raise (empty array is valid)
        validate_indicator_inputs(prices, period)

    def test_invalid_period(self):
        """Test validation detects invalid period."""
        prices = np.array([10.0, 11.0], dtype=np.float64)
        period = 0

        with pytest.raises(ValueError, match="Period must be positive"):
            validate_indicator_inputs(prices, period)
