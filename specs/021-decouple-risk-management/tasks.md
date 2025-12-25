# Tasks: Decouple Risk Management from Strategy

**Input**: Design documents from `/specs/021-decouple-risk-management/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: Included per verification plan in plan.md. Existing risk tests (6 files) verified during development; new tests created per SC-001 through SC-006.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root (per plan.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for risk management module

- [x] T001 Create policies directory structure at src/risk/policies/
- [x] T002 [P] Create src/risk/policies/**init**.py with policy exports
- [x] T003 [P] Create src/models/signal.py with Signal dataclass (symbol, direction, timestamp, entry_hint, metadata)
- [x] T004 [P] Create src/models/order_plan.py with OrderPlan dataclass (signal, entry_price, stop_price, target_price, position_size, etc.)
- [x] T005 Update src/models/**init**.py to export Signal and OrderPlan

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Create src/risk/config.py with RiskConfig pydantic model (risk_pct, stop_policy, take_profit_policy, position_sizer, max_position_size)
- [x] T007 Create src/risk/registry.py with PolicyRegistry class for string-based policy lookup
- [x] T008 [P] Create StopPolicy protocol in src/risk/policies/stop_policies.py (initial_stop, update_stop methods)
- [x] T009 [P] Create TakeProfitPolicy protocol in src/risk/policies/tp_policies.py (initial_tp method)
- [x] T010 [P] Create PositionSizer protocol in src/risk/policies/position_sizers.py (size method)
- [x] T011 Add RiskManager class to src/risk/manager.py (accepts RiskConfig, composes policies, build_orders method)
- [x] T012 Update src/risk/**init**.py to export RiskManager, RiskConfig, and policy protocols
- [x] T013 [P] Create tests/unit/test_risk_config.py validating RiskConfig schema and defaults

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Change Risk Policy Without Code Modification (Priority: P1) 🎯 MVP

**Goal**: Enable runtime selection of risk policies via config/CLI without touching strategy code

**Independent Test**: Run same strategy with two different risk configs, confirm different OrderPlan outcomes

### Tests for User Story 1

- [x] T014 [P] [US1] Create tests/unit/test_risk_manager.py with test_build_orders_with_different_configs (SC-001)
- [x] T015 [P] [US1] Create tests/integration/test_risk_policy_switching.py validating CLI policy switching (SC-002)

### Implementation for User Story 1

- [x] T016 [US1] Implement ATRStop class in src/risk/policies/stop_policies.py (initial_stop using ATR multiplier)
- [x] T017 [US1] Implement RiskMultipleTP class in src/risk/policies/tp_policies.py (TP at N× risk distance)
- [x] T018 [US1] Implement NoTakeProfit class in src/risk/policies/tp_policies.py (returns None)
- [x] T019 [US1] Register ATRStop, RiskMultipleTP, NoTakeProfit in src/risk/registry.py
- [x] T020 [US1] Add --risk-config, --risk-pct, --stop-policy, --tp-policy, --rr-ratio args to src/cli/run_backtest.py
- [x] T021 [US1] Parse CLI args and construct RiskConfig in src/cli/run_backtest.py
- [ ] T022 [US1] Modify src/backtest/orchestrator.py to accept optional RiskManager parameter
- [ ] T023 [US1] Inject RiskManager into \_run_vectorized_backtest() and transform signals to OrderPlans
- [ ] T024 [US1] Add risk manager labeling to backtest output (strategy_name, risk_manager_type, risk_params) for SC-005

**Checkpoint**: User Story 1 complete - can switch risk policies via CLI without code changes

---

## Phase 4: User Story 2 - Position Sizing by Risk Percent (Priority: P1)

**Goal**: Calculate position size automatically using risk_amount / (stop_distance × pip_value)

**Independent Test**: Validate position size matches formula with various risk_pct and stop distances

### Tests for User Story 2

- [ ] T025 [P] [US2] Create tests/unit/test_position_sizers.py with test_risk_percent_sizing_formula
- [ ] T026 [P] [US2] Add test_position_size_edge_cases in tests/unit/test_position_sizers.py (zero stop, max cap, JPY pairs) for SC-006

### Implementation for User Story 2

- [ ] T027 [US2] Implement RiskPercentSizer class in src/risk/policies/position_sizers.py using existing calculate_position_size logic
- [ ] T028 [US2] Register RiskPercentSizer in src/risk/registry.py
- [ ] T029 [US2] Wire PositionSizer into RiskManager.build_orders() in src/risk/manager.py
- [ ] T030 [US2] Add max_position_size capping with warning log in RiskPercentSizer

**Checkpoint**: User Story 2 complete - position sizing by risk percent works

---

## Phase 5: User Story 3 - Trailing Stop Updates on Each Bar (Priority: P2)

**Goal**: ATR-based trailing stop ratchets in favorable direction as price moves

**Independent Test**: Run simulation, verify stop price updates on consecutive bars as price moves favorably

### Tests for User Story 3

- [ ] T031 [P] [US3] Create tests/unit/test_stop_policies.py with test_atr_trailing_ratchet_up
- [ ] T032 [P] [US3] Add test_atr_trailing_never_widens in tests/unit/test_stop_policies.py

### Implementation for User Story 3

- [ ] T033 [US3] Implement ATRTrailingStop class in src/risk/policies/stop_policies.py with initial_stop and update_stop methods
- [ ] T034 [US3] Register ATRTrailingStop in src/risk/registry.py
- [ ] T035 [US3] Add update_trailing() method to RiskManager in src/risk/manager.py
- [ ] T036 [US3] Modify src/backtest/orchestrator.py to call RiskManager.update_trailing() per bar during simulation
- [ ] T037 [US3] Record exit_reason as "trailing_stop_hit" when trailing stop triggers

**Checkpoint**: User Story 3 complete - trailing stops ratchet correctly

---

## Phase 6: User Story 4 - Multiple Risk Policies Available at Launch (Priority: P2)

**Goal**: Ship with at least two stop policies and two TP policies; new policies addable without code changes

**Independent Test**: Backtest same strategy with each policy, confirm distinct trade lifecycles

### Tests for User Story 4

- [ ] T038 [P] [US4] Create tests/unit/test_tp_policies.py with tests for RiskMultipleTP and NoTakeProfit
- [ ] T039 [P] [US4] Add test_policy_registry_lookup in tests/unit/test_risk_config.py

### Implementation for User Story 4

- [ ] T040 [US4] Implement FixedPipsStop class in src/risk/policies/stop_policies.py
- [ ] T041 [US4] Register FixedPipsStop in src/risk/registry.py
- [ ] T042 [US4] Add --atr-mult, --atr-period, --fixed-pips CLI args to src/cli/run_backtest.py
- [ ] T043 [US4] Validate policy combinations in RiskConfig (e.g., ATR policies require period)
- [ ] T044 [US4] Document custom policy creation in specs/021-decouple-risk-management/quickstart.md

**Checkpoint**: User Story 4 complete - multiple policies available

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting multiple user stories, backward compatibility, documentation

- [ ] T045 Implement legacy adapter for existing TradeSignal-based strategies in src/risk/manager.py (FR-010)
- [ ] T046 Create default RiskConfig matching current behavior (0.25% risk, 2× ATR stop, 2:1 TP) in src/risk/config.py
- [ ] T047 Add regression test in tests/integration/test_risk_policy_switching.py verifying default config matches legacy behavior (SC-004)
- [ ] T048 Verify no strategy-to-risk imports via grep check (SC-003)
- [ ] T049 [P] Run poetry run black src/ tests/ --check
- [ ] T050 [P] Run poetry run ruff check src/ tests/
- [ ] T051 [P] Run poetry run pylint src/ --score=yes
- [ ] T052 Run full test suite: pytest tests/ -v --ignore=tests/performance/
- [ ] T053 [P] Update specs/021-decouple-risk-management/quickstart.md with final CLI examples
- [ ] T054 Create PR using .github/pull_request_template.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-6)**: All depend on Foundational phase completion
  - US1 and US2 can run in parallel (both P1 priority, independent components)
  - US3 depends on US1 (ATRTrailingStop extends stop policy architecture)
  - US4 depends on US1 (adds more policies to registry)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

| Story    | Can Start After | Dependencies                  | Independent?             |
| -------- | --------------- | ----------------------------- | ------------------------ |
| US1 (P1) | Phase 2         | None                          | ✅ Yes                   |
| US2 (P1) | Phase 2         | None                          | ✅ Yes                   |
| US3 (P2) | US1             | Uses stop policy architecture | ⚠️ Partial (extends US1) |
| US4 (P2) | US1             | Registry and CLI structure    | ⚠️ Partial (extends US1) |

### Within Each User Story

- Tests written first and MUST FAIL before implementation
- Models/protocols before implementations
- Implementations before CLI integration
- CLI integration before orchestrator changes

### Parallel Opportunities

- **Phase 1**: T002, T003, T004 can run in parallel
- **Phase 2**: T008, T009, T010, T013 can run in parallel
- **Phase 3-6**: All test tasks marked [P] can run in parallel within their phase
- **Phase 7**: T049, T050, T051, T053 can run in parallel

---

## Parallel Example: Phase 2

```bash
# Launch protocol definitions in parallel:
Task: "Create StopPolicy protocol in src/risk/policies/stop_policies.py"
Task: "Create TakeProfitPolicy protocol in src/risk/policies/tp_policies.py"
Task: "Create PositionSizer protocol in src/risk/policies/position_sizers.py"
Task: "Create tests/unit/test_risk_config.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test policy switching via CLI
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy (MVP!)
3. Add User Story 2 → Test sizing formula → Deploy
4. Add User Story 3 → Test trailing stops → Deploy
5. Add User Story 4 → Test multiple policies → Deploy
6. Polish phase → Final release

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (CLI & orchestrator)
   - Developer B: User Story 2 (position sizing)
3. After US1 complete:
   - Developer A: User Story 3 (trailing stops)
   - Developer B: User Story 4 (more policies)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group (per Constitution XI)
- Stop at any checkpoint to validate story independently
- Existing risk tests in tests/unit/test*risk*\*.py should pass throughout implementation

---

## Task Summary

| Phase                 | Task Count | Parallel Tasks |
| --------------------- | ---------- | -------------- |
| Phase 1: Setup        | 5          | 3              |
| Phase 2: Foundational | 8          | 4              |
| Phase 3: US1 (P1) MVP | 11         | 2              |
| Phase 4: US2 (P1)     | 6          | 2              |
| Phase 5: US3 (P2)     | 7          | 2              |
| Phase 6: US4 (P2)     | 7          | 2              |
| Phase 7: Polish       | 10         | 4              |
| **Total**             | **54**     | **19**         |
