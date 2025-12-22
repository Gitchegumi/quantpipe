# Research: Multi-Symbol Backtest Visualization

**Feature**: 016-multi-symbol-viz  
**Date**: 2025-12-21

## Summary

This feature enables multi-symbol visualization for backtests. Research focused on understanding existing code gaps and HoloViews/Bokeh patterns for linked crosshairs.

## Findings

### Decision 1: Fix Existing `_create_multi_symbol_layout()` vs. Rewrite

**Decision**: Fix existing function

**Rationale**: The function already exists in `src/visualization/datashader_viz.py` (lines 192-255) and handles the core loop. Only specific bugs need fixing:

1. `shared_axes=False` should be `True` for price panels (line 251)
2. Tuple unpacking error on line 221: `_create_candlestick_chart()` returns `(chart, xlim)` but only `price_chart` is captured
3. `_create_indicator_overlays()` call on line 223 passes only 1 arg but function requires 3

**Alternatives Considered**:

- Full rewrite: Rejected - too much duplication of working code

### Decision 2: Linked Crosshair Implementation

**Decision**: Use Bokeh `CrosshairTool` via HoloViews `.opts(hooks=...)` pattern

**Rationale**: Research confirms HoloViews supports linked crosshairs by:

1. Creating a shared `CrosshairTool` instance from `bokeh.models`
2. Defining a hook function that adds the tool to each plot
3. Applying hook via `.opts(hooks=[hook_fn])`

For isolated PnL panel crosshair, create a separate `CrosshairTool` instance.

**Alternatives Considered**:

- HoloViews Streams: Rejected - causes lag with large datasets
- Custom JavaScript: Rejected - more complex, harder to maintain

### Decision 3: CLI Integration Point

**Decision**: Remove the blocking condition in `run_backtest.py` lines 1287-1290

**Rationale**: The check `if result.is_multi_symbol:` logs warning and skips visualization. Remove this block and call `plot_backtest_results()` which already dispatches to `_create_multi_symbol_layout()`.

**Alternatives Considered**:

- Add separate multi-symbol visualization command: Rejected - unnecessary complexity

## Technical Notes

- `shared_axes=True` in HoloViews Layout links x-axis pan/zoom across all panels
- `CrosshairTool(dimensions="both")` creates vertical+horizontal hair
- For vertical-only crosshair, use `dimensions="height"`
- Trade markers already work per-symbol via existing `_create_trade_boxes()` function
