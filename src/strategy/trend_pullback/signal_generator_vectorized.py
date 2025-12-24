"""
Vectorized signal generator for the trend pullback strategy using Polars.

This module replaces the iterative object-oriented signal generation with efficient
columnar operations using Polars expressions. It implements the same logic:
1. Trend Classification (EMA crossovers)
2. Pullback Detection (Oscillator extremes)
3. Reversal Confirmation (Momentum turns + Candlestick patterns)
"""

import logging
from typing import Dict, Any, List, Optional
import polars as pl
import numpy as np
from datetime import datetime

from ...models.core import TradeSignal
from ...strategy.id_factory import compute_parameters_hash, generate_signal_id


logger = logging.getLogger(__name__)


def generate_signals_vectorized(
    df: pl.DataFrame,
    parameters: Dict[str, Any],
    direction_mode: str = "BOTH",  # "LONG", "SHORT", "BOTH"
) -> List[TradeSignal]:
    """
    Generate trade signals for the entire dataset using vectorized operations.

    Args:
        df: Polars DataFrame with OHLCV and indicator columns.
        parameters: Strategy parameters.
        direction_mode: Direction to generate signals for.

    Returns:
        List of TradeSignal objects.
    """
    if df.is_empty():
        return []

    # Ensure required columns exist
    required_cols = [
        "timestamp_utc",
        "open",
        "high",
        "low",
        "close",
        "ema20",
        "ema50",
        "rsi14",
        "stoch_rsi",
        "atr14",
    ]
    missing = [c for c in required_cols if c not in df.columns]

    # Handle legacy column names if necessary
    if "atr" in df.columns and "atr14" not in df.columns:
        df = df.with_columns(pl.col("atr").alias("atr14"))

    if missing and not ("atr" in missing and "atr14" in df.columns):
        # check again after aliasing
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    # compute parameters hash
    parameters_hash = compute_parameters_hash(parameters)

    # --- Step 1: Trend Classification ---
    # UP: EMA20 > EMA50, DOWN: EMA20 < EMA50
    # We also need to check for "RANGE" condition (too many crossovers),
    # but for vectorization we can simplify or implement the rolling count.

    cross_threshold = parameters.get("trend_cross_count_threshold", 3)

    # Calculate crossovers (where relationship changes)
    # 1 where EMA20 > EMA50, 0 otherwise
    ema_rel = (pl.col("ema20") > pl.col("ema50")).cast(pl.Int8)
    # Detect change: current != prev
    crossovers = (ema_rel != ema_rel.shift(1)).cast(pl.Int8).fill_null(0)

    # Rolling sum of crossovers in last 50 candles
    rolling_crosses = crossovers.rolling_sum(window_size=50).fill_null(0)

    # Define Trend State
    # 1 = UP, -1 = DOWN, 0 = RANGE
    trend_state = (
        pl.when(rolling_crosses >= cross_threshold)
        .then(0)
        .when(pl.col("ema20") > pl.col("ema50"))
        .then(1)
        .when(pl.col("ema20") < pl.col("ema50"))
        .then(-1)
        .otherwise(0)
    ).alias("trend_state")

    df = df.with_columns(trend_state)

    signals: List[TradeSignal] = []

    if direction_mode in ["LONG", "BOTH"]:
        long_signals = _generate_long_signals_vec(df, parameters, parameters_hash)
        signals.extend(long_signals)

    if direction_mode in ["SHORT", "BOTH"]:
        short_signals = _generate_short_signals_vec(df, parameters, parameters_hash)
        signals.extend(short_signals)

    # Deduplicate by timestamp if BOTH mode generated duplicate signals (shouldn't happen with logic)
    # Sort by timestamp
    signals.sort(key=lambda x: x.timestamp_utc)

    return signals


def _generate_long_signals_vec(
    df: pl.DataFrame, parameters: Dict[str, Any], parameters_hash: str
) -> List[TradeSignal]:
    """Generate LONG signals using Polars expressions."""

    rsi_oversold = parameters.get("rsi_oversold", 30.0)
    stoch_rsi_low = parameters.get("stoch_rsi_low", 0.2)
    min_candles_reversal = parameters.get("min_candles_reversal", 3)

    # --- Step 2: Pullback Detection (LONG) ---
    # Condition: Trend is UP AND (RSI < oversold OR StochRSI < low)
    # We need to find *active* pullbacks. A pullback starts when oscillator goes extreme
    # and remains valid for `pullback_max_age` candles.

    # Identify candles where oscillator is extreme
    is_extreme = (pl.col("trend_state") == 1) & (
        (pl.col("rsi14") < rsi_oversold) | (pl.col("stoch_rsi") < stoch_rsi_low)
    )

    # We need to propagate the "active pullback" state forward.
    # A pullback is active if `is_extreme` was true within the last N candles
    # AND the trend is still UP.
    pullback_max_age = parameters.get("pullback_max_age", 20)

    # Use rolling_max on the boolean (cast to int) to check if any in window was true
    # We shift by 1 because the *current* candle being extreme counts, but we also want
    # to know if a previous candle started the pullback.
    # Actually, if the current candle is extreme, we are in a pullback.
    # If a previous candle (up to max_age) was extreme, we are still in a pullback.
    pullback_active = (
        is_extreme.cast(pl.Int8).rolling_max(window_size=pullback_max_age).fill_null(0)
        == 1
    ) & (pl.col("trend_state") == 1)

    # --- Step 3: Reversal Detection (LONG) ---
    # 1. Momentum Turn:
    #    RSI low (<40) then rising, OR StochRSI low (<0.3) then rising.

    prev_rsi = pl.col("rsi14").shift(1)
    rsi_turn_up = (prev_rsi < 40) & (pl.col("rsi14") > prev_rsi)

    prev_stoch = pl.col("stoch_rsi").shift(1)
    stoch_turn_up = (prev_stoch < 0.3) & (pl.col("stoch_rsi") > prev_stoch)

    momentum_turn = rsi_turn_up | stoch_turn_up

    # 2. Candlestick Patterns (Bullish Engulfing or Hammer)
    prev_open = pl.col("open").shift(1)
    prev_close = pl.col("close").shift(1)

    # Bullish Engulfing
    # Prev: Red (close < open)
    # Curr: Green (close > open)
    # Engulfs: Open < Prev Close AND Close > Prev Open
    bullish_engulfing = (
        (prev_close < prev_open)
        & (pl.col("close") > pl.col("open"))
        & (pl.col("open") < prev_close)
        & (pl.col("close") > prev_open)
    )

    # Hammer
    # Body small (top), long lower wick, short upper wick
    body_size = (pl.col("close") - pl.col("open")).abs()
    upper_wick = pl.col("high") - pl.max_horizontal("open", "close")
    lower_wick = pl.min_horizontal("open", "close") - pl.col("low")

    is_hammer = (
        (body_size > 0) & (lower_wick >= 2 * body_size) & (upper_wick < 0.5 * body_size)
    )

    has_pattern = bullish_engulfing | is_hammer

    # Combined Signal Condition
    # Pullback Active AND Momentum Turn AND Pattern
    signal_condition = pullback_active & momentum_turn & has_pattern

    # Filter df to rows with signals
    signal_df = df.filter(signal_condition)

    if signal_df.is_empty():
        return []

    # Create TradeSignal objects
    signals = []
    stop_mult = parameters.get("stop_loss_atr_multiplier", 2.0)
    target_r_mult = parameters.get("target_r_mult", 2.0)  # Strategy's reward/risk
    risk_pct = parameters.get("position_risk_pct", 0.25)
    pair = parameters.get("pair", "EURUSD")

    # We iterate over the *filtered* rows, which should be very few compared to total data
    # iterating over Polars rows is slow if many, but signals are sparse.
    for row in signal_df.iter_rows(named=True):
        entry_price = row["close"]
        atr_val = row["atr14"] if row["atr14"] is not None else 0.002
        stop_distance = atr_val * stop_mult
        stop_price = entry_price - stop_distance
        target_price = entry_price + (stop_distance * target_r_mult)
        timestamp = row["timestamp_utc"]

        # Determine tags
        tags = ["pullback", "reversal", "long"]

        signal_id = generate_signal_id(
            pair=pair,
            timestamp_utc=timestamp,
            direction="LONG",
            entry_price=entry_price,
            stop_price=stop_price,
            position_size=0.01,  # Placeholder
            parameters_hash=parameters_hash,
        )

        signal = TradeSignal(
            id=signal_id,
            pair=pair,
            direction="LONG",
            entry_price=entry_price,
            initial_stop_price=stop_price,
            target_price=target_price,  # Strategy-defined TP
            risk_per_trade_pct=risk_pct,
            calc_position_size=0.01,
            tags=tags,
            version="0.1.0",
            timestamp_utc=timestamp,
        )
        signals.append(signal)

    return signals


def _generate_short_signals_vec(
    df: pl.DataFrame, parameters: Dict[str, Any], parameters_hash: str
) -> List[TradeSignal]:
    """Generate SHORT signals using Polars expressions."""

    rsi_overbought = parameters.get("rsi_overbought", 70.0)
    stoch_rsi_high = parameters.get("stoch_rsi_high", 0.8)

    # --- Step 2: Pullback Detection (SHORT) ---
    # Condition: Trend is DOWN AND (RSI > overbought OR StochRSI > high)

    is_extreme = (pl.col("trend_state") == -1) & (
        (pl.col("rsi14") > rsi_overbought) | (pl.col("stoch_rsi") > stoch_rsi_high)
    )

    pullback_max_age = parameters.get("pullback_max_age", 20)

    pullback_active = (
        is_extreme.cast(pl.Int8).rolling_max(window_size=pullback_max_age).fill_null(0)
        == 1
    ) & (pl.col("trend_state") == -1)

    # --- Step 3: Reversal Detection (SHORT) ---
    # 1. Momentum Turn:
    #    RSI high (>60) then falling, OR StochRSI high (>0.7) then falling.

    prev_rsi = pl.col("rsi14").shift(1)
    rsi_turn_down = (prev_rsi > 60) & (pl.col("rsi14") < prev_rsi)

    prev_stoch = pl.col("stoch_rsi").shift(1)
    stoch_turn_down = (prev_stoch > 0.7) & (pl.col("stoch_rsi") < prev_stoch)

    momentum_turn = rsi_turn_down | stoch_turn_down

    # 2. Candlestick Patterns (Bearish Engulfing or Shooting Star)
    prev_open = pl.col("open").shift(1)
    prev_close = pl.col("close").shift(1)

    # Bearish Engulfing
    # Prev: Green (close > open)
    # Curr: Red (close < open)
    # Engulfs: Open > Prev Close AND Close < Prev Open
    bearish_engulfing = (
        (prev_close > prev_open)
        & (pl.col("close") < pl.col("open"))
        & (pl.col("open") > prev_close)
        & (pl.col("close") < prev_open)
    )

    # Shooting Star
    # Small body (bottom), long upper wick, short lower wick
    body_size = (pl.col("close") - pl.col("open")).abs()
    upper_wick = pl.col("high") - pl.max_horizontal("open", "close")
    lower_wick = pl.min_horizontal("open", "close") - pl.col("low")

    is_shooting_star = (
        (body_size > 0) & (upper_wick >= 2 * body_size) & (lower_wick < 0.5 * body_size)
    )

    has_pattern = bearish_engulfing | is_shooting_star

    # Combined Signal Condition
    signal_condition = pullback_active & momentum_turn & has_pattern

    # Filter df to rows with signals
    signal_df = df.filter(signal_condition)

    if signal_df.is_empty():
        return []

    # Create TradeSignal objects
    signals = []
    stop_mult = parameters.get("stop_loss_atr_multiplier", 2.0)
    target_r_mult = parameters.get("target_r_mult", 2.0)  # Strategy's reward/risk
    risk_pct = parameters.get("position_risk_pct", 0.25)
    pair = parameters.get("pair", "EURUSD")

    for row in signal_df.iter_rows(named=True):
        entry_price = row["close"]
        atr_val = row["atr14"] if row["atr14"] is not None else 0.002
        stop_distance = atr_val * stop_mult
        stop_price = entry_price + stop_distance  # Stop above for shorts
        target_price = entry_price - (stop_distance * target_r_mult)  # Target below
        timestamp = row["timestamp_utc"]

        tags = ["pullback", "reversal", "short"]

        signal_id = generate_signal_id(
            pair=pair,
            timestamp_utc=timestamp,
            direction="SHORT",
            entry_price=entry_price,
            stop_price=stop_price,
            position_size=0.01,
            parameters_hash=parameters_hash,
        )

        signal = TradeSignal(
            id=signal_id,
            pair=pair,
            direction="SHORT",
            entry_price=entry_price,
            initial_stop_price=stop_price,
            target_price=target_price,  # Strategy-defined TP
            risk_per_trade_pct=risk_pct,
            calc_position_size=0.01,
            tags=tags,
            version="0.1.0",
            timestamp_utc=timestamp,
        )
        signals.append(signal)

    return signals
