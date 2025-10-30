# Tasks: Update 001 Test Suite Alignment

**Branch**: 003-update-001-tests | **Spec**: spec.md | **Plan**: plan.md

## Phase 1: Setup

- [ ] T001 Ensure Poetry environment installed (`poetry install`) at project root
- [ ] T002 Create/verify `pytest.ini` with marker registrations in project root
- [ ] T003 Create `tests/fixtures/` directory structure if absent
- [ ] T004 Add initial deterministic fixture CSV `tests/fixtures/fixture_trend_example.csv`
- [ ] T005 Add initial deterministic fixture CSV `tests/fixtures/fixture_flat_prices.csv`
- [ ] T006 Add initial deterministic fixture CSV `tests/fixtures/fixture_spike_outlier.csv`
- [ ] T007 Add README note for fixtures in `tests/fixtures/README.md`
- [ ] T008 Add seed helper `tests/conftest.py` (verify deterministic seeding) update

## Phase 2: Foundational

- [ ] T009 Refactor existing 001 tests into tier directories: move files into `tests/unit/`, `tests/integration/`, `tests/performance/`
- [ ] T010 Add/remove imports to align with current public interfaces in `src/strategy/` and `src/risk/`
- [ ] T011 [P] Introduce marker decorators to unit test files under `tests/unit/`
- [ ] T012 [P] Introduce marker decorators to integration test files under `tests/integration/`
- [ ] T013 [P] Introduce marker decorators to performance test files under `tests/performance/`
- [ ] T014 Normalize test function names to descriptive pattern (e.g., `test_indicator_ema_warmup_behavior`) across all tiers
- [ ] T015 Add docstrings to shared test utilities in `tests/` clarifying purpose
- [ ] T016 Enforce deterministic seeding in any test using randomness (search and patch)
- [ ] T017 Remove obsolete tests referencing deprecated interfaces (list each in commit body) under `tests/`
- [ ] T018 Consolidate redundant tests into parameterized form (e.g., pytest.mark.parametrize) in unit tier
- [ ] T019 Add risk sizing edge case tests (minimal balance, high volatility) in `tests/unit/test_risk_sizing_edge_cases.py`

## Phase 3: User Story 1 (Validate Core Strategy Behavior) [P1]

Story Goal: Deterministic verification of strategy signal, indicator, and risk behavior.
Independent Test Criteria: Running unit + integration tiers alone validates FR-001..FR-009 for strategy correctness.

- [ ] T020 [US1] Add indicator tests for EMA warm-up and ATR calculation in `tests/unit/test_indicators_core.py`
- [ ] T021 [US1] Add signal generation tests for entry/exit in `tests/integration/test_strategy_signals.py`
- [ ] T022 [US1] Add test ensuring long and short criteria (if applicable) produce expected number of signals `tests/integration/test_strategy_signal_counts.py`
- [ ] T023 [P] [US1] Add risk sizing normal case test `tests/unit/test_risk_sizing_normal.py`
- [ ] T024 [P] [US1] Add risk sizing high volatility adjustment test `tests/unit/test_risk_sizing_volatility.py`
- [ ] T025 [US1] Add performance tier scenario (longer backtest slice) `tests/performance/test_strategy_backtest_perf.py`
- [ ] T026 [US1] Add flakiness loop script `tests/performance/test_flakiness_smoke.py` (ensures stable results)
- [ ] T027 [US1] Validate naming/docstrings across US1 files
- [ ] T028 [US1] Map FR-001..FR-007 to explicit test assertions (inline comments)

## Phase 4: User Story 2 (Remove Obsolete / Redundant Tests) [P2]

Story Goal: Prune noise and redundancy while maintaining coverage.
Independent Test Criteria: Suite runs with reduced count and no missing coverage (SC-002).

- [ ] T029 [US2] Inventory existing tests referencing removed interfaces (create list in scratch) `tests/_inventory_removed.txt`
- [ ] T030 [US2] Remove each obsolete test file and update commit body notes
- [ ] T031 [P] [US2] Convert overlapping indicator tests into single parameterized test file `tests/unit/test_indicators_consolidated.py`
- [ ] T032 [US2] Replace duplicated risk sizing assertions with parameterized cases `tests/unit/test_risk_sizing_parametrized.py`
- [ ] T033 [US2] Confirm net test count reduction ≤30% unless justified (record final count in `specs/003-update-001-tests/analysis-report.md`)
- [ ] T034 [US2] Add justification comments for each removal inside commit message draft file `specs/003-update-001-tests/removal-notes.md`

## Phase 5: User Story 3 (Introduce Deterministic Fixtures) [P3]

Story Goal: Ensure fast, reproducible runs using curated fixtures.
Independent Test Criteria: Unit tier completes <5s with fixtures only; integration deterministic.

- [ ] T035 [US3] Finalize fixture datasets (ensure coverage of flat, spike, trend) `tests/fixtures/`
- [ ] T036 [US3] Add fixture manifest `tests/fixtures/manifest.yaml`
- [ ] T037 [US3] Add fixture validation test `tests/unit/test_fixture_validation.py`
- [ ] T038 [US3] Replace any lingering large dataset references with small fixtures
- [ ] T039 [P] [US3] Add test ensuring reproducible indicator values across three sequential runs `tests/unit/test_indicator_repeatability.py`
- [ ] T040 [US3] Add runtime measurement assertion for unit tier (<5s) `tests/unit/test_runtime_threshold.py`
- [ ] T041 [US3] Add integration runtime assertion (<30s) `tests/integration/test_integration_runtime.py`
- [ ] T042 [US3] Add performance runtime assertion (<120s) `tests/performance/test_performance_runtime.py`

## Phase 6: Polish & Cross-Cutting

- [ ] T043 Run Black, Ruff, Pylint and resolve issues (quality gates)
- [ ] T044 Add/update docstrings for new test modules (PEP 257 compliance)
- [ ] T045 Ensure lazy logging formatting in any test or helper using logging
- [ ] T046 Add summary of removed tests & final counts to `specs/003-update-001-tests/analysis-report.md`
- [ ] T047 Create commit message draft for final milestone `specs/003-update-001-tests/commit-draft.txt`
- [ ] T048 Validate all success criteria (SC-001..SC-007) via manual checklist `specs/003-update-001-tests/checklists/validation.md`
- [ ] T049 Add README update referencing new test tiering (root `README.md` tests section)
- [ ] T050 Final pass ensure no deprecated imports remain (`grep` or search) summary in `analysis-report.md`

## Dependencies & Ordering

User Story Order: US1 → US2 → US3 (priority-based). US1 provides baseline deterministic correctness; US2 reduces noise; US3 optimizes fixtures and timing.

Key Dependencies:
- T009 precedes all US1 tasks (directory realignment).
- T011–T013 marker introduction precedes runtime assertion tasks (T040–T042).
- Fixture creation (T004–T006) precedes indicator/signal tests (T020–T022).

## Parallel Execution Examples

- During Phase 2: T011, T012, T013 can run in parallel (distinct files).
- During US1: T023 and T024 parallel (independent risk sizing cases).
- During US3: T039, T040, T041 can start after T035 fixtures finalized.

## Implementation Strategy

MVP Scope: Complete Phase 1 + Phase 2 + US1 (Phases 3–5) to achieve validated core strategy behavior and tiering. Subsequent phases (US2, US3) optimize maintenance and performance.

Exit Criteria MVP: FR-001..FR-009 covered, SC-001..SC-004 satisfied, tier markers operational.

Full Completion: All tasks T001–T050 checked; SC-001..SC-007 satisfied; analysis-report.md contains final metrics.

## Independent Test Criteria Summary

- US1: Run unit+integration tiers to verify core signals, indicators, and risk sizing.
- US2: Run full suite; confirm reduced count & unchanged coverage metrics.
- US3: Time unit, integration, performance tiers; confirm thresholds and determinism.

## Task Counts

- Setup: 8
- Foundational: 11
- US1: 9
- US2: 6
- US3: 8
- Polish: 8
- Total: 50
