# Tasks: CTI Metrics & Progression (Feature 027)

**Feature Branch**: `027-cti-metrics-progression`
**Spec**: `specs/027-cti-metrics-progression/spec.md`

## Dependencies

- Phase 1 (Setup) blocks all other phases.
- Phase 2 (Metrics) blocks Phase 4 (Scaling) as scaling reports need metrics.
- Phase 3 (Challenge) and Phase 4 (Scaling) can be parallelized but both block Phase 5 (Integration).

## Phase 1: Setup & Configuration

**Goal**: Initialize configuration structures and load CTI presets.

- [ ] T001 [Setup] Create config directory `src/config/presets/cti/`
- [ ] T002 [Setup] Add `cti_1_step_challenge.json` to `src/config/presets/cti/`
- [ ] T003 [Setup] Add `cti_2_step_challenge.json` to `src/config/presets/cti/`
- [ ] T004 [Setup] Add `cti_instant_funding.json` to `src/config/presets/cti/`
- [ ] T005 [Setup] Add `cti_challenge_scaling_plan.json` to `src/config/presets/cti/`
- [ ] T006 [Setup] Add `cti_instant_scaling_plan.json` to `src/config/presets/cti/`
- [ ] T007 [Setup] Create `src/risk/prop_firm/` directory and `__init__.py`
- [ ] T008 [Setup] Implement Pydantic models in `src/risk/prop_firm/models.py` (`ChallengeConfig`, `ScalingConfig`, `LifeResult`)
- [ ] T009 [Setup] Implement configuration loader in `src/risk/prop_firm/loader.py`
- [ ] T010 [Setup] Create `tests/unit/prop_firm/test_loader.py` to verify JSON parsing

## Phase 2: Advanced Statistical Metrics (User Story 1 - P1)

**Goal**: Implement Sharpe, Sortino, and other key trading metrics.

- [ ] T011 [US1] Update `MetricsSummary` in `src/models/core.py` with new fields (sortino, duration, streaks)
- [ ] T012 [P] [US1] Implement `calculate_sortino` in `src/backtest/metrics.py`
- [ ] T013 [P] [US1] Implement `calculate_avg_duration` in `src/backtest/metrics.py` (Arithmetic Mean)
- [ ] T014 [P] [US1] Implement `calculate_streaks` in `src/backtest/metrics.py` (Max consecutive wins/losses)
- [ ] T015 [US1] Update `compute_metrics` in `src/backtest/metrics.py` to populate new fields
- [ ] T016 [US1] Create `tests/unit/test_metrics_advanced.py` to verify calculations against synthetic data

## Phase 3: CTI Challenge Rules Enforcement (User Story 2 - P1)

**Goal**: Evaluate backtest results against specific Challenge rules (Drawdown, Daily Loss).

- [ ] T017 [US2] Implement `reconstruct_daily_balance` logic in `src/risk/prop_firm/evaluator.py` (for Daily Loss check)
- [ ] T018 [US2] Implement `evaluate_challenge(result, config)` in `src/risk/prop_firm/evaluator.py`
- [ ] T019 [US2] Create test fixture with passing/failing equity curves in `tests/unit/prop_firm/conftest.py`
- [ ] T020 [US2] Create `tests/unit/prop_firm/test_evaluator.py` validating Max Drawdown (Closed Balance) and Daily Loss triggers

## Phase 4: Scaling & Independent Lives (User Story 3 - P2)

**Goal**: Simulate 4-month review periods, account promotion, and reset-to-entry logic.

- [ ] T021 [US3] Implement `evaluate_scaling` in `src/risk/prop_firm/scaling.py` with 4-month periodic review loop
- [ ] T022 [US3] Add "Reset Logic" to `scaling.py`: On failure, close current Life, reset balance to Tier 1, start new Life
- [ ] T023 [US3] Implement `ScalingReport` generation aggregating multiple `LifeResult` objects
- [ ] T024 [US3] Create `tests/unit/prop_firm/test_scaling.py`:
  - Verify promotion on >10% profit
  - Verify reset on drawdown violation
  - Verify independent PnL reporting (Life 1 PnL != Life 2 PnL)

## Phase 5: Integration & Polish

**Goal**: Expose new functionality via CLI and Report.

- [ ] T025 [CLI] Update `src/cli/run_backtest.py` to accept `--cti-mode` and `--account-size` arguments
- [ ] T026 [CLI] Wire up post-backtest evaluation: Load Config -> Run Backtest -> Run Evaluation/Scaling
- [ ] T027 [Report] Update `src/backtest/report.py` to render `ChallengeStatus` and `ScalingReport` sections
- [ ] T028 [Report] Update `src/backtest/report.py` to display new Advanced Metrics
- [ ] T029 [Verification] Manual Test: Run 1-Step Challenge backtest (`tests/manual/test_cti_flow.bat`)
- [ ] T030 [Verification] Manual Test: Run Instant Funding backtest with Resets enabled

## Implementation Strategy

1. **MVP (T001-T020)**: Deliver Metrics + Basic Challenge Evaluation. This satisfies P1 stories.
2. **Full Feature (T021-T028)**: Add Scaling/Reset complication.
3. **Polish (T029-T030)**: Verify end-to-end.
