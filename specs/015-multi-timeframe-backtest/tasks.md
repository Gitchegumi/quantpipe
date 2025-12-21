# Tasks: Multi-Timeframe Backtesting

**Input**: Design documents from `/specs/015-multi-timeframe-backtest/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create new module structure and foundational files

- [x] T001 Create `src/data_io/timeframe.py` with module docstring and imports
- [x] T002 [P] Create `src/data_io/resample.py` with module docstring and imports
- [x] T003 [P] Create `src/data_io/resample_cache.py` with module docstring and imports
- [x] T004 Create `.time_cache/.gitkeep` and add `.time_cache/` to `.gitignore`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core timeframe parsing that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Implement `Timeframe` dataclass in `src/data_io/timeframe.py`
- [x] T006 Implement `parse_timeframe(tf_str: str) -> Timeframe` in `src/data_io/timeframe.py`
- [x] T007 Implement `validate_timeframe(tf: Timeframe) -> None` in `src/data_io/timeframe.py`
- [x] T008 Add unit tests for timeframe parsing in `tests/unit/test_timeframe.py`

**Checkpoint**: Timeframe parsing ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Run Backtest on Higher Timeframe (Priority: P1) 🎯 MVP

**Goal**: Enable backtesting with `--timeframe 15m` via CLI, with correct OHLCV resampling

**Independent Test**: Run `python -m src.cli.run_backtest --direction LONG --data price_data/processed/eurusd/test --timeframe 15m` and verify backtest completes with 15m bars

### Implementation for User Story 1

- [x] T009 [US1] Implement `resample_ohlcv(df, target_minutes)` core aggregation in `src/data_io/resample.py`
- [x] T010 [US1] Add `bar_complete` column computation in `src/data_io/resample.py`
- [x] T011 [US1] Implement incomplete leading/trailing bar dropping in `src/data_io/resample.py`
- [x] T012 [US1] Add `--timeframe` argument to argparse in `src/cli/run_backtest.py`
- [x] T013 [US1] Parse and validate timeframe in `main()` of `src/cli/run_backtest.py`
- [x] T014 [US1] Pass `timeframe_minutes` to data pipeline in `src/cli/run_backtest.py`
- [x] T015 [US1] Add `timeframe_minutes` parameter to `run_vectorized_backtest()` in `src/backtest/orchestrator.py`
- [x] T016 [US1] Integrate resampling call before indicator computation in `src/backtest/orchestrator.py`
- [x] T017 [US1] Add unit tests for resampling correctness in `tests/unit/test_resample.py`
- [x] T018 [US1] Add integration test for CLI timeframe argument in `tests/integration/test_timeframe_backtest.py`

**Checkpoint**: User can run backtests on any timeframe via CLI - core feature complete

---

## Phase 4: User Story 2 - Configure Timeframe via Config File (Priority: P2)

**Goal**: Allow users to set default timeframe in YAML config file

**Independent Test**: Create config with `timeframe: "1h"` and verify backtest uses hourly bars without CLI flag

### Implementation for User Story 2

- [ ] T019 [US2] Add `timeframe` field to config schema in `src/config/` (if exists) or inline in `run_backtest.py` _(DEFERRED: project uses Pydantic, no YAML config system)_
- [ ] T020 [US2] Implement config file loading for timeframe in `src/cli/run_backtest.py` _(DEFERRED)_
- [ ] T021 [US2] Implement CLI precedence over config in `src/cli/run_backtest.py` _(DEFERRED)_
- [ ] T022 [US2] Add integration test for config-driven timeframe in `tests/integration/test_timeframe_backtest.py` _(DEFERRED)_

**Checkpoint**: Users can configure default timeframe via config file

---

## Phase 5: User Story 3 - Validate Timeframe Performance Improvement (Priority: P3)

**Goal**: Implement caching for resampled data to improve performance on repeated runs

**Independent Test**: Run same backtest twice — second run should show cache hit and faster completion

### Implementation for User Story 3

- [x] T023 [US3] Implement `get_cache_path()` in `src/data_io/resample_cache.py`
- [x] T024 [US3] Implement `load_cached_resample()` in `src/data_io/resample_cache.py`
- [x] T025 [US3] Implement `save_cached_resample()` in `src/data_io/resample_cache.py`
- [x] T026 [US3] Implement `resample_with_cache()` wrapper in `src/data_io/resample_cache.py`
- [x] T027 [US3] Integrate cache into orchestrator resampling flow in `src/backtest/orchestrator.py`
- [x] T028 [US3] Add telemetry logging (resample time, cache hits/misses) in `src/backtest/orchestrator.py`
- [x] T029 [US3] Add unit tests for cache behavior in `tests/unit/test_resample_cache.py`
- [x] T030 [US3] Add incomplete bar warning when threshold exceeded (10%) in `src/backtest/orchestrator.py`

**Checkpoint**: Caching reduces repeated backtest runtime significantly

---

## Phase 6: User Story 4 - Use Arbitrary Integer-Minute Timeframes (Priority: P4)

**Goal**: Accept any positive integer-minute timeframe (e.g., 7m, 90m, 120m)

**Independent Test**: Run `--timeframe 7m` and verify output contains correctly aggregated 7-minute bars

### Implementation for User Story 4

- [ ] T031 [US4] Extend timeframe parser regex to accept arbitrary integers in `src/data_io/timeframe.py`
- [ ] T032 [US4] Add validation for non-standard timeframes (e.g., 7m, 13m, 90m) in `src/data_io/timeframe.py`
- [ ] T033 [US4] Add unit tests for arbitrary timeframes in `tests/unit/test_timeframe.py`
- [ ] T034 [US4] Add integration test for 7m/90m timeframes in `tests/integration/test_timeframe_backtest.py`

**Checkpoint**: Full timeframe flexibility achieved

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, and final validation

- [ ] T035 [P] Update README.md with timeframe usage examples
- [ ] T036 [P] Create `docs/timeframes.md` with detailed documentation
- [ ] T037 Run full test suite to verify no regressions
- [ ] T038 Run quickstart.md validation commands
- [ ] T039 Lint check all new files (ruff, black, pylint)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (P1): Can start after Phase 2
  - US2 (P2): Can start after Phase 2, integrates with US1
  - US3 (P3): Can start after Phase 2, requires US1 resample functions
  - US4 (P4): Can start after Phase 2, extends US1 parser
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

| Story | Depends On               | Can Parallelize With |
| ----- | ------------------------ | -------------------- |
| US1   | Foundational only        | None (MVP)           |
| US2   | US1 (uses timeframe arg) | US3, US4             |
| US3   | US1 (uses resample func) | US2, US4             |
| US4   | US1 (extends parser)     | US2, US3             |

### Parallel Opportunities

**Within Phase 1:**

```bash
# Can run in parallel:
T002: Create src/data_io/resample.py
T003: Create src/data_io/resample_cache.py
```

**Within Phase 7:**

```bash
# Can run in parallel:
T035: Update README.md
T036: Create docs/timeframes.md
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test with `--timeframe 15m`
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → MVP Complete!
3. Add User Story 2 → Test config file → Config support
4. Add User Story 3 → Test caching → Performance optimized
5. Add User Story 4 → Test 7m/90m → Full flexibility

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group using semantic format: `feat(015): Description (T###)`
- Stop at any checkpoint to validate story independently
