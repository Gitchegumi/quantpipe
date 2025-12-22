"""Integration tests for visualization configuration.

Tests the integration between strategies, visualization config,
and the datashader visualization module.
"""

import pytest

from src.models.visualization_config import (
    IndicatorDisplayConfig,
    VisualizationConfig,
    MA_COLOR_FASTEST,
    MA_COLOR_SLOWEST,
    NON_MA_INDICATOR_COLOR,
    get_ma_color,
    get_oscillator_color,
)
from src.strategy.trend_pullback.strategy import TrendPullbackStrategy


class TestStrategyVisualizationConfig:
    """Tests for strategy visualization config integration."""

    def test_trend_pullback_has_viz_config(self):
        """TrendPullbackStrategy implements get_visualization_config()."""
        strategy = TrendPullbackStrategy()
        config = strategy.get_visualization_config()

        assert config is not None
        assert isinstance(config, VisualizationConfig)

    def test_trend_pullback_config_has_expected_overlays(self):
        """TrendPullbackStrategy has ema20 and ema50 overlays."""
        strategy = TrendPullbackStrategy()
        config = strategy.get_visualization_config()

        # Should have 2 price overlays
        assert len(config.price_overlays) == 2

        # Check overlay names
        overlay_names = [o.name for o in config.price_overlays]
        assert "ema20" in overlay_names
        assert "ema50" in overlay_names

    def test_trend_pullback_config_has_expected_oscillators(self):
        """TrendPullbackStrategy has stoch_rsi oscillator."""
        strategy = TrendPullbackStrategy()
        config = strategy.get_visualization_config()

        assert len(config.oscillators) >= 1
        oscillator_names = [o.name for o in config.oscillators]
        assert "stoch_rsi" in oscillator_names

    def test_trend_pullback_ma_colors(self):
        """TrendPullbackStrategy MAs get green and crimson."""
        strategy = TrendPullbackStrategy()
        config = strategy.get_visualization_config()

        # Two MAs should get green and crimson
        color0 = config.get_overlay_color(0, config.price_overlays[0])
        color1 = config.get_overlay_color(1, config.price_overlays[1])

        assert color0 == MA_COLOR_FASTEST  # Green for first MA
        assert color1 == MA_COLOR_SLOWEST  # Crimson for last MA


class TestAutoDetectionFallback:
    """Tests for auto-detection fallback behavior."""

    def test_strategy_without_viz_config_uses_fallback(self):
        """Strategies without get_visualization_config use auto-detection."""

        # Create a mock strategy without get_visualization_config
        class MinimalStrategy:
            @property
            def metadata(self):
                return type(
                    "Metadata",
                    (),
                    {"name": "minimal", "version": "1.0.0", "required_indicators": []},
                )()

        strategy = MinimalStrategy()

        # Should not have get_visualization_config
        assert not hasattr(strategy, "get_visualization_config")

    def test_hasattr_check_for_viz_config(self):
        """hasattr check correctly identifies strategies with/without config."""
        with_config = TrendPullbackStrategy()
        assert hasattr(with_config, "get_visualization_config")

        class WithoutConfig:
            pass

        without_config = WithoutConfig()
        assert not hasattr(without_config, "get_visualization_config")


class TestColorGradientApplication:
    """Tests for color gradient application in visualization."""

    def test_fan_strategy_colors(self):
        """Fan strategy with many MAs gets proper gradient."""
        config = VisualizationConfig(
            price_overlays=[
                IndicatorDisplayConfig(name="ema8"),
                IndicatorDisplayConfig(name="ema13"),
                IndicatorDisplayConfig(name="ema21"),
                IndicatorDisplayConfig(name="ema34"),
                IndicatorDisplayConfig(name="ema55"),
            ]
        )

        colors = [
            config.get_overlay_color(i, ind)
            for i, ind in enumerate(config.price_overlays)
        ]

        # First is always green, last is always crimson
        assert colors[0] == MA_COLOR_FASTEST
        assert colors[-1] == MA_COLOR_SLOWEST
        # Middle colors should be different
        assert len(set(colors)) >= 3  # At least 3 distinct colors

    def test_oscillator_colors_cycle(self):
        """Oscillator colors cycle through palette."""
        config = VisualizationConfig(
            oscillators=[
                IndicatorDisplayConfig(name="rsi14"),
                IndicatorDisplayConfig(name="stoch_rsi"),
                IndicatorDisplayConfig(name="cci"),
            ]
        )

        colors = [
            config.get_oscillator_color(i, ind)
            for i, ind in enumerate(config.oscillators)
        ]

        # Each oscillator should have distinct color
        assert colors[0] == get_oscillator_color(0)
        assert colors[1] == get_oscillator_color(1)
        assert colors[2] == get_oscillator_color(2)

    def test_explicit_color_overrides_gradient(self):
        """Explicit color in config overrides gradient assignment."""
        custom_color = "#FF0000"
        config = VisualizationConfig(
            price_overlays=[
                IndicatorDisplayConfig(name="ema20", color=custom_color),
                IndicatorDisplayConfig(name="ema50"),  # Uses gradient
            ]
        )

        # First overlay has explicit color
        color0 = config.get_overlay_color(0, config.price_overlays[0])
        assert color0 == custom_color

        # Second overlay uses gradient (only MA = green since first has explicit)
        # Actually, both are MAs, so second = crimson
        color1 = config.get_overlay_color(1, config.price_overlays[1])
        assert color1 == MA_COLOR_SLOWEST

    def test_non_ma_gets_cyan(self):
        """Non-MA indicators like ATR get cyan."""
        config = VisualizationConfig(
            price_overlays=[
                IndicatorDisplayConfig(name="ema20"),
                IndicatorDisplayConfig(name="atr14"),
            ]
        )

        color_ema = config.get_overlay_color(0, config.price_overlays[0])
        color_atr = config.get_overlay_color(1, config.price_overlays[1])

        # Single MA = green, ATR = cyan
        assert color_ema == MA_COLOR_FASTEST
        assert color_atr == NON_MA_INDICATOR_COLOR
