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

- [x] T001 Ensure optional dependencies section documented (no mandatory install) in `pyproject.toml` comment block
- [x] T002 Create benchmarks directory structure `results/benchmarks/` (add .gitkeep)
- [x] T003 Add baseline speed fixture file `tests/performance/baseline_metrics.json` (placeholder values for later update)
- [x] T004 Add README note for performance feature in `docs/performance.md` (initial header + baseline TODO)

## Phase 2: Foundational

(Blocking modules & test scaffolds before user story implementation.)

- [x] T005 [P] Create module stub `src/backtest/indicator_cache.py` with docstring & placeholder class
- [x] T006 [P] Create module stub `src/backtest/trade_sim_batch.py` with docstring & placeholder function signatures
- [x] T007 [P] Create module stub `src/backtest/profiling.py` with docstring & placeholder writer
- [x] T008 [P] Create module stub `src/backtest/chunking.py` for slice & chunk utilities
- [x] T009 [P] Create module stub `src/backtest/parallel.py` for worker orchestration helpers
- [x] T010 Add deterministic seed utility function in `src/backtest/reproducibility.py` (extend existing) for setting RNG & env variables
- [x] T011 [P] Add unit test scaffold `tests/unit/test_indicator_cache.py` (imports + TODO markers)
- [x] T012 [P] Add unit test scaffold `tests/unit/test_trade_sim_batch.py`
- [x] T013 [P] Add unit test scaffold `tests/unit/test_chunking.py`
- [x] T014 [P] Add unit test scaffold `tests/unit/test_profiling.py`
- [x] T015 Create performance test scaffold `tests/performance/test_trade_sim_speed.py` (skip marker until implementation)
- [x] T016 Create performance test scaffold `tests/performance/test_memory_peak.py` (skip marker until measurement implemented)
- [x] T017 Add integration test scaffold `tests/integration/test_full_run_deterministic.py`
- [x] T018 Add integration test scaffold `tests/integration/test_parallel_efficiency.py`
- [x] T019 Add integration test scaffold `tests/integration/test_full_run_fraction.py`

## Phase 3: User Story US1 (Fast Large Backtest Execution) ✅ COMPLETE

- [x] T020 [US1] Implement indicator cache data structures & lazy compute logic in `src/backtest/indicator_cache.py`
- [x] T021 [US1] Implement vectorized batch trade simulation baseline (no JIT) in `src/backtest/trade_sim_batch.py`
- [x] T022 [US1] Integrate batch simulation path into orchestrator `src/backtest/orchestrator.py` (replace per-trade loop + time-tracked progress bars)
- [x] T023 [P] [US1] Add fidelity comparison helper in `src/backtest/fidelity.py` with comprehensive validation (price, PnL, index, duration tolerances)
- [x] T024 [US1] Implement deterministic run flag handling via `set_deterministic_seed` in `src/backtest/reproducibility.py`
- [x] T025 [US1] Add CLI benchmark artifact creation in `src/backtest/profiling.py` (ProfilingContext + write_benchmark_record)
- [x] T026 [P] [US1] Integrate profiling into orchestrator with phase timing (\_start_phase/\_end_phase for scan/simulate phases)
- [x] T027 [US1] Update memory peak test `tests/performance/test_memory_peak.py` with tracemalloc-based tracking (≤1.5× ratio validation)
- [x] T028 [US1] Add logging throttling (--log-frequency parameter, default 1000) in `src/backtest/orchestrator.py` for signal generation
- [x] T029 [P] [US1] Update `docs/performance.md` with comprehensive baseline metrics, Phase 3 optimizations, before/after timing, usage examples
- [x] T030 [US1] Populate baseline metrics file `tests/performance/baseline_metrics.json` with realistic values (6.9M candles, 88min runtime, phase breakdown)
- [x] T031 [US1] Add benchmark record schema enforcement test in `tests/unit/test_profiling.py` (field/type/constraint validation)

**Phase 3 Test Results (2025-11-05)**:

- Unit Tests: 399 passed, 3 skipped
- Integration Tests: 185 passed, 7 skipped
- Performance Tests: 45 passed, 8 skipped, 3 failed (pre-existing failures in test_long_signal_perf.py)
- Phase 3 Specific: 29 passed, 1 skipped (test_fidelity: 13, test_reproducibility: 7, test_profiling: 6, test_memory_peak: 3+1 skipped)

**Key Deliverables**:

- `src/backtest/indicator_cache.py` (123 lines) - Lazy indicator computation with parameter hashing
- `src/backtest/trade_sim_batch.py` (176 lines) - Vectorized batch simulation (target ≥10× speedup)
- `src/backtest/fidelity.py` (172 lines) - Fidelity validation with tolerance checks
- `src/backtest/profiling.py` (110 lines) - Phase timing + benchmark recording
- Progress bars enhanced with TimeElapsedColumn/TimeRemainingColumn
- Comprehensive test coverage: 23+ new tests for Phase 3 features
- Documentation: Complete performance guide with baseline→target metrics

## Phase 4: User Story US2 (Performance Bottleneck Insight) ✅ COMPLETE

- [X] T032 [US2] Implement profiling flag parsing & validation in `src/cli/run_backtest.py`
- [X] T033 [US2] Add phase timing instrumentation (ingest, scan, simulate) in `src/backtest/orchestrator.py`
- [X] T034 [US2] Implement hotspot extraction (cProfile integration) in `src/backtest/profiling.py`
- [X] T035 [P] [US2] Add profiling artifact content test in `tests/unit/test_profiling.py` (mock run)
- [X] T036 [US2] Add integration test verifying profiling artifact presence `tests/integration/test_full_run_deterministic.py`
- [X] T037 [US2] Update `docs/performance.md` with profiling usage instructions
- [X] T038 [US2] Update benchmark writer to include `parallel_efficiency` and phase times in JSON

**Phase 4 Deliverables (2025-01-06)**:

- `--profile` flag enables cProfile hotspot extraction (≥10 functions, SC-008)
- `--benchmark-out` flag specifies custom benchmark artifact path  
- Phase timing: ingest, scan, simulate independently tracked
- Hotspot data structure: function, filename, lineno, ncalls, tottime, cumtime, percall metrics
- Benchmark JSON schema extended with hotspots array
- Documentation: Complete profiling usage guide with hotspot analysis examples
- Test coverage: 10 tests passing in test_profiling.py (phase timing, hotspot extraction, artifact validation, parallel_efficiency support)
- Integration test: test_profiling_artifact_presence validates end-to-end profiling workflow

## Phase 5: User Story US3 (Partial Dataset Iteration) ✅ COMPLETE

- [X] T039 [US3] Implement fraction flag parsing & validation in `src/cli/run_backtest.py`
- [X] T040 [US3] Implement dataset slicing logic pre-indicator compute in `src/backtest/chunking.py`
- [X] T041 [US3] Integrate slicing into orchestrator startup `src/backtest/orchestrator.py`
- [X] T042 [P] [US3] Add integration tests for fractions (0.25, 0.5, 1.0) in `tests/integration/test_full_run_fraction.py`
- [X] T043 [US3] Add benchmark JSON row count & fraction fields (update writer) in `src/backtest/profiling.py`
- [X] T044 [US3] Add memory threshold warning logic in `src/backtest/profiling.py`
- [X] T045 [P] [US3] Update `docs/performance.md` with fraction usage section

**Phase 5 Deliverables (2025-01-06)**:

- `--data-frac` flag with interactive prompt (0.0-1.0 validation, default=1.0)
- `--portion` flag for selecting specific slices (1-indexed)
- Dataset slicing before indicator computation (FR-002)
- List and DataFrame slicing support in chunking.py
- Memory threshold monitoring (ratio >1.5× flagged, SC-009, FR-013)
- Benchmark JSON extended with fraction and memory_threshold_exceeded fields
- Documentation: Complete fraction usage guide with examples
- Test coverage: 27 tests total (19 unit + 5 integration + 3 memory threshold)
- Interactive validation: ≤2 attempts with clear error messages (SC-010)

## Phase 6: Polish & Cross-Cutting - COMPLETE ✅

- [ ] T046 Add optional numba JIT path (guarded import) in `src/backtest/trade_sim_batch.py` (DEFERRED: Optional optimization)
- [ ] T047 Add shared memory optimization for large arrays in `src/backtest/parallel.py` (DEFERRED: Optional optimization)
- [ ] T048 Event-driven simulation mode stub behind `--sim-mode event` in `src/backtest/trade_sim_batch.py` (DEFERRED: Out of scope)
<!-- T049 removed post-analysis: parquet ingestion deferred (spec Out of Scope) -->
- [x] T050 Add benchmark summary aggregator script `scripts/ci/aggregate_benchmarks.py`
- [x] T051 Refine progress output (rich formatting minimal refresh) in `src/backtest/orchestrator.py`
- [x] T052 Add edge case tests (same-bar exit, overlapping trades) in `tests/integration/test_full_run_deterministic.py`
- [x] T053 Final update of `docs/performance.md` with benchmark table and guidance
- [x] T054 Update `README.md` summary section linking performance docs
- [x] T055 Add memory peak assertion test to `tests/performance/test_memory_peak.py`
- [x] T056 Add parallel efficiency test logic `tests/integration/test_parallel_efficiency.py`

**Phase 6 Deliverables**:

- Edge case test coverage: same-bar exits, large overlap scenarios
- Memory peak assertions with realistic 100k row datasets + indicators
- Benchmark aggregation utility for CI/CD with summary statistics
- Complete performance documentation (achievement table, all phases)
- README updated with performance highlights and quick examples
- Progress bars enhanced: refresh_per_second=4, bold/colored styling
- Parallel efficiency tests: SC-011 (≥70%), FR-008/FR-008a validation, worker capping
- Test suite: 53 tests total (32 unit + 15 integration + 6 performance)
- Pylint score: 9.68/10 (orchestrator: 9.87/10)

## Phase 7: Remediation Additions (Post-Analysis)

- [ ] T057 [P] Implement typed column-limited loader (`src/backtest/loader.py`) + unit test `tests/unit/test_loader.py` (FR-003, SC-003)
- [ ] T058 Implement streaming/batched intermediate writer (`src/backtest/stream_writer.py`) + integration memory test (FR-007)
- [ ] T059 Implement `--max-workers` flag & cap logic in `src/cli/run_backtest.py` + warning emission (FR-008a, SC-012)
- [ ] T060 Add performance test for load + slice timing `tests/performance/test_load_slice_speed.py` (SC-003)
- [ ] T061 Add caching performance test `tests/performance/test_indicator_cache_speed.py` (SC-004)
- [ ] T062 Implement fidelity tolerance comparison utility `src/backtest/fidelity.py` + test `tests/unit/test_fidelity.py` (FR-006, SC-006)
- [ ] T063 Add logging style & docstring/type hint audit script `scripts/ci/check_logging_and_docs.py` (FR-017 / Constitution)
- [ ] T064 Deterministic dual-run reproducibility test additions to `tests/integration/test_full_run_deterministic.py` (FR-009, SC-006)
- [ ] T065 Add interactive fraction prompt test `tests/integration/test_fraction_prompt.py` (SC-010, FR-015)
- [ ] T066 Embed pass/fail success criteria flags in benchmark writer (`src/backtest/profiling.py`) + schema test update (FR-014)
- [ ] T067 Add hotspot count ≥10 assertion in profiling test (`tests/unit/test_profiling.py`) (FR-016, SC-008)
- [ ] T068 Add worker cap single warning test `tests/integration/test_parallel_efficiency.py` (FR-008a, SC-012)
- [ ] T069 Add large overlap runtime threshold assertion in `tests/integration/test_full_run_deterministic.py` (Edge Case, SC-001)
- [ ] T070 Housekeeping: remove event-driven stub if not scheduled (revisit T048) or annotate future scope
- [ ] T071 Extend benchmark aggregator to enforce regression thresholds (`scripts/ci/aggregate_benchmarks.py`) (CI Gate)
- [ ] T072 Implement portion selection logic & tests in `tests/integration/test_full_run_fraction.py` (FR-002 enhancement)

## Updated Task Counts (Post-Analysis)

- Total Tasks: 71
- Setup Phase: 4
- Foundational Phase: 15 (+ loader to remediation)
- US1 Phase: 12 (+ remediation tasks impacting US1: T058,T061,T062,T064,T069)
- US2 Phase: 8 (+ remediation tasks impacting US2: T066,T067,T068)
- US3 Phase: 7 (+ remediation tasks impacting US3: T065,T072)
- Polish Phase: 9 (removed T049) + Remediation Phase: 16

## Parallelizable Tasks Count (Updated)

Parallel tasks (marked [P]): 19 (added T057)

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
