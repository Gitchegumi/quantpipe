# Feature Specification: Multi-Symbol Backtest Visualization

**Feature Branch**: `016-multi-symbol-viz`
**Created**: 2025-12-21
**Status**: Draft
**Input**: Issue #42 - Add visualization support for multi-symbol backtests

## Clarifications

### Session 2025-12-21

- Q: What is the maximum symbol limit for visualization? → A: Show warning at 5+ symbols but render anyway (no hard limit)

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Visualize Multi-Symbol Backtest Results (Priority: P1)

As a trader running backtests across multiple currency pairs (e.g., EURUSD and USDJPY), I want to see interactive visualizations for each symbol when I pass the `--visualize` flag so that I can analyze price action and trade entries/exits for each instrument.

**Why this priority**: This is the core functionality requested in the issue. Currently, multi-symbol visualization is explicitly disabled with the message "Visualization skipped for multi-symbol result (not yet supported)." Enabling this delivers immediate value.

**Independent Test**: Can be fully tested by running `poetry run python -m src.cli.run_backtest --pair EURUSD USDJPY --direction BOTH --visualize` and verifying that an interactive HTML chart opens with separate price panels for each symbol.

**Acceptance Scenarios**:

1. **Given** a multi-symbol backtest with EURUSD and USDJPY, **When** I pass `--visualize`, **Then** an interactive chart opens with separate price panels for each symbol
2. **Given** a multi-symbol backtest with 3+ symbols, **When** I pass `--visualize`, **Then** all symbols are rendered in a stacked vertical layout (one panel per symbol)
3. **Given** a multi-symbol backtest with one failing symbol, **When** I pass `--visualize`, **Then** only successful symbols are visualized and a warning is logged for the failed symbol

---

### User Story 2 - View Trade Markers Per Symbol (Priority: P1)

As a trader, I want to see entry/exit markers, TP/SL lines, and trade connections displayed correctly on each symbol's price chart so I can visually validate my strategy's entries and exits.

**Why this priority**: Trade markers are essential for understanding strategy behavior. Without them, the visualization has limited value.

**Independent Test**: Can be tested by running a multi-symbol backtest with `--visualize` and verifying that each symbol's chart displays green/red entry triangles, win/loss exit diamonds, and gray dashed connecting lines.

**Acceptance Scenarios**:

1. **Given** a multi-symbol backtest with trades on EURUSD, **When** I view the visualization, **Then** EURUSD's panel shows entry markers (triangles) and exit markers (diamonds) with correct colors
2. **Given** trades with TP/SL levels, **When** I view the visualization, **Then** TP lines (green dotted) and SL lines (red dotted) are drawn on the correct symbol's chart
3. **Given** trades on different symbols, **When** I view the visualization, **Then** trade markers appear only on their respective symbol's chart (no cross-contamination)

---

### User Story 3 - Aggregated Portfolio Equity Curve (Priority: P2)

As a trader, I want to see an aggregated portfolio equity curve at the bottom of the visualization that shows the combined performance across all symbols over time.

**Why this priority**: The portfolio equity curve provides a holistic view of strategy performance but builds upon the per-symbol charts. It's valuable but not strictly required for the MVP.

**Independent Test**: Run a multi-symbol backtest with `--visualize` and verify a portfolio value curve is displayed below all symbol charts, showing cumulative dollar performance.

**Acceptance Scenarios**:

1. **Given** a multi-symbol backtest with trades on multiple pairs, **When** I view the visualization, **Then** a portfolio equity curve is displayed below all price charts
2. **Given** trades closed at different times across symbols, **When** I view the portfolio curve, **Then** the curve reflects the chronological sequence of all trade closes
3. **Given** initial balance of $2,500 and risk per trade of $6.25, **When** I view the portfolio curve, **Then** the Y-axis shows dollar values starting at $2,500

---

### User Story 4 - Correct Timeframe Display (Priority: P2)

As a trader running multi-timeframe backtests, I want the chart title to display the correct timeframe for each symbol so I can distinguish between different analysis periods.

**Why this priority**: Timeframe context is important for interpretation but doesn't block the core visualization functionality.

**Independent Test**: Run `poetry run python -m src.cli.run_backtest --pair EURUSD USDJPY --timeframe 15m --visualize` and verify chart titles show the timeframe.

**Acceptance Scenarios**:

1. **Given** a 15-minute timeframe backtest, **When** I view the visualization, **Then** the title includes "(15m)" (e.g., "Multi-Symbol Backtest (15m)")
2. **Given** a 1-minute timeframe backtest (default), **When** I view the visualization, **Then** the title uses the simpler form without timeframe suffix

---

### User Story 5 - Synchronized Navigation and Crosshair (Priority: P2)

As a trader analyzing multi-symbol charts, I want all price charts to stay synchronized when I pan or zoom, and I want a crosshair that helps me compare price levels across symbols at the same point in time.

**Why this priority**: Synchronized navigation is essential for comparing correlated pairs, but the core visualization must work first.

**Independent Test**: Open a multi-symbol visualization, pan/zoom on one chart, and verify all price charts move together. Hover over a price chart and verify the vertical crosshair line extends across all price/oscillator panels.

**Acceptance Scenarios**:

1. **Given** a multi-symbol visualization with 2+ symbols, **When** I pan horizontally on one price chart, **Then** all price charts pan together (shared x-axis)
2. **Given** a multi-symbol visualization, **When** I zoom on one price chart, **Then** all price charts zoom together
3. **Given** my mouse hovering over a price chart, **When** I move the cursor, **Then** a vertical crosshair line extends across all price and oscillator panels (y-axis synchronized)
4. **Given** my mouse hovering over the PnL/portfolio equity panel, **When** I move the cursor, **Then** the crosshair only appears on the PnL panel (does not extend to price panels)

---

### Edge Cases

- What happens when one symbol has no data in the filtered date range? The system should log a warning and skip that symbol's chart.
- What happens when no symbols have trades? The system should display price charts without trade markers and log an informational message.
- What happens when the data lacks a "symbol" column for filtering? Each symbol should use the unfiltered data (fallback behavior for single-symbol data sources).
- What happens with very large datasets (500k+ candles per symbol)? The system should apply the existing 500k candle limit per symbol to maintain performance.
- What happens when 5 or more symbols are visualized? The system logs a warning about potential layout/performance concerns but renders all symbols anyway.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST generate visualization when `--visualize` is passed with multi-symbol backtests (no longer skip with "not yet supported" message)
- **FR-002**: System MUST render one price chart panel per symbol in a vertical stacked layout
- **FR-003**: System MUST correctly filter OHLC data by symbol column for each chart panel
- **FR-004**: System MUST display trade entry/exit markers only on the corresponding symbol's chart
- **FR-005**: System MUST include TP/SL level lines (green/red dotted) for trades on each symbol's chart
- **FR-006**: System MUST generate an aggregated portfolio equity curve from all symbols' trades
- **FR-007**: System MUST display correct timeframe in chart title when not using default 1-minute timeframe
- **FR-008**: System MUST handle tuple unpacking correctly when calling helper functions that return multiple values
- **FR-009**: System MUST save HTML output to `results/dashboards/` when visualization is generated
- **FR-010**: System MUST apply x-axis linking (shared_axes) between symbol charts for synchronized panning/zoom
- **FR-011**: System MUST synchronize pan and zoom actions across all price chart panels (shared x-axis)
- **FR-012**: System MUST display a vertical crosshair that extends across all price and oscillator panels when hovering over any price chart
- **FR-013**: System MUST display a crosshair on the PnL panel that does NOT extend to other panels when hovering over the PnL panel
- **FR-014**: System MUST use linked crosshairs for price-related panels but isolated crosshair for the portfolio equity panel
- **FR-015**: System MUST log a warning when visualizing 5 or more symbols (noting potential layout/performance concerns) but render all symbols anyway

### Key Entities

- **BacktestResult**: Contains multi-symbol results via `is_multi_symbol` flag and `results` dict mapping symbol names to individual `BacktestResult` objects
- **Trade Execution**: Represents a single trade with entry/exit timestamps, prices, direction, and PnL
- **Symbol Data**: OHLC price data filtered by symbol for each chart panel

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Users can see multi-symbol visualizations where previously they received "not yet supported" - 100% of multi-symbol `--visualize` runs produce a chart
- **SC-002**: All symbols with valid data produce a chart panel - 0 false skips for symbols with data
- **SC-003**: Trade markers display on correct symbol charts - 0 cross-contamination between symbols
- **SC-004**: Portfolio equity curve accurately reflects cumulative performance - final value matches sum of individual trade PnLs
- **SC-005**: Visualization renders within 30 seconds for typical multi-symbol backtests (2-3 symbols, 100k candles each)

## Assumptions

- The `_create_multi_symbol_layout()` function already exists and provides the foundation for this feature
- The visualization uses the existing HoloViews + Datashader stack
- Data passed to multi-symbol visualization will have a "symbol" column when multiple symbols are present
- The existing single-symbol visualization patterns (trade boxes, indicator overlays) can be reused per-symbol
