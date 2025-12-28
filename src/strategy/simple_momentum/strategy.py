"""Simple momentum strategy - Reference implementation.

This module provides a complete, working implementation of the Strategy Protocol
that can be used as a reference for creating new strategies. It demonstrates:

1. Proper metadata configuration with required indicators
2. Signal generation logic with candle iteration
3. Visualization configuration for chart display
4. Documentation patterns for strategy methods

The strategy uses a simple EMA crossover momentum approach:
- LONG: When fast EMA (20) crosses above slow EMA (50)
- SHORT: When fast EMA (20) crosses below slow EMA (50)

This is intentionally simple to serve as a learning example.
For production strategies, see src/strategy/trend_pullback/ for more
sophisticated signal logic.

Example:
    from src.strategy.simple_momentum import SIMPLE_MOMENTUM_STRATEGY

    # Generate signals from candle data
    signals = SIMPLE_MOMENTUM_STRATEGY.generate_signals(candles, parameters)
"""

import numpy as np

from src.models.visualization_config import (
    IndicatorDisplayConfig,
    VisualizationConfig,
)
from src.strategy.base import StrategyMetadata


class SimpleMomentumStrategy:
    """Simple EMA crossover momentum strategy.

    This reference implementation demonstrates the Strategy Protocol pattern.
    It uses EMA crossovers to identify momentum shifts:

    - LONG signals: Fast EMA crosses above slow EMA (bullish momentum)
    - SHORT signals: Fast EMA crosses below slow EMA (bearish momentum)

    Attributes:
        This class has no instance attributes. All configuration is
        provided through the metadata property.

    Example:
        strategy = SimpleMomentumStrategy()
        print(strategy.metadata.name)  # "simple_momentum"
        print(strategy.metadata.required_indicators)  # ["ema20", "ema50"]
    """

    # ==========================================================================
    # SECTION 1: METADATA
    # ==========================================================================
    # The metadata property tells the backtester what this strategy needs.
    # It declares required indicators so they're available on each candle.
    # ==========================================================================

    @property
    def metadata(self) -> StrategyMetadata:
        """Return strategy metadata including required indicators.

        This property is REQUIRED by the Strategy Protocol. It declares:
        - name: Unique identifier for registry lookup
        - version: Semantic version for tracking changes
        - required_indicators: Indicators the backtester must compute
        - tags: Classification for filtering strategies
        - max_concurrent_positions: Position limits (1 = one trade at a time)

        Returns:
            StrategyMetadata with complete strategy configuration.
        """
        return StrategyMetadata(
            # Unique name - used for CLI --strategy flag and registry lookup
            name="simple_momentum",
            # Semantic version - increment when logic changes
            version="1.0.0",
            # Required indicators - these will be available on each candle
            # Format: indicator_name (e.g., "ema20" = EMA with period 20)
            required_indicators=[
                "ema20",  # Fast EMA for momentum detection
                "ema50",  # Slow EMA for trend baseline
                "atr14",  # ATR for stop loss calculation
            ],
            # Tags for strategy classification and filtering
            tags=["momentum", "trend-following", "reference"],
            # Maximum concurrent positions (1 = single trade at a time)
            max_concurrent_positions=1,
        )

    # ==========================================================================
    # SECTION 2: VISUALIZATION CONFIG
    # ==========================================================================
    # Optional: Configure how indicators appear in backtest charts.
    # Return None to use auto-detection based on indicator names.
    # ==========================================================================

    def get_visualization_config(self) -> VisualizationConfig | None:
        """Return visualization configuration for chart display.

        This optional method controls how indicators appear in backtest
        visualization charts. Configure:
        - price_overlays: Indicators drawn on the price chart (EMAs, BBands)
        - oscillators: Indicators in separate panels (RSI, StochRSI)

        Returns:
            VisualizationConfig with display settings.
        """
        return VisualizationConfig(
            # Indicators overlaid on the price chart
            price_overlays=[
                # Fast EMA in gold color
                IndicatorDisplayConfig(name="ema20", color="#FFD700"),
                # Slow EMA in green
                IndicatorDisplayConfig(name="ema50", color="#32CD32"),
            ],
            # Oscillator indicators (shown in separate panel)
            oscillators=[
                # No oscillators in this simple strategy
            ],
        )

    # ==========================================================================
    # SECTION 3: SIGNAL GENERATION
    # ==========================================================================
    # The core logic that produces trade signals from candle data.
    # This is called by the backtester for each batch of candles.
    # ==========================================================================

    def generate_signals(
        self,
        candles: list,
        parameters: dict,
        direction: str = "BOTH",
    ) -> list:
        """Generate trade signals from candle data.

        This method is REQUIRED by the Strategy Protocol. It receives
        candle data with indicators already computed and returns a list
        of TradeSignal objects.

        The backtester calls this method with:
        - candles: List of Candle objects, each with indicator values
                  as attributes (e.g., candle.ema20, candle.atr14)
        - parameters: Dict with strategy parameters like:
                     - stop_atr_multiplier: ATR multiplier for stop loss
                     - take_profit_r: Risk/reward ratio for targets
        - direction: "LONG", "SHORT", or "BOTH" to filter signal types

        Args:
            candles: List of Candle objects with populated indicators.
                    Access indicators via attributes: candle.ema20
            parameters: Strategy parameters from config. Expected keys:
                       - stop_atr_multiplier (float, default: 2.0)
                       - take_profit_r (float, default: 2.0)
            direction: Trade direction filter. One of:
                      - "LONG": Only generate long signals
                      - "SHORT": Only generate short signals
                      - "BOTH": Generate both long and short signals

        Returns:
            List of TradeSignal objects. Each signal contains:
            - timestamp: Time of signal
            - direction: "LONG" or "SHORT"
            - entry_price: Suggested entry price
            - stop_price: Stop loss level
            - target_price: Take profit level

        Example:
            signals = strategy.generate_signals(candles, {"stop_atr_multiplier": 2})
            for signal in signals:
                print(f"{signal.direction} at {signal.entry_price}")
        """
        # Import here to avoid circular imports
        from src.models.core import TradeSignal

        # Extract parameters with defaults
        stop_atr_mult = parameters.get("stop_atr_multiplier", 2.0)
        take_profit_r = parameters.get("take_profit_r", 2.0)

        signals: list[TradeSignal] = []

        # Need at least 2 candles to detect crossover
        if len(candles) < 2:
            return signals

        # Iterate through candles looking for crossovers
        for i in range(1, len(candles)):
            curr = candles[i]
            prev = candles[i - 1]

            # Skip if indicators not available
            if not all(
                hasattr(curr, attr) and hasattr(prev, attr)
                for attr in ["ema20", "ema50", "atr14"]
            ):
                continue

            # Skip if any indicator is NaN
            if any(
                np.isnan(getattr(curr, attr)) for attr in ["ema20", "ema50", "atr14"]
            ):
                continue

            atr = curr.atr14
            stop_distance = atr * stop_atr_mult
            target_distance = stop_distance * take_profit_r

            # LONG signal: Fast EMA crosses above slow EMA
            if (
                direction in ("LONG", "BOTH")
                and prev.ema20 <= prev.ema50
                and curr.ema20 > curr.ema50
            ):
                signals.append(
                    TradeSignal(
                        id=f"simple_momentum_long_{i}",
                        pair=parameters.get("pair", "UNKNOWN"),
                        direction="LONG",
                        entry_price=curr.close,
                        initial_stop_price=curr.close - stop_distance,
                        target_price=curr.close + target_distance,
                        timestamp_utc=curr.timestamp,
                    )
                )

            # SHORT signal: Fast EMA crosses below slow EMA
            if (
                direction in ("SHORT", "BOTH")
                and prev.ema20 >= prev.ema50
                and curr.ema20 < curr.ema50
            ):
                signals.append(
                    TradeSignal(
                        id=f"simple_momentum_short_{i}",
                        pair=parameters.get("pair", "UNKNOWN"),
                        direction="SHORT",
                        entry_price=curr.close,
                        initial_stop_price=curr.close + stop_distance,
                        target_price=curr.close - target_distance,
                        timestamp_utc=curr.timestamp,
                    )
                )

        return signals

    # ==========================================================================
    # SECTION 4: VECTORIZED SCANNING (OPTIONAL)
    # ==========================================================================
    # For better performance with large datasets, implement scan_vectorized.
    # This uses NumPy array operations instead of Python loops.
    # Remove or leave as NotImplementedError if not needed.
    # ==========================================================================

    def scan_vectorized(
        self,
        close: np.ndarray,
        indicator_arrays: dict[str, np.ndarray],
        parameters: dict,
        direction: str,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Scan for signals using vectorized operations.

        This OPTIONAL method provides high-performance signal scanning
        using NumPy arrays instead of Python loops. The backtester will
        use this if available, otherwise falls back to generate_signals.

        Args:
            close: Close price array of shape (N,)
            indicator_arrays: Dict mapping indicator names to arrays.
                            e.g., {"ema20": np.array([...]), ...}
            parameters: Strategy parameters (same as generate_signals)
            direction: "LONG", "SHORT", or "BOTH"

        Returns:
            Tuple of 4 arrays, each of shape (M,) where M = number of signals:
            - signal_indices: Array indices where signals occurred
            - stop_prices: Stop loss prices for each signal
            - target_prices: Take profit prices for each signal
            - position_sizes: Position sizes (typically 1.0 for each)

        Raises:
            NotImplementedError: This reference strategy doesn't implement
                               vectorized scanning. Remove this method or
                               implement it for production strategies.
        """
        # Get required arrays
        ema20 = indicator_arrays.get("ema20")
        ema50 = indicator_arrays.get("ema50")
        atr14 = indicator_arrays.get("atr14")

        if ema20 is None or ema50 is None or atr14 is None:
            return (
                np.array([], dtype=np.int64),
                np.array([], dtype=np.float64),
                np.array([], dtype=np.float64),
                np.array([], dtype=np.float64),
            )

        # Extract parameters
        stop_atr_mult = parameters.get("stop_atr_multiplier", 2.0)
        take_profit_r = parameters.get("take_profit_r", 2.0)

        # Detect crossovers using vectorized comparison
        # Shift arrays to compare current vs previous
        ema20_curr = ema20[1:]
        ema20_prev = ema20[:-1]
        ema50_curr = ema50[1:]
        ema50_prev = ema50[:-1]
        # close[1:] and atr14[1:] accessed via signal_indices below

        # Long crossover: prev <= and curr >
        long_cross = (ema20_prev <= ema50_prev) & (ema20_curr > ema50_curr)
        # Short crossover: prev >= and curr <
        short_cross = (ema20_prev >= ema50_prev) & (ema20_curr < ema50_curr)

        # Combine based on direction
        if direction == "LONG":
            signals = long_cross
            is_long = np.ones(np.sum(signals), dtype=bool)
        elif direction == "SHORT":
            signals = short_cross
            is_long = np.zeros(np.sum(signals), dtype=bool)
        else:  # BOTH
            signals = long_cross | short_cross
            is_long = long_cross[signals]

        # Get signal indices (add 1 because we shifted by 1)
        signal_indices = np.where(signals)[0] + 1

        if len(signal_indices) == 0:
            return (
                np.array([], dtype=np.int64),
                np.array([], dtype=np.float64),
                np.array([], dtype=np.float64),
                np.array([], dtype=np.float64),
            )

        # Calculate stops and targets
        entry_prices = close[signal_indices]
        atr_at_signal = atr14[signal_indices]
        stop_distance = atr_at_signal * stop_atr_mult
        target_distance = stop_distance * take_profit_r

        # Adjust for direction
        stop_prices = np.where(
            is_long,
            entry_prices - stop_distance,
            entry_prices + stop_distance,
        )
        target_prices = np.where(
            is_long,
            entry_prices + target_distance,
            entry_prices - target_distance,
        )
        position_sizes = np.ones(len(signal_indices), dtype=np.float64)

        return signal_indices, stop_prices, target_prices, position_sizes


# ==========================================================================
# GLOBAL INSTANCE
# ==========================================================================
# Create a global instance for convenient access in backtesting.
# Import this directly:
#    from src.strategy.simple_momentum import SIMPLE_MOMENTUM_STRATEGY
# ==========================================================================

SIMPLE_MOMENTUM_STRATEGY = SimpleMomentumStrategy()
