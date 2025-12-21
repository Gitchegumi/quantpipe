# Walkthrough: Interactive Visualization (Feature 014)

## Overview

Successfully implemented an interactive backtest visualization feature using `lightweight-charts-python`. This allows users to inspect candle data, indicators, and trade markers in a high-performance GUI window throughout the entire backtest history.

## Changes

### 1. Visualization Module (`src/visualization/interactive.py`)

- Created a dedicated module for rendering charts.
- Implemented `plot_backtest_results` which:
  - Converts Polars data to Pandas OHLC format.
  - Adds indicator lines dynamically.
  - Overlays trade markers (Buy/Sell arrows).
  - Configures "magnet" crosshair and optimized zoom/pan interactions.

### 3. CLI Integration

- [x] Added `--visualize` flag.
- [x] **New Feature**: Added `--viz-start` and `--viz-end` for precise time window inspection (replaces truncation).
- [x] **Bug Fix**: Resolved indentation issue in `run_backtest.py`.
- [x] **Bug Fix**: Fixed `TradeExecution` parsing and marker synchronization.
- [x] **Improvement**: Added `rich` spinner. to prevent performance impact on headless runs.

### 3. Documentation

- Updated `quickstart.md` with usage instructions and troubleshooting.

## Verification Results

### Automated Tests

- `tests/visualization/test_interactive.py` passed.
- Verifies that:
  - Data preparation handles missing columns/rows gracefully.
  - Methods on the `Chart` object are called with correct parameters.
  - Markers are generated correctly for Buy/Sell signals.

### Manual Verification

- **Command**: `poetry run python -m src.cli.run_backtest --pair EURUSD --visualize --dry-run`
- **Observations**:
  - [x] Chart window launched successfully.
  - [x] Candles rendered correctly for EURUSD.
  - [x] Indicators (EMA) appeared as line series.
  - [x] Zooming and panning significantly smooth (better than Plotly).
  - [x] Crosshair magnet mode snapped to prices correctly.
  - [x] Legend toggle worked (FR-007).

## Next Steps

- Support for multi-symbol visualization (currently warns/skips).
- Adding more trade details to tooltips (currently just price/side).
