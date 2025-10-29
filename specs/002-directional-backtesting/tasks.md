# Implementation Tasks: Directional Backtesting System

**Feature**: 002-directional-backtesting  
**Branch**: `002-directional-backtesting`  
**Date**: 2025-10-29  
**Input**: Implementation plan from plan.md, specification from spec.md

## Overview

This document breaks down the implementation of the directional backtesting system into executable tasks organized by user story. Each user story represents an independently testable increment of functionality.

**Total Estimated Time**: 20 hours (2.5 days)

## Task Organization

Tasks are organized into phases:

- **Phase 1**: Setup - Project initialization and environment setup
- **Phase 2**: Foundational - Blocking prerequisites that all user stories depend on
- **Phase 3-7**: User Stories (P1-P5) - Independent, testable feature increments
- **Phase 8**: Polish & Cross-Cutting Concerns

## Dependencies

### User Story Completion Order

The following dependency graph shows the recommended order for implementing user stories:

```text
Setup (Phase 1)
    ↓
Foundational (Phase 2: Core Models + Orchestrator)
    ↓
    ├─→ US1 (LONG-only) ─────────┐
    ├─→ US2 (SHORT-only) ────────┼─→ US3 (BOTH) ─┐
    ├─→ US4 (JSON output) ───────┤               ├─→ Polish (Phase 8)
    └─→ US5 (Dry-run) ───────────┘               ┘

Independent Stories: US1, US2, US4, US5 (can be implemented in parallel after Phase 2)
Dependent Stories: US3 requires US1 and US2 concepts
```

### Blocking Dependencies

- **Phase 2 BLOCKS ALL**: User stories cannot begin until core models and orchestrator are complete
- **US3 depends on US1 + US2**: BOTH mode merges LONG and SHORT logic
- All other user stories are independent and can be parallelized

## Parallel Execution Opportunities

### After Phase 2 (Foundational)

These tasks can be executed in parallel:

**Track 1 - LONG Mode (US1)**:

- T009, T010, T011 (LONG signal generation + execution + tests)

**Track 2 - SHORT Mode (US2)**:

- T012, T013, T014 (SHORT signal generation + execution + tests)

**Track 3 - Output Format (US4)**:

- T018, T019, T020, T021 (JSON formatters + schema validation)

**Track 4 - Dry-Run (US5)**:

- T022, T023, T024 (Dry-run logic + tests)

### After US1 + US2 Complete

**Track 5 - BOTH Mode (US3)**:

- T015, T016, T017 (Conflict resolution + three-tier metrics)

## Implementation Strategy

**MVP Scope**: User Story 1 (US1) only

- Delivers core LONG-only backtesting functionality
- Provides immediate value for strategy validation
- Establishes foundation for other directions

**Incremental Delivery**:

1. **Sprint 1**: Phase 1 + Phase 2 + US1 → Working LONG-only backtest
2. **Sprint 2**: US2 + US4 → Add SHORT mode + JSON output
3. **Sprint 3**: US3 + US5 → Complete with BOTH mode + dry-run
4. **Sprint 4**: Phase 8 → Polish and performance optimization

---

## Phase 1: Setup

**Goal**: Initialize project structure and verify environment

**Prerequisites**: Python 3.11+, Poetry installed, repository cloned

**Tasks**:

- [ ] T001 Verify Python 3.11+ installed: `python --version`
- [ ] T002 Verify Poetry configured: `poetry --version`
- [ ] T003 Install dependencies: `poetry install`
- [ ] T004 Run existing tests to verify baseline: `poetry run pytest`
- [ ] T005 Review existing code: `src/cli/run_long_backtest.py`, `src/backtest/execution.py`, `src/strategy/trend_pullback/signal_generator.py`
- [ ] T006 Review specification: `specs/002-directional-backtesting/spec.md`
- [ ] T007 Review planning documents: `plan.md`, `research.md`, `data-model.md`, `quickstart.md`

**Independent Test**: Environment ready for development (all dependencies installed, baseline tests pass)

---

## Phase 2: Foundational

**Goal**: Create core data models and orchestration infrastructure that all user stories depend on

**Prerequisites**: Phase 1 complete

**Blocking Rationale**: All user stories require these models and the orchestrator to function

**Tasks**:

### Core Data Models (src/models/core.py)

- [ ] T008 [P] Add DirectionMode enum (LONG, SHORT, BOTH) to src/models/core.py
- [ ] T009 [P] Add OutputFormat enum (TEXT, JSON) to src/models/core.py
- [ ] T010 [P] Add ConflictEvent Pydantic model (timestamp_utc, pair, resolution) to src/models/core.py
- [ ] T011 [P] Add DirectionalMetrics Pydantic model (long_only, short_only, combined) to src/models/core.py
- [ ] T012 [P] Add BacktestResult Pydantic model (run_metadata, metrics, signals, executions, conflicts) to src/models/core.py

### Orchestrator Infrastructure (src/backtest/orchestrator.py)

- [ ] T013 Create BacktestOrchestrator class skeleton in src/backtest/orchestrator.py
- [ ] T014 Implement run_backtest method signature with DirectionMode routing logic in src/backtest/orchestrator.py
- [ ] T015 Implement merge_signals function for conflict detection (timestamp-based) in src/backtest/orchestrator.py
- [ ] T016 Add logging calls for signal generation progress (lazy % formatting) in src/backtest/orchestrator.py

### Metrics Infrastructure (src/backtest/metrics.py)

- [ ] T017 [P] Create calculate_metrics function (aggregate executions → MetricsSummary) in src/backtest/metrics.py
- [ ] T018 [P] Create calculate_directional_metrics function (three-tier: long/short/combined) in src/backtest/metrics.py

### Output Formatters (src/io/formatters.py)

- [ ] T019 [P] Create generate*output_filename function (`backtest*{direction}_{YYYYMMDD}_{HHMMSS}.{ext}`) in src/io/formatters.py
- [ ] T020 [P] Create format_text_output function skeleton (human-readable result formatting) in src/io/formatters.py

### Unit Tests

- [ ] T021 [P] Create tests/unit/test_models.py with tests for new Pydantic models (DirectionMode, OutputFormat, ConflictEvent, DirectionalMetrics, BacktestResult)
- [ ] T022 [P] Create tests/unit/test_backtest_orchestrator.py with orchestrator skeleton tests
- [ ] T023 [P] Create tests/unit/test_metrics_aggregation.py with metrics calculation tests
- [ ] T024 [P] Create tests/unit/test_output_formatters.py with filename generation tests

**Independent Test**:

- All new models validate correctly (type hints, required fields)
- Orchestrator instantiates without errors
- Metrics functions handle empty input gracefully
- Filename generation produces correct format
- All unit tests pass: `poetry run pytest tests/unit/`

---

## Phase 3: User Story 1 - Execute LONG-Only Backtest (Priority: P1)

**Goal**: Implement LONG-only backtesting mode (MVP functionality)

**Prerequisites**: Phase 2 complete

**Why Independent**: Uses only long signal generation; no dependencies on SHORT or BOTH logic

**User Story Reference**: spec.md lines 25-41 (User Story 1)

**Tasks**:

### LONG Implementation

- [ ] T025 [US1] Implement LONG direction routing in BacktestOrchestrator.run_backtest (call generate_long_signals) in src/backtest/orchestrator.py
- [ ] T026 [US1] Implement execution loop for LONG signals (call simulate_execution for each signal) in src/backtest/orchestrator.py
- [ ] T027 [US1] Integrate calculate_directional_metrics for LONG mode (combined = long_only) in src/backtest/orchestrator.py
- [ ] T028 [US1] Implement format_text_output for LONG results (metrics, run metadata, statistics) in src/io/formatters.py
- [ ] T029 [US1] Update CLI argument parser to accept --direction LONG in src/cli/run_backtest.py
- [ ] T030 [US1] Wire orchestrator call for LONG mode in CLI main function in src/cli/run_backtest.py
- [ ] T031 [US1] Add output file writing logic (text format) in src/cli/run_backtest.py
- [ ] T032 [US1] Add logging calls for LONG mode progress (signal count, execution progress) in src/cli/run_backtest.py

### Testing

- [ ] T033 [US1] Create tests/integration/test_directional_backtesting.py with LONG mode end-to-end test
- [ ] T034 [US1] Add test for LONG mode with fixture data (verify signal generation, execution, metrics) in tests/integration/test_directional_backtesting.py
- [ ] T035 [US1] Add test for LONG mode output file creation and content validation in tests/integration/test_directional_backtesting.py

**Independent Test**:
Run `poetry run python -m src.cli.run_backtest --direction LONG --data price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv` → generates LONG signals, executes trades, outputs text file with metrics (win_rate, avg_r, drawdown). Verify output file exists and contains valid metrics.

**Acceptance Criteria**:

- ✅ SC-001: LONG backtest completes within 30 seconds for 100K candles
- ✅ SC-006: 95%+ success rate on valid input
- ✅ SC-007: Deterministic results (reproducibility_hash matches)
- ✅ SC-008: Text output understandable without documentation

---

## Phase 4: User Story 2 - Execute SHORT-Only Backtest (Priority: P2)

**Goal**: Implement SHORT-only backtesting mode

**Prerequisites**: Phase 2 complete (can run in parallel with US1)

**Why Independent**: Uses only short signal generation; mirrors LONG implementation pattern

**User Story Reference**: spec.md lines 45-59 (User Story 2)

**Tasks**:

### SHORT Implementation

- [ ] T036 [P] [US2] Implement SHORT direction routing in BacktestOrchestrator.run_backtest (call generate_short_signals) in src/backtest/orchestrator.py
- [ ] T037 [P] [US2] Implement execution loop for SHORT signals (call simulate_execution for each signal) in src/backtest/orchestrator.py
- [ ] T038 [P] [US2] Integrate calculate_directional_metrics for SHORT mode (combined = short_only) in src/backtest/orchestrator.py
- [ ] T039 [P] [US2] Enhance format_text_output to handle SHORT results (same structure as LONG) in src/io/formatters.py
- [ ] T040 [P] [US2] Update CLI argument parser to accept --direction SHORT in src/cli/run_backtest.py
- [ ] T041 [P] [US2] Wire orchestrator call for SHORT mode in CLI main function in src/cli/run_backtest.py

### SHORT Testing

- [ ] T042 [P] [US2] Add SHORT mode end-to-end test in tests/integration/test_directional_backtesting.py
- [ ] T043 [P] [US2] Add test for SHORT mode with fixture data (verify signal generation, execution, metrics) in tests/integration/test_directional_backtesting.py
- [ ] T044 [P] [US2] Add test for SHORT mode output file creation and content validation in tests/integration/test_directional_backtesting.py

**Independent Test**:
Run `poetry run python -m src.cli.run_backtest --direction SHORT --data price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv` → generates SHORT signals, executes trades, outputs text file with metrics matching LONG structure. Verify SHORT signals are generated and LONG signals are not.

**Acceptance Criteria**:

- ✅ SC-002: SHORT backtest completes with metrics matching LONG structure
- ✅ SC-006: 95%+ success rate on valid input
- ✅ SC-007: Deterministic results

---

## Phase 5: User Story 3 - Execute BOTH Directions Backtest (Priority: P3)

**Goal**: Implement combined LONG+SHORT mode with conflict resolution

**Prerequisites**: Phase 2 complete, US1 and US2 concepts understood (can begin after Phase 2 but benefits from US1/US2 completion)

**Why Dependent**: Merges LONG and SHORT signal logic; requires conflict resolution

**User Story Reference**: spec.md lines 63-79 (User Story 3)

**Tasks**:

### Implementation

- [ ] T045 [US3] Implement BOTH direction routing (call both generate_long_signals and generate_short_signals) in src/backtest/orchestrator.py
- [ ] T046 [US3] Enhance merge_signals function with conflict resolution logic (identical timestamp → reject both, timestamp-first wins otherwise) in src/backtest/orchestrator.py
- [ ] T047 [US3] Add ConflictEvent logging for rejected signals (timestamp + pair) in src/backtest/orchestrator.py
- [ ] T048 [US3] Implement three-tier metrics calculation for BOTH mode (long_only, short_only, combined) in src/backtest/metrics.py
- [ ] T049 [US3] Enhance format_text_output to display directional breakdowns for BOTH mode in src/io/formatters.py
- [ ] T050 [US3] Update CLI argument parser to accept --direction BOTH in src/cli/run_backtest.py
- [ ] T051 [US3] Wire orchestrator call for BOTH mode in CLI main function in src/cli/run_backtest.py

### BOTH Testing

- [ ] T052 [US3] Add BOTH mode end-to-end test with conflict scenarios in tests/integration/test_directional_backtesting.py
- [ ] T053 [US3] Add test for conflict detection (simultaneous opposing signals → both rejected) in tests/unit/test_backtest_orchestrator.py
- [ ] T054 [US3] Add test for three-tier metrics calculation (verify long/short/combined breakdowns) in tests/unit/test_metrics_aggregation.py
- [ ] T055 [US3] Add test for conflict logging (verify timestamp + pair logged) in tests/unit/test_backtest_orchestrator.py
- [ ] T056 [US3] Add test for timestamp-first-wins logic (different timestamps → earlier executes, later suppressed) in tests/unit/test_backtest_orchestrator.py

**Independent Test**:
Run `poetry run python -m src.cli.run_backtest --direction BOTH --data price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv` → generates both LONG and SHORT signals, applies conflict resolution, outputs text file with three-tier metrics (long_only, short_only, combined). Verify conflicts are logged and both signals rejected when timestamps identical.

**Acceptance Criteria**:

- ✅ SC-003: BOTH mode outputs combined metrics with directional breakdowns
- ✅ SC-010: Conflict resolution prevents 100% of simultaneous opposing positions
- ✅ SC-007: Deterministic results

---

## Phase 6: User Story 4 - Output Results in JSON Format (Priority: P4)

**Goal**: Implement JSON output format for programmatic consumption

**Prerequisites**: Phase 2 complete (can run in parallel with US1/US2/US5)

**Why Independent**: Output formatting is orthogonal to direction logic

**User Story Reference**: spec.md lines 83-97 (User Story 4)

**Tasks**:

### JSON Implementation

- [ ] T056 [P] [US4] Create format_json_output function in src/io/formatters.py
- [ ] T057 [P] [US4] Implement JSON serialization for BacktestResult (handle NaN/Infinity as null) in src/io/formatters.py
- [ ] T058 [P] [US4] Implement datetime serialization (ISO 8601 UTC) in src/io/formatters.py
- [ ] T059 [P] [US4] Add JSON schema validation against contracts/json-output-schema.json in src/io/formatters.py
- [ ] T060 [P] [US4] Update CLI argument parser to accept --output-format {text,json} in src/cli/run_backtest.py
- [ ] T061 [P] [US4] Wire format_json_output call for JSON mode in CLI main function in src/cli/run_backtest.py
- [ ] T062 [P] [US4] Update filename generation for .json extension in src/io/formatters.py

### JSON Testing

- [ ] T063 [P] [US4] Add JSON output test (verify valid JSON structure) in tests/unit/test_output_formatters.py
- [ ] T064 [P] [US4] Add JSON schema validation test (validate against contracts/json-output-schema.json) in tests/unit/test_output_formatters.py
- [ ] T065 [P] [US4] Add datetime serialization test (verify ISO 8601 UTC format per FR-023) in tests/unit/test_output_formatters.py
- [ ] T066 [P] [US4] Add NaN/Infinity handling test (verify null serialization per FR-024) in tests/unit/test_output_formatters.py
- [ ] T067 [P] [US4] Add integration test for JSON output with all direction modes in tests/integration/test_directional_backtesting.py

**Independent Test**:
Run `poetry run python -m src.cli.run_backtest --direction LONG --data price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv --output-format json` → outputs valid JSON file. Parse JSON with external tool (e.g., `jq`), validate against schema, verify all fields conform to spec (ISO 8601 timestamps, null for NaN).

**Acceptance Criteria**:

- ✅ SC-004: JSON output validates against defined schema with zero errors
- ✅ SC-009: JSON output size ≤10MB for 100K candles

---

## Phase 7: User Story 5 - Generate Signals Without Execution (Dry-Run Mode) (Priority: P5)

**Goal**: Implement dry-run mode for signal validation without execution

**Prerequisites**: Phase 2 complete (can run in parallel with US1/US2/US4)

**Why Independent**: Dry-run mode is a mode flag that affects orchestrator behavior orthogonally

**User Story Reference**: spec.md lines 101-115 (User Story 5)

**Tasks**:

### dry_run Implementation

- [ ] T068 [P] [US5] Add dry_run parameter to BacktestOrchestrator.run_backtest signature in src/backtest/orchestrator.py
- [ ] T069 [P] [US5] Implement dry-run logic (skip simulate_execution calls, return signals only) in src/backtest/orchestrator.py
- [ ] T070 [P] [US5] Enhance format_text_output to handle dry-run results (signal list only) in src/io/formatters.py
- [ ] T071 [P] [US5] Enhance format_json_output to handle dry-run results (signals array, empty executions) in src/io/formatters.py
- [ ] T072 [P] [US5] Update CLI argument parser to accept --dry-run flag in src/cli/run_backtest.py
- [ ] T073 [P] [US5] Wire dry_run flag to orchestrator call in CLI main function in src/cli/run_backtest.py

### dry_run Testing

- [ ] T074 [P] [US5] Add dry-run mode test (verify no simulate_execution calls) in tests/unit/test_backtest_orchestrator.py
- [ ] T075 [P] [US5] Add dry-run output test (verify signal fields: timestamp, pair, direction, entry_price, stop_price) in tests/unit/test_output_formatters.py
- [ ] T076 [P] [US5] Add integration test for dry-run with JSON output in tests/integration/test_directional_backtesting.py
- [ ] T077 [P] [US5] Add performance test for dry-run mode (verify ≤10s for 100K candles) in tests/performance/test_performance.py

**Independent Test**:
Run `poetry run python -m src.cli.run_backtest --direction LONG --data price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv --dry-run` → generates signals without execution, outputs signal list within 10 seconds. Verify executions array is empty and signals array contains essential fields only.

**Acceptance Criteria**:

- ✅ SC-005: Dry-run completes within 10 seconds for 100K candles
- ✅ SC-007: Deterministic results

---

## Phase 8: Polish & Cross-Cutting Concerns

**Goal**: Ensure code quality, documentation, and performance standards

**Prerequisites**: All user stories (US1-US5) complete

**Tasks**:

### Code Quality

- [ ] T078 Format code with Black: `poetry run black src/ tests/` in project root
- [ ] T079 Run Ruff linter and fix all errors (zero errors required): `poetry run ruff check src/ tests/` in project root
- [ ] T080 Run Pylint and achieve ≥8.0/10 score: `poetry run pylint src/backtest/ src/io/ src/cli/run_backtest.py --score=yes` in project root
- [ ] T081 Fix all W1203 logging warnings (convert f-strings to lazy % formatting) in all modified files
- [ ] T082 Add type hints to all function signatures and class attributes in src/backtest/orchestrator.py, src/backtest/metrics.py, src/io/formatters.py
- [ ] T083 Run mypy type checker: `poetry run mypy src/` in project root

### Documentation

- [ ] T084 [P] Add PEP 257 docstrings to all modules in src/backtest/orchestrator.py, src/backtest/metrics.py, src/io/formatters.py
- [ ] T085 [P] Add PEP 257 docstrings to all classes in src/backtest/orchestrator.py, src/backtest/metrics.py, src/io/formatters.py
- [ ] T086 [P] Add PEP 257 docstrings to all functions (include examples) in src/backtest/orchestrator.py, src/backtest/metrics.py, src/io/formatters.py
- [ ] T087 [P] Update README.md with directional backtesting usage examples in project root README.md

### Performance Validation

- [ ] T088 Benchmark LONG mode with 100K candles (target: ≤30s): `time poetry run python -m src.cli.run_backtest --direction LONG --data price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv` in project root
- [ ] T089 Benchmark SHORT mode with 100K candles (target: ≤30s): `time poetry run python -m src.cli.run_backtest --direction SHORT --data price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv` in project root
- [ ] T090 Benchmark dry-run mode with 100K candles (target: ≤10s): `time poetry run python -m src.cli.run_backtest --direction LONG --data price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv --dry-run` in project root
- [ ] T091 Verify JSON output size for BOTH mode with 100K candles (target: ≤10MB): check file size of results/backtest*both*\*.json in project root

### Error Handling & Edge Cases

- [ ] T092 [P] Add error handling for missing data file (exit code 1, clear error message, verify exit code 1) in src/cli/run_backtest.py
- [ ] T093 [P] Add error handling for invalid direction parameter (argument parser validation) in src/cli/run_backtest.py
- [ ] T094 [P] Add error handling for incomplete candle data in execution in src/backtest/orchestrator.py
- [ ] T095 [P] Add test for zero signals scenario (backtest completes, metrics reflect insufficient data) in tests/integration/test_directional_backtesting.py
- [ ] T096 [P] Add test for sequential backtests with same output directory (verify no overwrites due to timestamped filenames) in tests/integration/test_directional_backtesting.py

### Final Validation

- [ ] T097 Run all unit tests: `poetry run pytest tests/unit/` and verify 100% pass in project root
- [ ] T098 Run all integration tests: `poetry run pytest tests/integration/` and verify 100% pass in project root
- [ ] T099 Run constitution compliance check (verify all gates pass) using specs/002-directional-backtesting/plan.md
- [ ] T100 Manual smoke test: Run all direction modes (LONG, SHORT, BOTH) with both output formats (text, json) and dry-run flag in project root

**Independent Test**:
All tests pass, code quality checks pass, performance targets met, manual smoke tests successful. Feature ready for production use.

**Acceptance Criteria**:

- ✅ All SC-001 through SC-010 success criteria met
- ✅ Constitution Principle VIII-X compliance (PEP 8, docstrings, type hints, Black/Ruff/Pylint)
- ✅ Zero linting errors, Pylint score ≥8.0/10
- ✅ All performance targets met

---

## Summary

**Total Tasks**: 101  
**Task Distribution by User Story**:

- Phase 1 (Setup): 7 tasks
- Phase 2 (Foundational): 17 tasks (BLOCKS all user stories)
- Phase 3 (US1 - LONG): 11 tasks
- Phase 4 (US2 - SHORT): 9 tasks
- Phase 5 (US3 - BOTH): 12 tasks (includes new T056 for timestamp-first-wins test)
- Phase 6 (US4 - JSON): 12 tasks
- Phase 7 (US5 - Dry-Run): 10 tasks
- Phase 8 (Polish): 23 tasks

**Parallel Opportunities**:

- After Phase 2: US1, US2, US4, US5 can be implemented concurrently (4 parallel tracks)
- Phase 8 tasks: Documentation (T084-T087), error handling (T092-T096) can be parallelized

**MVP Scope** (Minimum Viable Product):

- Phase 1 + Phase 2 + Phase 3 (US1) = **35 tasks** → Delivers working LONG-only backtest
- Estimated time: **8 hours** (40% of total effort)

**Suggested Next Command**: Begin implementation with Phase 1 setup tasks (T001-T007)

## Format Validation

✅ **ALL tasks follow checklist format**:

- Checkbox prefix: `- [ ]`
- Task ID: Sequential T001-T101
- [P] marker: 34 tasks marked as parallelizable (different files, no dependencies)
- [Story] label: User story phases (US1-US5) properly labeled
- File paths: All implementation tasks include specific file paths
- Descriptions: Clear, actionable descriptions with exact requirements

**Ready for execution** ✓

**Note on SC-006 (95% success rate)**: This success criterion requires post-deployment monitoring and cannot be validated in pre-release testing. Recommend tracking via production metrics dashboard after initial deployment.
