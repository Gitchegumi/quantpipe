# Tasks: Optimize & Decouple Ingestion (Spec 009)

Feature: Optimize & Decouple Ingestion Process (`009-optimize-ingestion`)

MVP Scope: Deliver User Story 1 (Fast Core Ingestion) with performance baseline (≤120s) and deterministic duplicate/gap handling.

---

## Phase 1: Setup

(Repository already bootstrapped; these tasks ensure environment + baseline measurement & shared conventions.)

- [X] T001 Ensure Arrow backend enabled default where available (set pandas options) in `src/io/arrow_config.py`
- [X] T002 Add performance benchmark raw data manifest (baseline dataset reference) in `tests/performance/fixtures/README.md`
- [X] T003 Create timing + memory sampling utility skeleton in `src/io/perf_utils.py`
- [X] T004 Add hash utility for core immutability verification in `src/io/hash_utils.py`
- [X] T005 Add logging constants (progress stage names) in `src/io/logging_constants.py`
- [X] T006 Create placeholder ingestion module file (will be filled in US1) at `src/io/ingestion.py`
- [X] T007 Create placeholder registry package `src/indicators/registry/__init__.py`
- [X] T008 Add stub enrich module (will be filled in US2) at `src/indicators/enrich.py`
- [X] T009 Add empty performance benchmark script placeholder at `tests/performance/benchmark_ingestion.py`
- [X] T010 Add integration test placeholder at `tests/integration/test_ingest_then_enrich_pipeline.py`
- [X] T011 Add README for indicators package at `src/indicators/README.md`

## Phase 2: Foundational (Shared Utilities / Blocking Prereqs)

- [X] T012 Implement cadence interval computation + expected row count helper in `src/io/cadence.py`
- [X] T013 Implement duplicate detection + resolution (keep-first) helper in `src/io/duplicates.py`
- [X] T014 Implement gap detection & index reindex helper (no fill yet) in `src/io/gaps.py`
- [X] T015 Implement gap fill synthesizer (vectorized insertion + flag) in `src/io/gap_fill.py`
- [X] T016 Implement numeric downcast utility with safe precision checks in `src/io/downcast.py`
- [X] T017 Implement throughput + runtime metric capture in `src/io/perf_utils.py`
- [X] T018 Implement progress stage reporter (≤5 updates) in `src/io/progress.py`
- [X] T019 Implement core schema enforcement & column restriction in `src/io/schema.py`
- [X] T020 Implement UTC timestamp validator (reject non-UTC) in `src/io/timezone_validate.py`
- [X] T021 Implement immutability hash function in `src/io/hash_utils.py`
- [X] T022 Implement registry base data structures (IndicatorSpec dataclass) in `src/indicators/registry/specs.py`
- [X] T023 Implement registry storage & register/unregister API in `src/indicators/registry/store.py`
- [X] T024 Implement dependency resolution (topological sort) in `src/indicators/registry/deps.py`
- [X] T025 Implement enrichment validation helpers (duplicate indicator names) in `src/indicators/validation.py`
- [X] T026 Add unit tests for foundational utilities at `tests/unit/test_foundations_ingestion.py`
- [X] T027 Add unit tests for registry base + deps at `tests/unit/test_indicator_registry.py`

## Phase 3: User Story 1 - Fast Core Ingestion (P1)

Goal: Ingest 6.9M-row baseline ≤120s; produce only core columns + deterministic gaps & duplicates handling.
Independent Test Criteria: (a) runtime ≤120s (b) core schema only (c) gap count correctness (d) duplicate removals logged (e) no per-row loops (static lint/inspection) (f) progress updates ≤5.

- [X] T028 [US1] Implement ingestion pipeline assembly (read→sort→dedupe→cadence validate→gap fill→schema restrict→metrics) in `src/io/ingestion.py`
- [X] T029 [P] [US1] Implement Arrow backend detection + fallback logging in `src/io/arrow_config.py`
- [X] T030 [P] [US1] Integrate downcast option into pipeline in `src/io/ingestion.py`
- [X] T031 [P] [US1] Add metrics struct (runtime, counts, backend) in `src/io/metrics.py`
- [X] T032 [P] [US1] Add progress stage emission (stages enumerated) in `src/io/progress.py`
- [X] T033 [US1] Implement gap fill vectorization using reindex & forward-fill in `src/io/gap_fill.py`
- [X] T034 [US1] Implement duplicate resolution integration into pipeline in `src/io/ingestion.py`
- [X] T035 [US1] Implement cadence deviation check (>2% threshold) in `src/io/cadence.py`
- [X] T036 [US1] Add unit tests: gap synthesis correctness at `tests/unit/test_ingestion_gap_fill.py`
- [X] T037 [US1] Add unit tests: duplicate handling deterministic at `tests/unit/test_ingestion_duplicates.py`
- [X] T038 [US1] Add unit tests: cadence validation errors at `tests/unit/test_ingestion_cadence.py`
- [X] T039 [US1] Add unit tests: schema restriction & column order at `tests/unit/test_ingestion_schema.py`
- [X] T040 [US1] Add integration test: end-to-end ingestion result invariants at `tests/integration/test_ingestion_pipeline.py`
- [x] T041 [US1] Add performance benchmark harness with baseline timing at `tests/performance/benchmark_ingestion.py`
- [x] T042 [US1] Add static scan (Ruff rule/custom) to detect forbidden per-row loops in `src/io/` at `scripts/ci/check_no_row_loops.py`
- [x] T043 [US1] Document ingestion usage & performance expectations at `docs/performance.md`
- [x] T044 [US1] Update quickstart ingestion section runtime notes in `specs/009-optimize-ingestion/quickstart.md`

## Phase 4: User Story 2 - Opt-In Indicator Enrichment (P2)

Goal: Compute only requested indicators via registry without mutating core dataset.
Independent Test Criteria: (a) only requested columns appended (b) unknown names fast-fail (strict) (c) non-strict accumulates failures (d) core hash stable (e) registry API supports dynamic registration.

- [x] T045 [US2] Implement enrichment orchestration (validate→resolve deps→compute→assemble result) in `src/indicators/enrich.py`
- [x] T046 [P] [US2] Implement immutability guard (hash before/after) in `src/indicators/enrich.py`
- [x] T047 [P] [US2] Implement strict vs non-strict handling (fast-fail) in `src/indicators/enrich.py`
- [x] T048 [P] [US2] Implement error types/exceptions for enrichment in `src/indicators/errors.py`
- [x] T049 [US2] Implement built-in EMA (vectorized) in `src/indicators/builtin/ema.py`
- [x] T050 [P] [US2] Implement ATR in `src/indicators/builtin/atr.py`
- [x] T051 [P] [US2] Implement placeholder StochRSI (if already existing move/refactor) in `src/indicators/builtin/stochrsi.py`
- [x] T052 [US2] Register built-in indicators in `src/indicators/registry/builtins.py`
- [x] T053 [US2] Add unit tests: registry registration/unregistration at `tests/unit/test_indicator_registry.py`
- [x] T054 [US2] Add unit tests: enrichment only requested columns at `tests/unit/test_enrich_selectivity.py`
- [x] T055 [US2] Add unit tests: strict unknown fast-fail at `tests/unit/test_enrich_strict.py`
- [x] T056 [US2] Add unit tests: non-strict collects failures at `tests/unit/test_enrich_non_strict.py`
- [x] T057 [US2] Add unit tests: immutability hash unchanged at `tests/unit/test_enrich_immutability.py`
- [x] T058 [US2] Add integration test: ingest→enrich pipeline at `tests/integration/test_ingest_then_enrich_pipeline.py`
- [x] T059 [US2] Update quickstart enrichment examples with final indicator names at `specs/009-optimize-ingestion/quickstart.md`
- [x] T060 [US2] Update contracts (`contracts/enrich.md`) with any param refinements

## Phase 5: User Story 3 - Dual Output Modes (P3)

Goal: Support both columnar DataFrame and iterator object modes with performance delta ≥25% advantage for columnar.
Independent Test Criteria: (a) iterator yields objects conforming to schema (b) columnar throughput advantage ≥25% (c) invalid mode errors (d) both paths share core logic, no duplication.

- [X] T061 [US3] Implement iterator wrapper class in `src/io/iterator_mode.py`
- [X] T062 [P] [US3] Integrate mode selection param & branching in `src/io/ingestion.py`
- [X] T063 [P] [US3] Add mode validation errors in `src/io/errors.py`
- [X] T064 [US3] Add unit tests: invalid mode errors at `tests/unit/test_ingestion_modes.py`
- [X] T065 [US3] Add unit tests: iterator first N objects correctness at `tests/unit/test_ingestion_modes.py`
- [X] T066 [US3] Add performance comparison test (assert ≥25% faster) at `tests/performance/test_ingestion_performance.py`
- [X] T067 [US3] Update contracts (`contracts/ingest.md`) mode section with iterator details
- [X] T068 [US3] Update quickstart dual mode example performance note at `specs/009-optimize-ingestion/quickstart.md`

## Final Phase: Polish & Cross-Cutting

- [ ] T069 Refine downcast heuristics (skip columns with precision risk) in `src/io/downcast.py`
- [ ] T070 Add memory peak sampling integration (optional psutil) in `src/io/perf_utils.py`
- [ ] T071 Add stretch goal optimization experiment notes in `docs/performance.md`
- [ ] T072 Add Ruff rule / config to flag .itertuples()/iterrows usage at `pyproject.toml`
- [ ] T073 Add CI script to run performance benchmark in non-blocking mode at `scripts/ci/run_performance.py`
- [ ] T074 Add documentation for adding a new indicator at `src/indicators/README.md`
- [ ] T075 Add multi-symbol extension placeholder design note in `specs/009-optimize-ingestion/research.md`
- [ ] T076 Add GPU future hook comment + TODO in `src/io/arrow_config.py`
- [ ] T077 Final spec & plan cross-check (update any drift) in `specs/009-optimize-ingestion/spec.md`
- [ ] T078 Final constitution compliance summary appended in `specs/009-optimize-ingestion/plan.md`
- [ ] T079 Prepare release notes entry (CHANGELOG) in `CHANGELOG.md`
- [ ] T080 Add benchmark summary JSON export integration at `results/benchmark_summary.json`
- [ ] T081 Add contract validation script (schema lint) at `scripts/ci/validate_contracts.py`
- [ ] T082 Remove placeholders / TODO markers across new modules in `src/io/*.py`
- [ ] T083 Add README section describing ingestion architecture in `README.md`
- [ ] T084 Ensure all new modules have docstrings & type hints in `src/io/` and `src/indicators/`
- [ ] T085 Final performance run & record metrics in `results/benchmarks/ingestion_final.txt`
- [ ] T086 Clean up orphan test fixtures in `tests/fixtures/`

### Remediation Additions (Address Analysis Findings)

- [X] T087 Add logging format enforcement script (no f-string logging) at `scripts/ci/check_logging_format.py` (NFR-004 / Principle X)
- [X] T088 Add unit test: empty input handling (FR-013) at `tests/unit/test_ingestion_empty_input.py`
- [X] T089 Add unit test: missing core columns error schema (FR-020) at `tests/unit/test_ingestion_missing_columns.py`
- [X] T090 Add static audit test: ingestion has no indicator imports (FR-017) at `tests/unit/test_ingestion_no_indicator_imports.py`
- [X] T091 Add unit test: downcast precision guard (FR-011) at `tests/unit/test_downcast_precision.py`
- [X] T092 Add unit test: Arrow fallback warning schema (FR-025) at `tests/unit/test_arrow_fallback_warning.py`
- [X] T093 Add performance throughput assertion (SC-002 / FR-015) at `tests/performance/test_throughput.py`
- [ ] T094 Add stretch runtime artifact recorder script at `scripts/ci/record_stretch_runtime.py` (FR-027)
- [X] T095 Add unit test: GPU independence (FR-028) at `tests/unit/test_no_gpu_dependency.py`
- [X] T096 Add unit test: non-UTC timestamp rejection (FR-014) at `tests/unit/test_ingestion_timezone.py`
- [X] T097 Add performance memory footprint test (SC-006 / NFR-002) at `tests/performance/test_memory_footprint.py`
- [ ] T098 Add dependency policy verification script (Principle IX) at `scripts/ci/check_dependencies.py`
- [X] T099 Add unit test: progress stage names & limit enforcement (FR-010 / NFR-003) at `tests/unit/test_progress_stages.py`
- [X] T100 Add unit test: cadence deviation formula correctness (FR-012 / NFR-007) at `tests/unit/test_cadence_formula.py`
- [X] T101 Add unit test: summary metrics include throughput & backend (FR-015) at `tests/unit/test_metrics_logging.py`
- [ ] T102 Update performance benchmark harness to produce JSON artifacts (FR-016 / NFR-009) at `tests/performance/benchmark_ingestion.py`
- [ ] T103 Update documentation: indicator contract details (FR-019) at `src/indicators/README.md`

---
\n## Dependency Graph (User Stories)

US1 (Fast Core Ingestion) → US2 (Indicator Enrichment) → US3 (Dual Output Modes)

Rationale: Enrichment depends on stable ingestion output; dual modes rely on ingestion core but are independent of enrichment logic (however, sequencing after US2 simplifies shared testing harness reuse).

## Parallel Execution Examples

US1 Parallelizable: T029, T030, T031, T032 can run alongside T028 once foundational utilities (Phase 2) merged.
US2 Parallelizable: T046, T047, T048, T049–T051 can proceed after T045 skeleton committed.
US3 Parallelizable: T062, T063 can proceed after core ingestion (T028) baseline merged.
Polish Phase Parallel: T069, T070, T072 may run simultaneously; T085 must occur last.

## Implementation Strategy

1. MVP: Complete Phases 1–3 (through T044) to deliver fast ingestion with performance benchmark & tests.
2. Iteration 2: Implement enrichment (Phase 4) enabling selective indicators; update quickstart.
3. Iteration 3: Add dual output modes (Phase 5) and performance comparison test.
4. Polish: Execute final optimizations, documentation, compliance, and stretch goal tuning.

## Independent Test Criteria (Per Story)

| Story | Criteria Summary |
|-------|------------------|
| US1 | Runtime ≤120s; core schema only; gaps correct; duplicates deterministic; ≤5 progress updates; no per-row loops |
| US2 | Only requested indicators; unknown strict fast-fail; non-strict collects failures; core hash stable; registry dynamic registration |
| US3 | Columnar ≥25% faster vs iterator; iterator correctness; invalid mode errors; shared pipeline |

## Task Counts

| Phase | Count |
|-------|-------|
| Setup | 11 |
| Foundational | 15 |
| US1 | 17 |
| US2 | 16 |
| US3 | 8 |
| Polish | 18 |
| Total | 85 |

Counts by User Story: US1=17, US2=16, US3=8.

Parallel Opportunities Identified: 4 (US1), 5 (US2), 2 (US3), 3 (Polish) groups.

Format Validation: All tasks follow `- [ ] T### [P]? [US#]? Description with file path` pattern.

---
Generated via speckit.tasks workflow using available artifacts (plan, spec, data-model, contracts, quickstart, research). Ready for execution.
