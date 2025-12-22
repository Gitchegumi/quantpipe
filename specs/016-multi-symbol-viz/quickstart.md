# Quickstart: Multi-Symbol Backtest Visualization

## Overview

This feature enables visualization of multi-symbol backtest results with synchronized charts and linked crosshairs.

## Usage

### Basic Multi-Symbol Visualization

```bash
poetry run python -m src.cli.run_backtest --pair EURUSD USDJPY --direction BOTH --visualize
```

### With Timeframe

```bash
poetry run python -m src.cli.run_backtest --pair EURUSD USDJPY --timeframe 15m --direction BOTH --visualize
```

### Date Range Filter

```bash
poetry run python -m src.cli.run_backtest --pair EURUSD USDJPY --visualize --viz-start 2024-01-01 --viz-end 2024-03-31
```

## Expected Output

1. **Price Panels**: One stacked chart per symbol with OHLC candlesticks
2. **Trade Markers**: Entry triangles (green/red) and exit diamonds (cyan/orange) per symbol
3. **TP/SL Lines**: Dotted lines showing take-profit (green) and stop-loss (red) levels
4. **Portfolio Curve**: Aggregated equity curve at bottom showing cumulative performance
5. **Synchronized Navigation**: Pan/zoom on any chart syncs all price panels
6. **Linked Crosshair**: Vertical crosshair extends across all price panels when hovering

## Files Modified

- `src/cli/run_backtest.py` - Enable multi-symbol visualization
- `src/visualization/datashader_viz.py` - Fix bugs, add crosshairs

## Related

- [Specification](file:///e:/GitHub/trading-strategies/specs/016-multi-symbol-viz/spec.md)
- [Implementation Plan](file:///e:/GitHub/trading-strategies/specs/016-multi-symbol-viz/plan.md)
