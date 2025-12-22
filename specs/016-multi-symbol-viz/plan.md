# Implementation Plan: Multi-Symbol Backtest Visualization

**Branch**: `016-multi-symbol-viz` | **Date**: 2025-12-21 | **Spec**: [spec.md](file:///e:/GitHub/trading-strategies/specs/016-multi-symbol-viz/spec.md)

## Summary

Enable multi-symbol backtest visualization by fixing bugs in the existing `_create_multi_symbol_layout()` function, removing the CLI block that skips visualization for multi-symbol results, and adding linked crosshairs via Bokeh hooks.

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: HoloViews, hvplot, Panel, Bokeh (existing visualization stack)  
**Storage**: N/A (HTML output to `results/dashboards/`)  
**Testing**: pytest  
**Target Platform**: Windows/Linux desktop  
**Performance Goals**: Render within 30 seconds for 2-3 symbols × 100k candles each  
**Constraints**: Existing visualization patterns must be reused

## Constitution Check

| Gate                               | Status  | Notes                                |
| ---------------------------------- | ------- | ------------------------------------ |
| Strategy-First Architecture        | ✅ Pass | No strategy changes                  |
| Risk Management                    | ✅ Pass | Visualization only, no trading logic |
| Code Quality (PEP 257, type hints) | ✅ Pass | Will add docstrings to new functions |
| Dependency Management (Poetry)     | ✅ Pass | No new dependencies required         |
| Linting (Black, Ruff)              | ✅ Pass | Will format all changes              |
| Task Tracking                      | ✅ Pass | Will update tasks.md                 |

## Project Structure

### Documentation (this feature)

```text
specs/016-multi-symbol-viz/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── tasks.md             # Task tracking (to be generated)
└── checklists/          # Quality checklists
```

### Source Code (affected files)

```text
src/
├── cli/
│   └── run_backtest.py          # [MODIFY] Remove multi-symbol viz skip
└── visualization/
    └── datashader_viz.py        # [MODIFY] Fix bugs, add crosshairs

tests/
└── visualization/
    └── test_multi_symbol_viz.py # [NEW] Unit tests for multi-symbol layout
```

---

## Proposed Changes

### CLI Module

#### [MODIFY] [run_backtest.py](file:///e:/GitHub/trading-strategies/src/cli/run_backtest.py)

**Lines 1286-1320**: Remove the `if result.is_multi_symbol:` block that skips visualization and replace with call to `plot_backtest_results()` for multi-symbol results, passing all symbol data.

---

### Visualization Module

#### [MODIFY] [datashader_viz.py](file:///e:/GitHub/trading-strategies/src/visualization/datashader_viz.py)

**Bug Fixes**:

1. **Line 221**: Fix tuple unpacking - `_create_candlestick_chart()` returns `(chart, xlim)`

   ```python
   # Before
   price_chart = _create_candlestick_chart(pdf, symbol)
   # After
   price_chart, xlim = _create_candlestick_chart(pdf, symbol)
   ```

2. **Line 223**: Fix `_create_indicator_overlays()` call to pass required `pair` and `xlim` arguments

   ```python
   # Before
   indicators = _create_indicator_overlays(pdf)
   # After
   indicators, oscillator_panel = _create_indicator_overlays(pdf, symbol, xlim)
   ```

3. **Line 251**: Change `shared_axes=False` to `True` for synchronized pan/zoom

   ```python
   layout = layout.opts(title=title, shared_axes=True)
   ```

**New Feature - Linked Crosshairs (FR-012 to FR-014)**:

Add crosshair hooks using Bokeh `CrosshairTool`:

```python
from bokeh.models import CrosshairTool

def _create_linked_crosshair_hook(crosshair: CrosshairTool):
    """Hook to add shared crosshair to a plot."""
    def hook(plot, element):
        plot.state.add_tools(crosshair)
    return hook
```

Apply to price and oscillator panels for linked behavior, use separate instance for PnL panel.

**New Feature - Symbol Count Warning (FR-015)**:

Add warning log when `len(result.results) >= 5`.

---

### Tests

#### [NEW] [test_multi_symbol_viz.py](file:///e:/GitHub/trading-strategies/tests/visualization/test_multi_symbol_viz.py)

Unit tests for multi-symbol visualization:

1. `test_create_multi_symbol_layout_returns_layout()` - Verify function returns HoloViews Layout
2. `test_shared_axes_enabled()` - Verify `shared_axes=True` in output
3. `test_symbol_count_warning()` - Verify warning logged for 5+ symbols
4. `test_crosshair_tools_present()` - Verify CrosshairTool added to plots

---

## Verification Plan

### Automated Tests

```bash
# Run all visualization tests
poetry run pytest tests/visualization/ -v

# Run new multi-symbol tests specifically
poetry run pytest tests/visualization/test_multi_symbol_viz.py -v

# Run linting
poetry run ruff check src/visualization/datashader_viz.py src/cli/run_backtest.py
poetry run black src/visualization/datashader_viz.py src/cli/run_backtest.py --check
```

### Manual Verification

#### **Test 1: Basic Multi-Symbol Visualization**

1. Run: `poetry run python -m src.cli.run_backtest --pair EURUSD USDJPY --direction BOTH --visualize`
2. Verify: HTML chart opens with 2 stacked price panels (EURUSD on top, USDJPY below) + portfolio equity curve at bottom
3. Expected: No "not yet supported" warning, visualization renders successfully

#### **Test 2: Synchronized Pan/Zoom**

1. With the visualization from Test 1 open
2. Click and drag horizontally on the EURUSD chart to pan
3. Verify: USDJPY chart pans in sync (same time range visible)
4. Use scroll wheel to zoom on EURUSD
5. Verify: USDJPY zooms in sync

#### **Test 3: Linked Crosshair on Price Panels**

1. Hover mouse over EURUSD price chart
2. Verify: Vertical crosshair line appears on EURUSD chart AND extends to USDJPY chart and any oscillator panels
3. Move mouse horizontally
4. Verify: Crosshair moves in sync across all price-related panels

#### **Test 4: Isolated PnL Panel Crosshair**

1. Hover mouse over portfolio equity curve at bottom
2. Verify: Crosshair appears ONLY on PnL panel, does NOT extend to price charts above

#### **Test 5: 5+ Symbols Warning**

1. Run: `poetry run python -m src.cli.run_backtest --pair EURUSD USDJPY GBPUSD AUDUSD NZDUSD --direction BOTH --visualize`
2. Verify: Log contains warning about 5+ symbols but visualization still renders all 5.

---

## Complexity Tracking

No constitution violations requiring justification.
