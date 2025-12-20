# Implementation Plan: Interactive Visualization

**Branch**: `014-interactive-viz` | **Date**: 2025-12-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/014-interactive-viz/spec.md`

## Summary

Implement an interactive visualization system using `lightweight-charts-python` to display backtest results. This includes a new CLI flag `--visualize` that opens a high-performance candlestick chart with overlaid indicators and trade markers (buy/sell).

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: `lightweight-charts`, `polars` (data), `pandas` (view compatibility)
**Storage**: N/A (Transient visualization)
**Testing**: `pytest` with mocking of GUI components
**Target Platform**: Local Execution (Windows/Linux with GUI support)
**Performance Goals**: < 5s load time for 1 year of 1-minute data (~370k rows)
**Constraints**: Requires local GUI environment (desktop)

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

- [x] **Principle I (Strategy-First)**: Visualization is decoupled from strategy logic; strategy emits signals/indicators, visualizer consumes them.
- [x] **Principle IV (Observability)**: Enhances observability by providing visual feedback of backtest execution.
- [x] **Principle VI (Data Provenance)**: Visualizes the data actually used in the backtest (verified via `enriched_df`).
- [x] **Principle XII (Task Tracking)**: Tasks are clearly defined in `task.md`.

## Project Structure

### Documentation (this feature)

```text
specs/014-interactive-viz/
├── plan.md              # This file
├── research.md          # Technology selection rationale
├── data-model.md        # Data flow definition
├── quickstart.md        # User guide
├── contracts/           # API interface definitions
└── tasks.md             # Task tracking
```

### Source Code (repository root)

```text
src/
├── visualization/       # [NEW] Visualization module
│   ├── __init__.py
│   └── interactive.py   # [NEW] Plotting logic
├── cli/
│   └── run_backtest.py  # [MODIFY] Add --visualize argument
└── pyproject.toml       # [MODIFY] Add lightweight-charts dependency
```

## Proposed Changes

### Configuration

#### [MODIFY] [pyproject.toml](file:///E:/GitHub/trading-strategies/pyproject.toml)

- Add `lightweight-charts = "^2.0.0"` to dependencies.

### Visualization Module

#### [NEW] [src/visualization/interactive.py](file:///E:/GitHub/trading-strategies/src/visualization/interactive.py)

- Implement `plot_backtest_results(data, result, pair, ...)`
- Logic:
  - Convert `polars` dataframe to `pandas` (required by library).
  - Initialize `Chart` object.
  - Add Candlestick series (Open, High, Low, Close, Time).
  - Add Line series for each indicator present in `data`.
  - Iterating through `result.executions` to add up/down markers for trades.
  - Call `chart.show(block=True)`.

### CLI Integration

#### [MODIFY] [src/cli/run_backtest.py](file:///E:/GitHub/trading-strategies/src/cli/run_backtest.py)

- Add `--visualize` boolean flag to `argparse`.
- In `main()`:
  - If `--visualize` is set:
    - Import `plot_backtest_results`.
    - After backtest completes, call `plot_backtest_results` with `enriched_df` and `result`.
  - Handle `is_multi_symbol_result`: Warn or visualize only the first symbol if multiple are present (MVP scope).

## Verification Plan

### Automated Tests

- `tests/visualization/test_interactive.py`
  - **Test**: `test_plot_backtest_results_calls`
  - **Method**: Mock `lightweight_charts.Chart`. Call `plot_backtest_results` with dummy `BacktestResult` and `DataFrame`. Verify `chart.set`, `chart.marker`, and `chart.show` are called with correct data.

### Manual Verification

- **Command**: `poetry run backtest --pair EURUSD --visualize --dry-run`
- **Verification**:
  1. A window opens showing the chart.
  2. Candlesticks are visible.
  3. Indicators (EMA, etc.) are overlaid.
  4. Trade markers (triangles) appear at appropriate times (if not dry-run, or mock a result with trades).
  5. Zoom and Pan work smoothly.
