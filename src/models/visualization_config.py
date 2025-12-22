"""Visualization configuration models for strategy-controlled chart display.

This module defines configuration dataclasses that allow strategies to specify
how their indicators should be visualized in backtest charts.

Per FR-001 (017-dynamic-viz-indicators), strategies expose visualization
configuration via get_visualization_config() method.
"""

from dataclasses import dataclass, field
from typing import Optional


# Full gradient palette for moving averages (fastest to slowest)
# Used to interpolate colors when there are 3+ MAs
_MA_GRADIENT = [
    "#00FF00",  # Bright Green (fastest)
    "#7FFF00",  # Chartreuse
    "#ADFF2F",  # Green Yellow
    "#FFFF00",  # Yellow
    "#FFD700",  # Gold
    "#FFA500",  # Orange
    "#FF8C00",  # Dark Orange
    "#FF4500",  # Orange Red
    "#FF0000",  # Red
    "#DC143C",  # Crimson (slowest)
]

# Anchor colors - always present when 2+ MAs
MA_COLOR_FASTEST = "#00FF00"  # Bright Green
MA_COLOR_SLOWEST = "#DC143C"  # Crimson

# Default color for non-MA price indicators (ATR, Bollinger Bands, etc.)
NON_MA_INDICATOR_COLOR = "#00FFFF"  # Cyan

# Ordered color palette for oscillators
# Distinct colors that work well together on dark backgrounds
OSCILLATOR_COLOR_PALETTE = [
    "#00FFFF",  # Cyan
    "#FF69B4",  # Hot Pink
    "#FFFF00",  # Yellow
    "#DA70D6",  # Orchid
    "#98FB98",  # Pale Green
]

# Fallback color when palettes are exhausted or color is invalid
DEFAULT_FALLBACK_COLOR = "#FFFFFF"  # White


def get_ma_color(index: int, total_count: int) -> str:
    """Get a color for a moving average by its position in the list.

    Color distribution logic:
    - 1 MA: Bright Green
    - 2 MAs: Green (first), Crimson (last)
    - 3+ MAs: Green (first), Crimson (last), middle colors interpolated

    Args:
        index: 0-based index of the MA in the list.
        total_count: Total number of MAs being displayed.

    Returns:
        Hex color string from the gradient palette.

    Examples:
        >>> get_ma_color(0, 1)  # Single MA
        '#00FF00'
        >>> get_ma_color(0, 2)  # First of two MAs
        '#00FF00'
        >>> get_ma_color(1, 2)  # Second of two MAs
        '#DC143C'
        >>> get_ma_color(1, 3)  # Middle of three MAs
        '#FFD700'
    """
    if total_count <= 0:
        return MA_COLOR_FASTEST

    if total_count == 1:
        # Single MA is always bright green
        return MA_COLOR_FASTEST

    if total_count == 2:
        # Two MAs: green and crimson
        return MA_COLOR_FASTEST if index == 0 else MA_COLOR_SLOWEST

    # 3+ MAs: anchor green and crimson, interpolate middle
    if index == 0:
        return MA_COLOR_FASTEST
    if index == total_count - 1:
        return MA_COLOR_SLOWEST

    # Calculate middle color from palette
    # Map index 1..(total_count-2) to gradient positions 1..(len-2)
    gradient_len = len(_MA_GRADIENT)
    # Calculate position in gradient (skip first and last)
    position = 1 + int((index - 1) * (gradient_len - 2) / max(total_count - 2, 1))
    position = min(position, gradient_len - 2)  # Clamp to valid range
    return _MA_GRADIENT[position]


def get_oscillator_color(index: int) -> str:
    """Get a color for an oscillator by its order index.

    Args:
        index: 0-based index in oscillator list.

    Returns:
        Hex color string from the oscillator palette.

    Examples:
        >>> get_oscillator_color(0)  # First oscillator
        '#00FFFF'
        >>> get_oscillator_color(1)  # Second oscillator
        '#FF69B4'
    """
    if index < 0:
        return OSCILLATOR_COLOR_PALETTE[0]
    if index >= len(OSCILLATOR_COLOR_PALETTE):
        # Cycle through palette if more oscillators than colors
        return OSCILLATOR_COLOR_PALETTE[index % len(OSCILLATOR_COLOR_PALETTE)]
    return OSCILLATOR_COLOR_PALETTE[index]


@dataclass(frozen=True)
class IndicatorDisplayConfig:
    """Display configuration for a single indicator.

    Attributes:
        name: Indicator column name in DataFrame (e.g., "ema20", "rsi14").
        color: CSS color for the indicator line (hex, named, or rgb).
            If None, color will be assigned automatically from palette.
        label: Display label in chart legend. If None, uses the name.
        is_ma: Whether this is a moving average indicator (affects color palette).
            If None, auto-detected from name.

    Examples:
        >>> config = IndicatorDisplayConfig(name="ema20", color="#FFD700")
        >>> config.name
        'ema20'
        >>> config.get_label()
        'ema20'

        >>> labeled = IndicatorDisplayConfig(name="ema20", label="Fast EMA")
        >>> labeled.get_label()
        'Fast EMA'
    """

    name: str
    color: Optional[str] = None  # None = auto-assign from palette
    label: Optional[str] = None
    is_ma: Optional[bool] = None  # None = auto-detect from name

    def get_label(self) -> str:
        """Return the display label, falling back to name if not set."""
        return self.label if self.label is not None else self.name

    def get_color_or_default(self, fallback: str = DEFAULT_FALLBACK_COLOR) -> str:
        """Return the configured color or a fallback if not set.

        Args:
            fallback: Color to use if self.color is None.

        Returns:
            The configured color or fallback.
        """
        return self.color if self.color is not None else fallback

    def is_moving_average(self) -> bool:
        """Determine if this indicator is a moving average.

        Returns True if:
        - is_ma is explicitly set to True
        - name contains 'ema', 'sma', or 'ma' (case-insensitive)

        Used to determine which color palette to use.
        """
        if self.is_ma is not None:
            return self.is_ma
        # Auto-detect from name
        name_lower = self.name.lower()
        ma_patterns = ["ema", "sma", "wma", "dema", "tema"]
        return any(p in name_lower for p in ma_patterns)


@dataclass(frozen=True)
class VisualizationConfig:
    """Visualization configuration for a strategy's indicators.

    Contains separate lists for price-scale overlays (EMAs, SMAs, etc.)
    and oscillator panel indicators (RSI, StochRSI, etc.).

    Colors are assigned automatically based on position in the list:
    - MAs: Green (fastest) -> Crimson (slowest) with middle interpolation
    - Non-MA price indicators: Cyan
    - Oscillators: Distinct colors cycling through palette

    Attributes:
        price_overlays: Indicators to overlay on the price chart.
            Order matters: first = fastest (green), last = slowest (crimson).
        oscillators: Indicators for the oscillator panel below the price chart.

    Examples:
        >>> config = VisualizationConfig(
        ...     price_overlays=[
        ...         IndicatorDisplayConfig(name="ema8"),   # Auto: green
        ...         IndicatorDisplayConfig(name="ema21"),  # Auto: middle
        ...         IndicatorDisplayConfig(name="ema50"),  # Auto: crimson
        ...     ],
        ...     oscillators=[
        ...         IndicatorDisplayConfig(name="stoch_rsi"),  # Auto: cyan
        ...     ],
        ... )
        >>> len(config.price_overlays)
        3
    """

    price_overlays: list[IndicatorDisplayConfig] = field(default_factory=list)
    oscillators: list[IndicatorDisplayConfig] = field(default_factory=list)

    def is_empty(self) -> bool:
        """Return True if no indicators are configured."""
        return not self.price_overlays and not self.oscillators

    def get_overlay_color(self, index: int, indicator: IndicatorDisplayConfig) -> str:
        """Get color for a price overlay at given index.

        Uses configured color if set, otherwise:
        - MAs: Color from green->crimson gradient
        - Non-MAs: Cyan
        """
        if indicator.color is not None:
            return indicator.color

        if indicator.is_moving_average():
            # Count total MAs for proper gradient distribution
            ma_count = sum(1 for ind in self.price_overlays if ind.is_moving_average())
            # Find this MA's position among all MAs
            ma_index = sum(
                1
                for i, ind in enumerate(self.price_overlays)
                if i < index and ind.is_moving_average()
            )
            return get_ma_color(ma_index, ma_count)
        else:
            return NON_MA_INDICATOR_COLOR

    def get_oscillator_color(
        self, index: int, indicator: IndicatorDisplayConfig
    ) -> str:
        """Get color for an oscillator at given index.

        Uses configured color if set, otherwise assigns from oscillator palette.
        """
        if indicator.color is not None:
            return indicator.color
        return get_oscillator_color(index)


__all__ = [
    "IndicatorDisplayConfig",
    "VisualizationConfig",
    "MA_COLOR_FASTEST",
    "MA_COLOR_SLOWEST",
    "NON_MA_INDICATOR_COLOR",
    "OSCILLATOR_COLOR_PALETTE",
    "DEFAULT_FALLBACK_COLOR",
    "get_ma_color",
    "get_oscillator_color",
]
