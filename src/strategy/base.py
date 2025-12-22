"""Base strategy interface and metadata.

This module defines the interface that all strategies must implement,
including declaring their required indicators.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Protocol

if TYPE_CHECKING:
    import numpy as np
    from src.models.visualization_config import VisualizationConfig


@dataclass(frozen=True)
class StrategyMetadata:
    """Metadata describing a strategy's requirements and characteristics.

    Attributes:
        name: Unique strategy identifier.
        version: Semantic version string.
        required_indicators: List of indicator names this strategy needs.
            Examples: ["ema20", "ema50", "atr14", "stoch_rsi"]
        tags: Classification tags for filtering/grouping.
    """

    name: str
    version: str
    required_indicators: list[str]
    tags: list[str] = None

    def __post_init__(self):
        """Ensure tags is always a list."""
        if self.tags is None:
            object.__setattr__(self, "tags", [])


class Strategy(Protocol):
    """Protocol defining the interface all strategies must implement.

    Strategies must provide metadata declaring their indicator requirements
    and implement signal generation methods.
    """

    @property
    def metadata(self) -> StrategyMetadata:
        """Return strategy metadata including required indicators."""

    def generate_signals(self, candles: list, parameters: dict) -> list:
        """Generate trade signals from candle data.

        Args:
            candles: List of Candle objects with indicator data populated.
            parameters: Strategy-specific parameters.

        Returns:
            List of TradeSignal objects.
        """

    def scan_vectorized(
        self,
        close: "np.ndarray",
        indicator_arrays: dict[str, "np.ndarray"],
        parameters: dict,
        direction: str,
    ) -> "np.ndarray":
        """Scan for signals using vectorized operations (optional, for performance).

        This is an optional method that strategies can implement for high-performance
        batch scanning. If not implemented, the backtester will fall back to calling
        generate_signals() in a loop.

        Args:
            close: Close price array
            indicator_arrays: Dictionary of indicator name -> NumPy array
                (e.g., {"ema_20": array([...]), "rsi": array([...])})
            parameters: Strategy-specific parameters
            direction: Trading direction ("LONG", "SHORT", or "BOTH")

        Returns:
            NumPy array of indices where signals occur

        Raises:
            NotImplementedError: If strategy doesn't support vectorized scanning
        """

    def get_visualization_config(self) -> Optional["VisualizationConfig"]:
        """Return visualization configuration for this strategy's indicators.

        Optional method that strategies can implement to control how their
        indicators are displayed in backtest visualization charts.

        Returns:
            VisualizationConfig specifying price overlays and oscillators,
            or None to use auto-detection fallback.

        Examples:
            >>> from src.models import VisualizationConfig, IndicatorDisplayConfig
            >>> def get_visualization_config(self):
            ...     return VisualizationConfig(
            ...         price_overlays=[
            ...             IndicatorDisplayConfig(name="ema20", color="#FFD700"),
            ...         ],
            ...         oscillators=[
            ...             IndicatorDisplayConfig(name="stoch_rsi", color="#00FFFF"),
            ...         ],
            ...     )
        """
