# Quickstart: Dynamic Visualization Indicators

**Feature**: 017-dynamic-viz-indicators
**Date**: 2025-12-21

## Overview

This feature allows trading strategies to define their own visualization configuration instead of relying on hardcoded indicator patterns in the visualization module.

## Basic Usage

### Strategy with Custom Visualization

```python
from src.strategy.base import Strategy, StrategyMetadata
from src.models.visualization_config import VisualizationConfig, IndicatorDisplayConfig


class MyCustomStrategy(Strategy):
    """Example strategy with visualization configuration."""

    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="my-custom",
            version="1.0.0",
            required_indicators=["ema20", "ema50", "rsi14"],
            tags=["custom"],
        )

    def get_visualization_config(self) -> VisualizationConfig:
        """Define how this strategy's indicators should be visualized."""
        return VisualizationConfig(
            price_overlays=[
                IndicatorDisplayConfig(name="ema20", color="#FFD700", label="Fast EMA"),
                IndicatorDisplayConfig(name="ema50", color="#00CED1", label="Slow EMA"),
            ],
            oscillators=[
                IndicatorDisplayConfig(name="rsi14", color="#FFFF00", label="RSI(14)"),
            ],
        )

    def generate_signals(self, candles, parameters, direction="BOTH"):
        # ... signal generation logic
        pass
```

### Strategy without Visualization Config (Backward Compatible)

Existing strategies that don't implement `get_visualization_config()` continue to work unchanged. The visualization module will auto-detect indicators based on column name patterns (ema, sma, rsi, stoch, etc.).

```python
class LegacyStrategy(Strategy):
    """Legacy strategy - visualization auto-detects indicators."""

    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="legacy",
            version="1.0.0",
            required_indicators=["ema20", "rsi14"],
        )

    # No get_visualization_config() - uses auto-detection

    def generate_signals(self, candles, parameters, direction="BOTH"):
        pass
```

## Running a Backtest with Visualization

```bash
# Standard backtest command - visualization automatically uses strategy config
python -m src.cli.run_backtest \
    --strategy trend-pullback \
    --csv data/EURUSD_1m.csv \
    --direction LONG \
    --visualize

# The visualization will:
# 1. Check if strategy implements get_visualization_config()
# 2. If yes: use configured indicators and colors
# 3. If no: fall back to auto-detection (backward compatible)
```

## Configuration Options

### IndicatorDisplayConfig Fields

| Field   | Type | Default     | Description                         |
| ------- | ---- | ----------- | ----------------------------------- |
| `name`  | str  | (required)  | Column name in DataFrame            |
| `color` | str  | `"#FFFFFF"` | CSS color for indicator line        |
| `label` | str  | `None`      | Legend label (uses name if not set) |

### VisualizationConfig Fields

| Field            | Type | Default | Description                    |
| ---------------- | ---- | ------- | ------------------------------ |
| `price_overlays` | list | `[]`    | Indicators on price chart      |
| `oscillators`    | list | `[]`    | Indicators in oscillator panel |

## Troubleshooting

### Indicator Not Appearing

1. Check that the indicator column exists in your enriched data
2. Verify the `name` field matches the exact column name (case-sensitive)
3. Check logs for warning messages about missing columns

### Color Not Visible

1. Ensure color has sufficient contrast against dark background
2. Use hex colors (`#FFD700`) for consistent behavior
3. Avoid very dark colors that blend with the chart background

### Auto-Detection Still Running

If you implement `get_visualization_config()` but auto-detection still runs:

1. Ensure the method returns a `VisualizationConfig` instance, not `None`
2. Verify the method is defined correctly on your strategy class
