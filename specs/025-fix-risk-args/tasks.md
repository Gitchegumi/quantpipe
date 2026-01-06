# Tasks: Fix Risk Argument Mapping

**Feature Branch**: `025-fix-risk-args`
**Status**: Planning

## Phase 1: Setup

- [ ] T001 Verify project environment and dependencies

## Phase 2: Foundational (Blocking)

> **Goal**: Update data models to support new risk parameters.

- [ ] T002 [US1] Add `max_position_size` to `StrategyParameters` in `src/config/parameters.py`

## Phase 3: Risk Parameters Override & Precedence (US1, US2)

> **Goal**: Ensure CLI arguments correctly map to strategy parameters and override defaults/config.
> **Independent Test**: Run backtest with `--rr-ratio 5.0` and verify results differ from default.

### Implementation

- [ ] T003 [US1] Implement argument mapping logic in `src/cli/run_backtest.py` for R:R, ATR Mult, Risk %, and Account Balance
- [ ] T004 [US1] Implement argument mapping logic in `src/cli/run_backtest.py` for `max_position_size`
- [ ] T005 [US2] Implement precedence logic (CLI > Config > Default) in `src/cli/run_backtest.py`
- [ ] T006 [US1] Add logging of active risk parameters in `src/cli/run_backtest.py` (FR-006)

### Verification

- [ ] T007 [US1] [P] Create integration test `tests/integration/test_cli_risk_args.py` verifying parameter mapping and precedence

## Dependencies

1. T001
2. T002
3. T003, T004, T005, T006 (Parallelizable)
4. T007

## Implementation Strategy

1. Update `StrategyParameters` first (T002) to ensure the target fields exist.
2. Modify `run_backtest.py` to parse and map the arguments, implementing the precedence logic simultaneously.
3. Validate with the integration test.
