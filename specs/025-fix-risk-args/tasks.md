# Tasks: Fix Risk Argument Mapping

**Feature Branch**: `025-fix-risk-args`
**Status**: Planning

## Phase 1: Setup

- [x] T001 Verify project environment and dependencies

## Phase 2: Foundational (Blocking)

> **Goal**: Update data models to support new risk parameters.

- [x] T002 [US1] Add `max_position_size` to `StrategyParameters` in `src/config/parameters.py`

## Phase 3: Risk Parameters Override & Precedence (US1, US2)

> **Goal**: Ensure CLI arguments correctly map to strategy parameters and override defaults/config.
> **Independent Test**: Run backtest with `--rr-ratio 5.0` and verify results differ from default.

### Implementation

- [x] T003 [US1] Implement argument mapping logic in `src/cli/run_backtest.py` for R:R, ATR Mult, Risk %, and Account Balance
- [x] T004 [US1] Implement argument mapping logic in `src/cli/run_backtest.py` for `max_position_size`
- [x] T005 [US2] Implement precedence logic (CLI > Config > Default) in `src/cli/run_backtest.py`
- [x] T006 [US1] Add logging of active risk parameters in `src/cli/run_backtest.py` (FR-006)

### Verification

- [x] T007 [US1] [P] Create integration test `tests/integration/test_cli_risk_args.py` verifying parameter mapping and precedence

### Feature Update: Trailing Stops

- [x] T008 [US2] [P] Update `src/risk/config.py` to support `MA_Trailing`, `FixedPips_Trailing` and new params (`ma_type`, `ma_period`)
- [x] T009 [US2] [P] Update `src/cli/run_backtest.py` to accept `--ma-type`, `--ma-period` and populate RiskConfig
- [x] T010 [US2] [P] Update `src/backtest/engine.py` to ensure MA indicators are calculated during enrichment
- [x] T011 [US2] [E] Refactor `PortfolioSimulator._simulate_symbol_vectorized` to extract indicator data and prepare trailing config
- [x] T012 [US2] [E] Refactor `src/backtest/trade_sim_batch.py` to accept `indicators` and implement vectorized trailing logic (ratchet)
- [x] T013 [US2] [V] Create `tests/integration/test_trailing_stops.py` with test cases for ATR, MA, and FixedPips trailing
- [x] T014 [US2] [V] Verify fixes with manual backtest runs and walkthrough update
- [x] T015 [US2] [P] Implement Trailing Trigger: Update `RiskConfig` and `CLI` with `trail_trigger_r`.
- [x] T016 [US2] [E] Update `trade_sim_batch.py` to support `trail_trigger_r` logic.
- [x] T017 [US2] [V] Update tests for trailing trigger.

## Dependencies

1. T001
2. T002
3. T003, T004, T005, T006 (Parallelizable)
4. T007

## Implementation Strategy

1. Update `StrategyParameters` first (T002) to ensure the target fields exist.
2. Modify `run_backtest.py` to parse and map the arguments, implementing the precedence logic simultaneously.
3. Validate with the integration test.
