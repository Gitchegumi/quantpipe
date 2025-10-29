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

### Total tasks: 10 | Parallelizable: 4 | First 40 tasks = MVP scope (includes US1 complete)

- [x] T001 Create base source directories per plan in `src/` (indicators/, strategy/trend_pullback/, risk/, backtest/, models/, io/, cli/)
- [x] T002 Create Python package initializer files in each new directory (`src/indicators/__init__.py`, etc.)
- [x] T003 Add `pyproject.toml` with project metadata, dependencies (numpy, pandas, pydantic, rich, pytest, hypothesis) using Poetry in repo root
- [x] T004 Add `.gitignore` entries for `.venv/`, data cache directory `/data/raw/`, backtest outputs `/runs/`
- [x] T005 Create `src/config/parameters.py` pydantic settings loader for strategy parameters
- [x] T006 Create `README.md` base referencing `specs/001-trend-pullback/quickstart.md`
- [x] T007 Create `tests/conftest.py` with global fixtures (temp manifest path, sample parameters)
- [x] T008 [P] Create `tests/fixtures/sample_candles_long.csv` synthetic dataset for US1 acceptance tests
- [x] T009 [P] Create `tests/fixtures/sample_candles_short.csv` synthetic dataset for US2 acceptance tests
- [x] T010 [P] Create `tests/fixtures/sample_candles_empty.csv` placeholder for US3 acceptance test

## Phase 2: Foundational (P1)

Low-level modules (indicators, ingestion, manifest, reproducibility, metrics).

- [x] T011 Implement core models dataclasses in `src/models/core.py` (Candle, TrendState, PullbackState, TradeSignal, TradeExecution, BacktestRun, DataManifest, MetricsSummary)
- [x] T012 Implement basic indicators (EMA, ATR, RSI) in `src/indicators/basic.py`
- [x] T013 [P] Implement streaming ingestion stub (iterator yielding Candle + gap check) in `src/io/ingestion.py`
- [x] T014 [P] Implement manifest loader & validator in `src/io/manifest.py`
- [x] T015 Implement deterministic signal ID helper `src/strategy/id_factory.py` (SHA-256 from pair + timestamp + parameters)
- [x] T016 Implement reproducibility service skeleton in `src/backtest/reproducibility.py` (hash accumulator + manifest ref tracking)
- [x] T017 Implement metrics aggregator skeleton in `src/backtest/metrics.py` (basic metrics: N trades, win/loss count)
- [x] T018 Implement latency sampling utility in `src/backtest/latency.py` (p95, mean from samples)
- [x] T019 [P] Implement structured logging config in `src/cli/logging_setup.py` (JSON formatter with log levels)
- [x] T020 Define base exceptions in `src/models/exceptions.py` (DataIntegrityError, RiskLimitError, ExecutionSimulationError)
- [x] T021 Add initial unit tests for indicators in `tests/unit/test_indicators_basic.py`
- [x] T022 [P] Add unit tests for manifest validation in `tests/unit/test_manifest.py`
- [x] T023 [P] Add unit tests for id determinism in `tests/unit/test_id_factory.py`
- [x] T024 Add unit tests for reproducibility service hash stability in `tests/unit/test_reproducibility.py`
- [x] T025 Add unit tests for metrics aggregator zero-trade case in `tests/unit/test_metrics_zero.py`

## Phase 3: User Story US1 (P1) - Long Trade Signal

Implements long-side logic; independently testable.

- [x] T026 [US1] Implement trend classifier in `src/strategy/trend_pullback/trend_classifier.py`
- [x] T027 [P] [US1] Implement pullback detector in `src/strategy/trend_pullback/pullback_detector.py`
- [x] T028 [P] [US1] Implement reversal pattern & momentum turn logic in `src/strategy/trend_pullback/reversal.py` including pullback expiry handling (FR-021: PULLBACK_MAX_AGE timeout)
- [x] T029 [US1] Implement long signal generator in `src/strategy/trend_pullback/signal_generator.py`
- [x] T030 [P] [US1] Implement risk manager (ATR stop calc + position sizing) in `src/risk/manager.py`
- [x] T031 [US1] Implement execution simulator with entry/exit logic including exit mode precedence rule (FR-026: fixed R target with trailing stop timeout fallback) in `src/backtest/execution.py`
- [x] T032 [P] [US1] Wire metrics ingestion for executions in `src/backtest/metrics_ingest.py`
- [x] T033 [US1] Implement observability reporter in `src/backtest/observability.py`
- [x] T034 [US1] Create CLI command `src/cli/run_long_backtest.py` for running long-signal-only backtest
- [x] T035 [US1] Add integration test for acceptance scenarios in `tests/integration/test_us1_long_signal.py`
- [ ] T036 [P] [US1] Add unit tests for reversal patterns in `tests/unit/test_reversal_patterns.py`
- [ ] T037 [US1] Add unit tests for risk sizing rounding in `tests/unit/test_risk_manager_rounding.py`
- [ ] T038 [US1] Add performance test harness stub in `tests/performance/test_long_signal_perf.py`

## Phase 4: User Story US2 (P2) - Short Trade Signal

Adds symmetry; reuses components where possible.

- [ ] T039 [US2] Extend signal generator to support short logic in `src/strategy/trend_pullback/signal_generator.py`
- [ ] T040 [P] [US2] Extend reversal logic tests for bearish patterns in `tests/unit/test_reversal_patterns.py`
- [ ] T041 [US2] Add short-specific integration test acceptance scenarios in `tests/integration/test_us2_short_signal.py`
- [ ] T042 [P] [US2] Add risk manager test for short stop direction in `tests/unit/test_risk_manager_short.py`
- [ ] T043 [US2] Add cooldown enforcement test in `tests/unit/test_cooldown.py`
- [ ] T044 [P] [US2] Update CLI to toggle direction modes `src/cli/run_backtest.py`

## Phase 5: User Story US3 (P3) - Backtest Result Generation

Full metrics, error handling, zero-trade case.

- [ ] T045 [US3] Implement full metrics calculations (expectancy, Sharpe estimate, profit factor) in `src/backtest/metrics.py`
- [ ] T046 [P] [US3] Implement drawdown curve & max drawdown computation in `src/backtest/drawdown.py`
- [ ] T047 [US3] Implement volatility regime classifier in `src/strategy/trend_pullback/volatility_regime.py`
- [ ] T048 [P] [US3] Implement data gap handling in ingestion `src/io/ingestion.py`
- [ ] T049 [US3] Implement reproducibility hash finalize & verify in `src/backtest/reproducibility.py`
- [ ] T050 [P] [US3] Implement CLI backtest command output JSON `src/cli/run_backtest.py`
- [ ] T051 [US3] Add integration test for manifest missing error path in `tests/integration/test_us3_manifest_error.py`
- [ ] T052 [US3] Add integration test for zero-trade metrics in `tests/integration/test_us3_zero_trades.py`
- [ ] T053 [P] [US3] Add performance throughput test `tests/performance/test_throughput.py`
- [ ] T054 [US3] Add memory footprint measurement test `tests/performance/test_memory_usage.py`

## Phase 6: Polish & Cross-Cutting

Refinements, quality, deferred items groundwork.

- [ ] T055 Add statistical significance test harness (p-value) in `tests/integration/test_significance.py`
- [ ] T056 [P] Add volatility regime adaptive sizing placeholder in `src/risk/adaptive_sizing.py`
- [ ] T057 Add Stoch RSI optional indicator in `src/indicators/stoch_rsi.py`
- [ ] T058 [P] Add higher timeframe filter implementation in `src/strategy/trend_pullback/htf_filter.py` (FR-016, FR-028: optional HTF EMA alignment check)
- [ ] T059 [P] Add configuration documentation section in `README.md`
- [ ] T060 Add ruff configuration file `.ruff.toml` with basic lint rules
- [ ] T061 [P] Add pre-commit config `.pre-commit-config.yaml` for formatting & linting
- [ ] T062 Add CLI help documentation in `src/cli/__init__.py`
- [ ] T063 Add CLI dry-run mode flag in `src/cli/run_backtest.py` (FR-024: emit signals without execution)
- [ ] T064 Final pass to ensure reproducibility hash documented in `specs/001-trend-pullback/quickstart.md`
- [ ] T065 [P] Add example Jupyter notebook `examples/long_signal_walkthrough.ipynb` (synthetic demonstration)
- [ ] T066 Add CHANGELOG entry in `CHANGELOG.md` summarizing feature implementation

## Dependency Graph (User Story Order)

```text
Setup -> Foundational -> US1 -> US2 -> US3 -> Polish
US1 provides core signal infra reused by US2 and metrics base used by US3.
- US2 depends on US1 trend/pullback logic (shared). US3 depends on execution & metrics from US1/US2.
```

## Parallel Execution Examples

- During Foundational: T013, T014, T019, T022, T023 can run in parallel (independent files)
- US1 Phase: T027, T028, T030, T032, T036 can run in parallel after T026
- US2 Phase: T040, T042, T044 in parallel after T039
- US3 Phase: T046, T048, T050, T053 in parallel after T045
- Polish Phase: T056, T058, T060, T063 in parallel after T055

## Independent Test Criteria by Story

- US1: Long signal emitted only after valid pullback + reversal; no emission in ranging conditions.
- US2: Short signal mirrors US1 logic; verifies direction correctness & cooldown.
- US3: Metrics generated (win_rate, avg_R, expectancy, max_drawdown_R, Sharpe_estimate); zero-trade and missing manifest scenarios handled gracefully.

## Task Counts

- Setup: 10
- Foundational: 15
- US1: 13
- US2: 6
- US3: 10
- Polish: 10
- Total: 64

## Suggested MVP Scope

MVP = Complete Setup + Foundational + US1 (first 38 tasks) delivering validated long trade signals and basic execution + metrics.

```text

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

- Setup: 10
- Foundational: 15
- US1: 13
- US2: 6
- US3: 10
- Polish: 12
- **Total: 66 tasks**

## Suggested MVP Scope

MVP = Complete Setup + Foundational + US1 (first 38 tasks) delivering validated long trade signals and basic execution + metrics.

## Format Validation

All tasks follow required format: `- [ ] T### optional [P] optional [USn] Description with file path`. Story labels only appear in story phases. Parallel markers applied only where no dependency conflict.

---
End of tasks.md
