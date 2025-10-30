"""
Reversal pattern detection and momentum turn logic.

This module identifies reversal signals that indicate a pullback is ending and
price is resuming the trend direction. Uses candlestick patterns and momentum
confirmation.
"""

import logging
from collections.abc import Sequence

from ...models.core import Candle, PullbackState


logger = logging.getLogger(__name__)


def detect_reversal(
    candles: Sequence[Candle],
    pullback_state: PullbackState,
    min_candles_for_reversal: int = 3,
) -> bool:
    """
    Detect if pullback is reversing back to trend direction.

    A reversal is confirmed when:
    - Pullback is active
    - Recent candles show momentum turning back to trend
    - Candlestick patterns support reversal (e.g., bullish engulfing in uptrend)

    Args:
        candles: Sequence of recent Candle objects (minimum 3).
        pullback_state: Current pullback state.
        min_candles_for_reversal: Minimum candles needed to detect reversal (default 3).

    Returns:
        True if reversal detected, False otherwise.

    Raises:
        ValueError: If insufficient candles provided.

    Examples:
        >>> from datetime import datetime, timezone
        >>> from models.core import Candle, PullbackState
        >>> candles = [...]  # Candles showing bullish reversal
        >>> pullback = PullbackState(
        ...     active=True,
        ...     direction="LONG",
        ...     start_timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ...     qualifying_candle_ids=[],
        ...     oscillator_extreme_flag=True
        ... )
        >>> has_reversal = detect_reversal(candles, pullback)
        >>> has_reversal
        True
    """
    if len(candles) < min_candles_for_reversal:
        raise ValueError(
            f"Need at least {min_candles_for_reversal} candles to detect reversal, "
            f"got {len(candles)}"
        )

    # No reversal if pullback not active
    if not pullback_state.active:
        return False

    # Get recent candles
    recent_candles = candles[-min_candles_for_reversal:]

    # Check for reversal patterns based on direction
    if pullback_state.direction == "LONG":
        has_reversal = _detect_bullish_reversal(recent_candles)
    elif pullback_state.direction == "SHORT":
        has_reversal = _detect_bearish_reversal(recent_candles)
    else:
        has_reversal = False

    if has_reversal:
        logger.info(
            "Reversal detected: direction=%s, timestamp=%s",
            pullback_state.direction,
            recent_candles[-1].timestamp_utc.isoformat(),
        )

    return has_reversal


def _detect_bullish_reversal(candles: Sequence[Candle]) -> bool:
    """
    Detect bullish reversal pattern in uptrend pullback.

    Looks for:
    - RSI turning up from oversold
    - Stochastic RSI turning up from low
    - Bullish candlestick patterns (engulfing, hammer)

    Args:
        candles: Recent candles (minimum 2).

    Returns:
        True if bullish reversal detected.

    Examples:
        >>> from models.core import Candle
        >>> candles = [...]  # Bullish pattern
        >>> is_bullish = _detect_bullish_reversal(candles)
        >>> is_bullish
        True
    """
    if len(candles) < 2:
        return False

    prev_candle = candles[-2]
    curr_candle = candles[-1]

    # Check RSI momentum turn
    rsi_turning_up = False
    if prev_candle.rsi is not None and curr_candle.rsi is not None:
        # RSI was low and is now rising
        rsi_turning_up = prev_candle.rsi < 40 and curr_candle.rsi > prev_candle.rsi

    # Check Stochastic RSI momentum turn
    stoch_rsi_turning_up = False
    if prev_candle.stoch_rsi is not None and curr_candle.stoch_rsi is not None:
        # Stoch RSI was low and is now rising
        stoch_rsi_turning_up = (
            prev_candle.stoch_rsi < 0.3
            and curr_candle.stoch_rsi > prev_candle.stoch_rsi
        )

    # Check for bullish engulfing pattern
    bullish_engulfing = _is_bullish_engulfing(prev_candle, curr_candle)

    # Check for hammer pattern
    hammer = _is_hammer(curr_candle)

    # Reversal confirmed if momentum turning AND pattern present
    has_momentum = rsi_turning_up or stoch_rsi_turning_up
    has_pattern = bullish_engulfing or hammer

    return has_momentum and has_pattern


def _detect_bearish_reversal(candles: Sequence[Candle]) -> bool:
    """
    Detect bearish reversal pattern in downtrend pullback.

    Looks for:
    - RSI turning down from overbought
    - Stochastic RSI turning down from high
    - Bearish candlestick patterns (engulfing, shooting star)

    Args:
        candles: Recent candles (minimum 2).

    Returns:
        True if bearish reversal detected.

    Examples:
        >>> from models.core import Candle
        >>> candles = [...]  # Bearish pattern
        >>> is_bearish = _detect_bearish_reversal(candles)
        >>> is_bearish
        True
    """
    if len(candles) < 2:
        return False

    prev_candle = candles[-2]
    curr_candle = candles[-1]

    # Check RSI momentum turn
    rsi_turning_down = False
    if prev_candle.rsi is not None and curr_candle.rsi is not None:
        # RSI was high and is now falling
        rsi_turning_down = prev_candle.rsi > 60 and curr_candle.rsi < prev_candle.rsi

    # Check Stochastic RSI momentum turn
    stoch_rsi_turning_down = False
    if prev_candle.stoch_rsi is not None and curr_candle.stoch_rsi is not None:
        # Stoch RSI was high and is now falling
        stoch_rsi_turning_down = (
            prev_candle.stoch_rsi > 0.7
            and curr_candle.stoch_rsi < prev_candle.stoch_rsi
        )

    # Check for bearish engulfing pattern
    bearish_engulfing = _is_bearish_engulfing(prev_candle, curr_candle)

    # Check for shooting star pattern
    shooting_star = _is_shooting_star(curr_candle)

    # Reversal confirmed if momentum turning AND pattern present
    has_momentum = rsi_turning_down or stoch_rsi_turning_down
    has_pattern = bearish_engulfing or shooting_star

    return has_momentum and has_pattern


def _is_bullish_engulfing(prev_candle: Candle, curr_candle: Candle) -> bool:
    """
    Check if current candle is a bullish engulfing pattern.

    Bullish engulfing: Current green candle completely engulfs previous red candle.

    Args:
        prev_candle: Previous candle.
        curr_candle: Current candle.

    Returns:
        True if bullish engulfing pattern detected.

    Examples:
        >>> from models.core import Candle
        >>> prev = Candle(..., open=1.10, close=1.098, ...)  # Red
        >>> curr = Candle(..., open=1.097, close=1.102, ...)  # Green, engulfing
        >>> _is_bullish_engulfing(prev, curr)
        True
    """
    # Previous candle is bearish
    prev_bearish = prev_candle.close < prev_candle.open

    # Current candle is bullish
    curr_bullish = curr_candle.close > curr_candle.open

    # Current body engulfs previous body
    engulfs = (
        curr_candle.open < prev_candle.close and curr_candle.close > prev_candle.open
    )

    return prev_bearish and curr_bullish and engulfs


def _is_bearish_engulfing(prev_candle: Candle, curr_candle: Candle) -> bool:
    """
    Check if current candle is a bearish engulfing pattern.

    Bearish engulfing: Current red candle completely engulfs previous green candle.

    Args:
        prev_candle: Previous candle.
        curr_candle: Current candle.

    Returns:
        True if bearish engulfing pattern detected.

    Examples:
        >>> from models.core import Candle
        >>> prev = Candle(..., open=1.10, close=1.102, ...)  # Green
        >>> curr = Candle(..., open=1.103, close=1.098, ...)  # Red, engulfing
        >>> _is_bearish_engulfing(prev, curr)
        True
    """
    # Previous candle is bullish
    prev_bullish = prev_candle.close > prev_candle.open

    # Current candle is bearish
    curr_bearish = curr_candle.close < curr_candle.open

    # Current body engulfs previous body
    engulfs = (
        curr_candle.open > prev_candle.close and curr_candle.close < prev_candle.open
    )

    return prev_bullish and curr_bearish and engulfs


def _is_hammer(candle: Candle) -> bool:
    """
    Check if candle is a hammer pattern (bullish reversal).

    Hammer characteristics:
    - Small body at top of candle
    - Long lower wick (2x body size)
    - Short or no upper wick

    Args:
        candle: Candle to analyze.

    Returns:
        True if hammer pattern detected.

    Examples:
        >>> from models.core import Candle
        >>> candle = Candle(..., open=1.10, high=1.101, low=1.095, close=1.099, ...)
        >>> _is_hammer(candle)
        True
    """
    body_size = abs(candle.close - candle.open)
    upper_wick = candle.high - max(candle.open, candle.close)
    lower_wick = min(candle.open, candle.close) - candle.low

    # Avoid division by zero
    if body_size == 0:
        return False

    # Long lower wick (at least 2x body)
    has_long_lower_wick = lower_wick >= 2 * body_size

    # Short upper wick (less than half body)
    has_short_upper_wick = upper_wick < 0.5 * body_size

    return has_long_lower_wick and has_short_upper_wick


def _is_shooting_star(candle: Candle) -> bool:
    """
    Check if candle is a shooting star pattern (bearish reversal).

    Shooting star characteristics:
    - Small body at bottom of candle
    - Long upper wick (2x body size)
    - Short or no lower wick

    Args:
        candle: Candle to analyze.

    Returns:
        True if shooting star pattern detected.

    Examples:
        >>> from models.core import Candle
        >>> candle = Candle(..., open=1.10, high=1.105, low=1.099, close=1.101, ...)
        >>> _is_shooting_star(candle)
        True
    """
    body_size = abs(candle.close - candle.open)
    upper_wick = candle.high - max(candle.open, candle.close)
    lower_wick = min(candle.open, candle.close) - candle.low

    # Avoid division by zero
    if body_size == 0:
        return False

    # Long upper wick (at least 2x body)
    has_long_upper_wick = upper_wick >= 2 * body_size

    # Short lower wick (less than half body)
    has_short_lower_wick = lower_wick < 0.5 * body_size

    return has_long_upper_wick and has_short_lower_wick
