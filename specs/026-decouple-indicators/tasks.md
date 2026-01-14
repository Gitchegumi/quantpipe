# Tasks: Decouple Indicator Registration

**Feature**: Decouple Indicator Registration (026-decouple-indicators)
**Status**: In Progress

## Dependencies

- **US1** (Strategy Indicators) must be completed before **US2** (Backward Compatibility/Verification).

## Phase 1: Foundational

- [ ] T001 [US1] Add `get_custom_indicators` method to `Strategy` base class in `src/strategy/base.py`

## Phase 2: User Story 1 - Strategy-Specific Indicators

**Goal**: Enable strategies to define and use custom indicators.

- [ ] T002 [US1] Update `calculate_indicators` in `src/indicators/dispatcher.py` to accept `custom_registry`
- [ ] T003 [US1] Implement lookup precedence logic (custom > global) in `src/indicators/dispatcher.py`
- [ ] T004 [US1] Update call site in `src/backtest/engine.py` (`run_portfolio_backtest`) to pass strategy indicators
- [ ] T005 [US1] Update call site in `src/backtest/engine.py` (`run_multi_symbol_backtest`) to pass strategy indicators
- [ ] T006 [US1] Update call site in `src/backtest/portfolio/independent_runner.py` (`_run_symbol_backtest`) to pass strategy indicators

## Phase 3: User Story 2 - Backward Compatibility & Verification

**Goal**: Ensure existing strategies work and new custom indicators function correctly.

- [ ] T007 [US2] Create reproduction test case `tests/integration/test_custom_indicators.py` verifying custom indicator logic
- [ ] T008 [US2] Run full integration suite `tests/integration/` to ensure no regressions
- [ ] T009 [US2] Verify `run_backtest` CLI still works with `trend_pullback` (standard indicators)

## Implementation Strategy

1. **Foundational**: Update the base class first so all strategies inherit the new method (returning empty dict by default).
2. **Dispatcher**: Update the core logic to handle the new parameter.
3. **Integration**: Wire up the orchestrators to pass the data.
4. **Verification**: Add a test that defines a custom indicator and asserts it runs.
