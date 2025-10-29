# Task Plan: Trend Pullback Continuation Strategy

Feature Branch: `001-trend-pullback`
Source Spec: `spec.md`
Generated: 2025-10-26

## Overview

This tasks file organizes implementation work by user story priority (P1, P2, P3) enabling independently testable increments. Each task follows required checklist format. Parallelizable tasks marked `[P]`. Story labels appear only in story phases.

User Stories:

- US1 (P1): Generate Valid Long Trade Signal
- US2 (P2): Generate Valid Short Trade Signal
- US3 (P3): Backtest Result Generation

## Phase 1: Setup

Essential repository and environment scaffolding.

- [ ] T001 Create base source directories per plan in `src/` (indicators/, strategy/trend_pullback/, risk/, backtest/, models/, io/, cli/)
- [ ] T002 Create Python package initializer files in each new directory (`src/indicators/__init__.py`, etc.)
- [ ] T003 Add `pyproject.toml` with project metadata, dependencies (numpy, pandas, pydantic, rich, pytest, hypothesis) in repo root
- [ ] T004 Add `requirements.txt` mirroring pyproject runtime deps in repo root
- [ ] T005 Add `.gitignore` entries for `.venv/`, data cache directory `/data/raw/`, backtest outputs `/runs/`
- [ ] T006 Create `src/config/parameters.py` pydantic settings loader for strategy parameters
- [ ] T007 Create `README.md` base referencing `specs/001-trend-pullback/quickstart.md`
- [ ] T008 Create `tests/conftest.py` with global fixtures (temp manifest path, sample parameters)
- [ ] T009 [P] Create `tests/fixtures/sample_candles_long.csv` synthetic dataset for US1 acceptance tests
- [ ] T010 [P] Create `tests/fixtures/sample_candles_short.csv` synthetic dataset for US2 acceptance tests
- [ ] T011 [P] Create `tests/fixtures/sample_candles_empty.csv` zero-trade dataset for US3 scenario 3

## Phase 2: Foundational (Cross-Story Prerequisites)

Implements domain primitives & shared services required by all stories.

- [ ] T012 Implement core dataclasses in `src/models/core.py` (Candle, TrendState, PullbackState, TradeSignal, TradeExecution, BacktestRun, DataManifest)
- [ ] T013 Implement indicator functions (EMA, ATR, RSI) in `src/indicators/basic.py`
- [ ] T014 [P] Implement streaming ingestion stub `src/io/ingestion.py` (iterator yielding Candle + gap check)
- [ ] T015 [P] Implement manifest loader & validator in `src/io/manifest.py`
- [ ] T016 Implement deterministic signal ID helper in `src/strategy/id_factory.py`
- [ ] T017 Implement reproducibility service skeleton in `src/backtest/reproducibility.py`
- [ ] T018 Implement metrics aggregator skeleton in `src/backtest/metrics.py`
- [ ] T019 Implement latency sampling utility in `src/backtest/latency.py`
- [ ] T020 [P] Setup structured logging JSON config in `src/cli/logging_setup.py`
- [ ] T021 Implement base exceptions `src/models/exceptions.py` (DataIntegrityError, RiskLimitError, ExecutionSimulationError)
- [ ] T022 Add initial unit tests for indicators in `tests/unit/test_indicators_basic.py`
- [ ] T023 [P] Add unit tests for manifest validation in `tests/unit/test_manifest.py`
- [ ] T024 [P] Add unit tests for id determinism in `tests/unit/test_id_factory.py`
- [ ] T025 Add unit tests for reproducibility service hash stability in `tests/unit/test_reproducibility.py`
- [ ] T026 Add unit tests for metrics aggregator zero-trade case in `tests/unit/test_metrics_zero.py`

## Phase 3: User Story US1 (P1) - Long Trade Signal

Implements long-side logic; independently testable.

- [ ] T027 [US1] Implement trend classifier in `src/strategy/trend_pullback/trend_classifier.py`
- [ ] T028 [P] [US1] Implement pullback detector in `src/strategy/trend_pullback/pullback_detector.py`
- [ ] T029 [P] [US1] Implement reversal pattern & momentum turn logic in `src/strategy/trend_pullback/reversal.py`
- [ ] T030 [US1] Implement long signal generator in `src/strategy/trend_pullback/signal_generator.py`
- [ ] T031 [P] [US1] Implement risk manager (ATR stop calc + position sizing) in `src/risk/manager.py`
- [ ] T032 [US1] Implement execution simulator with entry/exit logic including exit mode precedence rule (FR-026: fixed R target with trailing stop timeout fallback) in `src/backtest/execution.py`
- [ ] T033 [P] [US1] Wire metrics ingestion for executions in `src/backtest/metrics_ingest.py`
- [ ] T034 [US1] Implement observability reporter in `src/backtest/observability.py`
- [ ] T035 [US1] Create CLI command `src/cli/run_long_backtest.py` for running long-signal-only backtest
- [ ] T036 [US1] Add integration test for acceptance scenarios in `tests/integration/test_us1_long_signal.py`
- [ ] T037 [P] [US1] Add unit tests for reversal patterns in `tests/unit/test_reversal_patterns.py`
- [ ] T038 [US1] Add unit tests for risk sizing rounding in `tests/unit/test_risk_manager_rounding.py`
- [ ] T039 [US1] Add performance test harness stub in `tests/performance/test_long_signal_perf.py`

## Phase 4: User Story US2 (P2) - Short Trade Signal

Adds symmetry; reuses components where possible.

- [ ] T040 [US2] Extend signal generator to support short logic in `src/strategy/trend_pullback/signal_generator.py`
- [ ] T041 [P] [US2] Extend reversal logic tests for bearish patterns in `tests/unit/test_reversal_patterns.py`
- [ ] T042 [US2] Add short-specific integration test acceptance scenarios in `tests/integration/test_us2_short_signal.py`
- [ ] T043 [P] [US2] Add risk manager test for short stop direction in `tests/unit/test_risk_manager_short.py`
- [ ] T044 [US2] Add cooldown enforcement test in `tests/unit/test_cooldown.py`
- [ ] T045 [P] [US2] Update CLI to toggle direction modes `src/cli/run_backtest.py`

## Phase 5: User Story US3 (P3) - Backtest Result Generation

Full metrics, error handling, zero-trade case.

- [ ] T046 [US3] Implement full metrics calculations (expectancy, Sharpe estimate, profit factor) in `src/backtest/metrics.py`
- [ ] T047 [P] [US3] Implement drawdown curve & max drawdown computation in `src/backtest/drawdown.py`
- [ ] T048 [US3] Implement volatility regime classifier in `src/strategy/trend_pullback/volatility_regime.py`
- [ ] T049 [P] [US3] Implement data gap handling in ingestion `src/io/ingestion.py`
- [ ] T050 [US3] Implement reproducibility hash finalize & verify in `src/backtest/reproducibility.py`
- [ ] T051 [P] [US3] Implement CLI backtest command output JSON `src/cli/run_backtest.py`
- [ ] T052 [US3] Add integration test for manifest missing error path in `tests/integration/test_us3_manifest_error.py`
- [ ] T053 [US3] Add integration test for zero-trade metrics in `tests/integration/test_us3_zero_trades.py`
- [ ] T054 [P] [US3] Add performance throughput test `tests/performance/test_throughput.py`
- [ ] T055 [US3] Add memory footprint measurement test `tests/performance/test_memory_usage.py`

## Phase 6: Polish & Cross-Cutting

Refinements, quality, deferred items groundwork.

- [ ] T056 Add statistical significance test harness (p-value) in `tests/integration/test_significance.py`
- [ ] T057 [P] Add volatility regime adaptive sizing placeholder in `src/risk/adaptive_sizing.py`
- [ ] T058 Add Stoch RSI optional indicator in `src/indicators/stoch_rsi.py`
- [ ] T059 [P] Add configuration documentation section in `README.md`
- [ ] T060 Add ruff configuration file `.ruff.toml` with basic lint rules
- [ ] T061 [P] Add pre-commit config `.pre-commit-config.yaml` for formatting & linting
- [ ] T062 Add CLI help documentation in `src/cli/__init__.py`
- [ ] T063 Final pass to ensure reproducibility hash documented in `specs/001-trend-pullback/quickstart.md`
- [ ] T064 [P] Add example Jupyter notebook `examples/long_signal_walkthrough.ipynb` (synthetic demonstration)
- [ ] T065 Add CHANGELOG entry in `CHANGELOG.md` summarizing feature implementation

## Dependency Graph (User Story Order)

```text
Setup -> Foundational -> US1 -> US2 -> US3 -> Polish
US1 provides core signal infra reused by US2 and metrics base used by US3.
US2 depends on US1 trend/pullback logic (shared). US3 depends on execution & metrics from US1/US2.
```

## Parallel Execution Examples

- During Foundational: T014, T015, T020, T023, T024 can run in parallel (independent files)
- US1 Phase: T028, T029, T031, T033, T037 can run in parallel after T027
- US2 Phase: T041, T043, T045 in parallel after T040
- US3 Phase: T047, T049, T051, T054 in parallel after T046
- Polish Phase: T057, T059, T061, T064 in parallel after T056

## Independent Test Criteria by Story

- US1: Long signal emitted only after valid pullback + reversal; no emission in ranging conditions.
- US2: Short signal mirrors US1 logic; verifies direction correctness & cooldown.
- US3: Metrics generated (win_rate, avg_R, expectancy, max_drawdown_R, Sharpe_estimate); zero-trade and missing manifest scenarios handled gracefully.

## Task Counts

- Setup: 11
- Foundational: 15
- US1: 13
- US2: 6
- US3: 10
- Polish: 10
- Total: 65

## Suggested MVP Scope

MVP = Complete Setup + Foundational + US1 (first 39 tasks) delivering validated long trade signals and basic execution + metrics.

## Format Validation

All tasks follow required format: `- [ ] T### optional [P] optional [USn] Description with file path`. Story labels only appear in story phases. Parallel markers applied only where no dependency conflict.

---
End of tasks.md
