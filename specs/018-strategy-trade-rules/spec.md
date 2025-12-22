# Feature Specification: Strategy Trade Rules & Indicator Exposure

**Feature Branch**: `018-strategy-trade-rules`
**Created**: 2025-12-22
**Status**: Draft
**Input**: Fix trend-pullback strategy to enforce one trade at a time and properly expose indicators for visualization (Issue #38)

## User Scenarios & Testing _(mandatory)_

### User Story 1 - One Trade at a Time Enforcement (Priority: P1)

As a trader running backtests, I need the strategy to allow only one open position per symbol at a time, so that my backtest results accurately reflect realistic trading behavior where a trader manages one position before opening another.

**Why this priority**: This is the core behavioral requirement. Without it, backtest results are unrealistic and misleading because they allow overlapping positions that a real trader wouldn't manage.

**Independent Test**: Can be fully tested by running a backtest with sample data and verifying that at any point in time, there is at most one open position per symbol.

**Acceptance Scenarios**:

1. **Given** a backtest in progress with an open long position, **When** a new long signal is generated, **Then** the new signal is skipped and no new position is opened.
2. **Given** a backtest in progress with an open position, **When** that position is closed (via SL, TP, or time exit), **Then** the next valid signal can open a new position.
3. **Given** a backtest starting with no open positions, **When** a valid signal occurs, **Then** a position is opened normally.

---

### User Story 2 - Indicator Visibility in Visualization (Priority: P2)

As a trader analyzing backtest results, I need to see all indicators used by the strategy (EMA20, EMA50, RSI14, ATR14, Stoch RSI) displayed on the visualization chart, so that I can understand why trades were entered and exited.

**Why this priority**: Visualization is essential for strategy debugging and validation. If indicators aren't visible, the trader cannot verify strategy logic visually.

**Independent Test**: Can be fully tested by running a visualization and verifying that all required indicators appear on the chart—EMAs as price overlays and RSI/StochRSI as oscillators.

**Acceptance Scenarios**:

1. **Given** a backtest visualization is rendered, **When** the strategy specifies `get_visualization_config()`, **Then** EMA20 and EMA50 appear as price overlays.
2. **Given** a backtest visualization is rendered, **When** the strategy specifies `get_visualization_config()`, **Then** RSI14 and Stoch RSI appear as oscillator panels.
3. **Given** the strategy metadata declares `required_indicators`, **When** the enrichment pipeline runs, **Then** all declared indicators are computed and available for visualization.

---

### User Story 3 - Indicator Consistency Audit (Priority: P3)

As a developer maintaining the strategy, I need the `required_indicators` list in metadata to match the indicators used in `scan_vectorized()` and exposed in `get_visualization_config()`, so that there are no hidden dependencies or missing visualizations.

**Why this priority**: Consistency between declared and actual usage prevents bugs and confusion during maintenance.

**Independent Test**: Can be tested by comparing the sets of indicators declared in metadata, used in code, and exposed in visualization config.

**Acceptance Scenarios**:

1. **Given** the strategy declares `required_indicators = ["ema20", "ema50", "atr14", "rsi14", "stoch_rsi"]`, **When** `scan_vectorized()` is analyzed, **Then** all used indicators are present in the required list.
2. **Given** the strategy declares required indicators, **When** `get_visualization_config()` is analyzed, **Then** all visualized indicators are present in the required list.

---

### Edge Cases

- What happens when signals occur on consecutive candles with position already open? The second signal should be skipped.
- What happens when a position exits and a new signal occurs on the same candle? The new signal should be allowed.
- What happens if ATR is required for stop calculation but not visualized? ATR can remain in `required_indicators` without being in visualization config (it's used for calculation, not display).

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST prevent opening a new position while an existing position for the same symbol is still open.
- **FR-002**: System MUST allow a new position to open immediately after the previous position is closed (same candle allowed if exit happens first).
- **FR-003**: Strategy MUST expose visualization configuration via `get_visualization_config()` that includes:
  - Price overlays: EMA20, EMA50
  - Oscillators: Stoch RSI, RSI14
- **FR-004**: Strategy `required_indicators` metadata MUST include all indicators used by the strategy: `["ema20", "ema50", "atr14", "rsi14", "stoch_rsi"]`.
- **FR-005**: The signal filtering for one-trade-at-a-time MUST happen after signal generation but before position initialization in the batch simulation.
- **FR-006**: Exit reasons (SL hit, TP hit, time expiry) MUST reset the position state allowing new entries.

### Key Entities _(include if feature involves data)_

- **Signal Index**: Index in the data array where a trade signal was generated.
- **Position State**: Tracks whether a position is currently open (entry index, exit index, is_open flag).
- **Filtered Signals**: Subset of generated signals that respect the one-trade-at-a-time rule.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Backtests produce at most one open position per symbol at any point in time.
- **SC-002**: All unit tests for the strategy pass without modification (backward compatibility).
- **SC-003**: Visualization charts display EMA overlays and oscillator panels for RSI14 and Stoch RSI.
- **SC-004**: The `required_indicators` list matches the actual indicators used in strategy logic.
- **SC-005**: Existing backtest performance benchmarks remain within acceptable tolerances (no significant slowdown from filtering).
