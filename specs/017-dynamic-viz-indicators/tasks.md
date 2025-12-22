# Tasks: Dynamic Visualization Indicators

**Input**: Design documents from `/specs/017-dynamic-viz-indicators/`
**Prerequisites**: plan.md ✓, spec.md ✓, data-model.md ✓, quickstart.md ✓

**Tests**: Included - explicit requirements in spec.md for testing backward compatibility and visual verification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and model creation

- [ ] T001 [P] Create VisualizationConfig and IndicatorDisplayConfig dataclasses in src/models/visualization_config.py
- [ ] T002 [P] Add visualization_config to src/models/**init**.py exports

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Add optional get_visualization_config() method to Strategy protocol in src/strategy/base.py
- [ ] T004 Update \_create_indicator_overlays() signature to accept optional VisualizationConfig in src/visualization/datashader_viz.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Strategy-Defined Visualization Config (Priority: P1) 🎯 MVP

**Goal**: Strategies can define their own visualization configuration via get_visualization_config()

**Independent Test**: Run backtest with TrendPullbackStrategy and verify chart shows configured indicators with specified colors

### Tests for User Story 1

- [ ] T005 [P] [US1] Unit tests for IndicatorDisplayConfig creation and defaults in tests/unit/test_visualization_config.py
- [ ] T006 [P] [US1] Unit tests for VisualizationConfig with various configurations in tests/unit/test_visualization_config.py

### Implementation for User Story 1

- [ ] T007 [US1] Implement get_visualization_config() in TrendPullbackStrategy in src/strategy/trend_pullback/strategy.py
- [ ] T008 [US1] Implement config-based overlay creation in \_create_indicator_overlays() in src/visualization/datashader_viz.py
- [ ] T009 [US1] Thread viz_config parameter through plot_backtest_results() call chain in src/visualization/datashader_viz.py
- [ ] T010 [US1] Add warning logging for missing indicator columns in src/visualization/datashader_viz.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Backward Compatible Auto-Detection (Priority: P2)

**Goal**: Existing strategies without get_visualization_config() continue to work via auto-detection fallback

**Independent Test**: Run backtest with a strategy lacking get_visualization_config() and verify auto-detection still works

### Tests for User Story 2

- [ ] T011 [P] [US2] Integration test for auto-detection fallback when no config provided in tests/visualization/test_viz_config_integration.py

### Implementation for User Story 2

- [ ] T012 [US2] Implement fallback logic to auto-detect when config is None in src/visualization/datashader_viz.py
- [ ] T013 [US2] Add hasattr check for get_visualization_config() method in caller in src/visualization/datashader_viz.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Visible but Non-Overpowering Color Scheme (Priority: P3)

**Goal**: Indicator colors are visible on dark backgrounds but don't overpower candlesticks

**Independent Test**: Visual inspection of generated charts for color contrast and visibility

### Implementation for User Story 3

- [ ] T014 [P] [US3] Define default color palette constants for common indicators in src/models/visualization_config.py
- [ ] T015 [US3] Apply default colors when strategy config omits color in src/visualization/datashader_viz.py
- [ ] T016 [US3] Add color validation/fallback for invalid color specs in src/visualization/datashader_viz.py

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T017 [P] Update quickstart.md with actual usage examples in specs/017-dynamic-viz-indicators/quickstart.md
- [ ] T018 [P] Add docstrings to all new functions and classes per constitution standards
- [ ] T019 Run Black, Ruff, Pylint on all modified files and fix any issues
- [ ] T020 Run pytest on all new and existing visualization tests
- [ ] T021 Manual verification: run backtest with --visualize and confirm chart appearance

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - References same viz module but different code paths
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Enhances config defaults, no blocking deps

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/config before visualization logic
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T001, T002 can run in parallel (different files)
- T005, T006 can run in parallel (same test file, different test classes)
- T014 can run in parallel with other US3 tasks (adds to model file)
- T017, T018 can run in parallel (different files/concerns)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit tests for IndicatorDisplayConfig in tests/unit/test_visualization_config.py"
Task: "Unit tests for VisualizationConfig in tests/unit/test_visualization_config.py"

# After tests pass (verify they fail first):
Task: "Implement get_visualization_config() in TrendPullbackStrategy"
Task: "Implement config-based overlay creation"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T004)
3. Complete Phase 3: User Story 1 (T005-T010)
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Demo: Run backtest with `--visualize` and confirm TrendPullbackStrategy shows configured colors

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Demo (MVP!)
3. Add User Story 2 → Backward compatibility verified
4. Add User Story 3 → Color polish complete
5. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
