"""Unit tests for visualization configuration models.

Tests for IndicatorDisplayConfig and VisualizationConfig dataclasses
from src/models/visualization_config.py.
"""

import pytest

from src.models.visualization_config import (
    IndicatorDisplayConfig,
    VisualizationConfig,
    MA_COLOR_FASTEST,
    MA_COLOR_SLOWEST,
    NON_MA_INDICATOR_COLOR,
    OSCILLATOR_COLOR_PALETTE,
    DEFAULT_FALLBACK_COLOR,
    get_ma_color,
    get_oscillator_color,
)


class TestIndicatorDisplayConfig:
    """Tests for IndicatorDisplayConfig dataclass."""

    def test_creation_with_name_only(self):
        """Config with only name uses defaults."""
        config = IndicatorDisplayConfig(name="ema20")
        assert config.name == "ema20"
        assert config.color is None  # Auto-assign from palette
        assert config.label is None

    def test_creation_with_all_fields(self):
        """Config with all fields set."""
        config = IndicatorDisplayConfig(name="ema50", color="#FFD700", label="Slow EMA")
        assert config.name == "ema50"
        assert config.color == "#FFD700"
        assert config.label == "Slow EMA"

    def test_get_label_returns_name_when_no_label(self):
        """get_label() falls back to name."""
        config = IndicatorDisplayConfig(name="rsi14")
        assert config.get_label() == "rsi14"

    def test_get_label_returns_custom_label(self):
        """get_label() returns custom label when set."""
        config = IndicatorDisplayConfig(name="rsi14", label="RSI (14)")
        assert config.get_label() == "RSI (14)"

    def test_get_color_or_default_with_color(self):
        """get_color_or_default returns configured color."""
        config = IndicatorDisplayConfig(name="ema20", color="#00FF00")
        assert config.get_color_or_default() == "#00FF00"

    def test_get_color_or_default_without_color(self):
        """get_color_or_default returns fallback when no color set."""
        config = IndicatorDisplayConfig(name="ema20")
        assert config.get_color_or_default() == DEFAULT_FALLBACK_COLOR
        assert config.get_color_or_default("#123456") == "#123456"

    def test_frozen_immutable(self):
        """Config is immutable (frozen dataclass)."""
        config = IndicatorDisplayConfig(name="ema20")
        with pytest.raises(AttributeError):
            config.name = "ema50"  # type: ignore

    def test_is_moving_average_auto_detect(self):
        """is_moving_average auto-detects from name."""
        assert IndicatorDisplayConfig(name="ema20").is_moving_average() is True
        assert IndicatorDisplayConfig(name="sma50").is_moving_average() is True
        assert IndicatorDisplayConfig(name="wma100").is_moving_average() is True
        assert IndicatorDisplayConfig(name="atr14").is_moving_average() is False
        assert IndicatorDisplayConfig(name="rsi14").is_moving_average() is False

    def test_is_moving_average_explicit(self):
        """is_moving_average respects explicit is_ma setting."""
        # Explicit True overrides auto-detection
        config = IndicatorDisplayConfig(name="custom_avg", is_ma=True)
        assert config.is_moving_average() is True

        # Explicit False overrides auto-detection
        config = IndicatorDisplayConfig(name="ema20", is_ma=False)
        assert config.is_moving_average() is False


class TestVisualizationConfig:
    """Tests for VisualizationConfig dataclass."""

    def test_empty_config(self):
        """Empty config has no overlays or oscillators."""
        config = VisualizationConfig()
        assert config.price_overlays == []
        assert config.oscillators == []
        assert config.is_empty() is True

    def test_config_with_overlays(self):
        """Config with price overlays only."""
        overlays = [
            IndicatorDisplayConfig(name="ema20"),
            IndicatorDisplayConfig(name="ema50"),
        ]
        config = VisualizationConfig(price_overlays=overlays)
        assert len(config.price_overlays) == 2
        assert config.oscillators == []
        assert config.is_empty() is False

    def test_config_with_oscillators(self):
        """Config with oscillators only."""
        oscillators = [
            IndicatorDisplayConfig(name="rsi14"),
            IndicatorDisplayConfig(name="stoch_rsi"),
        ]
        config = VisualizationConfig(oscillators=oscillators)
        assert config.price_overlays == []
        assert len(config.oscillators) == 2
        assert config.is_empty() is False

    def test_config_with_both(self):
        """Config with both overlays and oscillators."""
        config = VisualizationConfig(
            price_overlays=[IndicatorDisplayConfig(name="ema20")],
            oscillators=[IndicatorDisplayConfig(name="stoch_rsi")],
        )
        assert len(config.price_overlays) == 1
        assert len(config.oscillators) == 1

    def test_single_ma_gets_green(self):
        """Single MA gets bright green."""
        config = VisualizationConfig(
            price_overlays=[IndicatorDisplayConfig(name="ema20")]
        )
        color = config.get_overlay_color(0, config.price_overlays[0])
        assert color == MA_COLOR_FASTEST

    def test_two_mas_get_green_and_crimson(self):
        """Two MAs get green (first) and crimson (last)."""
        config = VisualizationConfig(
            price_overlays=[
                IndicatorDisplayConfig(name="ema20"),
                IndicatorDisplayConfig(name="ema50"),
            ]
        )
        color0 = config.get_overlay_color(0, config.price_overlays[0])
        color1 = config.get_overlay_color(1, config.price_overlays[1])
        assert color0 == MA_COLOR_FASTEST  # Green
        assert color1 == MA_COLOR_SLOWEST  # Crimson

    def test_three_mas_get_gradient(self):
        """Three MAs get green, middle, crimson."""
        config = VisualizationConfig(
            price_overlays=[
                IndicatorDisplayConfig(name="ema8"),
                IndicatorDisplayConfig(name="ema21"),
                IndicatorDisplayConfig(name="ema50"),
            ]
        )
        color0 = config.get_overlay_color(0, config.price_overlays[0])
        color1 = config.get_overlay_color(1, config.price_overlays[1])
        color2 = config.get_overlay_color(2, config.price_overlays[2])

        assert color0 == MA_COLOR_FASTEST  # Green
        assert color2 == MA_COLOR_SLOWEST  # Crimson
        # Middle color should be different from both
        assert color1 != color0
        assert color1 != color2

    def test_non_ma_indicator_gets_cyan(self):
        """Non-MA price indicators (ATR, Bollinger) get cyan."""
        config = VisualizationConfig(
            price_overlays=[
                IndicatorDisplayConfig(name="atr14"),
                IndicatorDisplayConfig(name="bollinger_upper"),
            ]
        )
        color0 = config.get_overlay_color(0, config.price_overlays[0])
        color1 = config.get_overlay_color(1, config.price_overlays[1])
        assert color0 == NON_MA_INDICATOR_COLOR
        assert color1 == NON_MA_INDICATOR_COLOR

    def test_mixed_ma_and_non_ma(self):
        """MAs and non-MAs get correct colors when mixed."""
        config = VisualizationConfig(
            price_overlays=[
                IndicatorDisplayConfig(name="ema20"),
                IndicatorDisplayConfig(name="atr14"),  # Non-MA
                IndicatorDisplayConfig(name="ema50"),
            ]
        )
        # ema20 and ema50 are MAs (2 total), should be green and crimson
        color_ema20 = config.get_overlay_color(0, config.price_overlays[0])
        color_atr = config.get_overlay_color(1, config.price_overlays[1])
        color_ema50 = config.get_overlay_color(2, config.price_overlays[2])

        assert color_ema20 == MA_COLOR_FASTEST  # First MA = green
        assert color_atr == NON_MA_INDICATOR_COLOR  # Non-MA = cyan
        assert color_ema50 == MA_COLOR_SLOWEST  # Last MA = crimson

    def test_get_overlay_color_respects_explicit_color(self):
        """Explicit color overrides auto-assignment."""
        indicator = IndicatorDisplayConfig(name="ema20", color="#CUSTOM")
        config = VisualizationConfig(price_overlays=[indicator])
        assert config.get_overlay_color(0, indicator) == "#CUSTOM"

    def test_get_oscillator_color_uses_palette(self):
        """Oscillator colors use distinct palette."""
        config = VisualizationConfig(
            oscillators=[
                IndicatorDisplayConfig(name="rsi14"),
                IndicatorDisplayConfig(name="stoch_rsi"),
            ]
        )
        assert (
            config.get_oscillator_color(0, config.oscillators[0])
            == OSCILLATOR_COLOR_PALETTE[0]
        )
        assert (
            config.get_oscillator_color(1, config.oscillators[1])
            == OSCILLATOR_COLOR_PALETTE[1]
        )

    def test_get_oscillator_color_cycles(self):
        """Oscillator palette cycles when exhausted."""
        # More oscillators than palette colors
        many_oscillators = [
            IndicatorDisplayConfig(name=f"osc{i}")
            for i in range(len(OSCILLATOR_COLOR_PALETTE) + 2)
        ]
        config = VisualizationConfig(oscillators=many_oscillators)
        # After palette exhausted, should cycle
        last_idx = len(OSCILLATOR_COLOR_PALETTE)
        assert (
            config.get_oscillator_color(last_idx, many_oscillators[last_idx])
            == OSCILLATOR_COLOR_PALETTE[0]
        )


class TestColorPaletteFunctions:
    """Tests for color palette helper functions."""

    def test_get_ma_color_single(self):
        """Single MA returns bright green."""
        assert get_ma_color(0, 1) == MA_COLOR_FASTEST

    def test_get_ma_color_two(self):
        """Two MAs return green and crimson."""
        assert get_ma_color(0, 2) == MA_COLOR_FASTEST
        assert get_ma_color(1, 2) == MA_COLOR_SLOWEST

    def test_get_ma_color_three_plus(self):
        """Three+ MAs return green, middle, crimson."""
        # First is always green
        assert get_ma_color(0, 3) == MA_COLOR_FASTEST
        # Last is always crimson
        assert get_ma_color(2, 3) == MA_COLOR_SLOWEST
        # Middle is something else
        middle = get_ma_color(1, 3)
        assert middle != MA_COLOR_FASTEST
        assert middle != MA_COLOR_SLOWEST

    def test_get_ma_color_edge_cases(self):
        """Edge cases for get_ma_color."""
        # Zero or negative count returns green
        assert get_ma_color(0, 0) == MA_COLOR_FASTEST
        assert get_ma_color(0, -1) == MA_COLOR_FASTEST

    def test_get_oscillator_color_valid_indices(self):
        """Oscillator palette returns correct colors."""
        assert get_oscillator_color(0) == OSCILLATOR_COLOR_PALETTE[0]
        assert get_oscillator_color(1) == OSCILLATOR_COLOR_PALETTE[1]

    def test_get_oscillator_color_cycles(self):
        """Oscillator palette cycles when index exceeds length."""
        palette_len = len(OSCILLATOR_COLOR_PALETTE)
        assert get_oscillator_color(palette_len) == OSCILLATOR_COLOR_PALETTE[0]
        assert get_oscillator_color(palette_len + 1) == OSCILLATOR_COLOR_PALETTE[1]

    def test_palette_colors_are_valid_hex(self):
        """All palette colors are valid hex format."""
        import re

        hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
        assert hex_pattern.match(MA_COLOR_FASTEST)
        assert hex_pattern.match(MA_COLOR_SLOWEST)
        assert hex_pattern.match(NON_MA_INDICATOR_COLOR)
        for color in OSCILLATOR_COLOR_PALETTE:
            assert hex_pattern.match(color), f"Invalid hex color: {color}"
