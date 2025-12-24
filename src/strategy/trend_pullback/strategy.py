"""Trend pullback strategy implementation with indicator requirements.

This module provides the complete trend_pullback strategy implementation
conforming to the Strategy interface.
"""

from typing import Optional

import numpy as np

from src.models.visualization_config import (
    IndicatorDisplayConfig,
    VisualizationConfig,
)
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
            required_indicators=["ema20", "ema50", "atr14", "rsi14", "stoch_rsi"],
            tags=["trend-following", "pullback", "momentum"],
            max_concurrent_positions=1,  # One trade at a time per FR-001
        )

    def get_visualization_config(self) -> Optional[VisualizationConfig]:
        """Return visualization configuration for trend pullback indicators.

        Configures:
        - Price overlays: ema20 (fast, green), ema50 (slow, yellow-green)
        - Oscillators: stoch_rsi, rsi14 (auto-colored from palette)

        Colors are assigned from the ordered gradient palette:
        - ema20 (position 0) = green (fastest MA)
        - ema50 (position 1) = next gradient color

        Returns:
            VisualizationConfig with trend pullback indicators.
        """
        return VisualizationConfig(
            price_overlays=[
                # Order matters: fastest to slowest for gradient colors
                IndicatorDisplayConfig(name="ema20", label="EMA 20"),
                IndicatorDisplayConfig(name="ema50", label="EMA 50"),
            ],
            oscillators=[
                # Oscillators use distinct cycling palette
                IndicatorDisplayConfig(name="stoch_rsi", label="Stoch RSI"),
                IndicatorDisplayConfig(name="rsi14", label="RSI 14"),  # FR-003
            ],
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
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
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
            Tuple of (signal_indices, stop_prices, target_prices, position_sizes) arrays
        """
        # Extract required indicators (using actual registered names)
        ema20 = indicator_arrays["ema20"]
        ema50 = indicator_arrays["ema50"]
        stoch_rsi = indicator_arrays["stoch_rsi"]
        atr14 = indicator_arrays.get(
            "atr14", indicator_arrays.get("atr")
        )  # Handle both names

        # Get parameters with defaults (stoch_rsi is 0-1, not 0-100)
        rsi_oversold = parameters.get("rsi_oversold", 0.3)
        rsi_overbought = parameters.get("rsi_overbought", 0.7)
        stop_atr_mult = parameters.get("stop_loss_atr_multiplier", 2.0)
        target_atr_mult = parameters.get("target_profit_atr_multiplier", 4.0)  # 2:1 R:R

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

        signal_indices = np.where(signal_mask)[0]

        # Calculate stop/target prices from ATR (strategy logic, not backtester!)
        if len(signal_indices) == 0:
            return signal_indices, np.array([]), np.array([]), np.array([])

        entry_prices = close[signal_indices]
        atr_values = (
            atr14[signal_indices]
            if atr14 is not None
            else np.full(len(signal_indices), 0.002)
        )

        # LONG: stop below, target above
        # SHORT: stop above, target below
        # For now assume LONG (can be extended based on signal_mask)
        if direction == "LONG":
            stop_prices = entry_prices - (atr_values * stop_atr_mult)
            target_prices = entry_prices + (atr_values * target_atr_mult)
        elif direction == "SHORT":
            stop_prices = entry_prices + (atr_values * stop_atr_mult)
            target_prices = entry_prices - (atr_values * target_atr_mult)
        else:  # BOTH - need to determine direction per signal
            # Use the signal_mask to determine which are LONG vs SHORT
            is_long = (trend_up & pullback_long & cross_above)[signal_indices]
            stop_prices = np.where(
                is_long,
                entry_prices - (atr_values * stop_atr_mult),
                entry_prices + (atr_values * stop_atr_mult),
            )
            target_prices = np.where(
                is_long,
                entry_prices + (atr_values * target_atr_mult),
                entry_prices - (atr_values * target_atr_mult),
            )

        # Calculate position sizes based on risk parameters (strategy responsibility!)
        account_balance = parameters.get("account_balance", 2500.0)
        risk_per_trade_pct = parameters.get("risk_per_trade_pct", 0.25)  # 0.25%
        pip_value = 10.0  # Standard forex pip value

        # Calculate stop distance in pips
        stop_distances_pips = np.abs(entry_prices - stop_prices) * 10000
        stop_distances_pips = np.maximum(stop_distances_pips, 0.1)  # Avoid div by zero

        # Calculate risk amount and position sizes
        risk_amount = account_balance * (risk_per_trade_pct / 100.0)
        position_sizes = risk_amount / (stop_distances_pips * pip_value)

        # Round to lot step and clamp
        position_sizes = np.floor(position_sizes / 0.01) * 0.01
        position_sizes = np.clip(position_sizes, 0.01, 10.0)

        return signal_indices, stop_prices, target_prices, position_sizes


# Global instance for easy access
TREND_PULLBACK_STRATEGY = TrendPullbackStrategy()
