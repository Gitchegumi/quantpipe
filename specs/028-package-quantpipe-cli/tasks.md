# Implementation Tasks - Package 'quantpipe' CLI Tool

Feature: **package-quantpipe-cli**
Spec: [spec.md](spec.md)
Plan: [plan.md](plan.md)

This task list follows a User Story-based execution flow. Each phase represents a deliverable unit of value that can be independently tested.

## Checkpoint: Project Initialization

**Goal**: Prepare environment for packaging logic.

### Phase 1: Setup

- [ ] T001 Verify project structure and `pyproject.toml` existence for `package-quantpipe-cli` feature
- [ ] T002 [P] Create `src/cli` directory if it doesn't strictly exist (it does, but verifying context)
- [ ] T003 Verify `poetry` environment is active and running

## Checkpoint: Foundation

**Goal**: Implement shared core logic for both legacy and new CLI entry points.

### Phase 2: Foundational Components (Splitting Logic)

- [ ] T004 Refactor `src/cli/run_backtest.py` to extract `configure_backtest_parser` function
- [ ] T005 Refactor `src/cli/run_backtest.py` to extract `run_backtest_command` function
- [ ] T006 Ensure `src/cli/run_backtest.py` `main()` block calls extracted functions (Backward Compatibility)
- [ ] T007 [P] Create `src/cli/main.py` entry point file skeleton

## Checkpoint: User Story 1 - Install and Verify CLI (MVP!)

**Goal**: Enable `quantpipe` command via package installation.
**Priority**: P1
**Dependent On**: Phase 2

**Independent Test Criteria**:

1. `pip install .` works in a clean env.
2. `quantpipe --help` displays usage.
3. `quantpipe` command exists in `poetry run`.

### Phase 3: Installable CLI [US1]

- [ ] T008 [US1] Implement `main()` in `src/cli/main.py` with `argparse` and subcommands support
- [ ] T009 [US1] Update `pyproject.toml` to add `[tool.poetry.scripts]` mapping `quantpipe = "src.cli.main:main"`
- [ ] T010 [US1] Verify `poetry install` succeeds
- [ ] T011 [US1] Verify `poetry run quantpipe --help` works

## Checkpoint: User Story 2 - Execute Backtest via CLI

**Goal**: Expose backtest functionality via `quantpipe backtest`.
**Priority**: P1
**Dependent On**: Phase 3

**Independent Test Criteria**:

1. `quantpipe backtest [args]` runs a backtest.
2. Output matches legacy script.

### Phase 4: Backtest Subcommand [US2]

- [ ] T012 [P] [US2] Wire `backtest` subcommand in `src/cli/main.py` to use `configure_backtest_parser`
- [ ] T013 [P] [US2] Wire `backtest` subcommand execution in `src/cli/main.py` to use `run_backtest_command`
- [ ] T014 [US2] Manual verification: Run short backtest via `poetry run quantpipe backtest --dry-run`

## Checkpoint: Polish & Documentation

**Goal**: Clean up and document usage.

### Phase 5: Polish

- [ ] T015 [P] Add docstrings to `src/cli/main.py` explaining subcommand structure
- [ ] T016 [P] Update `README.md` (if applicable) or create `docs/cli.md` with `quantpipe` usage examples

## Dependencies

1. **Setup** (Phase 1)
2. **Foundational** (Phase 2)
   - Splits monolithic script into reusable components
3. **User Story 1** (Phase 3)
   - Depends on: Foundational (needs `src/cli/main.py` target)
   - Result: `quantpipe` command exists
4. **User Story 2** (Phase 4)
   - Depends on: User Story 1 (CLI must exist), Foundational (needs extracted logic)
   - Result: `quantpipe backtest` works

## Implementation Strategy

### Sequential MVP Strategy

1. **Phase 2 (Refactor)**: We must first break apart the existing script `run_backtest.py` so its logic can be reused without code duplication.
2. **Phase 3 (Wiring)**: Create the new entry point `main.py` and register it in `pyproject.toml`.
3. **Phase 4 (Functionality)**: Connect the backtest logic to the new entry point.

### Parallel Execution

- T015/T016 (Docs) can be done anytime after Phase 3.
- T012/T013 (Wiring) depend on T004/T005 (Refactor).
