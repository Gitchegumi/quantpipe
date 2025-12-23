---
description: "Task list for fix-portfolio-viz"
---

# Tasks: Fix Portfolio Mode Visualizations

**Input**: Design documents from `/specs/019-fix-portfolio-viz/`
**Prerequisites**: plan.md, spec.md, data-model.md
**Tests**: OPTIONAL (Integration tests included for verification)
**Organization**: Tasks are grouped by logical component dependencies (CLI logic first, then Visualization mapping).

## Phase 1: Setup & Tests (Foundational)

**Purpose**: Establish baseline verification integration tests to prove current failure and later success.

- [ ] T001 Create integration test `tests/integration/test_portfolio_flow.py` for execution flow verification
- [ ] T002 [P] Create integration test `tests/integration/test_portfolio_viz_structure.py` for visualization data structure verification

---

## Phase 2: User Story 2 & 3 - Execution Flow & Capital Logic (Priority: P1)

**Goal**: Ensure portfolio backtest runs exactly once and terminates, preventing confusing double-runs.

**Independent Test**: `test_portfolio_flow.py` passes (exit code 0, single execution log signature).

### Implementation for User Story 2 & 3

- [ ] T003 [US2] [P] Modify `src/cli/run_backtest.py` to add return statement after portfolio execution block
- [ ] T004 [US2] [P] Verify log output for duplicate "Starting..." messages removal
- [ ] T005 [US3] [P] Review `src/backtest/portfolio/portfolio_simulator.py` to ensure shared equity state is correctly finalized (No code change expected if logic holds, verification task)

**Checkpoint**: CLI runs cleanly for portfolio command without falling through to independent mode.

---

## Phase 3: User Story 1 - Independent Symbol Charts (Priority: P1)

**Goal**: Display separate price charts for each portfolio symbol instead of one merged mess.

**Independent Test**: `test_portfolio_viz_structure.py` passes (BacktestResult has correct child `results` structure); HTML file contains multiple plot panels.

### Implementation for User Story 1

- [ ] T006 [US1] Refactor `run_backtest.py` visualization block: Create hierarchical `BacktestResult` structure
- [ ] T007 [US1] [P] Implement symbol-based trade filtering loop to populate child results
- [ ] T008 [US1] Set `is_multi_symbol=True` and populates `results` dict in the visualization conversion logic
- [ ] T009 [US1] [P] Update `src/visualization/datashader_viz.py` to ensure it respects `Multi-Symbol` pair tag or auto-detects `results` dict
- [ ] T010 [US1] Verify HTML output renders separate charts with correct title "Multi-Symbol Backtest"

**Checkpoint**: Generating visualization for a portfolio run produces a multi-panel HTML file.

---

## Phase 4: Polish

**Purpose**: Cleanup and documentation.

- [ ] T011 Update `quickstart.md` with final verified output screenshot or description
- [ ] T012 Run full regression suite `tests/` to ensure no regression in single-symbol independent mode

---

## Dependencies & Execution Order

1. **Phase 1 (Tests)**: Write these first to define success.
2. **Phase 2 (CLI Fix)**: Depends on tests; Fixes the annoying double-run bug first.
3. **Phase 3 (Viz Fix)**: Depends on CLI Fix; Implements the data transformation.
4. **Phase 4 (Polish)**: Final verification.

## Parallel Opportunities

- T001 and T002 can be written in parallel.
- T003 (CLI Return) and T007 (Viz logic refactor) modify different parts of `run_backtest.py` (control flow vs viz block), but risk merge conflict. Better to do sequential or careful merge.
- T009 (Viz module check) is independent of various CLI changes.
