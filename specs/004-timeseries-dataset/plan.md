# Implementation Plan: Time Series Dataset Preparation

**Branch**: `004-timeseries-dataset` | **Date**: 2025-10-30 | **Spec**: `specs/004-timeseries-dataset/spec.md`
**Input**: Feature specification from `/specs/004-timeseries-dataset/spec.md`

**Note**: Generated via `/speckit.plan` workflow.

## Summary

Implement standardized dataset build pipeline that merges raw per-symbol CSV price data, performs deterministic 80/20 chronological split (older 80% test, newest 20% validation), generates metadata and summary reporting, and retools backtest execution to consume these partitions. Emphasis on preserving raw integrity (no filling/interpolation) while ensuring reproducibility and clear diagnostics.

## Technical Context

**Language/Version**: Python 3.11 (per project guidelines)
**Primary Dependencies**: numpy, pandas, pydantic, rich (logging/output), pytest (tests) – no new deps planned
**Storage**: File system (CSV inputs; processed outputs as CSV + JSON metadata)
**Testing**: pytest (unit for splitting logic, integration for multi-symbol build, performance for large dataset timing)
**Target Platform**: Local dev / CI (Windows & Linux compatibility assumed); no deployment target
**Project Type**: Single Python package (existing `src/` + `tests/` structure)
**Performance Goals**: Build ≤ 2 minutes for ~1M combined rows (sequential per symbol); memory usage fits within typical dev machine (<1GB resident)
**Constraints**: Line length ≤88 chars; lazy logging formatting; no mutation of price values; deterministic splits
**Scale/Scope**: Anticipated symbols: O(1–10); rows per symbol: up to low millions; time stamps at uniform or near-uniform minute granularity

NEEDS CLARIFICATION placeholders: None (spec clarifications resolved). All items concrete.

## Constitution Check

Gate Evaluation (Principle X & others):

- Dependency Management: Using Poetry, no new deps – PASS
- Code Quality: Will add docstrings, type hints, lazy logging – PASS (to be enforced in implementation)
- Logging Standard: Plan includes rich + lazy formatting – PASS
- Documentation: Will create quickstart, data-model, contracts (internal) – PASS
- Markdownlint: New docs will adhere to line length and structure – PASS

No violations requiring justification currently. Re-check after Phase 1 artifacts.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
src/
├── backtest/              # existing backtest logic (will integrate partition usage)
├── io/                    # add dataset builder module (new)
├── models/                # potential pydantic models for metadata
├── strategy/              # unchanged
└── utils/                 # (if needed for common helpers – avoid unless justified)

tests/
├── unit/
│   ├── test_dataset_split.py       # split logic
│   ├── test_metadata_generation.py # metadata
├── integration/
│   ├── test_multi_symbol_build.py  # end-to-end build
├── performance/
│   ├── test_large_build_timing.py  # timing assertions
└── fixtures/                       # sample raw price datasets
```

**Structure Decision**: Retain single-project layout; introduce dataset builder component within existing `src/io/` (or `src/backtest/io` if alignment preferred). Tests follow existing directory segmentation (unit/integration/performance). Avoid creating new top-level projects to minimize complexity.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --------- | ---------- | ------------------------------------ |
| (none)    | N/A        | Existing structure sufficient        |

## Phase 2: Implementation Planning (High-Level)

### Workstreams

- Dataset Builder Core (scan, merge, split)
- Metadata & Summary Generation
- Backtest Integration Adaptation
- CLI Commands & User Feedback
- Testing & Performance Validation

### Milestones

1. Core merge & split logic implemented with deterministic 80/20 partition.
2. Metadata + summary JSON generation complete.
3. Backtest module refactored to consume partitions; legacy single-file path removed.
4. CLI commands for build and backtest split mode exposed.
5. Test suite (unit + integration + performance) green; quality gates pass.

### Task Grouping (Outline)

- Core Logic:
  - Implement symbol discovery and raw file loader.
  - Merge & sort timestamps; compute gaps/overlaps metrics.
  - Partition logic (floor test size) and write CSV outputs.
- Metadata:
  - Per-symbol metadata builder.
  - Consolidated summary aggregator (duration tracking).
- Backtest Integration:
  - Adjust data loading interface to accept partition paths.
  - Separate metrics calculation per partition.
  - Graceful error when partitions absent.
- CLI:
  - Build command with optional symbol filter & force flag.
  - Backtest command supporting split mode.
- Testing:
  - Unit tests for partition size & determinism.
  - Unit tests for metadata correctness.
  - Integration test multi-symbol build end-to-end.
  - Performance test large synthetic dataset timing.
- Docs:
  - Update quickstart if command names differ.
  - README snippet referencing dataset build process.

### Risks & Mitigations

- Large memory footprint during merge → Stream reading + incremental concat.
- Schema mismatch frequency → Early validation & skip with clear reason.
- Performance degradation with very large symbols → Consider optional chunked processing.
- User confusion about validation usage → Clear CLI help text and separated metrics output.

### Definition of Done

- All functional requirements FR-001..FR-012 satisfied & validated by tests.
- Success criteria SC-001..SC-005 measured or asserted where practicable.
- No silent skips; summary lists all processed/skipped symbols.
- Documentation (quickstart + README update) present.
- Quality gates (Black, Ruff, Pylint, Markdownlint, pytest) pass in CI.
