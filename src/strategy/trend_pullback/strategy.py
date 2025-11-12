"""Trend pullback strategy implementation with indicator requirements.

This module provides the complete trend_pullback strategy implementation
conforming to the Strategy interface.
"""

import numpy as np

from src.strategy.base import Strategy, StrategyMetadata
from src.strategy.trend_pullback.signal_generator import (
    generate_long_signals,
    generate_short_signals,
)


class TrendPullbackStrategy(Strategy):
    """Trend pullback continuation strategy.

    This strategy identifies:
    1. Confirmed trends (EMA crossovers)
    2. Pullbacks within trend (RSI/StochRSI)
    3. Reversal confirmation (momentum + candlestick patterns)
    """

    @property
    def metadata(self) -> StrategyMetadata:
        """Return strategy metadata including required indicators."""
        return StrategyMetadata(
            name="trend-pullback",
            version="1.0.0",
            required_indicators=["ema20", "ema50", "atr14", "stoch_rsi"],
            tags=["trend-following", "pullback", "momentum"],
        )

    def generate_signals(
        self, candles: list, parameters: dict, direction: str = "BOTH"
    ) -> list:
        """Generate trade signals from candle data.

        Args:
            candles: List of Candle objects with indicators populated.
            parameters: Strategy parameters dict.
            direction: Trade direction - "LONG", "SHORT", or "BOTH".

        Returns:
            List of TradeSignal objects.
        """
        signals = []

        if direction in ("LONG", "BOTH"):
            long_signals = generate_long_signals(candles, parameters)
            signals.extend(long_signals)

        if direction in ("SHORT", "BOTH"):
            short_signals = generate_short_signals(candles, parameters)
            signals.extend(short_signals)

        return signals

    def scan_vectorized(
        self,
        close: np.ndarray,
        indicator_arrays: dict[str, np.ndarray],
        parameters: dict,
        direction: str,
    ) -> np.ndarray:
        """Scan for signals using vectorized operations.

        Implements trend-pullback logic using NumPy array operations:
        1. Trend: EMA20 > EMA50 (LONG) or EMA20 < EMA50 (SHORT)
        2. Pullback: RSI oversold (LONG) or overbought (SHORT)
        3. Reversal: Price crosses back above/below EMA20

        Args:
            close: Close price array
            indicator_arrays: Dict of indicator arrays (ema_20, ema_50, rsi, etc.)
            parameters: Strategy parameters
            direction: "LONG", "SHORT", or "BOTH"

        Returns:
            NumPy array of indices where signals occur
        """
        # Extract required indicators (using actual registered names)
        ema20 = indicator_arrays["ema20"]
        ema50 = indicator_arrays["ema50"]
        stoch_rsi = indicator_arrays["stoch_rsi"]

        # Get parameters with defaults (stoch_rsi is 0-1, not 0-100)
        rsi_oversold = parameters.get("rsi_oversold", 0.3)
        rsi_overbought = parameters.get("rsi_overbought", 0.7)

        # Vectorized trend classification
        trend_up = ema20 > ema50
        trend_down = ema20 < ema50

        # Vectorized pullback detection
        pullback_long = trend_up & (stoch_rsi < rsi_oversold)
        pullback_short = trend_down & (stoch_rsi > rsi_overbought)

        # Vectorized reversal detection (price crosses EMA20)
        close_above_ema20 = close > ema20
        close_below_ema20 = close < ema20

        # Detect crosses using shift
        prev_close_above = np.roll(close_above_ema20, 1)
        prev_close_below = np.roll(close_below_ema20, 1)
        prev_close_above[0] = False
        prev_close_below[0] = False

        cross_above = close_above_ema20 & ~prev_close_above
        cross_below = close_below_ema20 & ~prev_close_below

        # Combine conditions based on direction
        if direction == "LONG":
            signal_mask = trend_up & pullback_long & cross_above
        elif direction == "SHORT":
            signal_mask = trend_down & pullback_short & cross_below
        else:  # BOTH
            long_signals = trend_up & pullback_long & cross_above
            short_signals = trend_down & pullback_short & cross_below
            signal_mask = long_signals | short_signals

        return np.where(signal_mask)[0]


# Global instance for easy access
TREND_PULLBACK_STRATEGY = TrendPullbackStrategy()
