# Implementation Plan: Multi-Strategy Support

**Branch**: `006-multi-strategy` | **Date**: 2025-11-03 | **Spec**: `specs/006-multi-strategy/spec.md`
**Input**: Feature specification from `/specs/006-multi-strategy/spec.md`

## Summary

Introduce simultaneous multi-strategy backtesting with isolated per-strategy state, configurable per-strategy and global risk limits, aggregated portfolio metrics (PnL, drawdown, exposure, volatility), user-specified weighting (equal-weight fallback), deterministic repeatability, and robust CLI selection/filtering. Implementation adds a strategy registry, orchestration layer capable of concurrent execution, aggregation module for metrics, and manifest generation for reproducibility.

## Technical Context

**Language/Version**: Python 3.11 (per project standards)
**Primary Dependencies**: Poetry-managed; numpy, pandas (data & metrics), pydantic (config validation), rich/logging (structured logs), pytest (tests). No new external runtime services.
**Storage**: File-based artifacts (CSV/JSON) for outputs; in-memory state during runs.
**Testing**: pytest (unit, integration, performance slices). Determinism verified via repeat runs.
**Target Platform**: Local/CI execution on Windows/Linux (cross-platform Python environment).
**Project Type**: Single Python project (CLI + library modules).
**Performance Goals**: Aggregation file produced ≤5s post-run (≤1M rows baseline); adding a strategy increases runtime ≤15% vs single baseline (up to 10 strategies).
**Constraints**: Line length 88 chars; zero Ruff errors; pylint ≥8.0; Markdownlint compliance; memory footprint—should not exceed baseline by >10% per added strategy (heuristic, monitoring via optional profiling). NEEDS CLARIFICATION: exact reliability uptime target (non-critical for batch backtest, will define in research).
**Scale/Scope**: Up to 20 strategies in a single run; dataset sizes up to ~1M price rows baseline, scalable to multi-instrument datasets.

## Constitution Check

| Principle                        | Alignment | Notes                                                                                      |
| -------------------------------- | --------- | ------------------------------------------------------------------------------------------ |
| Strategy-First Architecture (I)  | Pass      | Each strategy isolated with registry pattern.                                              |
| Risk Management (II)             | Pass      | Per-strategy + global drawdown controls defined.                                           |
| Backtesting & Validation (III)   | Pass      | Metrics + deterministic repeatability + risk breach scenarios.                             |
| Monitoring (IV)                  | Partial   | Logging lifecycle events; NEEDS CLARIFICATION: add structured aggregation metrics logging. |
| Data Integrity & Security (V)    | Pass      | Reuses existing ingestion; manifest unchanged.                                             |
| Data Version Control (VI)        | Pass      | RunManifest will reference data manifest.                                                  |
| Parsimony (VII)                  | Pass      | Lightweight registry/aggregation; no complex modeling.                                     |
| Code Quality & Docs (VIII)       | Pass      | Will add docstrings for new modules.                                                       |
| Dependency Management (IX)       | Pass      | No new deps; Poetry locked.                                                                |
| Quality Automation & Linting (X) | Pass      | Plan includes tests + formatting compliance.                                               |
| Risk Management Standards        | Partial   | Correlation monitoring not yet in aggregation; deferred.                                   |

Gate Status: ACCEPT WITH MINOR PARTIALS (monitoring metrics details, correlation). These will be resolved in Phase 0 research.

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
├── backtest/          # Orchestrator, metrics aggregation extensions
├── strategy/          # Strategy base & implementations (existing folder extended)
├── config/            # Parameters & validation models (extended per-strategy overrides)
├── cli/               # CLI commands (add multi-strategy flags)
├── models/            # Core data models (StrategyConfig, RunManifest additions)
└── io/                # Dataset loading unchanged; may add manifest augmentation

tests/
├── unit/              # Registry tests, aggregation logic
├── integration/       # Multi-strategy backtest run scenarios
├── performance/       # Runtime scaling tests (strategy count)
└── contract/          # Validation of OpenAPI contract examples
```

**Structure Decision**: Single project architecture retained; augment existing `strategy`, `backtest`, `cli`, `models` with new registry, aggregation, and manifest components. No additional top-level services required.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation                       | Why Needed          | Simpler Alternative Rejected Because                                        |
| ------------------------------- | ------------------- | --------------------------------------------------------------------------- |
| Correlation monitoring deferred | Complexity/time-box | Not critical to initial multi-strategy evaluation; adds processing overhead |
| Global abort limited set only   | Preserve resilience | Broader abort triggers reduce insight into individual strategy robustness   |

---

## Phase 0: Research

Objectives: Resolve monitoring metric detail, reliability target, and correlation handling deferral justification.

Research Tasks:

1. Logging/Monitoring: Define minimal structured metrics for aggregated output (fields: strategies_count, runtime_seconds, aggregate_volatility, drawdown_pct, net_exposure_by_instrument).
2. Reliability Target: Establish acceptable failure rate for multi-strategy batch runs.
3. Correlation Handling: Document rationale for deferring correlation monitoring & future approach.

Decisions will be captured in `research.md`.

## Phase 1: Design & Contracts

Deliverables:

- `data-model.md`: Strategy, StrategyConfig, StrategyState, StrategyResult, PortfolioAggregate, RunManifest.
- `contracts/openapi.yaml`: Conceptual REST contract for registry and backtest execution.
- `quickstart.md`: How to register, run multi-strategy backtests, view outputs.
- Updated agent context (copilot) via script.

## Phase 2: Implementation Preparation

High-Level Steps (not executed here):

- Implement registry class & interface.
- Extend orchestrator for multi-strategy loop and isolation.
- Add aggregation module & manifest builder.
- Add CLI flags: `--strategies`, `--weights`, `--aggregate/--no-aggregate`, `--global-drawdown`.
- Add tests for isolation, aggregation, risk breach, determinism.

---

## Post-Design Constitution Re-Check (Planned)

Will verify monitoring partial resolved with structured metrics logging; confirm no new dependencies violate Principles.

---

## Open Points (Should be resolved in research.md)

- Structured metrics fields final list.
- Reliability target (success rate threshold).
- Correlation monitoring deferral justification.

## Risks & Mitigations

| Risk                        | Mitigation                                        |
| --------------------------- | ------------------------------------------------- |
| Runtime scaling degradation | Early performance tests in performance/ directory |
| Misconfigured weights       | Validation & equal-weight fallback                |
| Incorrect aggregation logic | Unit tests for netting & edge scenarios           |
| Global abort misfires       | Strict criteria & logging manifest entries        |

## Tooling & Quality Gates

All new Python modules will include docstrings, type hints; run Black, Ruff, Pylint, Markdownlint on added docs. Manifest and aggregation components instrumented with lazy logging.

## Definition of Done (Feature)

1. Multi-strategy backtest runs ≥3 strategies with aggregated output.
2. All success criteria SC-001..SC-010 plus FR-021 validated by tests.
3. Structured metrics logged (run manifest, aggregated file).
4. OpenAPI contract examples pass rudimentary validation tests.
5. No lint violations; pylint score ≥8.0 for new modules.
6. Deterministic repeatability test passes thrice.
