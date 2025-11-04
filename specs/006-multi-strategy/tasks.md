# Tasks: Multi-Strategy Support

**Branch**: 006-multi-strategy  
**Spec**: ./spec.md  
**Plan**: ./plan.md  
**Data Model**: ./data-model.md  
**Contracts**: ./contracts/openapi.yaml  
**Research**: ./research.md

## Dependency Graph (User Stories)

1. US1 (Run Multiple Strategies Together) → foundational for aggregated metrics
2. US2 (Strategy Registration & Configuration) → enables discovery; can proceed in parallel with parts of US1 after registry interface stub
3. US3 (Strategy Selection & Filtering) → depends on registry + orchestration base

Independent Test Increments:

- US1: Backtest run with ≥2 strategies producing individual + aggregated outputs
- US2: Register new strategy; list; single-strategy run with overrides
- US3: Filtered multi-strategy run with weights + validation errors for unknown ids

## Phase 1: Setup

- [x] T001 Initialize multi-strategy directory structure (no code changes) confirm existing `src/strategy`, `src/backtest`, `tests/` present
- [x] T002 Add placeholder module for registry in `src/strategy/registry.py`
- [x] T003 Add placeholder aggregation module in `src/backtest/aggregation.py`
- [x] T004 Create run manifest placeholder in `src/models/run_manifest.py`
- [x] T005 Create weights parsing helper stub in `src/strategy/weights.py`
- [x] T006 Add markdownlint spacing fixes to new docs (plan.md, research.md, data-model.md, quickstart.md)
- [x] T007 Add initial tests folder scaffolds `tests/unit/registry/`, `tests/integration/multistrategy/`, `tests/performance/` (ensure **init**.py)
- [x] T008 Add logging setup confirmation for multi-strategy to `src/cli/logging_setup.py`

## Phase 2: Foundational

- [x] T009 Implement StrategyRegistry class in `src/strategy/registry.py` (register, list, get)
- [x] T010 [P] Implement StrategyConfig validation model in `src/models/strategy_config.py`
- [x] T011 Implement RiskLimits model with validation in `src/models/risk_limits.py`
- [x] T012 [P] Implement RunManifest data structure in `src/models/run_manifest.py`
- [x] T013 Implement deterministic_run_id generator in `src/backtest/reproducibility.py`
- [x] T014 [P] Implement weights parsing & normalization in `src/strategy/weights.py`
- [x] T015 Implement abort criteria evaluator in `src/backtest/abort.py`
- [x] T016 Add structured metrics fields definition in `src/backtest/metrics_schema.py`
- [x] T017 [P] Write unit tests for registry operations in `tests/unit/registry/test_registry.py`
- [x] T018 Write unit tests for weights parsing in `tests/unit/strategy/test_weights.py`
- [x] T019 [P] Write unit tests for deterministic_run_id in `tests/unit/backtest/test_reproducibility.py`
- [x] T020 Write unit tests for abort criteria evaluator in `tests/unit/backtest/test_abort.py`
- [x] T021 Implement validation pre-run function in `src/backtest/validation.py` (unknown strategies fail fast)

## Phase 3: User Story 1 (Run Multiple Strategies Together)

- [x] T022 [US1] Extend orchestrator for multi-strategy loop in `src/backtest/orchestrator.py`
- [x] T023 [P] [US1] Implement per-strategy state isolation container in `src/backtest/state_isolation.py`
- [x] T024 [US1] Implement aggregation logic (net exposures, PnL combine) in `src/backtest/aggregation.py`
- [x] T025 [P] [US1] Implement portfolio metrics computation in `src/backtest/metrics.py`
- [x] T026 [US1] Implement global drawdown evaluation in `src/backtest/risk_global.py`
- [x] T027 [US1] Implement per-strategy risk breach handling in `src/backtest/risk_strategy.py`
- [x] T028 [P] [US1] Implement manifest writer in `src/backtest/manifest_writer.py`
- [x] T029 [US1] Integrate reproducibility hash creation in orchestrator
- [x] T030 [US1] Integrate structured logging events in `src/backtest/observability.py`
- [x] T031 [US1] Write integration test: multi-strategy run baseline `tests/integration/multistrategy/test_run_baseline.py`
- [x] T032 [P] [US1] Write integration test: net exposure aggregation `tests/integration/multistrategy/test_net_exposure.py`
- [x] T033 [US1] Write integration test: risk breach isolation `tests/integration/multistrategy/test_risk_breach.py`
- [x] T034 [P] [US1] Write integration test: global drawdown abort `tests/integration/multistrategy/test_global_abort.py`
- [x] T035 [US1] Write performance scaling test (strategy count) `tests/performance/test_scaling.py`
- [x] T036 [US1] Write determinism repeatability test `tests/integration/multistrategy/test_determinism.py`

## Phase 4: User Story 2 (Strategy Registration & Configuration)

- [x] T037 [US2] Add registration CLI command in `src/cli/run_backtest.py` (mode: --register-strategy)
- [x] T038 [P] [US2] Add strategy listing CLI flag in `src/cli/run_backtest.py` (--list-strategies)
- [x] T039 [US2] Implement configuration override merge logic in `src/strategy/config_override.py`
- [x] T040 [P] [US2] Add risk limit enforcement hook integration in `src/backtest/risk_strategy.py`
- [x] T041 [US2] Unit test registration and listing in `tests/unit/registry/test_cli_listing.py`
- [x] T042 [P] [US2] Unit test configuration overrides in `tests/unit/strategy/test_config_override.py`
- [x] T043 [US2] Integration test single-strategy run with overrides `tests/integration/multistrategy/test_single_override.py`
- [x] T044 [US2] Add documentation section to `quickstart.md` for strategy registration

## Phase 5: User Story 3 (Strategy Selection & Filtering)

- [x] T045 [US3] Implement strategy filtering by tags & ids in `src/strategy/registry.py`
- [x] T046 [P] [US3] Implement CLI parsing for --strategies and --weights in `src/cli/run_backtest.py`
- [x] T047 [US3] Implement unknown strategy error handling path in `src/backtest/validation.py`
- [x] T048 [P] [US3] Add aggregation toggle flags (--aggregate / --no-aggregate) in `src/cli/run_backtest.py`
- [x] T049 [US3] Unit test filtering logic in `tests/unit/registry/test_filtering.py`
- [x] T050 [P] [US3] Integration test multi-strategy selection subset `tests/integration/multistrategy/test_selection_subset.py`
- [x] T051 [US3] Integration test unknown strategy error path `tests/integration/multistrategy/test_unknown_strategy.py`
- [x] T052 [US3] Integration test weights fallback equal-weight `tests/integration/multistrategy/test_weights_fallback.py`

## Final Phase: Polish & Cross-Cutting

- [ ] T053 Add README update referencing multi-strategy feature `README.md`
- [ ] T054 [P] Add correlation placeholder note in `spec.md` and `quickstart.md`
- [ ] T055 Add OpenAPI examples tests in `tests/contract/test_openapi_examples.py`
- [ ] T056 [P] Add logging standards verification (no f-string) `tests/unit/backtest/test_logging_standards.py`
- [ ] T057 Add markdownlint spacing fixes for all feature docs (spec, plan, research, data-model, quickstart)
- [ ] T058 [P] Add Pylint score check script enhancement `scripts/ci/check_quality.py`
- [ ] T059 Add reliability batch test harness `tests/performance/test_reliability.py`
- [ ] T060 [P] Add manifest hash validation test `tests/unit/backtest/test_manifest_hash.py`
- [ ] T061 Final pass determinism & performance thresholds validation `tests/performance/test_final_validation.py`
- [ ] T062 Prepare conventional commit draft `specs/006-multi-strategy/commit-draft.txt`

### Added Coverage & Validation Extensions

- [ ] T063 Define reliability target test harness threshold doc reference (ensure ≥99% over 100 runs) `tests/performance/test_reliability.py` (extend existing)
- [ ] T064 Add memory sampling helper + test (peak RSS compare) `tests/performance/test_memory_growth.py`
- [ ] T065 Test aggregation file includes manifest hash reference `tests/unit/backtest/test_aggregation_manifest_ref.py`
- [ ] T066 Validate weights length mismatch handling + normalization behavior `tests/integration/multistrategy/test_weights_validation.py`
- [ ] T067 Finalize structured metrics schema + logging verification `tests/unit/backtest/test_structured_metrics_logging.py`
- [ ] T068 Negative test: global abort not triggered on single local breach `tests/integration/multistrategy/test_local_breach_no_global_abort.py`

## Parallel Execution Examples

- Registry tests (T017) can run in parallel with weights parsing tests (T018) and deterministic run id tests (T019).
- Aggregation logic (T024) parallelizable with state isolation (T023) and portfolio metrics (T025).
- CLI flags (T038, T046, T048) parallel once base parsing is stubbed.
- Risk breach tests (T033) can run while global abort test (T034) executes.

## MVP Scope Recommendation

Deliver minimal multi-strategy capability: Complete Phases 1–3 tasks up to T036 (User Story 1). Defer registration enhancements (US2) and selection/filtering (US3) if schedule constrained.

## Task Counts

- Total Tasks: 62
- US1 Tasks: 15 (T022–T036)
- US2 Tasks: 8 (T037–T044)
- US3 Tasks: 8 (T045–T052)
- Parallelizable Tasks Marked [P]: 22

## Independent Test Criteria Summary

- US1: Run with ≥2 strategies outputs individual + portfolio metrics; deterministic repeat test passes.
- US2: Register + list + single strategy override run produces modified metrics and respects risk limits.
- US3: Filtered subset executes; unknown strategy yields validation error <1s; weights fallback applied.

## Implementation Strategy

1. Establish registry & validation foundation (Phase 2).
2. Implement orchestration + aggregation (Phase 3) achieving MVP.
3. Add configuration/registration enhancements (Phase 4).
4. Add selection & filtering features (Phase 5).
5. Polish docs, quality, reliability, and performance (Final Phase).

## Format Validation

All tasks follow required format: `- [ ] T### [P] [US#] Description path`. Setup and Foundational phases omit story labels per rules.
