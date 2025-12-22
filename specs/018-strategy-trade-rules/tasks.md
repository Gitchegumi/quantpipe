# Tasks: Strategy Trade Rules & Indicator Exposure

**Input**: Design documents from `/specs/018-strategy-trade-rules/`
**Prerequisites**: plan.md (required), spec.md (required)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Strategy metadata enhancement needed by all user stories

- [x] T001 Add `max_concurrent_positions` field to `StrategyMetadata` in `src/strategy/base.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities that MUST be complete before user story implementation

- [x] T002 Create signal filtering module `src/backtest/signal_filter.py` with `filter_overlapping_signals()` function
- [x] T003 [P] Create unit tests for signal filtering in `tests/unit/test_signal_filtering.py`
- [x] T004 [P] Create unit tests for strategy metadata in `tests/unit/test_strategy_metadata.py`

**Checkpoint**: Foundational utilities ready - user story implementation can begin

---

## Phase 3: User Story 1 - One Trade at a Time Enforcement (Priority: P1) 🎯 MVP

**Goal**: Prevent multiple simultaneous positions per symbol in backtests

**Independent Test**: Run backtest and verify at most one open position per symbol at any time

### Implementation for User Story 1

- [x] T005 [US1] Update `TrendPullbackStrategy.metadata` to set `max_concurrent_positions=1` in `src/strategy/trend_pullback/strategy.py`
- [x] T006 [US1] Integrate signal filter into backtest orchestrator (call after `scan_vectorized()`)
- [x] T007 [US1] Create integration tests for one-trade-at-a-time rule in `tests/integration/test_one_trade_at_time.py`
- [x] T008 [US1] Run existing backtest tests to verify no regression: `poetry run pytest tests/integration/test_directional_backtesting.py -v`

**Checkpoint**: User Story 1 complete - backtests respect one trade at a time per strategy config

---

## Phase 4: User Story 2 - Indicator Visibility in Visualization (Priority: P2)

**Goal**: Display all strategy indicators (EMA, RSI, StochRSI) on visualization charts

**Independent Test**: Run visualization and verify RSI14 appears as oscillator panel

### Implementation for User Story 2

- [x] T009 [US2] Add `rsi14` to oscillators in `get_visualization_config()` in `src/strategy/trend_pullback/strategy.py`
- [x] T010 [US2] Run visualization config tests: `poetry run pytest tests/unit/test_visualization_config.py -v`
- [x] T011 [US2] Manual verification: Run `poetry run python -m src.cli.run_backtest --pair EURUSD --dataset test --visualize` and verify RSI14 oscillator panel appears

**Checkpoint**: User Story 2 complete - all strategy indicators visible in visualization

---

## Phase 5: User Story 3 - Indicator Consistency Audit (Priority: P3)

**Goal**: Ensure `required_indicators` matches actual usage in code and visualization

**Independent Test**: Compare indicators in metadata, `scan_vectorized()`, and `get_visualization_config()`

### Implementation for User Story 3

- [x] T012 [US3] Verify `required_indicators` in strategy metadata includes all used indicators (ema20, ema50, atr14, rsi14, stoch_rsi) - update if needed
- [x] T013 [US3] Add consistency documentation comment in `src/strategy/trend_pullback/strategy.py`

**Checkpoint**: User Story 3 complete - indicator consistency verified

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and documentation

- [x] T014 Run full test suite: `poetry run pytest tests/ -v --tb=short`
- [x] T015 [P] Run linting: `poetry run ruff check src/ tests/`
- [x] T016 [P] Run formatting check: `poetry run black --check src/ tests/`
- [x] T017 Create walkthrough.md documenting completed changes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 - BLOCKS all user stories
- **User Stories (Phases 3-5)**: All depend on Foundational phase completion
  - US1 (Phase 3): Can start after Foundational
  - US2 (Phase 4): Can start after Foundational (parallel with US1)
  - US3 (Phase 5): Can start after Foundational (parallel with US1/US2)
- **Polish (Phase 6)**: Depends on all user stories being complete

### Within Each User Story

- Implementation before integration tests
- Tests should pass before moving to next story

### Parallel Opportunities

- T003 and T004 can run in parallel (different test files)
- T015 and T016 can run in parallel (different linting tools)
- User Stories 2 and 3 can be worked on while US1 is in progress

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002-T004)
3. Complete Phase 3: User Story 1 (T005-T008)
4. **STOP and VALIDATE**: Test one-trade-at-a-time behavior
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. User Story 1 → Test → MVP complete
3. User Story 2 → Test → Visualization improved
4. User Story 3 → Test → Consistency verified
5. Polish → Full suite passes

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Tests in plan.md define specific test functions to implement (see plan for details)
- Commit after each task following Principle XI commit format
