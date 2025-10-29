"""
Trend classification logic for the trend pullback strategy.

This module identifies trend direction based on EMA crossovers. A trend is
classified as UP when fast EMA > slow EMA, DOWN when fast EMA < slow EMA,
and RANGE when neither condition is stable.
"""

import logging
from collections.abc import Sequence

from ...models.core import Candle, TrendState

logger = logging.getLogger(__name__)


def classify_trend(
    candles: Sequence[Candle],
    cross_count_threshold: int = 3,
) -> TrendState:
    """
    Classify current trend direction from candle sequence.

    Analyzes the most recent candles to determine if the market is in an
    uptrend (fast EMA > slow EMA), downtrend (fast EMA < slow EMA), or
    ranging (frequent EMA crossovers).

    A trend is confirmed when:
    - Fast EMA is consistently above/below slow EMA
    - Fewer than `cross_count_threshold` crossovers in recent candles

    Args:
        candles: Sequence of Candle objects with computed EMA values.
        cross_count_threshold: Maximum crossovers allowed to maintain trend
            classification (default 3).

    Returns:
        TrendState object with current trend classification.

    Raises:
        ValueError: If candles is empty or contains insufficient data.

    Examples:
        >>> from datetime import datetime, timezone
        >>> from models.core import Candle
        >>> candles = [
        ...     Candle(
        ...         timestamp_utc=datetime(2025, 1, 1, i, 0, tzinfo=timezone.utc),
        ...         open=1.10 + i*0.001,
        ...         high=1.101 + i*0.001,
        ...         low=1.099 + i*0.001,
        ...         close=1.10 + i*0.001,
        ...         volume=1000.0,
        ...         ema20=1.10 + i*0.001,
        ...         ema50=1.095,
        ...         atr=0.002,
        ...         rsi=60.0,
        ...         stoch_rsi=0.7
        ...     )
        ...     for i in range(50)
        ... ]
        >>> trend = classify_trend(candles)
        >>> trend.state
        'UP'
    """
    if not candles:
        raise ValueError("Candles sequence cannot be empty")

    if len(candles) < 2:
        raise ValueError("Need at least 2 candles to classify trend")

    # Get most recent candle
    latest_candle = candles[-1]

    # Check if EMA values are available
    if latest_candle.ema20 is None or latest_candle.ema50 is None:
        raise ValueError("Candles must have computed EMA values")

    # Determine current EMA relationship
    if latest_candle.ema20 > latest_candle.ema50:
        current_state = "UP"
    elif latest_candle.ema20 < latest_candle.ema50:
        current_state = "DOWN"
    else:
        current_state = "RANGE"

    # Count EMA crossovers in recent history
    cross_count = _count_ema_crossovers(candles[-50:])  # Look back 50 candles

    # If too many crosses, classify as RANGE
    if cross_count >= cross_count_threshold:
        current_state = "RANGE"
        logger.debug(
            "Trend classified as RANGE due to %d crossovers (threshold: %d)",
            cross_count,
            cross_count_threshold,
        )

    # Find when trend last changed
    last_change_timestamp = _find_last_trend_change(candles)

    trend_state = TrendState(
        state=current_state,
        cross_count=cross_count,
        last_change_timestamp=last_change_timestamp,
    )

    logger.debug(
        "Trend classified: %s (crossovers=%d, last_change=%s)",
        current_state,
        cross_count,
        last_change_timestamp.isoformat() if last_change_timestamp else "N/A",
    )

    return trend_state


def _count_ema_crossovers(candles: Sequence[Candle]) -> int:
    """
    Count EMA crossovers in candle sequence.

    A crossover occurs when fast EMA crosses above or below slow EMA.

    Args:
        candles: Sequence of candles with EMA values.

    Returns:
        Number of crossovers detected.

    Examples:
        >>> from models.core import Candle
        >>> from datetime import datetime, timezone
        >>> candles = [...]  # Candles with alternating EMA relationships
        >>> count = _count_ema_crossovers(candles)
        >>> count
        3
    """
    if len(candles) < 2:
        return 0

    cross_count = 0
    previous_above = candles[0].ema20 > candles[0].ema50

    for candle in candles[1:]:
        if candle.ema20 is None or candle.ema50 is None:
            continue

        current_above = candle.ema20 > candle.ema50

        # Detect crossover
        if current_above != previous_above:
            cross_count += 1

        previous_above = current_above

    return cross_count


def _find_last_trend_change(candles: Sequence[Candle]):
    """
    Find timestamp of most recent trend change.

    Scans backwards through candles to find when EMA relationship last flipped.

    Args:
        candles: Sequence of candles with EMA values.

    Returns:
        Timestamp of last trend change, or None if no change detected.

    Examples:
        >>> from models.core import Candle
        >>> from datetime import datetime, timezone
        >>> candles = [...]  # Candles with trend change
        >>> timestamp = _find_last_trend_change(candles)
        >>> timestamp
        datetime.datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
    """
    if len(candles) < 2:
        return None

    # Get current EMA relationship
    latest_candle = candles[-1]
    if latest_candle.ema20 is None or latest_candle.ema50 is None:
        return None

    current_above = latest_candle.ema20 > latest_candle.ema50

    # Scan backwards to find crossover
    for i in range(len(candles) - 2, -1, -1):
        candle = candles[i]

        if candle.ema20 is None or candle.ema50 is None:
            continue

        previous_above = candle.ema20 > candle.ema50

        # Found crossover
        if previous_above != current_above:
            # Return timestamp of candle AFTER the crossover
            if i + 1 < len(candles):
                return candles[i + 1].timestamp_utc
            return candle.timestamp_utc

    # No crossover found in history
    return None


def is_uptrend(trend_state: TrendState) -> bool:
    """
    Check if current trend is UP.

    Args:
        trend_state: TrendState object.

    Returns:
        True if trend is UP, False otherwise.

    Examples:
        >>> trend = TrendState(state="UP", cross_count=1, last_change_timestamp=None)
        >>> is_uptrend(trend)
        True
    """
    return trend_state.state == "UP"


def is_downtrend(trend_state: TrendState) -> bool:
    """
    Check if current trend is DOWN.

    Args:
        trend_state: TrendState object.

    Returns:
        True if trend is DOWN, False otherwise.

    Examples:
        >>> trend = TrendState(state="DOWN", cross_count=1, last_change_timestamp=None)
        >>> is_downtrend(trend)
        True
    """
    return trend_state.state == "DOWN"


def is_ranging(trend_state: TrendState) -> bool:
    """
    Check if current trend is RANGE.

    Args:
        trend_state: TrendState object.

    Returns:
        True if trend is RANGE, False otherwise.

    Examples:
        >>> trend = TrendState(state="RANGE", cross_count=5, last_change_timestamp=None)
        >>> is_ranging(trend)
        True
    """
    return trend_state.state == "RANGE"
