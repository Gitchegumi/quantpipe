"""Trend pullback strategy implementation with indicator requirements.

This module provides the complete trend_pullback strategy implementation
conforming to the Strategy interface.
"""

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


# Global instance for easy access
TREND_PULLBACK_STRATEGY = TrendPullbackStrategy()
