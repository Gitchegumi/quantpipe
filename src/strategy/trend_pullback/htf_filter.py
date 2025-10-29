"""Higher timeframe (HTF) filter for trend confirmation.

This module provides optional filtering logic that checks higher timeframe
price alignment before taking trades. Implements FR-016 and FR-028.

Example use case:
- Trading on 15-minute chart
- Filter requires 1-hour EMA alignment before entry
- Prevents counter-trend trades on lower timeframe noise

Configuration:
- htf_enabled: True/False toggle
- htf_timeframe_multiplier: e.g., 4x (15m -> 1h)
- htf_ema_period: EMA period for HTF trend check
"""

from typing import List, Optional
import logging

from src.models.core import Candle

logger = logging.getLogger(__name__)


def check_htf_ema_alignment(
    htf_candles: List[Candle],
    ema_period: int = 50,
    direction: str = "long",
) -> bool:
    """Check if higher timeframe price is aligned with trade direction.

    Args:
        htf_candles: List of candles from higher timeframe
        ema_period: EMA period for trend determination (default 50)
        direction: Trade direction "long" or "short"

    Returns:
        True if HTF alignment confirmed, False otherwise

    Logic:
        - For long trades: HTF close > HTF EMA
        - For short trades: HTF close < HTF EMA
    """
    if len(htf_candles) < ema_period:
        logger.debug(
            "Insufficient HTF candles: %d < %d", len(htf_candles), ema_period
        )
        return False

    # Compute HTF EMA
    closes = [c.close for c in htf_candles]
    ema = compute_ema(closes, ema_period)

    if len(ema) == 0:
        return False

    current_close = htf_candles[-1].close
    current_ema = ema[-1]

    if direction == "long":
        aligned = current_close > current_ema
        logger.debug(
            "HTF long alignment: close=%.5f, ema=%.5f, aligned=%s",
            current_close,
            current_ema,
            aligned,
        )
        return aligned

    if direction == "short":
        aligned = current_close < current_ema
        logger.debug(
            "HTF short alignment: close=%.5f, ema=%.5f, aligned=%s",
            current_close,
            current_ema,
            aligned,
        )
        return aligned

    logger.warning("Invalid direction for HTF filter: %s", direction)
    return False


def compute_ema(values: List[float], period: int) -> List[float]:
    """Compute Exponential Moving Average.

    Args:
        values: List of price values
        period: EMA period

    Returns:
        List of EMA values (same length as input)
        First (period - 1) values use SMA initialization
    """
    if len(values) < period:
        return []

    ema_values = []
    alpha = 2.0 / (period + 1)

    # Initialize with SMA
    sma = sum(values[:period]) / period
    ema_values.append(sma)

    # Compute EMA for remaining values
    for i in range(period, len(values)):
        ema = alpha * values[i] + (1 - alpha) * ema_values[-1]
        ema_values.append(ema)

    # Pad front with NaN for alignment
    result = [float("nan")] * (period - 1) + ema_values
    return result


def convert_timeframe_to_htf(
    base_candles: List[Candle],
    multiplier: int = 4,
) -> List[Candle]:
    """Convert lower timeframe candles to higher timeframe.

    Args:
        base_candles: List of base timeframe candles
        multiplier: Timeframe multiplier (e.g., 4 = 15m -> 1h)

    Returns:
        List of aggregated higher timeframe candles

    Note:
        Placeholder implementation. Assumes candles are continuous.
        Production implementation should handle gaps and timestamps properly.
    """
    if len(base_candles) < multiplier:
        return []

    htf_candles = []
    for i in range(0, len(base_candles), multiplier):
        chunk = base_candles[i : i + multiplier]
        if len(chunk) < multiplier:
            break  # Incomplete final bar

        htf_candle = aggregate_candles(chunk)
        htf_candles.append(htf_candle)

    return htf_candles


def aggregate_candles(candles: List[Candle]) -> Candle:
    """Aggregate multiple candles into a single higher timeframe candle.

    Args:
        candles: List of candles to aggregate

    Returns:
        Single aggregated candle with:
        - Open = first candle open
        - High = highest high
        - Low = lowest low
        - Close = last candle close
        - Volume = sum of volumes
        - Timestamp = last candle timestamp
    """
    if len(candles) == 0:
        raise ValueError("Cannot aggregate zero candles")

    open_price = candles[0].open
    high_price = max(c.high for c in candles)
    low_price = min(c.low for c in candles)
    close_price = candles[-1].close
    volume = sum(c.volume for c in candles)
    timestamp = candles[-1].timestamp

    return Candle(
        timestamp=timestamp,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
    )


def filter_trade_with_htf(
    base_candles: List[Candle],
    direction: str,
    htf_enabled: bool = False,
    htf_multiplier: int = 4,
    htf_ema_period: int = 50,
) -> tuple[bool, Optional[str]]:
    """Apply HTF filter to trade signal.

    Args:
        base_candles: Base timeframe candles
        direction: Trade direction "long" or "short"
        htf_enabled: Enable HTF filtering (default False)
        htf_multiplier: Timeframe multiplier (default 4)
        htf_ema_period: HTF EMA period (default 50)

    Returns:
        Tuple of (filter_pass, rejection_reason)
        - filter_pass: True if trade allowed, False if rejected
        - rejection_reason: None if passed, string if rejected
    """
    if not htf_enabled:
        return True, None

    # Convert to HTF
    htf_candles = convert_timeframe_to_htf(base_candles, multiplier=htf_multiplier)

    if len(htf_candles) < htf_ema_period:
        reason = f"Insufficient HTF candles: {len(htf_candles)} < {htf_ema_period}"
        logger.debug(reason)
        return False, reason

    # Check alignment
    aligned = check_htf_ema_alignment(htf_candles, ema_period=htf_ema_period, direction=direction)

    if not aligned:
        reason = f"HTF EMA not aligned for {direction} trade"
        logger.info(reason)
        return False, reason

    logger.debug("HTF filter passed for %s trade", direction)
    return True, None
