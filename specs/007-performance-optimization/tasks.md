# Task Plan: Performance Optimization: Backtest Orchestrator & Trade Simulation

**Branch**: 007-performance-optimization  
**Spec**: ./spec.md  
**Plan**: ./plan.md  
**Generated**: 2025-11-05

## Dependency Graph (User Stories)

US1 (Fast Large Backtest Execution) → US2 (Profiling & Bottleneck Insight) → US3 (Partial Dataset Iteration)

Rationale: Core speed improvements (US1) must exist before profiling is meaningful (US2). Fractional runs (US3) depend on stable fast pipeline + profiling benchmarks for validation.

## Parallel Execution Examples

- Indicator cache implementation (src/backtest/indicator_cache.py) can proceed in parallel with batch simulation scaffolding (src/backtest/trade_sim_batch.py) after shared type decisions.
- Unit test scaffolds for cache, simulation, chunking can be written in parallel to module stubs.
- Profiling artifact writer (src/backtest/profiling.py) can be developed while simulation optimization stabilizes.

## Independent Test Criteria Per User Story

- US1: Run full dataset synthetic benchmark; wall-clock ≤ target; fidelity tests pass.
- US2: Profiling flag produces artifact with phase timings + ≥10 hotspots; repeat run after change shows reduced simulation time.
- US3: Runs with --data-frac values (0.25, 0.5, 1.0) process correct row counts and scale runtime roughly proportionally.

## MVP Scope

Deliver US1 only: fast execution path (indicator caching, batch simulation, deterministic mode, baseline benchmark recording, fidelity + performance tests).

---
\n## Phase 1: Setup

(Repository already initialized; focus on environment and baseline capture.)

- [ ] T001 Ensure optional dependencies section documented (no mandatory install) in `pyproject.toml` comment block
- [ ] T002 Create benchmarks directory structure `results/benchmarks/` (add .gitkeep)
- [ ] T003 Add baseline speed fixture file `tests/performance/baseline_metrics.json` (placeholder values for later update)
- [ ] T004 Add README note for performance feature in `docs/performance.md` (initial header + baseline TODO)

## Phase 2: Foundational

(Blocking modules & test scaffolds before user story implementation.)

- [ ] T005 [P] Create module stub `src/backtest/indicator_cache.py` with docstring & placeholder class
- [ ] T006 [P] Create module stub `src/backtest/trade_sim_batch.py` with docstring & placeholder function signatures
- [ ] T007 [P] Create module stub `src/backtest/profiling.py` with docstring & placeholder writer
- [ ] T008 [P] Create module stub `src/backtest/chunking.py` for slice & chunk utilities
- [ ] T009 [P] Create module stub `src/backtest/parallel.py` for worker orchestration helpers
- [ ] T010 Add deterministic seed utility function in `src/backtest/reproducibility.py` (extend existing) for setting RNG & env variables
- [ ] T011 [P] Add unit test scaffold `tests/unit/test_indicator_cache.py` (imports + TODO markers)
- [ ] T012 [P] Add unit test scaffold `tests/unit/test_trade_sim_batch.py`
- [ ] T013 [P] Add unit test scaffold `tests/unit/test_chunking.py`
- [ ] T014 [P] Add unit test scaffold `tests/unit/test_profiling.py`
- [ ] T015 Create performance test scaffold `tests/performance/test_trade_sim_speed.py` (skip marker until implementation)
- [ ] T016 Create performance test scaffold `tests/performance/test_memory_peak.py` (skip marker until measurement implemented)
- [ ] T017 Add integration test scaffold `tests/integration/test_full_run_deterministic.py`
- [ ] T018 Add integration test scaffold `tests/integration/test_parallel_efficiency.py`
- [ ] T019 Add integration test scaffold `tests/integration/test_full_run_fraction.py`

## Phase 3: User Story US1 (Fast Large Backtest Execution)

- [ ] T020 [US1] Implement indicator cache data structures & lazy compute logic in `src/backtest/indicator_cache.py`
- [ ] T021 [US1] Implement vectorized batch trade simulation baseline (no JIT) in `src/backtest/trade_sim_batch.py`
- [ ] T022 [US1] Integrate batch simulation path into orchestrator `src/backtest/orchestrator.py` (replace per-trade loop)
- [ ] T023 [P] [US1] Add fidelity comparison helper in `tests/integration/test_full_run_deterministic.py` (baseline vs optimized)
- [ ] T024 [US1] Implement deterministic run flag handling in `src/cli/run_backtest.py`
- [ ] T025 [US1] Add CLI benchmark artifact creation in `src/backtest/profiling.py` (benchmark writer function)
- [ ] T026 [P] [US1] Update performance test `tests/performance/test_trade_sim_speed.py` with timing assertion (≥10× speedup vs baseline placeholder)
- [ ] T027 [US1] Update memory peak test `tests/performance/test_memory_peak.py` to capture RSS / tracemalloc
- [ ] T028 [US1] Add logging throttling (progress every N trades) in `src/backtest/orchestrator.py`
- [ ] T029 [P] [US1] Update `docs/performance.md` with initial before/after timing section
- [ ] T030 [US1] Populate baseline metrics file `tests/performance/baseline_metrics.json` with captured pre-optimization values
- [ ] T031 [US1] Add benchmark record schema enforcement test in `tests/unit/test_profiling.py`

## Phase 4: User Story US2 (Performance Bottleneck Insight)

- [ ] T032 [US2] Implement profiling flag parsing & validation in `src/cli/run_backtest.py`
- [ ] T033 [US2] Add phase timing instrumentation (ingest, scan, simulate) in `src/backtest/orchestrator.py`
- [ ] T034 [US2] Implement hotspot extraction (cProfile integration) in `src/backtest/profiling.py`
- [ ] T035 [P] [US2] Add profiling artifact content test in `tests/unit/test_profiling.py` (mock run)
- [ ] T036 [US2] Add integration test verifying profiling artifact presence `tests/integration/test_full_run_deterministic.py`
- [ ] T037 [US2] Update `docs/performance.md` with profiling usage instructions
- [ ] T038 [US2] Update benchmark writer to include `parallel_efficiency` and phase times in JSON

## Phase 5: User Story US3 (Partial Dataset Iteration)

- [ ] T039 [US3] Implement fraction flag parsing & validation in `src/cli/run_backtest.py`
- [ ] T040 [US3] Implement dataset slicing logic pre-indicator compute in `src/backtest/chunking.py`
- [ ] T041 [US3] Integrate slicing into orchestrator startup `src/backtest/orchestrator.py`
- [ ] T042 [P] [US3] Add integration tests for fractions (0.25, 0.5, 1.0) in `tests/integration/test_full_run_fraction.py`
- [ ] T043 [US3] Add benchmark JSON row count & fraction fields (update writer) in `src/backtest/profiling.py`
- [ ] T044 [US3] Add memory threshold warning logic in `src/backtest/profiling.py`
- [ ] T045 [P] [US3] Update `docs/performance.md` with fraction usage section

## Phase 6: Polish & Cross-Cutting

- [ ] T046 Add optional numba JIT path (guarded import) in `src/backtest/trade_sim_batch.py`
- [ ] T047 Add shared memory optimization for large arrays in `src/backtest/parallel.py`
- [ ] T048 Event-driven simulation mode stub behind `--sim-mode event` in `src/backtest/trade_sim_batch.py`
- [ ] T049 Add parquet ingestion flag handling & fallback warning in `src/cli/run_backtest.py`
- [ ] T050 Add benchmark summary aggregator script `scripts/ci/aggregate_benchmarks.py`
- [ ] T051 Refine progress output (rich formatting minimal refresh) in `src/backtest/orchestrator.py`
- [ ] T052 Add edge case tests (same-bar exit, overlapping trades) in `tests/integration/test_full_run_deterministic.py`
- [ ] T053 Final update of `docs/performance.md` with benchmark table and guidance
- [ ] T054 Update `README.md` summary section linking performance docs
- [ ] T055 Add memory peak assertion test to `tests/performance/test_memory_peak.py`
- [ ] T056 Add parallel efficiency test logic `tests/integration/test_parallel_efficiency.py`

## Format Validation

All tasks follow pattern: `- [ ] T### [P]? [US#]? Description with file path`.

## Task Counts

- Total Tasks: 56
- Setup Phase: 4
- Foundational Phase: 15
- US1 Phase: 12
- US2 Phase: 8
- US3 Phase: 7
- Polish Phase: 10

## Parallelizable Tasks Count

Tasks marked [P]: 18 (independent file creations or updates).

## Next Steps

Begin execution with Phase 1 tasks (T001–T004). MVP target completion after US1 (T020–T031) to validate speed & fidelity.
