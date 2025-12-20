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
poetry run backtest --pair EURUSD --visualize
```

## Features

- **Zoom/Pan**: Use mouse wheel and drag to navigate.
- **Trade Markers**: Triangles indicate Buy (Up) and Sell (Down) entries.
- **Indicators**: Moving averages and other indicators from the strategy are overlayed.
- **Performance**: Capable of handling millions of data points smoothly.

## Troubleshooting

- **No Window**: Ensure you are running in a GUI environment (desktop). WSL requires X server configuration.
- **Slow Load**: For extreme datasets (>10 years), the initial load might take a few seconds.
