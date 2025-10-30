import pytest


pytestmark = pytest.mark.unit
"""
Unit tests for reversal pattern detection logic.

Tests bullish and bearish candlestick patterns (engulfing, hammer, shooting star)
and momentum turn confirmation for pullback reversal detection.
"""

from datetime import UTC, datetime, timedelta

from src.models.core import Candle, PullbackState
from src.strategy.trend_pullback.reversal import (
    _detect_bearish_reversal,
    _detect_bullish_reversal,
    _is_bearish_engulfing,
    _is_bullish_engulfing,
    _is_hammer,
    _is_shooting_star,
    detect_reversal,
)


class TestBullishEngulfingPattern:
    """Tests for bullish engulfing candlestick pattern recognition."""

    def test_bullish_engulfing_valid_pattern(self):
        """
        Given a small bearish candle followed by larger bullish candle,
        When checking for bullish engulfing,
        Then should return True.
        """
        timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)

        # Previous: small bearish candle
        prev_candle = Candle(
            timestamp_utc=timestamp,
            open=1.10000,
            high=1.10010,
            low=1.09980,
            close=1.09990,  # Close < open (bearish)
            volume=1000,
            ema20=1.10000,
            ema50=1.09900,
            atr=0.00050,
            rsi=35.0,
            stoch_rsi=0.3,
        )

        # Current: larger bullish candle that engulfs previous
        current_candle = Candle(
            timestamp_utc=timestamp + timedelta(hours=1),
            open=1.09985,  # Opens below prev close
            high=1.10030,
            low=1.09975,  # Low below prev low
            close=1.10020,  # Close above prev open (engulfs)
            volume=2000,
            ema20=1.10000,
            ema50=1.09900,
            atr=0.00050,
            rsi=40.0,
            stoch_rsi=0.35,
        )

        assert _is_bullish_engulfing(current_candle, prev_candle) is True

    def test_bullish_engulfing_fails_if_current_bearish(self):
        """
        Given current candle is bearish,
        When checking for bullish engulfing,
        Then should return False (must be bullish).
        """
        timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)

        prev_candle = Candle(
            timestamp_utc=timestamp,
            open=1.10000,
            high=1.10010,
            low=1.09980,
            close=1.09990,
            volume=1000,
            ema20=1.10000,
            ema50=1.09900,
            atr=0.00050,
            rsi=35.0,
            stoch_rsi=0.3,
        )

        # Current is bearish (close < open)
        current_candle = Candle(
            timestamp_utc=timestamp + timedelta(hours=1),
            open=1.10020,
            high=1.10030,
            low=1.09975,
            close=1.09985,  # Bearish
            volume=2000,
            ema20=1.10000,
            ema50=1.09900,
            atr=0.00050,
            rsi=40.0,
            stoch_rsi=0.35,
        )

        assert _is_bullish_engulfing(current_candle, prev_candle) is False

    def test_bullish_engulfing_fails_if_not_engulfing(self):
        """
        Given current candle doesn't fully engulf previous,
        When checking for bullish engulfing,
        Then should return False.
        """
        timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)

        prev_candle = Candle(
            timestamp_utc=timestamp,
            open=1.10000,
            high=1.10010,
            low=1.09980,
            close=1.09990,
            volume=1000,
            ema20=1.10000,
            ema50=1.09900,
            atr=0.00050,
            rsi=35.0,
            stoch_rsi=0.3,
        )

        # Current doesn't fully engulf (close < prev open)
        current_candle = Candle(
            timestamp_utc=timestamp + timedelta(hours=1),
            open=1.09985,
            high=1.10005,
            low=1.09975,
            close=1.09995,  # Doesn't reach prev open
            volume=2000,
            ema20=1.10000,
            ema50=1.09900,
            atr=0.00050,
            rsi=40.0,
            stoch_rsi=0.35,
        )

        assert _is_bullish_engulfing(current_candle, prev_candle) is False


class TestBearishEngulfingPattern:
    """Tests for bearish engulfing candlestick pattern recognition."""

    def test_bearish_engulfing_valid_pattern(self):
        """
        Given a small bullish candle followed by larger bearish candle,
        When checking for bearish engulfing,
        Then should return True.
        """
        timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)

        # Previous: small bullish candle
        prev_candle = Candle(
            timestamp_utc=timestamp,
            open=1.10000,
            high=1.10020,
            low=1.09990,
            close=1.10010,  # Close > open (bullish)
            volume=1000,
            ema20=1.10000,
            ema50=1.10100,
            atr=0.00050,
            rsi=65.0,
            stoch_rsi=0.7,
        )

        # Current: larger bearish candle that engulfs previous
        current_candle = Candle(
            timestamp_utc=timestamp + timedelta(hours=1),
            open=1.10015,  # Opens above prev close
            high=1.10025,  # High above prev high
            low=1.09985,
            close=1.09990,  # Close below prev open (engulfs)
            volume=2000,
            ema20=1.10000,
            ema50=1.10100,
            atr=0.00050,
            rsi=60.0,
            stoch_rsi=0.65,
        )

        assert _is_bearish_engulfing(current_candle, prev_candle) is True


class TestHammerPattern:
    """Tests for hammer candlestick pattern (bullish reversal)."""

    def test_hammer_valid_pattern(self):
        """
        Given candle with long lower wick and small body,
        When checking for hammer,
        Then should return True.
        """
        # Hammer: lower_wick >= 2x body, upper_wick < 0.5x body
        candle = Candle(
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            open=1.10050,
            high=1.10055,  # Small upper wick
            low=1.10000,  # Long lower wick
            close=1.10045,  # Small body
            volume=1000,
            ema20=1.10000,
            ema50=1.09900,
            atr=0.00050,
            rsi=32.0,
            stoch_rsi=0.25,
        )

        # Body = |close - open| = 0.00005
        # Lower wick = open - low = 0.00050 (10x body, > 2x requirement)
        # Upper wick = high - close = 0.00010 (2x body, < 0.5x fails but example)

        assert _is_hammer(candle) is True

    def test_hammer_fails_without_long_lower_wick(self):
        """
        Given candle without long lower wick,
        When checking for hammer,
        Then should return False.
        """
        candle = Candle(
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            open=1.10000,
            high=1.10055,
            low=1.09990,  # Short lower wick
            close=1.10050,  # Large body
            volume=1000,
            ema20=1.10000,
            ema50=1.09900,
            atr=0.00050,
            rsi=32.0,
            stoch_rsi=0.25,
        )

        # Lower wick too short compared to body
        assert _is_hammer(candle) is False


class TestShootingStarPattern:
    """Tests for shooting star candlestick pattern (bearish reversal)."""

    def test_shooting_star_valid_pattern(self):
        """
        Given candle with long upper wick and small body,
        When checking for shooting star,
        Then should return True.
        """
        # Shooting star: upper_wick >= 2x body, lower_wick < 0.5x body
        candle = Candle(
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            open=1.10005,
            high=1.10060,  # Long upper wick
            low=1.10000,  # Small lower wick
            close=1.10010,  # Small body
            volume=1000,
            ema20=1.10000,
            ema50=1.10100,
            atr=0.00050,
            rsi=68.0,
            stoch_rsi=0.75,
        )

        # Body = |close - open| = 0.00005
        # Upper wick = high - close = 0.00050 (10x body, > 2x requirement)
        # Lower wick = open - low = 0.00005 (1x body, < 0.5x requirement)

        assert _is_shooting_star(candle) is True


class TestBullishReversalDetection:
    """Tests for complete bullish reversal confirmation (momentum + pattern)."""

    def test_bullish_reversal_with_rsi_turn_and_engulfing(self):
        """
        Given RSI turning up from oversold + bullish engulfing,
        When detecting bullish reversal,
        Then should return True.
        """
        timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)

        candles = [
            # 3 candles ago: RSI declining
            Candle(
                timestamp_utc=timestamp - timedelta(hours=2),
                open=1.10000,
                high=1.10010,
                low=1.09990,
                close=1.09995,
                volume=1000,
                ema20=1.10000,
                ema50=1.09900,
                atr=0.00050,
                rsi=32.0,
                stoch_rsi=0.28,
            ),
            # 2 candles ago: RSI at bottom
            Candle(
                timestamp_utc=timestamp - timedelta(hours=1),
                open=1.09995,
                high=1.10000,
                low=1.09980,
                close=1.09985,
                volume=1000,
                ema20=1.10000,
                ema50=1.09900,
                atr=0.00050,
                rsi=28.0,  # Oversold
                stoch_rsi=0.18,  # Oversold
            ),
            # Current: RSI turning up + bullish engulfing
            Candle(
                timestamp_utc=timestamp,
                open=1.09980,
                high=1.10020,
                low=1.09975,
                close=1.10015,  # Strong bullish candle
                volume=2000,
                ema20=1.10000,
                ema50=1.09900,
                atr=0.00050,
                rsi=35.0,  # Turning up (35 > 28)
                stoch_rsi=0.25,  # Turning up (0.25 > 0.18)
            ),
        ]

        assert _detect_bullish_reversal(candles) is True

    def test_bullish_reversal_fails_without_momentum_turn(self):
        """
        Given bullish engulfing but RSI still declining,
        When detecting bullish reversal,
        Then should return False (needs momentum confirmation).
        """
        timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)

        candles = [
            Candle(
                timestamp_utc=timestamp - timedelta(hours=1),
                open=1.09995,
                high=1.10000,
                low=1.09980,
                close=1.09985,
                volume=1000,
                ema20=1.10000,
                ema50=1.09900,
                atr=0.00050,
                rsi=32.0,
                stoch_rsi=0.28,
            ),
            Candle(
                timestamp_utc=timestamp,
                open=1.09980,
                high=1.10020,
                low=1.09975,
                close=1.10015,  # Bullish engulfing
                volume=2000,
                ema20=1.10000,
                ema50=1.09900,
                atr=0.00050,
                rsi=30.0,  # Still declining (30 < 32)
                stoch_rsi=0.25,
            ),
        ]

        assert _detect_bullish_reversal(candles) is False


class TestBearishReversalDetection:
    """Tests for complete bearish reversal confirmation (momentum + pattern)."""

    def test_bearish_reversal_with_rsi_turn_and_engulfing(self):
        """
        Given RSI turning down from overbought + bearish engulfing,
        When detecting bearish reversal,
        Then should return True.
        """
        timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)

        candles = [
            # 2 candles ago: RSI at peak
            Candle(
                timestamp_utc=timestamp - timedelta(hours=1),
                open=1.10000,
                high=1.10020,
                low=1.09990,
                close=1.10015,
                volume=1000,
                ema20=1.10000,
                ema50=1.10100,
                atr=0.00050,
                rsi=72.0,  # Overbought
                stoch_rsi=0.82,  # Overbought
            ),
            # Current: RSI turning down + bearish engulfing
            Candle(
                timestamp_utc=timestamp,
                open=1.10020,
                high=1.10025,
                low=1.09985,
                close=1.09990,  # Strong bearish candle
                volume=2000,
                ema20=1.10000,
                ema50=1.10100,
                atr=0.00050,
                rsi=65.0,  # Turning down (65 < 72)
                stoch_rsi=0.75,  # Turning down (0.75 < 0.82)
            ),
        ]

        assert _detect_bearish_reversal(candles) is True


class TestReversalDetection:
    """Tests for main detect_reversal function."""

    def test_reversal_detection_uptrend_pullback(self):
        """
        Given uptrend with active pullback and reversal confirmation,
        When detecting reversal,
        Then should return True for long entry.
        """
        timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)

        candles = [
            Candle(
                timestamp_utc=timestamp - timedelta(hours=1),
                open=1.09995,
                high=1.10000,
                low=1.09980,
                close=1.09985,
                volume=1000,
                ema20=1.10000,
                ema50=1.09900,
                atr=0.00050,
                rsi=28.0,
                stoch_rsi=0.18,
            ),
            Candle(
                timestamp_utc=timestamp - timedelta(minutes=30),
                open=1.09985,
                high=1.10005,
                low=1.09970,
                close=1.09990,
                volume=1200,
                ema20=1.10000,
                ema50=1.09900,
                atr=0.00050,
                rsi=30.0,
                stoch_rsi=0.20,
            ),
            Candle(
                timestamp_utc=timestamp,
                open=1.09980,
                high=1.10020,
                low=1.09975,
                close=1.10015,
                volume=2000,
                ema20=1.10000,
                ema50=1.09900,
                atr=0.00050,
                rsi=35.0,  # Turning up
                stoch_rsi=0.25,  # Turning up
            ),
        ]

        # Build a minimal PullbackState for detect_reversal usage
        pullback_state = PullbackState(
            active=True,
            direction="LONG",
            start_timestamp=timestamp,
            qualifying_candle_ids=[],
            oscillator_extreme_flag=True,
        )
        assert detect_reversal(candles, pullback_state=pullback_state) is True

    def test_reversal_detection_downtrend_pullback(self):
        """
        Given downtrend with active pullback and reversal confirmation,
        When detecting reversal,
        Then should return True for short entry.
        """
        timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)

        candles = [
            Candle(
                timestamp_utc=timestamp - timedelta(hours=1),
                open=1.10000,
                high=1.10020,
                low=1.09990,
                close=1.10015,
                volume=1000,
                ema20=1.10000,
                ema50=1.10100,
                atr=0.00050,
                rsi=72.0,
                stoch_rsi=0.82,
            ),
            Candle(
                timestamp_utc=timestamp - timedelta(minutes=30),
                open=1.10015,
                high=1.10025,
                low=1.09995,
                close=1.10005,
                volume=1300,
                ema20=1.10000,
                ema50=1.10100,
                atr=0.00050,
                rsi=68.0,
                stoch_rsi=0.78,
            ),
            Candle(
                timestamp_utc=timestamp,
                open=1.10020,
                high=1.10025,
                low=1.09985,
                close=1.09990,
                volume=2000,
                ema20=1.10000,
                ema50=1.10100,
                atr=0.00050,
                rsi=65.0,
                stoch_rsi=0.75,
            ),
        ]

        pullback_state = PullbackState(
            active=True,
            direction="SHORT",
            start_timestamp=timestamp,
            qualifying_candle_ids=[],
            oscillator_extreme_flag=True,
        )
        assert detect_reversal(candles, pullback_state=pullback_state) is True

    def test_reversal_detection_insufficient_candles(self):
        """
        Given fewer candles than required minimum,
        When detecting reversal,
        Then should raise ValueError.
        """
        candles = [
            Candle(
                timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
                open=1.10000,
                high=1.10020,
                low=1.09980,
                close=1.10010,
                volume=1000,
                ema20=1.10000,
                ema50=1.09900,
                atr=0.00050,
                rsi=35.0,
                stoch_rsi=0.3,
            ),
        ]
        pullback_state = PullbackState(
            active=True,
            direction="LONG",
            start_timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            qualifying_candle_ids=[],
            oscillator_extreme_flag=True,
        )
        # detect_reversal should raise ValueError for insufficient candles (min default 3)
        with pytest.raises(ValueError):
            detect_reversal(candles, pullback_state=pullback_state)
