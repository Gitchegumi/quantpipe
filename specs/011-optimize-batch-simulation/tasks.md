# Tasks: Optimize Batch Simulation Performance

**Branch**: `011-optimize-batch-simulation` | **Date**: 2025-11-12 | **Spec**: [spec.md](spec.md)

**Note**: This project uses Poetry for dependency management. Do not create new virtual environments; use Poetry commands for installing packages.

This document outlines the tasks required to optimize the batch simulation performance.

## Phase 1: Setup & Research

- [ ] T001 Install profiling tools (`py-spy`, `cProfile`) using Poetry.
- [ ] T002 Profile the existing simulation engine to identify performance bottlenecks in `src/backtest/`.
- [ ] T003 Document the profiling results in `research.md`.
- [ ] T004 Evaluate parallelization libraries (`multiprocessing`, `joblib`, `dask`, `ray`) and document the findings in `research.md`.
- [ ] T005 Evaluate high-performance data manipulation libraries (`polars`, `vaex`) and document the findings in `research.md`.
- [ ] T006 Based on the research, decide on the parallelization library and data manipulation library to be used. Update `research.md` with the decision.

## Phase 2: Foundational Changes

- [ ] T007 [P] Install the chosen parallelization library and add it to `pyproject.toml`.
- [ ] T008 [P] Install the chosen data manipulation library and add it to `pyproject.toml`.
- [ ] T009 Create a new module `src/backtest/parallel_runner.py` to encapsulate the parallel execution logic.
- [ ] T010 Refactor the data loading and preprocessing steps in `src/preprocess/` to use the new data manipulation library.

## Phase 3: User Story 1 - Faster Single Simulation Run

- [ ] T011 [US1] Refactor the core simulation loop in `src/backtest/trade_sim_batch.py` to use the new data manipulation library.
- [ ] T012 [US1] Optimize the identified bottlenecks from the profiling step in the `src/backtest/` modules.
- [ ] T013 [US1] Create a benchmark test to measure the execution time of a single simulation run in `tests/performance/test_single_simulation.py`.
- [ ] T014 [US1] Run the benchmark test and verify that the execution time is reduced by at least 90%.

## Phase 4: User Story 2 - Efficient Multi-Experiment Execution

- [ ] T015 [US2] Implement the batch simulation logic in `src/backtest/batch_simulation.py` using the `parallel_runner.py` module.
- [ ] T016 [US2] Update the CLI in `src/cli/main.py` to support running batch simulations.
- [ ] T017 [US2] Create a benchmark test to measure the execution time of a batch of 50 simulations in `tests/performance/test_batch_simulation.py`.
- [ ] T018 [US2] Run the benchmark test and verify that the batch of 50 simulations completes within 4 hours.

## Phase 5: Polish & Cross-Cutting Concerns

- [ ] T019 Update the `quickstart.md` with the new commands and instructions.
- [ ] T020 Review and update all relevant documentation.
- [ ] T021 Ensure all new code has at least 80% test coverage.
- [ ] T022 Final code cleanup and refactoring.

## Dependencies

- **User Story 1 (US1)** depends on the completion of Phase 2.
- **User Story 2 (US2)** depends on the completion of Phase 3.

## Parallel Execution

- Tasks marked with `[P]` can be executed in parallel.
- Within each user story phase, the implementation tasks can be parallelized to some extent. For example, the refactoring of different modules can be done in parallel.

## Implementation Strategy

The implementation will follow an MVP-first approach. The initial focus will be on optimizing the single simulation run (User Story 1). Once that is achieved, the focus will be shifted to implementing the batch simulation feature (User Story 2).
