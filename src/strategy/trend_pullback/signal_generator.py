"""
Signal generator for the trend pullback strategy (long and short).

This module orchestrates trend classification, pullback detection, and reversal
confirmation to generate trade signals in both directions. Only generates signals
when all conditions align.
"""

import logging
from collections.abc import Sequence
from datetime import datetime

from ...models.core import Candle, TradeSignal
from ...risk.manager import calculate_position_size
from ...strategy.id_factory import compute_parameters_hash, generate_signal_id
from .pullback_detector import detect_pullback
from .reversal import detect_reversal
from .trend_classifier import classify_trend


logger = logging.getLogger(__name__)


def generate_long_signals(
    candles: Sequence[Candle],
    parameters: dict,
    parameters_hash: str | None = None,
) -> list[TradeSignal]:
    """
    Generate long trade signals from candle sequence.

    Analyzes candles for:
    1. Confirmed uptrend (fast EMA > slow EMA)
    2. Active pullback (RSI/Stoch RSI oversold)
    3. Reversal confirmation (momentum turn + candlestick pattern)

    Only generates signal when all three conditions are met.

    Args:
        candles: Sequence of Candle objects with computed indicators.
        parameters: Strategy parameters dictionary.
        parameters_hash: Pre-computed parameters hash (optional, will compute if None).

    Returns:
        List of TradeSignal objects (0 or 1 signal).

    Raises:
        ValueError: If candles is empty or missing required data.

    Examples:
        >>> from datetime import datetime, timezone
        >>> from models.core import Candle
        >>> candles = [...]  # Candles showing long setup
        >>> params = {
        ...     "ema_fast": 20,
        ...     "ema_slow": 50,
        ...     "rsi_period": 14,
        ...     "position_risk_pct": 0.25
        ... }
        >>> signals = generate_long_signals(candles, params)
        >>> len(signals)
        1
        >>> signals[0].direction
        'LONG'
    """
    if not candles:
        raise ValueError("Candles sequence cannot be empty")

    if len(candles) < 50:
        logger.debug(
            "Insufficient candles for signal generation: %d < 50", len(candles)
        )
        return []

    # Compute parameters hash if not provided
    if parameters_hash is None:
        parameters_hash = compute_parameters_hash(parameters)

    # Step 1: Classify trend
    try:
        trend_state = classify_trend(
            candles,
            cross_count_threshold=parameters.get("trend_cross_count_threshold", 3),
        )
    except ValueError as e:
        logger.warning("Trend classification failed: %s", e)
        return []

    # Only proceed if in uptrend
    if trend_state.state != "UP":
        logger.debug("Not in uptrend: %s", trend_state.state)
        return []

    # Step 2: Detect pullback
    try:
        pullback_state = detect_pullback(
            candles,
            trend_state,
            rsi_oversold=parameters.get("rsi_oversold", 30.0),
            rsi_overbought=parameters.get("rsi_overbought", 70.0),
            stoch_rsi_low=parameters.get("stoch_rsi_low", 0.2),
            stoch_rsi_high=parameters.get("stoch_rsi_high", 0.8),
            pullback_max_age_candles=parameters.get("pullback_max_age", 20),
        )
    except ValueError as e:
        logger.warning("Pullback detection failed: %s", e)
        return []

    # Only proceed if pullback is active
    if not pullback_state.active:
        logger.debug("No active pullback")
        return []

    # Step 3: Detect reversal
    try:
        has_reversal = detect_reversal(
            candles,
            pullback_state,
            min_candles_for_reversal=parameters.get("min_candles_reversal", 3),
        )
    except ValueError as e:
        logger.warning("Reversal detection failed: %s", e)
        return []

    # Only generate signal if reversal confirmed
    if not has_reversal:
        logger.debug("No reversal detected")
        return []

    # All conditions met - generate signal
    latest_candle = candles[-1]

    # Calculate entry, stop, and target prices
    entry_price = latest_candle.close
    atr_value = latest_candle.atr if latest_candle.atr is not None else 0.002
    stop_distance = atr_value * parameters.get("stop_loss_atr_multiplier", 2.0)
    stop_price = entry_price - stop_distance

    # Calculate target price using strategy's reward/risk ratio
    target_r_mult = parameters.get("target_r_mult", 2.0)
    target_price = entry_price + (stop_distance * target_r_mult)

    # Calculate position size based on account balance and risk percentage
    account_balance = parameters.get("account_balance", 2500.0)  # Default $2,500
    position_size = (
        0.01  # Temporary placeholder, will be calculated after signal creation
    )

    # Generate deterministic signal ID
    signal_id = generate_signal_id(
        pair=parameters.get("pair", "UNKNOWN"),
        timestamp_utc=latest_candle.timestamp_utc,
        direction="LONG",
        entry_price=entry_price,
        stop_price=stop_price,
        position_size=position_size,
        parameters_hash=parameters_hash,
    )

    # Create signal with placeholder position size
    signal = TradeSignal(
        id=signal_id,
        pair=parameters.get("pair", "EURUSD"),
        direction="LONG",
        entry_price=entry_price,
        initial_stop_price=stop_price,
        target_price=target_price,  # Strategy-defined TP
        risk_per_trade_pct=parameters.get("position_risk_pct", 0.25),
        calc_position_size=position_size,  # Will be updated below
        tags=["pullback", "reversal", "long"],
        version="0.1.0",
        timestamp_utc=latest_candle.timestamp_utc,
    )

    # Calculate actual position size based on risk parameters
    calculated_position_size = calculate_position_size(
        signal=signal,
        account_balance=account_balance,
        risk_per_trade_pct=signal.risk_per_trade_pct,
        pip_value=10.0,
        lot_step=0.01,
        max_position_size=10.0,
    )

    # Create final signal with correct position size
    signal = TradeSignal(
        id=signal_id,
        pair=parameters.get("pair", "EURUSD"),
        direction="LONG",
        entry_price=entry_price,
        initial_stop_price=stop_price,
        target_price=target_price,  # Strategy-defined TP
        risk_per_trade_pct=parameters.get("risk_per_trade_pct", 0.25),
        calc_position_size=calculated_position_size,
        tags=["pullback", "reversal", "long"],
        version="0.1.0",
        timestamp_utc=latest_candle.timestamp_utc,
    )

    logger.debug(
        "Long signal generated: id=%s..., entry=%.5f, stop=%.5f, target=%.5f, timestamp=%s",
        signal_id[:16],
        entry_price,
        stop_price,
        target_price,
        latest_candle.timestamp_utc.isoformat(),
    )

    return [signal]


def generate_short_signals(
    candles: Sequence[Candle],
    parameters: dict,
    parameters_hash: str | None = None,
) -> list[TradeSignal]:
    """
    Generate short trade signals from candle sequence.

    Analyzes candles for:
    1. Confirmed downtrend (fast EMA < slow EMA)
    2. Active pullback (RSI/Stoch RSI overbought)
    3. Reversal confirmation (momentum turn + bearish candlestick pattern)

    Only generates signal when all three conditions are met.

    Args:
        candles: Sequence of Candle objects with computed indicators.
        parameters: Strategy parameters dictionary.
        parameters_hash: Pre-computed parameters hash (optional, will compute if None).

    Returns:
        List of TradeSignal objects (0 or 1 signal).

    Raises:
        ValueError: If candles is empty or missing required data.

    Examples:
        >>> from datetime import datetime, timezone
        >>> from models.core import Candle
        >>> candles = [...]  # Candles showing short setup
        >>> params = {
        ...     "ema_fast": 20,
        ...     "ema_slow": 50,
        ...     "rsi_period": 14,
        ...     "position_risk_pct": 0.25
        ... }
        >>> signals = generate_short_signals(candles, params)
        >>> len(signals)
        1
        >>> signals[0].direction
        'SHORT'
    """
    if not candles:
        raise ValueError("Candles sequence cannot be empty")

    if len(candles) < 50:
        logger.debug(
            "Insufficient candles for signal generation: %d < 50", len(candles)
        )
        return []

    # Compute parameters hash if not provided
    if parameters_hash is None:
        parameters_hash = compute_parameters_hash(parameters)

    # Step 1: Classify trend
    try:
        trend_state = classify_trend(
            candles,
            cross_count_threshold=parameters.get("trend_cross_count_threshold", 3),
        )
    except ValueError as e:
        logger.warning("Trend classification failed: %s", e)
        return []

    # Only proceed if in downtrend
    if trend_state.state != "DOWN":
        logger.debug("Not in downtrend: %s", trend_state.state)
        return []

    # Step 2: Detect pullback (overbought for shorts)
    try:
        pullback_state = detect_pullback(
            candles,
            trend_state,
            rsi_oversold=parameters.get("rsi_oversold", 30.0),
            rsi_overbought=parameters.get("rsi_overbought", 70.0),
            stoch_rsi_low=parameters.get("stoch_rsi_low", 0.2),
            stoch_rsi_high=parameters.get("stoch_rsi_high", 0.8),
            pullback_max_age_candles=parameters.get("pullback_max_age", 20),
        )
    except ValueError as e:
        logger.warning("Pullback detection failed: %s", e)
        return []

    # Only proceed if pullback is active
    if not pullback_state.active:
        logger.debug("No active pullback")
        return []

    # Step 3: Detect reversal (bearish for shorts)
    try:
        has_reversal = detect_reversal(
            candles,
            pullback_state,
            min_candles_for_reversal=parameters.get("min_candles_reversal", 3),
        )
    except ValueError as e:
        logger.warning("Reversal detection failed: %s", e)
        return []

    # Only generate signal if reversal confirmed
    if not has_reversal:
        logger.debug("No reversal detected")
        return []

    # All conditions met - generate signal
    latest_candle = candles[-1]

    # Calculate entry, stop, and target prices (SHORT: stop above entry, target below)
    entry_price = latest_candle.close
    atr_value = latest_candle.atr if latest_candle.atr is not None else 0.002
    stop_distance = atr_value * parameters.get("stop_loss_atr_multiplier", 2.0)
    stop_price = entry_price + stop_distance  # Stop above for shorts

    # Calculate target price using strategy's reward/risk ratio
    target_r_mult = parameters.get("target_r_mult", 2.0)
    target_price = entry_price - (
        stop_distance * target_r_mult
    )  # Target below for shorts

    # Calculate position size based on account balance and risk percentage
    account_balance = parameters.get("account_balance", 2500.0)  # Default $2,500
    position_size = (
        0.01  # Temporary placeholder, will be calculated after signal creation
    )

    # Generate deterministic signal ID
    signal_id = generate_signal_id(
        pair=parameters.get("pair", "UNKNOWN"),
        timestamp_utc=latest_candle.timestamp_utc,
        direction="SHORT",
        entry_price=entry_price,
        stop_price=stop_price,
        position_size=position_size,
        parameters_hash=parameters_hash,
    )

    # Create signal with placeholder position size
    signal = TradeSignal(
        id=signal_id,
        pair=parameters.get("pair", "EURUSD"),
        direction="SHORT",
        entry_price=entry_price,
        initial_stop_price=stop_price,
        target_price=target_price,  # Strategy-defined TP
        risk_per_trade_pct=parameters.get("position_risk_pct", 0.25),
        calc_position_size=position_size,  # Will be updated below
        tags=["pullback", "reversal", "short"],
        version="0.1.0",
        timestamp_utc=latest_candle.timestamp_utc,
    )

    # Calculate actual position size based on risk parameters
    calculated_position_size = calculate_position_size(
        signal=signal,
        account_balance=account_balance,
        risk_per_trade_pct=signal.risk_per_trade_pct,
        pip_value=10.0,
        lot_step=0.01,
        max_position_size=10.0,
    )

    # Create final signal with correct position size
    signal = TradeSignal(
        id=signal_id,
        pair=parameters.get("pair", "EURUSD"),
        direction="SHORT",
        entry_price=entry_price,
        initial_stop_price=stop_price,
        target_price=target_price,  # Strategy-defined TP
        risk_per_trade_pct=parameters.get("position_risk_pct", 0.25),
        calc_position_size=calculated_position_size,
        tags=["pullback", "reversal", "short"],
        version="0.1.0",
        timestamp_utc=latest_candle.timestamp_utc,
    )

    logger.debug(
        "Short signal generated: id=%s..., entry=%.5f, stop=%.5f, target=%.5f, timestamp=%s",
        signal_id[:16],
        entry_price,
        stop_price,
        target_price,
        latest_candle.timestamp_utc.isoformat(),
    )

    return [signal]


def can_generate_signal(
    candles: Sequence[Candle],
    last_signal_timestamp: datetime | None = None,
    cooldown_candles: int = 5,
) -> bool:
    """
    Check if signal generation is allowed (cooldown check).

    Prevents generating multiple signals in quick succession.

    Args:
        candles: Current candle sequence.
        last_signal_timestamp: Timestamp of last generated signal (None if no previous signal).
        cooldown_candles: Minimum candles between signals (default 5).

    Returns:
        True if signal generation allowed, False if in cooldown period.

    Examples:
        >>> from datetime import datetime, timezone
        >>> from models.core import Candle
        >>> candles = [...]
        >>> last_signal = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        >>> can_generate = can_generate_signal(candles, last_signal, cooldown_candles=5)
        >>> can_generate
        True
    """
    if last_signal_timestamp is None:
        return True

    if not candles:
        return False

    # Count candles since last signal
    candles_since_signal = 0
    for candle in reversed(candles):
        if candle.timestamp_utc <= last_signal_timestamp:
            break
        candles_since_signal += 1

    # Allow signal if cooldown period passed
    return candles_since_signal >= cooldown_candles
