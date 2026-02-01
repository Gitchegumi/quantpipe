"""Z-Score Mean Reversion Strategy.

This strategy identifies overextended price movements using rolling Z-scores:
- LONG: Z-score < -2.0 (oversold)
- SHORT: Z-score > +2.0 (overbought)
- EXIT: Z-score returns to mean (near 0) or after a fixed period.
"""

import numpy as np
import polars as pl
from typing import Optional, Callable, Any

from src.models.visualization_config import (
    IndicatorDisplayConfig,
    VisualizationConfig,
)
from src.strategy.base import StrategyMetadata, Strategy
from src.indicators.stats import calculate_zscore


class ZScoreMeanReversionStrategy:
    """Z-Score Mean Reversion Strategy implementation."""

    @property
    def metadata(self) -> StrategyMetadata:
        """Return strategy metadata."""
        return StrategyMetadata(
            name="zscore_mean_reversion",
            version="1.0.0",
            required_indicators=[
                "zscore_100",  # Default period
                "mean_100",    # For target exit
                "atr14",       # For stop loss
            ],
            tags=["mean-reversion", "statistical"],
            max_concurrent_positions=1,
        )

    def get_visualization_config(self) -> Optional[VisualizationConfig]:
        """Configure chart display."""
        return VisualizationConfig(
            price_overlays=[],
            oscillators=[
                IndicatorDisplayConfig(name="zscore_100", color="#8884d8"),
            ],
        )

    def get_custom_indicators(self) -> dict[str, Callable[[pl.DataFrame, Any], pl.DataFrame]]:
        """Define the Z-score indicator."""
        from src.indicators.stats import calculate_rolling_mean
        
        def zscore_100(df: pl.DataFrame, **kwargs) -> pl.DataFrame:
            return calculate_zscore(df, period=100, output_col="zscore_100")
        
        def zscore_50(df: pl.DataFrame, **kwargs) -> pl.DataFrame:
            return calculate_zscore(df, period=50, output_col="zscore_50")

        def mean_100(df: pl.DataFrame, **kwargs) -> pl.DataFrame:
            return calculate_rolling_mean(df, period=100, output_col="mean_100")
        
        def mean_50(df: pl.DataFrame, **kwargs) -> pl.DataFrame:
            return calculate_rolling_mean(df, period=50, output_col="mean_50")

        return {
            "zscore_100": zscore_100,
            "zscore_50": zscore_50,
            "mean_100": mean_100,
            "mean_50": mean_50,
        }

    def generate_signals(
        self,
        candles: list,
        parameters: dict,
        direction: str = "BOTH",
    ) -> list:
        """Generate trade signals from candle data."""
        from src.models.core import TradeSignal
        from src.risk.manager import calculate_position_size
        from src.strategy.id_factory import compute_parameters_hash, generate_signal_id

        # Extract parameters
        period = parameters.get("zscore_period", 100)
        z_col = f"zscore_{period}"
        mean_col = f"mean_{period}"
        entry_threshold = parameters.get("entry_threshold", 2.0)
        stop_atr_mult = parameters.get("stop_atr_multiplier", 3.0)
        
        signals: list[TradeSignal] = []

        if not candles or len(candles) < period:
            return signals

        parameters_hash = compute_parameters_hash(parameters)
        
        for i in range(period, len(candles)):
            curr = candles[i]
            prev = candles[i - 1]
            
            # Check if indicators are available
            z_score = curr.indicators.get(z_col)
            prev_z_score = prev.indicators.get(z_col)
            atr = curr.indicators.get("atr14")
            rolling_mean = curr.indicators.get(mean_col)
            
            if any(val is None or np.isnan(val) for val in [z_score, prev_z_score, atr, rolling_mean]):
                continue

            signal_direction = None
            # CROSS into oversold: prev >= -threshold and curr < -threshold
            if direction in ("LONG", "BOTH") and prev_z_score >= -entry_threshold and z_score < -entry_threshold:
                signal_direction = "LONG"
            # CROSS into overbought: prev <= threshold and curr > threshold
            elif direction in ("SHORT", "BOTH") and prev_z_score <= entry_threshold and z_score > entry_threshold:
                signal_direction = "SHORT"

            if signal_direction:
                entry_price = curr.close
                
                if signal_direction == "LONG":
                    stop_price = entry_price - (atr * stop_atr_mult)
                    target_price = rolling_mean
                else:
                    stop_price = entry_price + (atr * stop_atr_mult)
                    target_price = rolling_mean

                # Calculate deterministic signal ID
                signal_id = generate_signal_id(
                    pair=parameters.get("pair", "UNKNOWN"),
                    timestamp_utc=curr.timestamp_utc,
                    direction=signal_direction,
                    entry_price=entry_price,
                    stop_price=stop_price,
                    position_size=0.01, # Placeholder
                    parameters_hash=parameters_hash,
                )

                # Create signal
                signal = TradeSignal(
                    id=signal_id,
                    pair=parameters.get("pair", "UNKNOWN"),
                    direction=signal_direction,
                    entry_price=entry_price,
                    initial_stop_price=stop_price,
                    target_price=target_price,
                    risk_per_trade_pct=parameters.get("risk_per_trade_pct", 0.25),
                    calc_position_size=0.01, # Placeholder
                    tags=["mean-reversion", "zscore", signal_direction.lower()],
                    version="1.0.0",
                    timestamp_utc=curr.timestamp_utc,
                    metadata={"zscore": z_score}
                )

                # Calculate actual position size
                calc_size = calculate_position_size(
                    signal=signal,
                    account_balance=parameters.get("account_balance", 2500.0),
                    risk_per_trade_pct=signal.risk_per_trade_pct,
                    pip_value=parameters.get("pip_value", 10.0),
                )

                # Re-create signal with correct position size
                signal = TradeSignal(
                    id=signal_id,
                    pair=signal.pair,
                    direction=signal.direction,
                    entry_price=signal.entry_price,
                    initial_stop_price=signal.initial_stop_price,
                    target_price=signal.target_price,
                    risk_per_trade_pct=signal.risk_per_trade_pct,
                    calc_position_size=calc_size,
                    tags=signal.tags,
                    version=signal.version,
                    timestamp_utc=signal.timestamp_utc,
                    metadata=signal.metadata
                )
                signals.append(signal)

        return signals


# Global instance
ZSCORE_STRATEGY = ZScoreMeanReversionStrategy()
