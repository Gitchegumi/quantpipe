# Research: Fix Portfolio Mode Visualization (Feature 019)

**Status**: Complete
**Date**: 2025-12-23

## Decisions & Rationale

### 1. Visualization Layout Strategy

**Decision**: Use `_create_multi_symbol_layout` logic by passing `is_multi_symbol=True` in the mapped result object.
**Rationale**: `datashader_viz.py` already contains verified logic for stacking price charts vertically (`hv.Layout.cols(1)`). Reusing this is safer and faster than creating a new specific "portfolio layout". The key is ensuring the CLI reconstructs the data into the format `_create_multi_symbol_layout` expects (dict of single-symbol results) rather than the flattened "Portfolio" entity it currently produces.

### 2. Execution Flow Fix

**Decision**: Explicitly `return 0` in `run_backtest.py` after portfolio block.
**Rationale**: The "fall-through" behavior is a simple control flow bug. No complex architecture change is needed.

### 3. Shared Capital Logic

**Decision**: Retain "Exit-Time Equity Update" logic in `PortfolioSimulator`.
**Rationale**: Switching to "Entry-Time" logic requires accurate point-in-time equity which is hard to vectorize without `polars.scan` or loops. Given the constraint "No per-candle looping", the current approximation (updating equity when trades close) is the accepted tradeoff for performance.

## Clarifications

All ambiguities resolved during `/speckit.clarify` session.
