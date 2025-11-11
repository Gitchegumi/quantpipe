# Feature 010 – Scan & Simulation Performance Optimization Tasks

Generated per speckit tasks prompt. Canonical stack: Python 3.11, Polars + Parquet (zstd), NumPy, pydantic, rich, pytest. Pandas only for legacy verification. All tasks follow required checklist format.

## Phase 1 – Setup

- [ ] T001 Initialize Parquet ingestion directory structure in `src/io/ingestion`
- [ ] T002 Create Poetry entry for Polars (verify version) in `pyproject.toml`
- [ ] T003 Add performance targets module `src/backtest/performance_targets.py`
- [ ] T004 Create empty manifest model file `src/io/ingestion/manifest.py`
- [ ] T005 Create placeholder conversion module `src/io/ingestion/parquet_convert.py`
- [ ] T006 Create placeholder loader module `src/io/ingestion/load.py`
- [ ] T007 Add performance report model `src/models/performance_report.py`
- [ ] T008 Add deterministic env capture utility `src/backtest/env_info.py`
- [ ] T009 Add memory sampler utility `src/backtest/memory_sampler.py`
- [ ] T010 Add progress dispatcher scaffold `src/backtest/progress.py`

## Phase 2 – Foundational

- [ ] T011 Implement Manifest pydantic model in `src/io/ingestion/manifest.py`
- [ ] T012 Implement CSV→Parquet conversion with zstd & checksum in `src/io/ingestion/parquet_convert.py`
- [ ] T013 Implement Parquet LazyFrame loader & schema fingerprint in `src/io/ingestion/load.py`
- [ ] T014 Implement performance targets constants in `src/backtest/performance_targets.py`
- [ ] T015 Implement env metadata capture in `src/backtest/env_info.py`
- [ ] T016 Implement memory sampler (tracemalloc + psutil fallback) in `src/backtest/memory_sampler.py`
- [ ] T017 Implement progress dispatcher stride + time logic in `src/backtest/progress.py`
- [ ] T018 Add dedupe utility `src/backtest/dedupe.py`
- [ ] T019 Add columnar extraction helper `src/backtest/arrays.py`
- [ ] T020 Add baseline equivalence fixture ingestion helper `tests/fixtures/baseline_equivalence.py`

## Phase 3 – User Story 1 (Accelerated Market Scan) P1

- [ ] T021 [US1] Implement batch scan core `src/backtest/batch_scan.py`
- [ ] T022 [P] [US1] Implement indicator input extractor `src/preprocess/indicator_inputs.py`
- [ ] T023 [US1] Integrate dedupe + extraction + progress into scan pipeline `src/backtest/batch_scan.py`
- [ ] T024 [US1] Add scan equivalence test (timestamps & counts) `tests/integration/test_scan_equivalence.py`
- [ ] T025 [US1] Add performance benchmark test (duration assertion) `tests/performance/test_scan_perf.py`  # Removed [P]; depends on stable scan core
- [ ] T026 [US1] Add memory usage benchmark (peak reduced ≥30%) `tests/performance/test_scan_memory.py`  # Removed [P]; depends on scan implementation
- [ ] T027 [US1] Add progress cadence test (interval ≤120s) `tests/unit/test_progress_scan.py`
- [ ] T028 [US1] Add duplicate timestamp handling test `tests/unit/test_dedupe.py`

## Phase 4 – User Story 2 (Strategy-Owned Indicators) P2

- [ ] T029 [US2] Enforce indicator declaration location (strategy only) `src/strategy/indicator_registry.py`
- [ ] T030 [P] [US2] Implement indicator ownership audit test `tests/contract/test_indicator_ownership.py`
- [ ] T031 [US2] Remove any legacy indicator mutation from `src/backtest/` modules
- [ ] T032 [US2] Add zero-indicator strategy test `tests/unit/test_zero_indicator_strategy.py`
- [ ] T033 [US2] Add warm-up NaN exclusion test `tests/unit/test_indicator_warmup.py`

## Phase 5 – User Story 3 (Efficient Trade Simulation) P3

- [ ] T034 [US3] Implement batch simulation core `src/backtest/batch_simulation.py`
- [ ] T035 [US3] Implement vectorized SL/TP evaluation helper `src/backtest/sim_eval.py`  # Removed [P]; requires batch simulation scaffold
- [ ] T036 [US3] Implement position state arrays (entry/exit indices) `src/backtest/batch_simulation.py`
- [ ] T037 [US3] Add simulation equivalence test (trade count, PnL tolerance) `tests/integration/test_sim_equivalence.py`
- [ ] T038 [US3] Add simulation performance benchmark test `tests/performance/test_sim_perf.py`  # Removed [P]; after core simulation stable
- [ ] T039 [US3] Add memory usage benchmark test `tests/performance/test_sim_memory.py`
- [ ] T040 [US3] Add deterministic multi-run test (±1% timing variance) `tests/integration/test_deterministic_runs.py`

## Phase 6 – Polish & Cross-Cutting

- [ ] T041 Consolidate PerformanceReport generation `src/backtest/report.py`
- [ ] T042 Integrate report emission into CLI backtest `src/cli/run_backtest.py`
- [ ] T043 Add JSON summary writer `src/backtest/report_writer.py`
- [ ] T044 Add documentation updates for mandatory Polars in `specs/010-scan-sim-perf/quickstart.md`
- [ ] T045 Add performance rationale section in `docs/performance.md`
- [ ] T046 Add CI script updates for new benchmarks `scripts/ci/aggregate_benchmarks.py`
- [ ] T047 Add logging format audits (lazy format enforcement) `scripts/ci/check_logging_format.py`
- [ ] T048 Add progress overhead test (<1%) `tests/performance/test_progress_overhead.py`
- [ ] T049 Add manifest provenance test `tests/unit/test_manifest_provenance.py`
- [ ] T050 Add README performance section update `README.md`
- [ ] T051 Run lint & formatting (Black/Ruff/Pylint/Markdownlint) – meta task
- [ ] T052 Generate final equivalence & performance summary `results/benchmark_summary.json`
- [ ] T053 Optional numba experiment script `scripts/experiment_numba_sim.py`
- [ ] T054 Optional Polars streaming prototype `src/backtest/streaming_scan.py`

## Phase 7 – Coverage & Determinism Extensions

- [ ] T055 [US1] Add scan determinism test `tests/integration/test_scan_deterministic.py` (repeat scan x3; identical signals & ≤1% timing variance)
- [ ] T056 Add memory abort scenario test `tests/unit/test_memory_abort.py` (simulate low available memory; expect structured abort log) [FR-009]
- [ ] T057 [US2] Add indicator mapping report test `tests/contract/test_indicator_mapping_report.py` (PerformanceReport indicator_names[] matches strategy registry) [FR-013]
- [ ] T058 Add allocation profiling harness `scripts/ci/profile_scan_allocations.py` (captures baseline & optimized allocation counts) [FR-002, FR-014]
- [ ] T059 [US1] Add allocation reduction assertion test `tests/performance/test_scan_allocations.py` (≥70% reduction vs baseline) [FR-014]
- [ ] T060 Add manifest provenance validation test `tests/unit/test_manifest_in_report.py` (checksum/path match manifest) [FR-012]
- [ ] T061 Extend performance report generation with new fields `src/backtest/report.py` (progress_overhead_pct, indicator_names[], allocation metrics) [FR-007, FR-011–FR-014]
- [ ] T062 [US1] Add progress final emission test `tests/unit/test_progress_final.py` (mandatory 100% emission + overhead ≤1%) [FR-011]
- [ ] T063 Add indicator mapping generation in report writer `src/backtest/report_writer.py` [FR-013]
- [ ] T064 Add structured abort logging utility `src/backtest/abort.py` (emits memory abort record) [FR-009]
- [ ] T065 Add allocation baseline capture script `scripts/capture_allocation_baseline.py` (unoptimized scan) [FR-002]
- [ ] T066 Gate numba experiment script activation post-baseline (update `scripts/experiment_numba_sim.py`) [T053 dependency]
- [ ] T067 Mark streaming prototype experimental or relocate to future feature (update documentation comment in `src/backtest/streaming_scan.py`) [Scope]
- [ ] T068 Extend logging format audit for new modules `scripts/ci/check_logging_format.py` (include progress, memory, abort, report) [Principle X]

## Dependencies (User Story Order)

US1 → US2 (indicator ownership audit depends on working scan path) → US3 (simulation depends on signals). Polish depends on all stories.

## Parallel Execution Examples

- T022, T025, T026 can run parallel with T021 once batch_scan scaffold exists.
- T030 can run parallel with T029 after registry stub present.
- T035 & T038 can run parallel with initial simulation scaffold T034.

## Independent Test Criteria

- US1: `test_scan_equivalence.py` + perf/memory + progress & dedupe tests.
- US2: Ownership audit + zero-indicator + warm-up NaN tests.
- US3: Simulation equivalence + performance + memory + deterministic multi-run tests.

## MVP Scope Suggestion

Implement Phase 1–2 plus US1 (Tasks T001–T028). Provides accelerated scan with equivalence & reporting foundation.

## Format Validation

All tasks use: `- [ ] T### [P]? [US#]? Description with file path`. Parallelizable tasks marked `[P]`; user story tasks include `[US1]`, `[US2]`, `[US3]` labels.

## Totals

- Total Tasks: 68
- US1 Tasks: 12 (T021–T028, T055, T059, T062)
- US2 Tasks: 6 (T029–T033, T057)
- US3 Tasks: 7 (T034–T040)
- Setup + Foundational: 20 (T001–T020)
- Coverage & Determinism Extensions: 14 (T055–T068)
- Polish & Cross-Cutting (original): 14 (T041–T054)
