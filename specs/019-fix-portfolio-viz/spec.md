# Feature Specification: Fix Portfolio Mode Visualizations

**Feature Branch**: `019-fix-portfolio-viz`
**Created**: 2025-12-23
**Status**: Draft
**Input**: User description: "I need to fix portfolio mode visualizations. Currently, it show a single price chart, but it should be showing seperate price charts for each symbol similar to how the isolated multi-symbol back test does it. All implementations should use Polars and vectorized scanning. There should be no per-candle looping, and the trade filtering must be maintained."

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Independent Symbol Charts (Priority: P1)

AS A trader analyzing a portfolio backtest
I WANT to see separate price charts for each symbol in the portfolio
SO THAT I can evaluate the performance and trade entry/exits for each asset individually without visual clutter/overlapping.

**Why this priority**: Essential for visual verification of backtest results. The current single-chart view is misleading/unusable for multi-symbol portfolios. Currently, the system incorrectly treats the portfolio as a single entity ("Portfolio") in the visualization.

**Independent Test**: Run a portfolio backtest with 2 distinct symbols (e.g., EURUSD and USDJPY). The output HTML must render two distinct chart areas, each with its own price series and trade markers.

**Acceptance Scenarios**:

1. **Given** a portfolio backtest with symbols [A, B], **When** the visualization is generated, **Then** the report displays two separate price charts stacked vertically.
2. **Given** a portfolio backtest where Symbol A has trades and Symbol B does not, **When** viewed, **Then** Symbol A's chart shows trade markers, and Symbol B's chart shows price history only.
3. **Given** the new visualization, **When** comparing to the existing "isolated multi-symbol" visualization, **Then** the layout structure (separate charts) appears similar.

---

### User Story 2 - Correct Execution Flow (Priority: P1)

AS A user running a portfolio backtest
I WANT the simulation to run exactly once and exit
SO THAT I don't waste time waiting for a second, redundant single-symbol simulation to run immediately after.

**Why this priority**: Critical bug fix. Currently, the CLI falls through from portfolio mode into single-symbol mode, causing double execution and confusing output (two visualizations).

**Independent Test**: Run `poetry run python -m src.cli.run_backtest --pair EURUSD USDJPY --portfolio-mode` and verify logs show only one "Starting... backtest" sequence and the process terminates after the portfolio report.

**Acceptance Scenarios**:

1. **Given** the CLI command for portfolio mode, **When** executed, **Then** it produces the portfolio result/visualization and exits 0.
2. **Given** the logs, **When** checked, **Then** there is no evidence of a subsequent single-symbol (EURUSD) backtest starting after the portfolio run.

---

### User Story 3 - Shared Capital Logic (Priority: P1)

AS A trader using portfolio mode
I WANT the simulation to treat symbols as independent trading opportunities that share a single capital account
SO THAT wins/losses in one symbol correctly affect the available margin/equity for subsequent trades in other symbols.

**Why this priority**: Core definition of portfolio backtesting. Treating them as a "single entity" (e.g. averaging prices) or fully isolated (separate capital) is incorrect.

**Independent Test**: Verify via log inspection or specific test case that a large loss in Symbol A reduces the position sizing capacity for a subsequent trade in Symbol B (assuming risk % sizing).

**Acceptance Scenarios**:

1. **Given** a portfolio run, **When** a trade closes on Symbol A, **Then** the shared equity balance is updated before the next potential trade on Symbol B.
2. **Given** the visualization, **When** inspected, **Then** the PnL curve reflects the aggregate equity of the shared account over time.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: The system MUST generate a separate Datashader/Bokeh plot for each unique symbol present in the portfolio backtest results.
- **FR-002**: The visualization data preparation pipeline MUST use Polars for all data manipulations (filtering, joining, formatting).
- **FR-003**: The system MUST NOT use Python-level loops to iterate over individual candles or rows during visualization preparation.
- **FR-004**: The visualization MUST accurately map trades to their respective symbol's chart based on the trade's symbol identifier.
- **FR-005**: The visualization MUST support the same interactive features (zoom, pan, crosshair) as the existing single-symbol view, synchronized across all charts.
- **FR-006**: The PnL (profit and loss) curve MUST represent the aggregate portfolio performance (shared equity).
- **FR-007**: The CLI execution flow MUST terminate immediately after completing the portfolio mode backtest/visualization, preventing any fall-through to single-symbol execution.

### Key Entities _(include if feature involves data)_

- **PortfolioVizData**: A structure holding the aligned price data for all symbols and the list of executed trades.
- **SymbolChart**: A visual component representing the price action and trades for a specific instrument.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Visualization generation time for a 3-symbol, 1-year minute-data backtest is under 5 seconds.
- **SC-002**: 100% of executed trades from the backtest results are visible on the correct symbol charts.
- **SC-003**: 0% of trades are displayed on the wrong symbol's chart.
- **SC-004**: The resulting HTML report renders correctly in a standard web browser without JavaScript errors.
