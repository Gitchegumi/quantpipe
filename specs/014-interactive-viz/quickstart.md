# Quickstart: Interactive Visualization

## Overview

The interactive visualization feature allows you to visually inspect backtest results using a high-performance candlestick chart.

## Prerequisities

Ensure `lightweight-charts` is installed:

```bash
poetry install
```

## Usage

Run a backtest with the `--visualize` flag:

```bash
poetry run python -m src.cli.run_backtest --pair EURUSD --visualize
```

For multi-symbol backtests, currently only the first symbol will be visualized, or you can use `--pair` to select a specific one.

## Features

- **Zoom/Pan**: Use mouse wheel and drag to navigate.
- **Crosshair**: Magnet mode enabled for precise OHL reading.
- **Layer Control**: Toggle indicators via the legend.
- **Trade Markers**: Blue (Buy) and Pink (Sell) arrows indicating entry points.
- **Performance**: High-frame rate rendering via TradingView engine.

## Troubleshooting

- **No Window**: Ensure you are running in a GUI environment (desktop). WSL requires X server configuration (e.g., VcXsrv).
- **Slow Load**: For extreme datasets (>10 years), the initial load might take a few seconds.
