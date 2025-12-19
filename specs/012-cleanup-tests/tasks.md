# Tasks: Clean Up Tests and Fix Integration Tests

**Input**: Design documents from `/specs/012-cleanup-tests/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md

**Tests**: This feature is about fixing and cleaning up tests, so verification is built into the implementation tasks themselves.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Capture baseline metrics before making changes

- [ ] T001 Run baseline test collection and record total test count with `poetry run pytest --collect-only -q`
- [ ] T002 Run full integration test suite and document current failures with `poetry run pytest tests/integration -v --tb=short`

---

## Phase 2: Foundational (Analysis)

**Purpose**: Confirm inventory and identify exact tests to modify/remove

**⚠️ CRITICAL**: Complete analysis before any file modifications

- [ ] T003 Review existing inventory in tests/\_inventory_removed.txt and confirm tests to remove
- [ ] T004 Analyze test_both_mode_backtest.py to confirm all 4 failing tests use legacy_ingestion pattern
- [ ] T005 Identify exact tests to remove from test_indicators_basic.py (6 redundant tests)
- [ ] T006 Identify exact tests to remove from test_risk_manager_rounding.py (3-4 redundant tests)

**Checkpoint**: Analysis complete - implementation can now begin

---

## Phase 3: User Story 1 - Fix Failing Integration Tests (Priority: P1) 🎯 MVP

**Goal**: Make all integration tests pass in CI (0 failures, exit code 0)

**Independent Test**: `poetry run pytest tests/integration -v --tb=short` returns exit code 0

### Implementation for User Story 1

- [x] T007 [US1] Analyze test_vectorized_direct.py to understand working ingestion pattern in tests/integration/test_vectorized_direct.py
- [x] T008 [US1] Refactor test_both_backtest_execution in tests/integration/test_both_mode_backtest.py to use vectorized API
- [x] T009 [US1] Refactor test_both_backtest_dry_run in tests/integration/test_both_mode_backtest.py to use vectorized API
- [x] T010 [US1] Refactor test_both_backtest_text_output in tests/integration/test_both_mode_backtest.py to use vectorized API
- [x] T011 [US1] Refactor test_both_backtest_json_output in tests/integration/test_both_mode_backtest.py to use vectorized API
- [ ] T012 [US1] Run integration tests to verify all pass with `poetry run pytest tests/integration -v --tb=short`

**Checkpoint**: All integration tests pass (SC-001 satisfied)

---

## Phase 4: User Story 2 - Remove Obsolete/Redundant Tests (Priority: P2)

**Goal**: Remove redundant tests while preserving unique edge case coverage

**Independent Test**: `poetry run pytest tests/unit -v --tb=short` passes; test count reduced by 6-10

### Implementation for User Story 2

- [ ] T013 [P] [US2] Remove 6 redundant tests from tests/unit/test_indicators_basic.py (keep edge cases: empty, single value)
- [ ] T014 [P] [US2] Remove 3-4 redundant position sizing tests from tests/unit/test_risk_manager_rounding.py
- [ ] T015 [US2] Run unit tests to verify no regression with `poetry run pytest tests/unit -v --tb=short`
- [ ] T016 [US2] Run full test suite to verify test count reduction ≤30% with `poetry run pytest --collect-only -q`

**Checkpoint**: Redundant tests removed, coverage maintained (SC-002, SC-004 satisfied)

---

## Phase 5: User Story 3 - Audit and Document Test Suite (Priority: P3)

**Goal**: Document all test changes with justifications for future developers

**Independent Test**: Review tests/removal-notes.md and confirm each removed test has justification

### Implementation for User Story 3

- [ ] T017 [US3] Create tests/removal-notes.md documenting all removed tests with justifications
- [ ] T018 [US3] Update tests/\_inventory_removed.txt to mark completed actions

**Checkpoint**: Documentation complete (SC-005 satisfied)

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and code quality checks

- [ ] T019 Run lint checks with `poetry run ruff check tests/ && poetry run black tests/ --check`
- [ ] T020 Run full test suite to verify all tests pass with `poetry run pytest -v --tb=short`
- [ ] T021 Commit changes with semantic format `test(012): Fix failing integration tests and remove redundant tests`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **Analysis (Phase 2)**: Depends on Setup completion
- **User Story 1 (Phase 3)**: Depends on Analysis completion - BLOCKS other stories
- **User Story 2 (Phase 4)**: Depends on User Story 1 (to ensure baseline passes)
- **User Story 3 (Phase 5)**: Depends on User Story 2 (to document what was removed)
- **Polish (Phase 6)**: Depends on all user stories

### User Story Dependencies

- **User Story 1 (P1)**: MUST complete first - restores CI to green
- **User Story 2 (P2)**: Depends on US1 passing - removes redundant tests
- **User Story 3 (P3)**: Depends on US2 - documents all changes

### Within Each User Story

- Analysis → Implementation → Verification
- Refactor one test at a time (T008-T011 are sequential for same file)
- Parallel tasks marked [P] can run concurrently (T013, T014)

### Parallel Opportunities

- T013 and T014 can run in parallel (different files)
- Other tasks are sequential due to file dependencies

---

## Parallel Example: User Story 2

```bash
# Launch redundant test removals in parallel:
Task: "Remove 6 redundant tests from tests/unit/test_indicators_basic.py"
Task: "Remove 3-4 redundant tests from tests/unit/test_risk_manager_rounding.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (capture baseline)
2. Complete Phase 2: Analysis (confirm targets)
3. Complete Phase 3: User Story 1 (fix failing tests)
4. **STOP and VALIDATE**: Run `poetry run pytest tests/integration -v` - all must pass
5. If CI is green, MVP is achieved

### Incremental Delivery

1. Setup + Analysis → Baseline captured
2. User Story 1 → All tests pass → **CI is green!**
3. User Story 2 → Redundant tests removed → Test suite cleaner
4. User Story 3 → Documentation complete → Knowledge preserved
5. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit with semantic format: `test(012): <description> (T###)`
- Stop at any checkpoint to validate story independently
