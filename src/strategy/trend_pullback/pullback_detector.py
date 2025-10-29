"""
Pullback detection logic for the trend pullback strategy.

This module identifies pullback conditions within an established trend. A
pullback is detected when price retraces against the trend direction while
oscillators reach extreme levels.
"""

import logging
from datetime import datetime, timedelta
from typing import Sequence

from ...models.core import Candle, PullbackState, TrendState

logger = logging.getLogger(__name__)


def detect_pullback(
    candles: Sequence[Candle],
    trend_state: TrendState,
    rsi_oversold: float = 30.0,
    rsi_overbought: float = 70.0,
    stoch_rsi_low: float = 0.2,
    stoch_rsi_high: float = 0.8,
    pullback_max_age_candles: int = 20,
) -> PullbackState:
    """
    Detect if market is in a pullback state within the current trend.

    A pullback is identified when:
    - In uptrend: RSI < oversold OR Stochastic RSI < low threshold
    - In downtrend: RSI > overbought OR Stochastic RSI > high threshold
    - Price has retraced against trend direction

    Args:
        candles: Sequence of Candle objects.
        trend_state: Current trend classification.
        rsi_oversold: RSI threshold for oversold (default 30).
        rsi_overbought: RSI threshold for overbought (default 70).
        stoch_rsi_low: Stochastic RSI low threshold (default 0.2).
        stoch_rsi_high: Stochastic RSI high threshold (default 0.8).
        pullback_max_age_candles: Maximum candles pullback can last (default 20).

    Returns:
        PullbackState object with pullback status and metadata.

    Raises:
        ValueError: If candles is empty or missing required data.

    Examples:
        >>> from datetime import datetime, timezone
        >>> from models.core import Candle, TrendState
        >>> candles = [...]  # Candles with pullback pattern
        >>> trend = TrendState(state="UP", cross_count=1, last_change_timestamp=None)
        >>> pullback = detect_pullback(candles, trend)
        >>> pullback.active
        True
        >>> pullback.direction
        'LONG'
    """
    if not candles:
        raise ValueError("Candles sequence cannot be empty")

    latest_candle = candles[-1]

    # Check if oscillator values are available
    if latest_candle.rsi is None or latest_candle.stoch_rsi is None:
        raise ValueError("Candles must have computed RSI and Stochastic RSI values")

    # No pullback in ranging market
    if trend_state.state == "RANGE":
        return PullbackState(
            active=False,
            direction=None,
            start_timestamp=None,
            qualifying_candle_ids=[],
            oscillator_extreme_flag=False,
        )

    # Determine if oscillators show extreme
    if trend_state.state == "UP":
        oscillator_extreme = (
            latest_candle.rsi < rsi_oversold
            or latest_candle.stoch_rsi < stoch_rsi_low
        )
        direction = "LONG"
    else:  # DOWN
        oscillator_extreme = (
            latest_candle.rsi > rsi_overbought
            or latest_candle.stoch_rsi > stoch_rsi_high
        )
        direction = "SHORT"

    # Find pullback start (when oscillator first hit extreme)
    start_timestamp = None
    qualifying_candle_ids = []

    if oscillator_extreme:
        # Look back to find when pullback started
        for i in range(len(candles) - 1, max(len(candles) - pullback_max_age_candles - 1, -1), -1):
            candle = candles[i]

            if candle.rsi is None or candle.stoch_rsi is None:
                continue

            # Check if this candle shows extreme
            if trend_state.state == "UP":
                is_extreme = (
                    candle.rsi < rsi_oversold or candle.stoch_rsi < stoch_rsi_low
                )
            else:
                is_extreme = (
                    candle.rsi > rsi_overbought or candle.stoch_rsi > stoch_rsi_high
                )

            if is_extreme:
                start_timestamp = candle.timestamp_utc
                # Use timestamp as candle ID (string representation)
                qualifying_candle_ids.append(candle.timestamp_utc.isoformat())
            else:
                # Found first non-extreme candle, stop
                break

        # Reverse to chronological order
        qualifying_candle_ids.reverse()

    # Check if pullback is too old
    active = oscillator_extreme
    if active and start_timestamp:
        age_candles = len(candles) - 1 - _find_candle_index(candles, start_timestamp)
        if age_candles > pullback_max_age_candles:
            active = False
            logger.debug(
                f"Pullback expired: age={age_candles} candles "
                f"(max={pullback_max_age_candles})"
            )

    pullback_state = PullbackState(
        active=active,
        direction=direction if active else None,
        start_timestamp=start_timestamp if active else None,
        qualifying_candle_ids=qualifying_candle_ids if active else [],
        oscillator_extreme_flag=oscillator_extreme,
    )

    if active:
        logger.debug(
            f"Pullback detected: direction={direction}, "
            f"start={start_timestamp.isoformat() if start_timestamp else 'N/A'}, "
            f"qualifying_candles={len(qualifying_candle_ids)}"
        )

    return pullback_state


def _find_candle_index(candles: Sequence[Candle], timestamp: datetime) -> int:
    """
    Find index of candle with given timestamp.

    Args:
        candles: Sequence of candles.
        timestamp: Timestamp to search for.

    Returns:
        Index of candle, or -1 if not found.

    Examples:
        >>> from models.core import Candle
        >>> from datetime import datetime, timezone
        >>> candles = [...]
        >>> idx = _find_candle_index(candles, datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))
        >>> idx
        42
    """
    for i, candle in enumerate(candles):
        if candle.timestamp_utc == timestamp:
            return i
    return -1


def is_pullback_active(pullback_state: PullbackState) -> bool:
    """
    Check if pullback is currently active.

    Args:
        pullback_state: PullbackState object.

    Returns:
        True if pullback is active, False otherwise.

    Examples:
        >>> pullback = PullbackState(
        ...     active=True,
        ...     direction="LONG",
        ...     start_timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ...     qualifying_candle_ids=["2025-01-01T00:00:00"],
        ...     oscillator_extreme_flag=True
        ... )
        >>> is_pullback_active(pullback)
        True
    """
    return pullback_state.active


def get_pullback_direction(pullback_state: PullbackState) -> str | None:
    """
    Get pullback direction (trade bias).

    Args:
        pullback_state: PullbackState object.

    Returns:
        "LONG" or "SHORT" if pullback active, None otherwise.

    Examples:
        >>> pullback = PullbackState(
        ...     active=True,
        ...     direction="LONG",
        ...     start_timestamp=None,
        ...     qualifying_candle_ids=[],
        ...     oscillator_extreme_flag=True
        ... )
        >>> get_pullback_direction(pullback)
        'LONG'
    """
    return pullback_state.direction if pullback_state.active else None
