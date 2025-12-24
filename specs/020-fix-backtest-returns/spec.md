# Feature Specification: Fix Backtest Return Calculations

**Feature Branch**: `020-fix-backtest-returns`
**Created**: 2025-12-23
**Status**: Draft
**Input**: User description: "I need to determine why the isolated and individual backtest simulations are giving overly optimistic returns of 8+R when the strategy is specifically designed to have a TP at 2R. The portfolio mode has been fixed in this regard, so we just need to fix isolated multi-symbol and individual simulations so they follow the strategy rules. There should be no calculations occurring in run_backtest or any of the backtest logic. Everything should come from the strategy."

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Individual Symbol Backtest Returns Correct R-Multiple (Priority: P1)

As a trading strategy developer, when I run a backtest on an individual symbol using a strategy with a 2R take-profit target, I need the final results to show trade returns consistent with the 2R maximum, not inflated values like 8+R. This ensures I can trust the backtest results for strategy evaluation.

**Why this priority**: This is the most critical issue because it directly affects the reliability of backtest results. Overly optimistic returns (8+R when expecting 2R) completely invalidate backtesting for strategy validation and risk assessment.

**Independent Test**: Can be fully tested by running a single-symbol backtest with a known TP strategy and verifying that all winning trades close at the specified R-multiple (e.g., 2R) and that the final metrics accurately reflect this constraint.

**Acceptance Scenarios**:

1. **Given** a strategy configured with a 2R take-profit target, **When** I run an individual symbol backtest, **Then** the maximum observed return for any winning trade should be 2R (within a small tolerance for slippage/fees)
2. **Given** a completed individual backtest with 10 winning trades, **When** I examine the trade-by-trade results, **Then** each winning trade should show an exit at or below the 2R target price
3. **Given** a strategy with defined stop-loss and take-profit levels, **When** the backtest simulation processes trades, **Then** the exit logic should respect the strategy's target_prices without applying additional calculations

---

### User Story 2 - Isolated Multi-Symbol Mode Returns Correct R-Multiples (Priority: P2)

As a trader backtesting a strategy across multiple symbols in isolated mode (one backtest per symbol), I need each symbol's backtest to show accurate returns based on the strategy's defined risk/reward parameters, not inflated returns.

**Why this priority**: Multi-symbol isolated mode is commonly used to compare strategy performance across different instruments. Inflated returns make it impossible to identify which symbols perform well and which don't.

**Independent Test**: Can be tested by running isolated multi-symbol backtests on 3-5 different symbols with the same 2R TP strategy and verifying that all results show consistent R-multiples across all symbols.

**Acceptance Scenarios**:

1. **Given** a multi-symbol backtest in isolated mode with a 2R TP strategy, **When** I review results for each symbol separately, **Then** no symbol should show winning trades exceeding 2R
2. **Given** isolated mode backtests for symbols A, B, and C, **When** all use the same strategy configuration, **Then** the maximum R-multiple should be consistent (all ~2R) across all three symbols
3. **Given** a completed isolated multi-symbol backtest, **When** I aggregate the results, **Then** the overall average R-multiple for winners should align with the 2R target (accounting for partial fills and losses)

---

### User Story 3 - Strategy Parameters Control All Trade Exits (Priority: P1)

As a strategy developer, I need all trade exit logic to be controlled exclusively by the strategy's defined parameters (stop_prices, target_prices) without any interference from backtest orchestration code or CLI logic.

**Why this priority**: This is a fundamental architecture requirement. If backtest orchestration or CLI code performs calculations or overrides strategy logic, it creates a maintenance nightmare and breeds bugs like the current 8+R issue.

**Independent Test**: Can be verified through code inspection and unit tests validating that backtest simulator classes accept strategy outputs as-is without modification, and that no price/return calculations occur outside strategy code.

**Acceptance Scenarios**:

1. **Given** a strategy that provides stop_prices and target_prices arrays, **When** the backtest simulator processes signals, **Then** it should use these exact prices for exit calculations without modification
2. **Given** the backtest orchestration code in `run_backtest.py`, **When** processing simulation results, **Then** no R-multiple calculations or trade return adjustments should occur
3. **Given** a debugging session tracing a single trade from signal to exit, **When** examining the code flow, **Then** the exit price should trace directly back to the strategy's target_prices output with no intermediate transformations
4. **Given** portfolio mode (which has been fixed), **When** comparing its code path to isolated/individual mode, **Then** both should use identical exit price logic sourced from the strategy

---

### Edge Cases

- What happens when a trade exits early (e.g., stop-loss hit before reaching 2R TP)? The R-multiple should reflect the actual exit, not the target.
- What happens if the strategy provides invalid target_prices (NaN, infinity, or negative values)? The system should validate and error gracefully.
- How does the system handle partial fills or mid-candle exits? The exit should still respect the strategy's price levels, not recalculate based on OHLC data.
- What if different symbols have different risk parameters (e.g., Symbol A uses 2R, Symbol B uses 3R)? Each should honor its own strategy-defined targets independently.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: Individual symbol backtests MUST calculate trade returns using only the exit prices provided by the strategy's target_prices output, without additional calculations
- **FR-002**: Isolated multi-symbol backtests MUST apply the same exit price logic to each symbol independently, producing consistent R-multiples when using the same strategy
- **FR-003**: The backtest simulator MUST NOT perform any R-multiple calculations or price transformations on strategy-provided stop_prices or target_prices
- **FR-004**: The CLI orchestration code (`run_backtest.py`) MUST NOT calculate or modify trade returns, R-multiples, or exit prices
- **FR-005**: All trade exit logic MUST be sourced exclusively from the strategy class methods (scan_vectorized or equivalent)
- **FR-006**: When a strategy specifies a 2R take-profit target, the maximum observed R-multiple for winning trades MUST be approximately 2R (within ±0.1R tolerance for fees/slippage)
- **FR-007**: The backtest results MUST clearly identify where trade exits originated (strategy stop-loss, strategy take-profit, end-of-data, etc.) to enable debugging
- **FR-008**: Individual and isolated mode MUST use the same trade simulation logic as the (already-fixed) portfolio mode to ensure consistency

### Key Entities

- **Trade**: Represents a single trade execution with entry price, exit price, direction (long/short), and calculated R-multiple based on the actual exit vs. the initial stop-loss
- **Strategy**: Defines trading rules and outputs signal indices, stop_prices, and target_prices that fully constrain when and how trades should exit
- **BacktestResult**: Contains aggregated metrics including trade-by-trade details, with R-multiples derived from actual executed exits
- **Simulation Modes**: Individual (single symbol), Isolated (multiple symbols independently), Portfolio (multiple symbols with shared capital - already fixed)

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: When running a backtest with a strategy configured for 2R take-profit, no winning trade in individual or isolated mode shows an R-multiple exceeding 2.2R (allowing 0.2R tolerance for fees)
- **SC-002**: Individual and isolated multi-symbol backtests produce the same R-multiple distribution as portfolio mode when using identical strategy parameters and data
- **SC-003**: Code inspection confirms zero instances of R-multiple calculations, trade return calculations, or price modifications in `run_backtest.py` or orchestration logic
- **SC-004**: All existing integration and unit tests pass, confirming that the fix doesn't break other backtest functionality
- **SC-005**: Running the same strategy on the same data in individual, isolated, and portfolio modes produces statistically equivalent average R-multiples (within ±5% due to capital allocation differences)
