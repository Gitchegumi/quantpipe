# Implementation Plan: Optimize & Decouple Ingestion Process

**Branch**: `009-optimize-ingestion` | **Date**: 2025-11-07 | **Spec**: `specs/009-optimize-ingestion/spec.md`
**Input**: Feature specification from `/specs/009-optimize-ingestion/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Refactor ingestion to produce only normalized core OHLCV + `is_gap` rapidly (≤2:00 baseline, stretch ≤90s) while decoupling all indicator computations to an opt‑in enrichment layer. Performance gains achieved via vectorized batch gap fill, columnar (Arrow backend) fast path, optional materialized iterator for legacy code, and pluggable indicator registry. No GPU requirement; RTX 4080 available for future optional acceleration.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: pandas (Arrow dtype backend), numpy, rich (progress), pydantic (configs), pytest (tests); optional future: pyarrow explicitly (already implied), potential future GPU libs (NOT in scope now)
**Storage**: File-based CSV input; output in-memory DataFrame; optional serialization to CSV/JSON (unchanged)
**Testing**: pytest (unit: gap fill correctness, performance harness, indicator registry validation; integration: ingestion→enrichment pipeline; performance: timing & memory)
**Target Platform**: Local workstation (Windows w/ RTX 4080) + CI (Linux) – GPU not required
**Project Type**: Single Python library/package (`src/`) with tests hierarchy
**Performance Goals**: Baseline ≤120s ingest of 6.9M rows; stretch ≤90s CPU; optional future ≤75s GPU (SC-013)
**Constraints**: Memory peak ≤ baseline -25%; no per-row loops; progress ≤5 updates; dataset uniform cadence validation; no mandatory new dependencies
**Scale/Scope**: Single-symbol ingestion per call; dataset size ≈6.9M rows; indicators appended selectively post-ingestion

**Unknowns / NEEDS CLARIFICATION**: None (all resolved in spec). Potential future GPU path deliberately deferred.

## Constitution Check (Initial)

| Principle | Compliance | Notes |
|-----------|------------|-------|
| I Strategy-First | ✓ | Decouples data from strategy logic; strategies opt-in to indicators. |
| II Risk Mgmt | ✓ (indirect) | Data integrity supports accurate risk metrics; no strategy risk logic altered. |
| III Backtesting | ✓ | Faster ingestion increases test iteration frequency; integrity preserved. |
| IV Monitoring | ✓ | Defined progress stages (read, sort, dedupe, gaps, finalize); limited updates. |
| V Data Integrity | ✓ | Standardized `is_gap` column; deterministic duplicates & UTC enforcement. |
| VI Data Provenance | ✓ | Metrics & artifacts reference manifest; benchmark JSON planned. |
| VII Parsimony | ✓ | Removes unnecessary indicator precompute; selective enrichment only. |
| VIII Code Quality | ✓ | Docstrings, type hints, immutability & registry patterns; logging standard enforced (script task). |
| IX Dependencies | ✓ | No new mandatory dependencies; Arrow optional; dependency check task planned. |
| X Linting/Automation | ✓ | Static loop scan & logging format scan added; benchmark artifacts integrated. |
| XI Commit Format | ✓ | Will use semantic format (feat/test/docs) referencing tasks (e.g., T087). |

Gate Result: PASS – proceed to Phase 0.

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
├── io/                  # Ingestion module (new refactor target)
├── indicators/          # Indicator enrichment (decoupled computations)
├── backtest/            # Existing backtest orchestration (unchanged integration point)
├── models/              # Data classes (Candle record optionally updated for immutability)
├── strategy/            # Strategy implementations (consume core + enrichment)
└── config/              # Runtime configuration (enrichment selection)

tests/
├── unit/
│   ├── test_ingestion_gap_fill.py
│   ├── test_ingestion_performance.py (uses timing harness)
│   └── test_indicator_registry.py
├── integration/
│   └── test_ingest_then_enrich_pipeline.py
├── performance/
│   └── benchmark_ingestion.py
└── contract/            # (If endpoint-like contracts are simulated locally)
```

**Structure Decision**: Single Python package; introduce dedicated ingestion and indicator registry modules; performance harness under `tests/performance/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Additional performance test harness script | Needed for deterministic timing & metrics | Ad-hoc timing in unit tests too noisy/inconsistent |
| Indicator registry abstraction | Enables opt-in, prevents monolithic ingestion | Hard-coded indicator list would require code edits per indicator |

## Post-Design Constitution Recheck (Phase 1 Completion)

Added artifacts: `data-model.md`, `contracts/ingest.md`, `contracts/enrich.md`, `quickstart.md`.

Re-evaluated principles:

| Principle | Status | Notes (Post-Design) |
|-----------|--------|---------------------|
| I Strategy-First | ✓ | Enrichment layer separated; ingestion free of indicator logic (audit planned). |
| V Data Integrity | ✓ | Contracts formalize duplicate + gap + UTC enforcement steps; standardized `is_gap`. |
| VII Parsimony | ✓ | Minimal ingestion path documented; enrichment optional. |
| IX Dependencies | ✓ | Dependency check script scheduled; no new mandatory deps. |
| X Linting/Automation | ✓ | Added logging formatting enforcement & per-row loop scan. |
| XI Commit Format | ✓ | Semantic commit usage planned with task references. |

New Complexity Justifications:

| Addition | Justification | Alternative Rejected |
|----------|--------------|----------------------|
| Dual mode support (columnar + iterator) documentation | Eases phased migration for legacy code while enabling performance path | Forcing single mode would delay adoption or regress existing strategies |
| Validation checklists in contracts & quickstart | Provides executable acceptance criteria, reduces ambiguity in tests | Embedding solely in tests would hide criteria from design reviewers |

No new constitutional violations detected. Ready to proceed to task generation (`tasks.md`) and subsequent implementation phases.
