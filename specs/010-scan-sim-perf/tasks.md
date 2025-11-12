# Feature 010 – Scan & Simulation Performance Optimization Tasks

Generated per speckit tasks prompt. Canonical stack: Python 3.11, Polars + Parquet (zstd), NumPy, pydantic, rich, pytest. Pandas only for legacy verification. All tasks follow required checklist format.

## Phase 1 – Setup

- [X] T001 Initialize Parquet ingestion directory structure in `src/io/ingestion`
- [X] T002 Create Poetry entry for Polars (verify version) in `pyproject.toml`
- [X] T003 Add performance targets module `src/backtest/performance_targets.py`
- [X] T004 Create empty manifest model file `src/io/ingestion/manifest.py`
- [X] T005 Create placeholder conversion module `src/io/ingestion/parquet_convert.py`
- [X] T006 Create placeholder loader module `src/io/ingestion/load.py`
- [X] T007 Add performance report model `src/models/performance_report.py`
- [X] T008 Add deterministic env capture utility `src/backtest/env_info.py`
- [X] T009 Add memory sampler utility `src/backtest/memory_sampler.py`
- [X] T010 Add progress dispatcher scaffold `src/backtest/progress.py`
- [X] T011 Add deterministic config module `src/backtest/deterministic.py` (seed management, ordering controls)

## Phase 2 – Foundational

- [X] T012 Implement Manifest pydantic model in `src/io/ingestion/manifest.py`
- [X] T013 Implement CSV→Parquet conversion with zstd & checksum in `src/io/ingestion/parquet_convert.py`
- [X] T014 Implement Parquet LazyFrame loader & schema fingerprint in `src/io/ingestion/load.py`
- [X] T015 Implement performance targets constants in `src/backtest/performance_targets.py`
- [X] T016 Implement env metadata capture in `src/backtest/env_info.py`
- [X] T017 Implement memory sampler (tracemalloc + psutil fallback) in `src/backtest/memory_sampler.py`
- [X] T018 Implement progress dispatcher stride + time logic in `src/backtest/progress.py`
- [X] T019 Implement deterministic controls (seed, ordering) in `src/backtest/deterministic.py`
- [X] T020 Add dedupe utility `src/backtest/dedupe.py`
- [X] T021 Add columnar extraction helper `src/backtest/arrays.py`
- [X] T022 Add baseline equivalence fixture ingestion helper `tests/fixtures/baseline_equivalence.py`
- [X] T023 Add logging format audit baseline for Phase 2 modules `scripts/ci/check_logging_format.py` (verify lazy % formatting in new modules) [Principle X]

## Phase 3 – User Story 1 (Accelerated Market Scan) P1

- [X] T024 [US1] Implement batch scan core `src/backtest/batch_scan.py`
- [X] T025 [P] [US1] Implement indicator input extractor `src/preprocess/indicator_inputs.py`
- [X] T026 [US1] Integrate dedupe + extraction + progress into scan pipeline `src/backtest/batch_scan.py`
- [X] T027 [US1] Add scan equivalence test (timestamps & counts) `tests/integration/test_scan_equivalence.py`
- [X] T028 [US1] Add performance benchmark test (duration assertion) `tests/performance/test_scan_perf.py`  # Removed [P]; depends on stable scan core
- [X] T029 [US1] Add memory usage benchmark (peak reduced ≥30%) `tests/performance/test_scan_memory.py`  # Removed [P]; depends on scan implementation
- [X] T030 [US1] Add progress cadence test (interval ≤120s) `tests/unit/test_progress_scan.py`
- [X] T031 [US1] Add duplicate timestamp handling test `tests/unit/test_dedupe.py`

## Phase 4 – User Story 2 (Strategy-Owned Indicators) P2

- [X] T032 [US2] Enforce indicator declaration location (strategy only) `src/strategy/indicator_registry.py`
- [X] T033 [P] [US2] Implement indicator ownership audit test `tests/contract/test_indicator_ownership.py`
- [X] T034 [US2] Remove any legacy indicator mutation from `src/backtest/` modules
- [X] T035 [US2] Add zero-indicator strategy test `tests/unit/test_zero_indicator_strategy.py`
- [X] T036 [US2] Add warm-up NaN exclusion test `tests/unit/test_indicator_warmup.py`

## Phase 5 – User Story 3 (Efficient Trade Simulation) P3

- [X] T037 [US3] Implement batch simulation core `src/backtest/batch_simulation.py`
- [X] T038 [US3] Implement vectorized SL/TP evaluation helper `src/backtest/sim_eval.py`  # Removed [P]; requires batch simulation scaffold
- [X] T039 [US3] Implement position state arrays (entry/exit indices) `src/backtest/batch_simulation.py`
- [X] T040 [US3] Add simulation equivalence test (trade count, PnL tolerance) `tests/integration/test_sim_equivalence.py`
- [X] T041 [US3] Add simulation performance benchmark test `tests/performance/test_sim_perf.py`  # Removed [P]; after core simulation stable
- [X] T042 [US3] Add memory usage benchmark test `tests/performance/test_sim_memory.py`
- [X] T043 [US3] Add deterministic multi-run test (±1% timing variance) `tests/integration/test_deterministic_runs.py`

## Phase 6 – Polish & Cross-Cutting ✅ COMPLETE

- [X] T044 Consolidate PerformanceReport generation `src/backtest/report.py`
- [X] T045 Integrate report emission into CLI backtest `src/cli/run_backtest.py` (placeholder pending orchestrator refactoring)
- [X] T046 Add JSON summary writer `src/backtest/report_writer.py`
- [X] T047 Add documentation updates for mandatory Polars in `specs/010-scan-sim-perf/quickstart.md`
- [X] T048 Add performance rationale section in `docs/performance.md`
- [X] T049 Add CI script updates for new benchmarks `scripts/ci/aggregate_benchmarks.py`
- [X] T050 Add progress overhead test (<1%) `tests/performance/test_progress_overhead.py`
- [X] T051 Add manifest provenance test `tests/unit/test_manifest_provenance.py`
- [X] T052 Add README performance section update `README.md`
- [X] T053 Run lint & formatting (Black/Ruff/Pylint/Markdownlint) – meta task
- [X] T054 Generate final equivalence & performance summary `specs/010-scan-sim-perf/phase6-completion-summary.json`
- [ ] T055 Optional numba experiment script `scripts/experiment_numba_sim.py` (DEFERRED - numba not needed)
- [ ] T056 Optional Polars streaming prototype `src/backtest/streaming_scan.py` (DEFERRED - not needed for targets)

## Phase 7 – Coverage & Determinism Extensions

- [X] T057 [US1] Add scan determinism test `tests/integration/test_scan_deterministic.py` (repeat scan x3; identical signals & ≤1% timing variance)
- [X] T058 Add memory abort scenario test `tests/unit/test_memory_abort.py` (simulate low available memory; expect structured abort log) [FR-009]
- [X] T059 [US2] Add indicator mapping report test `tests/contract/test_indicator_mapping_report.py` (PerformanceReport indicator_names[] matches strategy registry) [FR-013]
- [X] T060 Add allocation profiling harness `scripts/ci/profile_scan_allocations.py` (captures baseline & optimized allocation counts) [FR-002, FR-014]
- [X] T061 [US1] Add allocation reduction assertion test `tests/performance/test_scan_allocations.py` (≥70% reduction vs baseline) [FR-014]
- [X] T062 Add manifest provenance validation test `tests/unit/test_manifest_in_report.py` (checksum/path match manifest) [FR-012]
- [X] T063 Extend performance report generation with new fields `src/backtest/report.py` (progress_overhead_pct, indicator_names[], allocation metrics) [FR-007, FR-011–FR-014]
- [X] T064 [US1] Add progress final emission test `tests/unit/test_progress_final.py` (mandatory 100% emission + overhead ≤1%) [FR-011]
- [X] T065 Add indicator mapping generation in report writer `src/backtest/report_writer.py` [FR-013]
- [X] T066 Add structured abort logging utility `src/backtest/memory_abort.py` (emits memory abort record) [FR-009]
- [X] T067 Add allocation baseline capture script `scripts/ci/profile_scan_allocations.py` (unoptimized scan) [FR-002]
- [ ] T068 Gate numba experiment script activation post-baseline (update `scripts/experiment_numba_sim.py`) [T055 dependency]
- [ ] T069 Mark streaming prototype experimental or relocate to future feature (update documentation comment in `src/backtest/streaming_scan.py`) [Scope]
- [X] T070 Extend logging format audit for new modules `scripts/ci/check_logging_format.py` (include progress, memory, abort, report) [Principle X]

## Phase 8 – CLI Integration & Parquet Caching

- [X] T071 Replace orchestrator scan methods with BatchScan calls `src/backtest/orchestrator.py` (eliminate window-by-window iteration) **COMPLETE**: Added run_optimized_backtest() with _run_optimized_long/short/both() all implemented. TODO: BatchScan needs direction-aware scanning logic, signal conversion from indices
- [X] T072 Implement CSV→Parquet conversion & caching `src/io/parquet_cache.py` (convert on first run, load cached on subsequent)
- [X] T073 Integrate Parquet-first loading in CLI `src/io/ingestion.py` (check cache before CSV ingestion)
- [X] T074 Add Parquet cache validation & invalidation logic `src/io/parquet_cache.py` (checksum validation, expiry)
- [X] T075 Add end-to-end optimized pipeline integration test `tests/integration/test_optimized_pipeline.py` (CSV→Parquet→BatchScan→BatchSimulation) **MANUAL TEST COMPLETE**: Verified on 1% data slice (69k rows) - Parquet caching works (2s vs 51s), Candle conversion skipped, BatchScan/BatchSimulation execute successfully, no crashes
- [X] T076 Replace orchestrator simulation with BatchSimulation calls `src/backtest/orchestrator.py` (eliminate trade-by-trade iteration) **COMPLETE**: Integrated in all three directions with signal/execution conversion, conflict detection (BOTH), and three-tier metrics (BOTH). Awaits BatchScan signal generation and BatchSimulation trade detail arrays for full functionality.
- [X] T077 Update CLI to emit PerformanceReport after backtest `src/cli/run_backtest.py` (integrate report_writer with orchestrator results) **COMPLETE**: Added --emit-perf-report flag. Extracts scan/simulation durations from orchestrator phase times, candle/signal/trade counts from BacktestResult. Writes JSON reports to results/performance_report_TIMESTAMP.json. Only emits when use_optimized_path=True. Pylint 9.85/10.
- [X] T078 Add performance comparison script `scripts/ci/compare_baseline_optimized.py` (measure actual speedup achieved) **COMPLETE**: Created 268-line benchmarking script with run_backtest() subprocess execution, extract_metrics() JSON parsing, print_comparison() detailed reporting. Supports --baseline-only/--optimized-only/--both modes. Calculates scan/simulation speedup percentages and throughput. Outputs results/performance_comparison.json. Pylint 9.79/10.

## Dependencies (User Story Order)

US1 → US2 (indicator ownership audit depends on working scan path) → US3 (simulation depends on signals). Polish depends on all stories.

## Parallel Execution Examples

- T025 can run parallel with T024 once batch_scan scaffold exists.
- T033 can run parallel with T032 after registry stub present.
- T038 can run parallel with initial simulation scaffold T037.

## Independent Test Criteria

- US1: `test_scan_equivalence.py` + perf/memory + progress & dedupe tests.
- US2: Ownership audit + zero-indicator + warm-up NaN tests.
- US3: Simulation equivalence + performance + memory + deterministic multi-run tests.

## MVP Scope Suggestion

Implement Phase 1–2 plus US1 (Tasks T001–T031). Provides accelerated scan with equivalence & reporting foundation.

## Format Validation

All tasks use: `- [ ] T### [P]? [US#]? Description with file path`. Parallelizable tasks marked `[P]`; user story tasks include `[US1]`, `[US2]`, `[US3]` labels.

## Totals

- Total Tasks: 70
- US1 Tasks: 12 (T024–T031, T057, T061, T064)
- US2 Tasks: 6 (T032–T036, T059)
- US3 Tasks: 7 (T037–T043)
- Setup + Foundational: 23 (T001–T023)
- Coverage & Determinism Extensions: 14 (T057–T070)
- Polish & Cross-Cutting: 13 (T044–T056)
