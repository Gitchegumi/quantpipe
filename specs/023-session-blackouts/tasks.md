# Tasks: Session Blackouts + High-Impact News Avoidance

**Input**: Design documents from `/specs/023-session-blackouts/`  
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Tests**: Unit and integration tests are included as this feature involves critical backtesting logic.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create blackout subpackage structure and base configuration

- [x] T001 Create blackout subpackage directory `src/risk/blackout/`
- [x] T002 Create module init file `src/risk/blackout/__init__.py` with public exports
- [x] T003 [P] Create test directory `tests/unit/blackout/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core entities and configuration that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create `BlackoutWindow` dataclass in `src/risk/blackout/windows.py` (start_utc, end_utc, source)
- [x] T005 Create `NewsEvent` dataclass in `src/risk/blackout/calendar.py` (event_name, currency, event_time_utc)
- [x] T006 [P] Create `NewsBlackoutConfig` pydantic model in `src/risk/blackout/config.py`
- [x] T007 [P] Create `SessionBlackoutConfig` pydantic model in `src/risk/blackout/config.py`
- [x] T008 Create `BlackoutConfig` composite model in `src/risk/blackout/config.py`
- [x] T009 Add `blackout: BlackoutConfig | None = None` field to `src/risk/config.py` (RiskConfig)
- [x] T010 Update `src/risk/__init__.py` to export blackout components
- [x] T011 [P] Create unit test `tests/unit/blackout/test_config.py` for config validation

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 3 - Generate Rule-Based News Calendar (Priority: P3 → Executed First) 🎯 MVP

**Goal**: Generate deterministic NFP/IJC event calendars without external dependencies

**Independent Test**: Generate calendar for 2020, verify 52 IJC events (Thursdays) and 12 NFP events (first Fridays)

> **Note**: US3 is executed first because US1 and US2 depend on calendar generation

### Unit Tests for User Story 3

- [x] T012 [P] [US3] Create `tests/unit/blackout/test_holidays.py` with holiday detection tests
- [x] T013 [P] [US3] Create `tests/unit/blackout/test_calendar.py` with NFP/IJC generation tests

### Implementation for User Story 3

- [x] T014 [P] [US3] Implement `is_us_market_holiday(date)` in `src/risk/blackout/holidays.py`
- [x] T015 [P] [US3] Implement `get_us_holidays_for_year(year)` in `src/risk/blackout/holidays.py`
- [x] T016 [US3] Implement `generate_nfp_events(start, end)` in `src/risk/blackout/calendar.py` (first Friday of month)
- [x] T017 [US3] Implement `generate_ijc_events(start, end)` in `src/risk/blackout/calendar.py` (every Thursday)
- [x] T018 [US3] Implement `generate_news_calendar(start, end, event_types)` in `src/risk/blackout/calendar.py`
- [x] T019 [US3] Add holiday skip logic to calendar generation (skip events on U.S. holidays)
- [x] T020 [US3] Add DST-aware timezone conversion (America/New_York → UTC)
- [x] T021 [US3] Run and verify all US3 unit tests pass: `poetry run pytest tests/unit/blackout/test_calendar.py tests/unit/blackout/test_holidays.py -v`

**Checkpoint**: Calendar generation works independently - can generate and export NFP/IJC events

---

## Phase 4: User Story 1 - Enable News Blackouts During Backtests (Priority: P1)

**Goal**: Block new trade entries during news event windows (NFP, IJC)

**Independent Test**: Run backtest with `news.enabled=True`, verify zero entries within 10min before → 30min after NFP

**Depends on**: US3 (calendar generation)

### Unit Tests for User Story 1

- [x] T022 [P] [US1] Create `tests/unit/blackout/test_windows.py` with window merge/overlap tests

### Implementation for User Story 1

- [x] T023 [US1] Implement `expand_news_windows(events, config)` in `src/risk/blackout/windows.py`
- [x] T024 [US1] Implement `merge_overlapping_windows(windows)` in `src/risk/blackout/windows.py`
- [x] T025 [US1] Implement `is_in_blackout(timestamp, windows)` in `src/risk/blackout/windows.py`
- [x] T026 [US1] Implement **vectorized** `filter_blackout_signals(indices, timestamps, windows)` in `src/backtest/signal_filter.py` using NumPy boolean masks (NO per-candle loops)
- [x] T027 [US1] Add telemetry logging for blocked entries in `src/risk/blackout/windows.py`
- [x] T028 [US1] Run and verify all US1 unit tests pass: `poetry run pytest tests/unit/blackout/test_windows.py -v`

**Checkpoint**: News blackouts work independently - entries blocked during NFP/IJC windows

---

## Phase 5: User Story 2 - Enable Session Blackouts During Backtests (Priority: P2)

**Goal**: Block new trade entries during NY close → Asian open gap

**Independent Test**: Run backtest with `sessions.enabled=True`, verify no entries in session gap

**Depends on**: US1 (window merging logic)

### Implementation for User Story 2

- [x] T029 [US2] Implement `expand_session_windows(date_range, config)` in `src/risk/blackout/windows.py`
- [x] T030 [US2] Add session window tests to `tests/unit/blackout/test_windows.py`
- [x] T031 [US2] Add session anchor configuration (NY close: 17:00 ET, Asian open: 09:00 Tokyo)
- [x] T032 [US2] Run and verify session window tests pass: `poetry run pytest tests/unit/blackout/test_windows.py -v`

**Checkpoint**: Session blackouts work - entries blocked during NY close → Asian open

---

## Phase 6: Integration & Orchestrator Wiring

**Purpose**: Wire blackout checks into backtest execution pipeline

- [x] T033 Add blackout window building to backtest orchestrator in `src/backtest/orchestrator.py`
- [x] T034 Wire `filter_blackout_signals` into signal filtering pipeline in `src/backtest/orchestrator.py`
- [ ] T035 Add optional force-close callback structure (stub for future implementation)
- [x] T036 [P] Create integration test `tests/integration/test_blackout_backtest.py`
- [x] T037 Run integration tests: `poetry run pytest tests/integration/test_blackout_backtest.py -v`

**Checkpoint**: End-to-end blackout filtering works in real backtests

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, and final validation

- [x] T038 [P] Update `src/risk/blackout/__init__.py` with complete public API exports
- [ ] T039 [P] Add docstrings to all public functions (PEP 257 compliance)
- [ ] T040 Run full linting: `poetry run ruff check src/risk/blackout/`
- [x] T041 Run full test suite: `poetry run pytest tests/unit/blackout/ tests/integration/test_blackout_backtest.py -v`
- [ ] T042 Validate quickstart.md examples work as documented
- [ ] T043 [P] Update GEMINI.md with new module reference

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **US3 Calendar (Phase 3)**: Depends on Foundational - executed FIRST (other stories depend on it)
- **US1 News (Phase 4)**: Depends on US3 (needs calendar events)
- **US2 Session (Phase 5)**: Depends on US1 (reuses window merge logic)
- **Integration (Phase 6)**: Depends on US1 + US2
- **Polish (Phase 7)**: Depends on Integration

### User Story Dependencies

```text
                    ┌─────────────────┐
                    │ Phase 1: Setup  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Phase 2: Found. │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ US3: Calendar   │ ← MVP (generates events)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ US1: News       │ ← Uses calendar events
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ US2: Sessions   │ ← Reuses window logic
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Phase 6: Integ. │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Phase 7: Polish │
                    └─────────────────┘
```

### Parallel Opportunities

**Within Phase 2 (Foundational)**:

```bash
# These can run in parallel:
Task: T006 [P] Create NewsBlackoutConfig
Task: T007 [P] Create SessionBlackoutConfig
Task: T011 [P] Create test_config.py
```

**Within Phase 3 (US3)**:

```bash
# These can run in parallel:
Task: T012 [P] Create test_holidays.py
Task: T013 [P] Create test_calendar.py
Task: T014 [P] Implement is_us_market_holiday
Task: T015 [P] Implement get_us_holidays_for_year
```

---

## Implementation Strategy

### MVP First (US3 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 3 (Calendar Generation)
4. **STOP and VALIDATE**: Test calendar output for 2023
5. Export calendar to CSV for manual verification

### Incremental Delivery

1. Setup + Foundational → Base structure ready
2. Add US3 (Calendar) → Test → Verify deterministic output
3. Add US1 (News Blackouts) → Test → Run backtest, verify blocked entries
4. Add US2 (Session Blackouts) → Test → Run backtest, verify session gaps handled
5. Integration → Full end-to-end validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US3 is prioritized over US1/US2 because it generates the events they consume
- Commit after each task using format: `feat(023): Description (T###)`
- Run `poetry run pytest tests/unit/blackout/ -v` after each implementation phase
- Total tasks: 43
