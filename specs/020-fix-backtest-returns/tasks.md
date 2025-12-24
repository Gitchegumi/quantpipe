---
description: "Fix backtest return calculations to honor strategy-defined 2R take-profit targets"
---

# Tasks: Fix Backtest Return Calculations

**Input**: Design documents from `/specs/020-fix-backtest-returns/`
**Prerequisites**: plan.md, spec.md, research.md

**Tests**: Unit and integration tests are included to verify the fix works correctly across all modes

**Organization**: Tasks are grouped by user story. User Stories 1 and 2 can be addressed together since they share the same root cause (old batch simulation path bug).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths below use absolute paths from `e:\GitHub\trading-strategies\`

---

## Phase 1: Setup (No Changes Required)

**Purpose**: Verify existing project structure

- [ ] T001 Verify project structure matches plan.md (single Python project with src/ and tests/)
- [ ] T002 Confirm pytest is available for running tests

---

## Phase 2: Foundational (Code Audit & Verification)

**Purpose**: Understand current code paths before making changes

**⚠️ CRITICAL**: Complete audit before implementing fixes

- [ ] T003 [P] Audit `_run_vectorized_backtest()` in src/backtest/orchestrator.py (lines 633-866) to verify stop_prices/target_prices flow
- [ ] T004 [P] Audit `BatchSimulation.simulate()` in src/backtest/batch_simulation.py (lines 136-244) to confirm no hardcoded R-multiples
- [ ] T005 [P] Review portfolio mode implementation in src/backtest/portfolio/portfolio_simulator.py (lines 246-381) as reference

**Checkpoint**: Understand which paths are broken vs. working before proceeding

---

## Phase 3: User Stories 1 & 2 - Fix Individual and Isolated Mode Returns (Priority: P1, P2) 🎯 MVP

**Goal**: Fix `BacktestOrchestrator._simulate_batch()` to use per-trade SL/TP and strategy's target_r_mult

**Independent Test**: Run single-symbol backtest with 2R strategy, verify max R ≤ 2.2R

### Tests for User Stories 1 & 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T006 [P] [US1] [US2] Create unit test file tests/unit/test_simulate_batch_fix.py
- [ ] T007 [P] [US1] [US2] Write test_simulate_batch_respects_per_trade_sltp() to verify 3 entries with different SL/TP% (2%, 5%, 10%)
- [ ] T008 [P] [US1] [US2] Write test_simulate_batch_target_r_mult_from_strategy() to mock strategy with target_r_mult=3.0
- [ ] T009 [P] [US1] [US2] Write test_simulate_batch_no_global_defaults() to verify per-trade values are required
- [ ] T010 [US1] [US2] Run new unit tests, confirm they FAIL as expected: `poetry run pytest tests/unit/test_simulate_batch_fix.py -v`

### Implementation for User Stories 1 & 2

- [ ] T011 [US1] [US2] Modify simulate_trades_batch() signature in src/backtest/trade_sim_batch.py (lines 30-31) to make stop_loss_pct and take_profit_pct Optional[float] = None
- [ ] T012 [US1] [US2] Update fallback logic in src/backtest/trade_sim_batch.py (lines 102-103) to require per-trade SL/TP with ValueError if missing
- [ ] T013 [US1] [US2] Add target_r_mult parameter to \_simulate_batch() signature in src/backtest/orchestrator.py (line 130)
- [ ] T014 [US1] [US2] Replace hardcoded 2.0 with target_r_mult parameter in src/backtest/orchestrator.py (line 186)
- [ ] T015 [US1] [US2] Remove global stop_loss_pct and take_profit_pct from simulate_trades_batch() call in src/backtest/orchestrator.py (lines 211-215)
- [ ] T016 [US1] [US2] Find all call sites of \_simulate_batch() and ensure target_r_mult is passed from strategy
- [ ] T017 [US1] [US2] Run unit tests to verify fix: `poetry run pytest tests/unit/test_simulate_batch_fix.py -v`

**Checkpoint**: Old batch simulation path now honors per-trade SL/TP and strategy target_r_mult

---

## Phase 4: User Story 3 - Verify Strategy-Only Exit Logic (Priority: P1)

**Goal**: Confirm vectorized path and portfolio mode use strategy-provided prices without calculations

**Independent Test**: Code inspection shows no R-multiple calculations in orchestration/CLI code

### Verification for User Story 3

- [ ] T018 [US3] Grep src/backtest/orchestrator.py for hardcoded "2.0" or "2R" in \_run_vectorized_backtest() (lines 633-866)
- [ ] T019 [US3] Verify src/backtest/batch_simulation.py passes stop_prices/target_prices arrays directly to sim_eval (no transformations)
- [ ] T020 [US3] Grep src/cli/run_backtest.py for any R-multiple calculations or exit price modifications
- [ ] T021 [US3] Confirm vectorized path (lines 1614-1615 in orchestrator.py) passes ScanResult arrays directly to BatchSimulation.simulate()
- [ ] T022 [US3] Document findings: Create verification_notes.md listing any hardcoded values found (expected: none in vectorized path)

**Checkpoint**: Confirm vectorized path is clean (no changes needed)

---

## Phase 5: Integration Testing (All User Stories)

**Purpose**: Verify all three modes (individual, isolated, portfolio) produce equivalent R-multiples

- [ ] T023 [P] Create integration test file tests/integration/test_rmult_mode_equivalence.py
- [ ] T024 [US1] [US2] Write test_individual_mode_honors_2r_target() to run single-symbol backtest and verify max R ≤ 2.2R
- [ ] T025 [US1] [US2] Write test_isolated_mode_honors_2r_target() to run 3-symbol isolated backtest and verify all max R ≤ 2.2R
- [ ] T026 [US1] [US2] Write test_individual_isolated_portfolio_rmult_equivalence() to verify ±5% avg R across all three modes
- [ ] T027 Run integration tests: `poetry run pytest tests/integration/test_rmult_mode_equivalence.py -v`

**Checkpoint**: All modes show consistent R-multiples within tolerance

---

## Phase 6: Regression Testing

**Purpose**: Ensure existing tests still pass after fixes

- [ ] T028 [P] Run existing backtest tests: `poetry run pytest tests/integration/test_backtest_split_mode.py -v`
- [ ] T029 [P] Run directional backtest tests: `poetry run pytest tests/integration/test_directional_backtesting.py -v`
- [ ] T030 [P] Run portfolio flow tests: `poetry run pytest tests/integration/test_portfolio_flow.py -v`
- [ ] T031 [P] Run orchestrator unit tests: `poetry run pytest tests/unit/test_backtest_orchestrator.py -v`
- [ ] T032 Run full backtest test suite: `poetry run pytest tests/ -k "backtest or portfolio or simulation" --tb=short`

**Checkpoint**: All existing tests pass (100% pass rate)

---

## Phase 7: Manual Validation

**Purpose**: User confirms fix resolves 8+R bug

- [ ] T033 Document current behavior: Run backtest and capture max R-multiple before fix (expected: 8+R)
- [ ] T034 Run same backtest after fix and capture max R-multiple (expected: ≤2.2R)
- [ ] T035 Compare results and verify reduction from 8+R to ~2R

**User provides**: Confirmation that max R-multiple is now reasonable

---

## Phase 8: Polish & Documentation

**Purpose**: Final cleanup and documentation

- [ ] T036 [P] Update docstrings in src/backtest/trade_sim_batch.py to document deprecated global SL/TP parameters
- [ ] T037 [P] Update docstrings in src/backtest/orchestrator.py to document target_r_mult parameter
- [ ] T038 Add code comments explaining per-trade SL/TP requirement
- [ ] T039 Run linting: `poetry run ruff check src/backtest/orchestrator.py src/backtest/trade_sim_batch.py`
- [ ] T040 Run formatting: `poetry run black src/backtest/orchestrator.py src/backtest/trade_sim_batch.py`
- [ ] T041 Create CHANGELOG entry documenting bug fix

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - confirm structure
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories 1 & 2 (Phase 3)**: Depends on Foundational audit - Core fix (MVP)
- **User Story 3 (Phase 4)**: Can run in parallel with Phase 3 (verification only, no code changes)
- **Integration Testing (Phase 5)**: Depends on Phase 3 completion
- **Regression Testing (Phase 6)**: Depends on Phase 3 completion
- **Manual Validation (Phase 7)**: Depends on Phase 3 completion
- **Polish (Phase 8)**: Depends on all tests passing

### User Story Dependencies

- **User Story 1 (P1)**: Individual symbol backtest fix - can start after Foundational
- **User Story 2 (P2)**: Isolated multi-symbol backtest fix - shares same code path as US1, combined implementation
- **User Story 3 (P1)**: Strategy-only exit logic verification - independent audit, can run in parallel with US1/US2 implementation

### Within Each Phase

- Tests MUST be written and FAIL before implementation
- Implementation tasks follow sequential order (modify function signature → update logic → update call sites)
- Verification tasks can run in parallel once implementation is complete

### Parallel Opportunities

- Phase 2 audit tasks (T003-T005) can all run in parallel
- Phase 3 test writing tasks (T006-T009) can all run in parallel
- Phase 4 verification tasks (T018-T021) can all run in parallel
- Phase 5 integration test writing (T023-T026) can run in parallel
- Phase 6 regression tests (T028-T031) can all run in parallel
- Phase 8 documentation tasks (T036-T038) can run in parallel

---

## Parallel Example: User Stories 1 & 2 (Phase 3)

```bash
# Launch all test file creation together:
Task: "Create unit test file tests/unit/test_simulate_batch_fix.py"
Task: "Write test_simulate_batch_respects_per_trade_sltp()"
Task: "Write test_simulate_batch_target_r_mult_from_strategy()"
Task: "Write test_simulate_batch_no_global_defaults()"

# Then implement fixes sequentially (due to same file dependencies):
Task: "Modify simulate_trades_batch() signature" (trade_sim_batch.py)
Task: "Update fallback logic" (trade_sim_batch.py)
Task: "Add target_r_mult parameter" (orchestrator.py)
Task: "Replace hardcoded 2.0" (orchestrator.py)
Task: "Remove global SL/TP from call" (orchestrator.py)
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only)

1. Complete Phase 1: Setup (verify structure)
2. Complete Phase 2: Foundational (audit code paths)
3. Complete Phase 3: User Stories 1 & 2 (core fix)
4. Complete Phase 5: Integration Testing
5. **STOP and VALIDATE**: Verify max R ≤ 2.2R
6. Complete user confirmation (Phase 7)

### Full Feature Delivery

1. Complete Setup + Foundational → Understand code
2. Complete User Stories 1 & 2 → Fix old batch path
3. Complete User Story 3 → Verify vectorized path clean
4. Complete Integration + Regression Testing → Validate fix
5. Complete Manual Validation → User confirms
6. Complete Polish → Production ready

### Estimated Task Count

- **Total Tasks**: 41
- **Phase 1 (Setup)**: 2 tasks
- **Phase 2 (Foundational)**: 3 tasks
- **Phase 3 (US1/US2 - Core Fix)**: 12 tasks (5 tests + 7 implementation)
- **Phase 4 (US3 - Verification)**: 5 tasks
- **Phase 5 (Integration Tests)**: 5 tasks
- **Phase 6 (Regression)**: 5 tasks
- **Phase 7 (Manual Validation)**: 3 tasks
- **Phase 8 (Polish)**: 6 tasks

### Parallel Opportunities

- **Foundational audit**: 3 tasks in parallel
- **Test writing (Phase 3)**: 4 tasks in parallel
- **Verification (Phase 4)**: 5 tasks in parallel (can overlap with Phase 3 implementation)
- **Integration test writing**: 3 tasks in parallel
- **Regression tests**: 4 tasks in parallel
- **Documentation**: 3 tasks in parallel

**Total parallelizable tasks**: 22/41 (54%)

---

## Notes

- [P] tasks = different files/independent work, no dependencies
- [Story] label maps task to specific user story for traceability
- Tests written first (TDD approach) to verify fixes work
- User Stories 1 and 2 combined into single phase (same root cause, same fix)
- User Story 3 is verification-only (no code changes expected in vectorized path)
- Commit after logical groups (e.g., after T017, after T022, after T027, after T032)
- Stop at Phase 3 checkpoint to validate core fix works before proceeding to full test suite
