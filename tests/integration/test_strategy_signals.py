"""
Integration tests for strategy signal generation (T021).

This module validates entry and exit signal generation for both long and short
trend pullback strategies. Tests verify that signals are generated only when
all required conditions are met:

Long Entry:
- Uptrend: EMA(20) > EMA(50)
- Pullback: Price pullback to EMA(20) zone, RSI < 30 or StochRSI < 0.2
- Reversal: Bullish candlestick pattern + momentum turn

Short Entry:
- Downtrend: EMA(20) < EMA(50)
- Pullback: Price rally to EMA(20) zone, RSI > 70 or StochRSI > 0.8
- Reversal: Bearish candlestick pattern + momentum turn

Tests use synthetic candle fixtures with known patterns to validate deterministic
signal generation.
"""

# pylint: disable=redefined-outer-name

import logging

import numpy as np
import pytest

from src.indicators.basic import atr, ema, rsi
from src.models.core import Candle
from src.strategy.id_factory import compute_parameters_hash
from src.strategy.trend_pullback.signal_generator import (
    generate_long_signals,
    generate_short_signals,
)


pytestmark = pytest.mark.integration

logger = logging.getLogger(__name__)


def _compute_stochastic_rsi(rsi_values: np.ndarray, period: int = 14) -> np.ndarray:
    """
    Compute Stochastic RSI from RSI values.

    Stochastic RSI = (RSI - min(RSI, period)) / (max(RSI, period) - min(RSI, period))

    Args:
        rsi_values: Array of RSI values (0-100).
        period: Lookback period for min/max calculation.

    Returns:
        Array of Stochastic RSI values (0-1 range), NaN for insufficient data.
    """
    result = np.full_like(rsi_values, np.nan)

    for i in range(period - 1, len(rsi_values)):
        window = rsi_values[i - period + 1 : i + 1]
        if np.any(np.isnan(window)):
            continue

        min_rsi = np.min(window)
        max_rsi = np.max(window)

        # Avoid division by zero
        if max_rsi - min_rsi == 0:
            result[i] = 0.5  # Neutral value when RSI is flat
        else:
            result[i] = (rsi_values[i] - min_rsi) / (max_rsi - min_rsi)

    return result


@pytest.fixture()
def long_setup_candles():
    """
    Create deterministic candle sequence showing long entry setup.

    Pattern:
    - Candles 0-199: Strong uptrend established (EMA20 > EMA50)
    - Candles 200-217: Pullback (declining prices, RSI < 30)
    - Candles 218-220: Bullish reversal (bullish engulfing pattern at END)

    Returns:
        List[Candle]: 221 candles with computed indicators.
    """
    from datetime import UTC, datetime, timedelta

    candles = []
    timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)

    # Price arrays for indicator calculation
    open_prices = []
    high_prices = []
    low_prices = []
    close_prices = []

    # Phase 1: Strong uptrend (200 candles) to maintain EMA20 > EMA50
    base_price = 1.10000
    for i in range(200):
        open_price = base_price + (i * 0.00020)
        close_price = open_price + 0.00025
        high = close_price + 0.00005
        low = open_price - 0.00005

        open_prices.append(open_price)
        high_prices.append(high)
        low_prices.append(low)
        close_prices.append(close_price)

        timestamp += timedelta(minutes=5)

    # Phase 2: Moderate pullback (18 candles) to get RSI < 30
    peak_price = close_prices[-1]
    for i in range(18):
        open_price = peak_price - (i * 0.00030)
        close_price = open_price - 0.00035
        high = open_price + 0.00005
        low = close_price - 0.00010

        open_prices.append(open_price)
        high_prices.append(high)
        low_prices.append(low)
        close_prices.append(close_price)

        timestamp += timedelta(minutes=5)

    # Phase 3: Reversal pattern (3 candles) - setup for bullish engulfing
    # Candle 1: small bearish (part of pullback)
    open_price = close_prices[-1]
    close_price = open_price - 0.00005
    high = open_price + 0.00003
    low = close_price - 0.00003

    open_prices.append(open_price)
    high_prices.append(high)
    low_prices.append(low)
    close_prices.append(close_price)

    timestamp += timedelta(minutes=5)

    # Candle 2: small bearish (setup for engulfing)
    prev_open = close_prices[-1]
    prev_close = prev_open - 0.00008  # Bearish
    high = prev_open + 0.00002
    low = prev_close - 0.00002

    open_prices.append(prev_open)
    high_prices.append(high)
    low_prices.append(low)
    close_prices.append(prev_close)

    timestamp += timedelta(minutes=5)

    # Candle 3: bullish engulfing (reversal signal)
    curr_open = prev_close - 0.00005  # Open below previous close
    curr_close = prev_open + 0.00010  # Close above previous open (engulfs)
    high = curr_close + 0.00005
    low = curr_open - 0.00003

    open_prices.append(curr_open)
    high_prices.append(high)
    low_prices.append(low)
    close_prices.append(curr_close)

    timestamp += timedelta(minutes=5)

    # Convert to numpy arrays for indicator calculation
    open_arr = np.array(open_prices, dtype=np.float64)
    high_arr = np.array(high_prices, dtype=np.float64)
    low_arr = np.array(low_prices, dtype=np.float64)
    close_arr = np.array(close_prices, dtype=np.float64)

    # Compute indicators
    ema20_arr = ema(close_arr, 20)
    ema50_arr = ema(close_arr, 50)
    rsi_arr = rsi(close_arr, 14)
    atr_arr = atr(high_arr, low_arr, close_arr, 14)
    stoch_rsi_arr = _compute_stochastic_rsi(rsi_arr, 14)

    # Create Candle objects - reset timestamp
    timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    for i, close_val in enumerate(close_arr):
        candle = Candle(
            timestamp_utc=timestamp,
            open=open_arr[i],
            high=high_arr[i],
            low=low_arr[i],
            close=close_val,
            volume=1000,
            ema20=ema20_arr[i],
            ema50=ema50_arr[i],
            rsi=rsi_arr[i],
            atr=atr_arr[i],
            stoch_rsi=(
                float(stoch_rsi_arr[i]) if not np.isnan(stoch_rsi_arr[i]) else None
            ),
        )
        candles.append(candle)

        timestamp += timedelta(minutes=5)

    return candles


@pytest.fixture()
def short_setup_candles():
    """
    Create deterministic candle sequence showing short entry setup.

    Pattern:
    - Candles 0-199: Strong downtrend established (EMA20 < EMA50)
    - Candles 200-217: Pullback rally (rising prices, RSI > 70)
    - Candles 218-220: Bearish reversal (bearish engulfing pattern at END)

    Returns:
        List[Candle]: 221 candles with computed indicators.
    """
    from datetime import UTC, datetime, timedelta

    candles = []
    timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)

    # Price arrays for indicator calculation
    open_prices = []
    high_prices = []
    low_prices = []
    close_prices = []

    # Phase 1: Strong downtrend (200 candles) to maintain EMA20 < EMA50
    base_price = 1.10000
    for i in range(200):
        open_price = base_price - (i * 0.00020)
        close_price = open_price - 0.00025
        high = open_price + 0.00005
        low = close_price - 0.00005

        open_prices.append(open_price)
        high_prices.append(high)
        low_prices.append(low)
        close_prices.append(close_price)

        timestamp += timedelta(minutes=5)

    # Phase 2: Moderate pullback rally (18 candles) to get RSI > 70
    trough_price = close_prices[-1]
    for i in range(18):
        open_price = trough_price + (i * 0.00030)
        close_price = open_price + 0.00035
        high = close_price + 0.00010
        low = open_price - 0.00005

        open_prices.append(open_price)
        high_prices.append(high)
        low_prices.append(low)
        close_prices.append(close_price)

        timestamp += timedelta(minutes=5)

    # Phase 3: Reversal pattern (3 candles) - setup for bearish engulfing
    # Candle 1: small bullish (part of pullback)
    open_price = close_prices[-1]
    close_price = open_price + 0.00005
    high = close_price + 0.00003
    low = open_price - 0.00003

    open_prices.append(open_price)
    high_prices.append(high)
    low_prices.append(low)
    close_prices.append(close_price)

    timestamp += timedelta(minutes=5)

    # Candle 2: small bullish (setup for engulfing)
    prev_open = close_prices[-1]
    prev_close = prev_open + 0.00008  # Bullish
    high = prev_close + 0.00002
    low = prev_open - 0.00002

    open_prices.append(prev_open)
    high_prices.append(high)
    low_prices.append(low)
    close_prices.append(prev_close)

    timestamp += timedelta(minutes=5)

    # Candle 3: bearish engulfing (reversal signal)
    curr_open = prev_close + 0.00005  # Open above previous close
    curr_close = prev_open - 0.00010  # Close below previous open (engulfs)
    high = curr_open + 0.00003
    low = curr_close - 0.00005

    open_prices.append(curr_open)
    high_prices.append(high)
    low_prices.append(low)
    close_prices.append(curr_close)

    timestamp += timedelta(minutes=5)

    # Convert to numpy arrays for indicator calculation
    open_arr = np.array(open_prices, dtype=np.float64)
    high_arr = np.array(high_prices, dtype=np.float64)
    low_arr = np.array(low_prices, dtype=np.float64)
    close_arr = np.array(close_prices, dtype=np.float64)

    # Compute indicators
    ema20_arr = ema(close_arr, 20)
    ema50_arr = ema(close_arr, 50)
    rsi_arr = rsi(close_arr, 14)
    atr_arr = atr(high_arr, low_arr, close_arr, 14)
    stoch_rsi_arr = _compute_stochastic_rsi(rsi_arr, 14)

    # Create Candle objects - reset timestamp
    timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    for i, close_val in enumerate(close_arr):
        candle = Candle(
            timestamp_utc=timestamp,
            open=open_arr[i],
            high=high_arr[i],
            low=low_arr[i],
            close=close_val,
            volume=1000,
            ema20=ema20_arr[i],
            ema50=ema50_arr[i],
            rsi=rsi_arr[i],
            atr=atr_arr[i],
            stoch_rsi=(
                float(stoch_rsi_arr[i]) if not np.isnan(stoch_rsi_arr[i]) else None
            ),
        )
        candles.append(candle)

        timestamp += timedelta(minutes=5)

    return candles


@pytest.fixture()
def default_parameters():
    """
    Return default strategy parameters for signal generation tests.

    Returns:
        dict: Strategy parameters with standard values.
    """
    return {
        "pair": "EURUSD",
        "ema_fast": 20,
        "ema_slow": 50,
        "rsi_period": 14,
        "rsi_oversold": 30.0,
        "rsi_overbought": 70.0,
        "stoch_rsi_low": 0.2,
        "stoch_rsi_high": 0.8,
        "stop_loss_atr_multiplier": 2.0,
        "position_risk_pct": 0.25,
        "trend_cross_count_threshold": 3,
        "pullback_max_age": 20,
        "min_candles_reversal": 3,
    }


class TestLongSignalGeneration:
    """Test long signal generation conditions."""

    def test_long_signal_generated_with_all_conditions(
        self, long_setup_candles, default_parameters
    ):
        """
        T021: Verify long signal generated when all conditions met.

        Given candles showing uptrend + pullback + reversal,
        When calling generate_long_signals,
        Then exactly one long signal should be generated.
        """
        signals = generate_long_signals(long_setup_candles, default_parameters)

        assert len(signals) == 1, "Should generate exactly one long signal"
        signal = signals[0]
        assert signal.direction == "LONG"
        assert signal.pair == "EURUSD"
        assert signal.entry_price > 0
        assert signal.initial_stop_price > 0
        assert signal.initial_stop_price < signal.entry_price

    def test_long_signal_not_generated_without_uptrend(self, default_parameters):
        """
        T021: Verify no long signal generated without uptrend.

        Given candles showing sideways/downtrend,
        When calling generate_long_signals,
        Then no signals should be generated.
        """
        from datetime import UTC, datetime

        # Create sideways market (EMA20 ≈ EMA50)
        candles = []
        timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)

        open_prices = []
        high_prices = []
        low_prices = []
        close_prices = []

        base_price = 1.10000
        for i in range(100):
            # Oscillate around base price
            open_price = base_price + (0.00010 if i % 2 == 0 else -0.00010)
            close_price = base_price + (0.00005 if i % 2 == 0 else -0.00005)
            high = max(open_price, close_price) + 0.00005
            low = min(open_price, close_price) - 0.00005

            open_prices.append(open_price)
            high_prices.append(high)
            low_prices.append(low)
            close_prices.append(close_price)

            timestamp = timestamp.replace(hour=(timestamp.hour + 1) % 24)
            if timestamp.hour == 0:
                timestamp = timestamp.replace(day=timestamp.day + 1)

        # Compute indicators
        open_arr = np.array(open_prices, dtype=np.float64)
        high_arr = np.array(high_prices, dtype=np.float64)
        low_arr = np.array(low_prices, dtype=np.float64)
        close_arr = np.array(close_prices, dtype=np.float64)

        ema20_arr = ema(close_arr, 20)
        ema50_arr = ema(close_arr, 50)
        rsi_arr = rsi(close_arr, 14)
        atr_arr = atr(high_arr, low_arr, close_arr, 14)
        stoch_rsi_arr = _compute_stochastic_rsi(rsi_arr, 14)

        # Create candles
        timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        for i, close_val in enumerate(close_arr):
            candle = Candle(
                timestamp_utc=timestamp,
                open=open_arr[i],
                high=high_arr[i],
                low=low_arr[i],
                close=close_val,
                volume=1000,
                ema20=ema20_arr[i],
                ema50=ema50_arr[i],
                rsi=rsi_arr[i],
                atr=atr_arr[i],
                stoch_rsi=(
                    float(stoch_rsi_arr[i]) if not np.isnan(stoch_rsi_arr[i]) else None
                ),
            )
            candles.append(candle)

            timestamp = timestamp.replace(hour=(timestamp.hour + 1) % 24)
            if timestamp.hour == 0:
                timestamp = timestamp.replace(day=timestamp.day + 1)

        signals = generate_long_signals(candles, default_parameters)
        assert len(signals) == 0, "Should not generate signal without uptrend"

    def test_long_signal_requires_valid_entry_and_stop(
        self, long_setup_candles, default_parameters
    ):
        """
        T021: Verify long signal has valid entry and stop prices.

        Given successful long signal generation,
        When inspecting signal fields,
        Then entry price should be latest close,
        And stop price should be entry - (ATR * multiplier).
        """
        signals = generate_long_signals(long_setup_candles, default_parameters)

        assert len(signals) == 1
        signal = signals[0]

        latest_candle = long_setup_candles[-1]
        assert signal.entry_price == pytest.approx(latest_candle.close, abs=1e-6)

        # Stop should be below entry by ATR multiple
        expected_stop_distance = (
            latest_candle.atr * default_parameters["stop_loss_atr_multiplier"]
        )
        expected_stop = signal.entry_price - expected_stop_distance
        assert signal.initial_stop_price == pytest.approx(expected_stop, abs=1e-6)


class TestShortSignalGeneration:
    """Test short signal generation conditions."""

    def test_short_signal_generated_with_all_conditions(
        self, short_setup_candles, default_parameters
    ):
        """
        T021: Verify short signal generated when all conditions met.

        Given candles showing downtrend + pullback rally + reversal,
        When calling generate_short_signals,
        Then exactly one short signal should be generated.
        """
        signals = generate_short_signals(short_setup_candles, default_parameters)

        assert len(signals) == 1, "Should generate exactly one short signal"
        signal = signals[0]
        assert signal.direction == "SHORT"
        assert signal.pair == "EURUSD"
        assert signal.entry_price > 0
        assert signal.initial_stop_price > 0
        assert signal.initial_stop_price > signal.entry_price

    def test_short_signal_not_generated_without_downtrend(self, default_parameters):
        """
        T021: Verify no short signal generated without downtrend.

        Given candles showing sideways/uptrend,
        When calling generate_short_signals,
        Then no signals should be generated.
        """
        from datetime import UTC, datetime

        # Create sideways market (EMA20 ≈ EMA50)
        candles = []
        timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)

        open_prices = []
        high_prices = []
        low_prices = []
        close_prices = []

        base_price = 1.10000
        for i in range(100):
            # Oscillate around base price
            open_price = base_price + (0.00010 if i % 2 == 0 else -0.00010)
            close_price = base_price + (0.00005 if i % 2 == 0 else -0.00005)
            high = max(open_price, close_price) + 0.00005
            low = min(open_price, close_price) - 0.00005

            open_prices.append(open_price)
            high_prices.append(high)
            low_prices.append(low)
            close_prices.append(close_price)

            timestamp = timestamp.replace(hour=(timestamp.hour + 1) % 24)
            if timestamp.hour == 0:
                timestamp = timestamp.replace(day=timestamp.day + 1)

        # Compute indicators
        open_arr = np.array(open_prices, dtype=np.float64)
        high_arr = np.array(high_prices, dtype=np.float64)
        low_arr = np.array(low_prices, dtype=np.float64)
        close_arr = np.array(close_prices, dtype=np.float64)

        ema20_arr = ema(close_arr, 20)
        ema50_arr = ema(close_arr, 50)
        rsi_arr = rsi(close_arr, 14)
        atr_arr = atr(high_arr, low_arr, close_arr, 14)
        stoch_rsi_arr = _compute_stochastic_rsi(rsi_arr, 14)

        # Create candles
        timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        for i, close_val in enumerate(close_arr):
            candle = Candle(
                timestamp_utc=timestamp,
                open=open_arr[i],
                high=high_arr[i],
                low=low_arr[i],
                close=close_val,
                volume=1000,
                ema20=ema20_arr[i],
                ema50=ema50_arr[i],
                rsi=rsi_arr[i],
                atr=atr_arr[i],
                stoch_rsi=(
                    float(stoch_rsi_arr[i]) if not np.isnan(stoch_rsi_arr[i]) else None
                ),
            )
            candles.append(candle)

            timestamp = timestamp.replace(hour=(timestamp.hour + 1) % 24)
            if timestamp.hour == 0:
                timestamp = timestamp.replace(day=timestamp.day + 1)

        signals = generate_short_signals(candles, default_parameters)
        assert len(signals) == 0, "Should not generate signal without downtrend"

    def test_short_signal_requires_valid_entry_and_stop(
        self, short_setup_candles, default_parameters
    ):
        """
        T021: Verify short signal has valid entry and stop prices.

        Given successful short signal generation,
        When inspecting signal fields,
        Then entry price should be latest close,
        And stop price should be entry + (ATR * multiplier).
        """
        signals = generate_short_signals(short_setup_candles, default_parameters)

        assert len(signals) == 1
        signal = signals[0]

        latest_candle = short_setup_candles[-1]
        assert signal.entry_price == pytest.approx(latest_candle.close, abs=1e-6)

        # Stop should be above entry by ATR multiple
        expected_stop_distance = (
            latest_candle.atr * default_parameters["stop_loss_atr_multiplier"]
        )
        expected_stop = signal.entry_price + expected_stop_distance
        assert signal.initial_stop_price == pytest.approx(expected_stop, abs=1e-6)


class TestSignalDeterminism:
    """Test signal generation determinism."""

    def test_long_signals_deterministic_across_runs(
        self, long_setup_candles, default_parameters
    ):
        """
        T021: Verify long signal generation is deterministic.

        Given identical candle inputs,
        When calling generate_long_signals multiple times,
        Then signals should be identical (same ID, prices, timestamps).
        """
        # Compute parameters hash once for all runs
        params_hash = compute_parameters_hash(default_parameters)

        signals1 = generate_long_signals(
            long_setup_candles, default_parameters, params_hash
        )
        signals2 = generate_long_signals(
            long_setup_candles, default_parameters, params_hash
        )
        signals3 = generate_long_signals(
            long_setup_candles, default_parameters, params_hash
        )

        assert len(signals1) == len(signals2) == len(signals3) == 1

        # Verify all signals are identical
        assert signals1[0].id == signals2[0].id == signals3[0].id
        assert (
            signals1[0].entry_price
            == signals2[0].entry_price
            == signals3[0].entry_price
        )
        assert (
            signals1[0].initial_stop_price
            == signals2[0].initial_stop_price
            == signals3[0].initial_stop_price
        )
        assert (
            signals1[0].timestamp_utc
            == signals2[0].timestamp_utc
            == signals3[0].timestamp_utc
        )

    def test_short_signals_deterministic_across_runs(
        self, short_setup_candles, default_parameters
    ):
        """
        T021: Verify short signal generation is deterministic.

        Given identical candle inputs,
        When calling generate_short_signals multiple times,
        Then signals should be identical (same ID, prices, timestamps).
        """
        # Compute parameters hash once for all runs
        params_hash = compute_parameters_hash(default_parameters)

        signals1 = generate_short_signals(
            short_setup_candles, default_parameters, params_hash
        )
        signals2 = generate_short_signals(
            short_setup_candles, default_parameters, params_hash
        )
        signals3 = generate_short_signals(
            short_setup_candles, default_parameters, params_hash
        )

        assert len(signals1) == len(signals2) == len(signals3) == 1

        # Verify all signals are identical
        assert signals1[0].id == signals2[0].id == signals3[0].id
        assert (
            signals1[0].entry_price
            == signals2[0].entry_price
            == signals3[0].entry_price
        )
        assert (
            signals1[0].initial_stop_price
            == signals2[0].initial_stop_price
            == signals3[0].initial_stop_price
        )
        assert (
            signals1[0].timestamp_utc
            == signals2[0].timestamp_utc
            == signals3[0].timestamp_utc
        )
