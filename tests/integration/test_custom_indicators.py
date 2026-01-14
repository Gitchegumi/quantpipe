import pytest
import polars as pl
import numpy as np
from src.strategy.base import Strategy, StrategyMetadata
from src.indicators.dispatcher import calculate_indicators
from typing import Callable, Any, Optional
from src.models.visualization_config import VisualizationConfig


def custom_func(df: pl.DataFrame, **kwargs) -> pl.DataFrame:
    # Simple indicator: close * 1.01
    return df.with_columns((pl.col("close") * 1.01).alias("custom_ind"))


class CustomIndicatorStrategy:
    """Mock strategy implementing the Protocol."""

    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="test-custom-ind",
            version="1.0.0",
            required_indicators=["custom_ind"],
            tags=["test"],
            max_concurrent_positions=1,
        )

    def get_custom_indicators(self) -> dict[str, Callable]:
        return {"custom_ind": custom_func}

    def generate_signals(self, candles, parameters):
        return []

    def scan_vectorized(self, close, indicator_arrays, parameters, direction):
        return (np.array([]), np.array([]), np.array([]), np.array([]))

    def get_visualization_config(self) -> Optional["VisualizationConfig"]:
        return None


def test_custom_indicator_resolution():
    strategy = CustomIndicatorStrategy()
    custom_registry = strategy.get_custom_indicators()

    # Create mock data
    df = pl.DataFrame(
        {
            "time": [1, 2, 3],
            "open": [100.0, 101.0, 102.0],
            "high": [105.0, 106.0, 107.0],
            "low": [95.0, 96.0, 97.0],
            "close": [100.0, 101.0, 102.0],
            "volume": [1000, 1000, 1000],
        }
    )

    # Calculate indicators using the dispatcher
    enriched_df = calculate_indicators(
        df, ["custom_ind"], custom_registry=custom_registry
    )

    # Verify column exists
    assert "custom_ind" in enriched_df.columns
    # Verify calculation
    assert enriched_df["custom_ind"][0] == 100.0 * 1.01
