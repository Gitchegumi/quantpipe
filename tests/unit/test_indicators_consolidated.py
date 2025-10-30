"""
Consolidated unit tests for technical indicators.

This module consolidates tests from test_indicators_basic.py and
test_indicators_core.py using parameterized tests to reduce duplication
while maintaining comprehensive coverage.

Test categories:
- EMA warm-up periods and calculations
- ATR warm-up periods and true range calculations  
- RSI calculation and bounds
- Indicator edge cases (empty arrays, insufficient data, validation)
- Indicator integration (crossovers, volatility response, determinism)
"""

import numpy as np
import pytest

from src.indicators.basic import atr, ema, rsi, validate_indicator_inputs


pytestmark = pytest.mark.unit


class TestEMAWarmUp:
    """Test EMA warm-up behavior with parameterized periods."""

    @pytest.mark.parametrize(
        "period,expected_nan_count",
        [
            (20, 19),  # EMA(20) - from test_indicators_core.py
            (50, 49),  # EMA(50) - from test_indicators_core.py
        ],
    )
    def test_ema_warm_up_nan_count(self, period, expected_nan_count):
        """
        Test EMA warm-up periods produce correct number of NaN values.

        Given: Price array with sufficient data
        When: Calculating EMA with specified period
        Then: First (period-1) values should be NaN

        Consolidated from:
        - test_indicators_core.py::test_ema20_warm_up_nan_count (T020b)
        - test_indicators_core.py::test_ema50_warm_up_nan_count (T020a/T020b)
        """
        prices = np.arange(1.0, 101.0, dtype=np.float64)  # 100 values

        result = ema(prices, period)

        # Count NaN values at start
        nan_count = np.sum(np.isnan(result[:period]))
        assert (
            nan_count == expected_nan_count
        ), f"Expected {expected_nan_count} NaN values for EMA({period}), got {nan_count}"

        # First valid value should be at index (period-1)
        assert not np.isnan(
            result[period - 1]
        ), f"EMA({period}) should have valid value at index {period-1}"

        # All subsequent values should be valid
        valid_values = result[period - 1 :]
        assert not np.any(
            np.isnan(valid_values)
        ), "All values after warm-up should be valid"

    def test_ema_values_non_nan_after_warmup(self):
        """
        Test EMA produces valid values after warm-up period.

        From test_indicators_core.py (T020).
        """
        prices = np.linspace(1.10000, 1.10100, 100, dtype=np.float64)
        period = 50

        result = ema(prices, period)

        # First (period-1) values should be NaN
        assert np.sum(np.isnan(result[: period - 1])) == period - 1

        # All values after warm-up should be valid
        valid_values = result[period - 1 :]
        assert not np.any(np.isnan(valid_values))

    def test_ema_sequence_uptrend(self):
        """
        Test EMA increases monotonically in uptrend.

        From test_indicators_core.py::test_ema50_sequence_values (T020a).
        """
        prices = np.linspace(1.10000, 1.10100, 100, dtype=np.float64)
        period = 50

        result = ema(prices, period)

        first_ema = result[49]
        assert first_ema > prices[0], "EMA should be higher than start in uptrend"
        assert first_ema < prices[49], "EMA should lag behind current price"

        # EMA should increase monotonically with uptrend
        valid_ema = result[49:]
        for i in range(1, len(valid_ema)):
            assert valid_ema[i] >= valid_ema[i - 1], f"EMA should increase at index {49+i}"


class TestATRWarmUp:
    """Test ATR warm-up behavior and calculation sequences."""

    def test_atr_warm_up_nan_count(self):
        """
        Test ATR(14) produces exactly 13 NaN values during warm-up.

        From test_indicators_core.py::test_atr14_warm_up_nan_count (T020b).
        
        ATR uses EMA for smoothing, which has (period-1) NaN values.
        """
        size = 50
        high = np.linspace(1.10050, 1.10150, size, dtype=np.float64)
        low = np.linspace(1.09950, 1.10050, size, dtype=np.float64)
        close = np.linspace(1.10000, 1.10100, size, dtype=np.float64)
        period = 14

        result = atr(high, low, close, period)

        nan_count = np.sum(np.isnan(result))
        assert (
            nan_count == period - 1
        ), f"Expected {period-1} NaN values for ATR({period}), got {nan_count}"

        # First valid ATR should be at index 13 (period-1)
        assert np.isnan(result[12]), "Index 12 should still be NaN"
        assert not np.isnan(result[13]), f"ATR({period}) should have valid value at index {period-1}"

    def test_atr_values_positive_after_warmup(self):
        """
        Test ATR produces positive values after warm-up.

        From test_indicators_core.py::test_atr14_sequence_numeric_values (T020c).
        """
        # Create fixture with known True Range
        high = np.array(
            [
                1.10020, 1.10040, 1.10030, 1.10050, 1.10045,
                1.10060, 1.10055, 1.10070, 1.10065, 1.10080,
                1.10075, 1.10090, 1.10085, 1.10100, 1.10095,
                1.10110, 1.10105, 1.10120, 1.10115, 1.10130,
            ],
            dtype=np.float64,
        )
        low = np.array(
            [
                1.10000, 1.10020, 1.10010, 1.10030, 1.10025,
                1.10040, 1.10035, 1.10050, 1.10045, 1.10060,
                1.10055, 1.10070, 1.10065, 1.10080, 1.10075,
                1.10090, 1.10085, 1.10100, 1.10095, 1.10110,
            ],
            dtype=np.float64,
        )
        close = np.array(
            [
                1.10010, 1.10030, 1.10020, 1.10040, 1.10035,
                1.10050, 1.10045, 1.10060, 1.10055, 1.10070,
                1.10065, 1.10080, 1.10075, 1.10090, 1.10085,
                1.10100, 1.10095, 1.10110, 1.10105, 1.10120,
            ],
            dtype=np.float64,
        )
        period = 14

        result = atr(high, low, close, period)

        # Verify first 13 values are NaN
        assert np.sum(np.isnan(result[:13])) == 13

        # Verify all subsequent values are valid and positive
        valid_atr = result[13:]
        assert not np.any(np.isnan(valid_atr)), "All ATR values after index 13 should be valid"
        assert np.all(valid_atr > 0), "All ATR values should be positive"
        assert np.all(valid_atr < 0.001), "ATR values should be reasonable (< 100 pips)"


class TestIndicatorEdgeCases:
    """Test indicator behavior with edge case inputs."""

    @pytest.mark.parametrize(
        "indicator,params,array_type,expected_behavior",
        [
            ("ema", {"period": 5}, "insufficient", "all_nan"),
            ("ema", {"period": 1}, "single", "valid_value"),
            ("rsi", {"period": 14}, "insufficient", "all_nan"),
        ],
    )
    def test_indicator_edge_cases(self, indicator, params, array_type, expected_behavior):
        """
        Test indicators handle edge case inputs correctly.

        Consolidated from test_indicators_basic.py:
        - test_ema_insufficient_data
        - test_ema_single_value
        - test_rsi_insufficient_data
        
        Note: Empty array test removed - indicators now raise ValueError on empty input.
        """
        # Create test arrays based on array_type
        if array_type == "insufficient":
            prices = np.array([10.0, 11.0], dtype=np.float64)
        elif array_type == "single":
            prices = np.array([10.0], dtype=np.float64)
        else:
            raise ValueError(f"Unknown array_type: {array_type}")

        # Call appropriate indicator
        if indicator == "ema":
            result = ema(prices, params["period"])
        elif indicator == "rsi":
            result = rsi(prices, params["period"])
        else:
            raise ValueError(f"Unknown indicator: {indicator}")

        # Verify expected behavior
        if expected_behavior == "all_nan":
            assert np.all(np.isnan(result)), "Insufficient data should produce all NaN"
        elif expected_behavior == "valid_value":
            assert not np.isnan(result[0]), "Single value should produce valid result"
        else:
            raise ValueError(f"Unknown expected_behavior: {expected_behavior}")

    def test_atr_mismatched_lengths(self):
        """
        Test ATR raises ValueError for mismatched array lengths.

        From test_indicators_basic.py.
        """
        high = np.array([10.0, 11.0], dtype=np.float64)
        low = np.array([9.0], dtype=np.float64)
        close = np.array([9.5, 10.5], dtype=np.float64)

        with pytest.raises(ValueError, match="High, low, and close arrays must have the same length"):
            atr(high, low, close, period=2)

    def test_rsi_bounds(self):
        """
        Test RSI stays within 0-100 range.

        From test_indicators_basic.py.
        """
        # Extreme uptrend
        prices = np.array([1.0 * (1.1**i) for i in range(30)], dtype=np.float64)
        period = 14

        result = rsi(prices, period)

        # All valid RSI values should be in [0, 100]
        valid_rsi = result[~np.isnan(result)]
        assert np.all(valid_rsi >= 0), "RSI values should be >= 0"
        assert np.all(valid_rsi <= 100), "RSI values should be <= 100"


class TestInputValidation:
    """Test input validation helper functions."""

    def test_valid_inputs(self):
        """
        Test validation passes for valid inputs.

        From test_indicators_basic.py::TestValidateIndicatorInputs.
        """
        prices = np.array([10.0, 11.0, 12.0], dtype=np.float64)
        period = 2

        # Should not raise
        validate_indicator_inputs(prices, period)

    @pytest.mark.parametrize(
        "prices,period,error_match",
        [
            (np.array([10.0, np.nan, 12.0]), 2, "contains NaN"),
            (np.array([10.0, np.inf, 12.0]), 2, "contains infinite"),
            (np.array([10.0, 11.0]), 0, "Period must be >= 1"),
        ],
    )
    def test_invalid_inputs(self, prices, period, error_match):
        """
        Test validation detects invalid inputs.

        Parameterized test combining:
        - test_nan_values
        - test_inf_values
        - test_invalid_period
        
        From test_indicators_basic.py::TestValidateIndicatorInputs.
        """
        with pytest.raises(ValueError, match=error_match):
            validate_indicator_inputs(prices, period)

    def test_empty_array_raises(self):
        """
        Test validation rejects empty arrays (min_length default is 2).

        From test_indicators_basic.py::TestValidateIndicatorInputs::test_empty_array.
        Updated to match actual validator behavior - empty arrays are rejected by default.
        """
        prices = np.array([], dtype=np.float64)
        period = 2

        # Should raise ValueError due to min_length check
        with pytest.raises(ValueError, match="must have at least 2 elements"):
            validate_indicator_inputs(prices, period)


class TestIndicatorIntegration:
    """Test indicator interactions and integration scenarios."""

    def test_ema_crossover_detection(self):
        """
        Test EMA(20) crosses EMA(50) in uptrend scenario.

        From test_indicators_core.py::test_ema20_ema50_crossover_detection.
        """
        # Create price series: downtrend then sharp uptrend
        downtrend = np.linspace(1.11000, 1.10000, 50, dtype=np.float64)
        uptrend = np.linspace(1.10000, 1.11000, 50, dtype=np.float64)
        prices = np.concatenate([downtrend, uptrend])

        ema20 = ema(prices, 20)
        ema50 = ema(prices, 50)

        # At index 60 (in downtrend region), EMA(20) should be below EMA(50)
        assert ema20[60] < ema50[60], "EMA(20) should be below EMA(50) in downtrend"

        # At index 90 (in uptrend region), EMA(20) should be above EMA(50)
        assert ema20[90] > ema50[90], "EMA(20) should be above EMA(50) in uptrend"

    def test_atr_increases_with_volatility(self):
        """
        Test ATR increases when volatility increases.

        From test_indicators_core.py::test_atr_increases_with_volatility.
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
        assert (
            atr_high_vol > atr_low_vol * 2
        ), "ATR should at least double with 5x volatility increase"

    def test_indicator_determinism(self):
        """
        Test indicators produce identical results with same input.

        From test_indicators_core.py::test_indicator_determinism.
        """
        np.random.seed(42)
        prices = np.random.uniform(1.09, 1.11, 100)

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


class TestRSICalculation:
    """Test RSI calculation from test_indicators_basic.py."""

    @pytest.mark.parametrize(
        "price_type,expected_range",
        [
            ("uptrend", (70, 100)),  # Strong uptrend: RSI > 70
            ("downtrend", (0, 30)),  # Strong downtrend: RSI < 30
        ],
    )
    def test_rsi_trend_detection(self, price_type, expected_range):
        """
        Test RSI calculation in uptrend and downtrend.

        Consolidated from test_indicators_basic.py:
        - test_rsi_basic_calculation
        - test_rsi_downtrend
        """
        period = 5

        if price_type == "uptrend":
            prices = np.array(
                [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0],
                dtype=np.float64,
            )
        else:  # downtrend
            prices = np.array(
                [20.0, 19.0, 18.0, 17.0, 16.0, 15.0, 14.0, 13.0, 12.0, 11.0, 10.0],
                dtype=np.float64,
            )

        result = rsi(prices, period)

        # First few values should be NaN
        assert np.isnan(result[:period]).all()

        # RSI should be in expected range
        assert expected_range[0] <= result[-1] <= expected_range[1], (
            f"RSI for {price_type} should be in range {expected_range}, got {result[-1]}"
        )
