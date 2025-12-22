# Tasks: Multi-Symbol Backtest Visualization

**Input**: Design documents from `/specs/016-multi-symbol-viz/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, quickstart.md ✓

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, etc.)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Enable multi-symbol visualization in CLI (remove blocking code)

- [ ] T001 Remove multi-symbol visualization skip block in `src/cli/run_backtest.py` (lines 1287-1290)
- [ ] T002 Update CLI to call `plot_backtest_results()` for multi-symbol results in `src/cli/run_backtest.py`

---

## Phase 2: Foundational Bug Fixes

**Purpose**: Fix existing `_create_multi_symbol_layout()` bugs that block all user stories

**⚠️ CRITICAL**: These bugs must be fixed before any visualization features work

- [ ] T003 Fix tuple unpacking on line 221 in `src/visualization/datashader_viz.py` - `_create_candlestick_chart()` returns `(chart, xlim)`
- [ ] T004 Fix `_create_indicator_overlays()` call on line 223 in `src/visualization/datashader_viz.py` - pass required `pair` and `xlim` arguments
- [ ] T005 Change `shared_axes=False` to `True` on line 251 in `src/visualization/datashader_viz.py`
- [ ] T006 Add symbol count warning (5+ symbols) in `_create_multi_symbol_layout()` in `src/visualization/datashader_viz.py`

**Checkpoint**: Foundation ready - multi-symbol visualization now renders

---

## Phase 3: User Story 1 & 2 - Multi-Symbol Charts with Trade Markers (Priority: P1) 🎯 MVP

**Goal**: Render separate price chart panels per symbol with correct trade markers

**Independent Test**: Run `poetry run python -m src.cli.run_backtest --pair EURUSD USDJPY --direction BOTH --visualize` and verify stacked charts with trade markers appear

### Implementation for US1 & US2

- [ ] T007 [US1] Verify symbol data filtering works correctly in `_create_multi_symbol_layout()` in `src/visualization/datashader_viz.py`
- [ ] T008 [US2] Verify trade markers display on correct symbol's chart (no cross-contamination) in `src/visualization/datashader_viz.py`
- [ ] T009 [US2] Verify TP/SL lines (green/red dotted) render per symbol in `src/visualization/datashader_viz.py`

**Checkpoint**: MVP complete - multi-symbol visualization with trade markers works

---

## Phase 4: User Story 3 - Aggregated Portfolio Equity Curve (Priority: P2)

**Goal**: Display aggregated portfolio equity curve below all symbol charts

**Independent Test**: Run multi-symbol backtest with `--visualize` and verify portfolio curve shows cumulative dollar performance

### Implementation for US3

- [ ] T010 [US3] Verify portfolio equity curve aggregates trades from all symbols in `_create_multi_symbol_layout()` in `src/visualization/datashader_viz.py`
- [ ] T011 [US3] Verify portfolio curve uses correct initial balance ($2,500) and risk per trade ($6.25) in `src/visualization/datashader_viz.py`

**Checkpoint**: Portfolio equity curve displays correctly

---

## Phase 5: User Story 4 - Timeframe Display (Priority: P2)

**Goal**: Show correct timeframe in chart title when not using default 1m

**Independent Test**: Run `--pair EURUSD USDJPY --timeframe 15m --visualize` and verify title shows "(15m)"

### Implementation for US4

- [ ] T012 [US4] Verify timeframe parameter is passed to `_create_multi_symbol_layout()` in `src/visualization/datashader_viz.py`
- [ ] T013 [US4] Verify chart title format includes timeframe suffix when not 1m in `src/visualization/datashader_viz.py`

**Checkpoint**: Timeframe displays correctly in titles

---

## Phase 6: User Story 5 - Synchronized Navigation and Crosshair (Priority: P2)

**Goal**: Sync pan/zoom across charts and add linked crosshairs

**Independent Test**: Open visualization, pan/zoom on one chart, verify all charts move together. Hover to see crosshair.

### Implementation for US5

- [ ] T014 [US5] Add `_create_linked_crosshair_hook()` helper function in `src/visualization/datashader_viz.py`
- [ ] T015 [US5] Create shared `CrosshairTool` instance for price/oscillator panels in `src/visualization/datashader_viz.py`
- [ ] T016 [US5] Create isolated `CrosshairTool` instance for PnL panel in `src/visualization/datashader_viz.py`
- [ ] T017 [US5] Apply crosshair hooks via `.opts(hooks=[...])` to all charts in `_create_multi_symbol_layout()` in `src/visualization/datashader_viz.py`
- [ ] T018 [US5] Verify `shared_axes=True` enables synchronized pan/zoom (already set in T005)

**Checkpoint**: Synchronized navigation and crosshairs work correctly

---

## Phase 7: Tests & Polish

**Purpose**: Add unit tests and run verification

- [ ] T019 [P] Create `tests/visualization/test_multi_symbol_viz.py` with test fixtures
- [ ] T020 [P] Add `test_create_multi_symbol_layout_returns_layout()` in `tests/visualization/test_multi_symbol_viz.py`
- [ ] T021 [P] Add `test_symbol_count_warning_logged()` in `tests/visualization/test_multi_symbol_viz.py`
- [ ] T022 [P] Add `test_crosshair_tools_present()` in `tests/visualization/test_multi_symbol_viz.py`
- [ ] T023 Run linting: `poetry run ruff check src/visualization/datashader_viz.py src/cli/run_backtest.py`
- [ ] T024 Run formatting: `poetry run black src/visualization/datashader_viz.py src/cli/run_backtest.py`
- [ ] T025 Run all visualization tests: `poetry run pytest tests/visualization/ -v`
- [ ] T026 Manual verification per quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - removes CLI block
- **Foundational (Phase 2)**: Depends on Phase 1 - fixes core bugs
- **US1/US2 (Phase 3)**: Depends on Phase 2 - core visualization
- **US3 (Phase 4)**: Depends on Phase 2 - can run parallel with Phase 3
- **US4 (Phase 5)**: Depends on Phase 2 - can run parallel with Phase 3/4
- **US5 (Phase 6)**: Depends on Phase 2 - crosshairs require working charts
- **Polish (Phase 7)**: Depends on all user story phases

### Parallel Opportunities

- T019-T022 (tests) can all run in parallel
- Phases 3, 4, 5 can run in parallel after Phase 2 completes
- Phase 6 (crosshairs) can run parallel with Phases 3-5 since it touches different code sections

---

## Implementation Strategy

### MVP First (Phases 1-3 Only)

1. Complete Phase 1: CLI enablement (T001-T002)
2. Complete Phase 2: Bug fixes (T003-T006)
3. Complete Phase 3: US1+US2 charts with markers (T007-T009)
4. **STOP and VALIDATE**: Test with `--pair EURUSD USDJPY --visualize`
5. This delivers the core issue #42 request

### Full Implementation

1. Complete MVP (Phases 1-3)
2. Add Phase 4: Portfolio curve (T010-T011)
3. Add Phase 5: Timeframe display (T012-T013)
4. Add Phase 6: Crosshairs (T014-T018)
5. Complete Phase 7: Tests and polish (T019-T026)

---

## Notes

- Most work is in `src/visualization/datashader_viz.py` - single file focus
- CLI change is minimal (just remove skip block)
- Existing `_create_multi_symbol_layout()` provides 80% of structure
- Crosshair feature is enhancement on top of working visualization
