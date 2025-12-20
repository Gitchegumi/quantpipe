# Tasks: Interactive Visualization

**Feature**: 014-interactive-viz
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

## Phase 1: Setup & Configuration

**Goal**: Initialize dependencies and prepare the environment for visualization.

- [ ] T001 Install `lightweight-charts-python` dependency in pyproject.toml
- [ ] T002 Update poetry lock file and install environment
- [ ] T003 Create `src/visualization` module structure with `__init__.py`

## Phase 2: Foundational Implementation

**Goal**: Implement the core visualization engine capable of rendering a chart.

- [ ] T004 [P] Create `src/visualization/interactive.py` with basic `plot_backtest_results` signature
- [ ] T005 [P] Implement `_prepare_candle_data` helper in `interactive.py` to convert Polars DF to pandas OHLC format
- [ ] T006 [P] Implement `_prepare_indicator_data` helper in `interactive.py` to extraction indicator series
- [ ] T007 Implement basic chart rendering in `plot_backtest_results` (candles only) in `src/visualization/interactive.py`
- [ ] T008 Add `test_plot_backtest_results_calls` to `tests/visualization/test_interactive.py` (mocked)

## Phase 3: User Story 1 (View Results)

**Goal**: Visual verification of backtest results with indicators.

- [ ] T009 [US1] Update `plot_backtest_results` to loop through indicators and add line series in `src/visualization/interactive.py`
- [ ] T010 [US1] Implement `_add_trade_markers` helper to convert `BacktestResult.executions` to marker data
- [ ] T011 [US1] Integration: Integrate `plot_backtest_results` into `src/cli/run_backtest.py` behind `--visualize` flag
- [ ] T012 [US1] Manual Verify: Run `backtest --visualize` and confirm chart opens with candles, indicators, and markers

## Phase 4: User Story 2 (Interactive Analysis)

**Goal**: Zoom, pan, and inspect data points.

- [ ] T013 [US2] Verify and fine-tune zoom/pan settings in `lightweight-charts` configuration (default usually suffices)
- [ ] T014 [US2] Customize tooltip/crosshair behavior if needed in `src/visualization/interactive.py`
- [ ] T015 [US2] Manual Verify: Check zoom/pan responsiveness on a large dataset

## Phase 5: Polish & Cross-Cutting

- [ ] T016 Validate performance with 10-year dataset (load time check)
- [ ] T017 Finalize documentation in `docs/` or `quickstart.md` updates
- [ ] T018 Cleanup: Ensure no heavy imports in main path if `--visualize` is not used

## Dependencies

- Phase 2 must complete before Phase 3
- T011 requires core visualization (T007) and markers (T010)

## Parallel Execution

- T004, T005, T006 can be implemented in parallel.
