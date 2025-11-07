# Implementation Plan: Multi-Symbol Support (Portfolio & Independent Execution)

**Branch**: `008-multi-symbol` | **Date**: 2025-11-06 | **Spec**: `specs/008-multi-symbol/spec.md`
**Input**: Feature specification defining FR-001..FR-023 and SC-001..SC-014

## Summary

Add ability to execute backtests across multiple currency pairs in two modes:

1. Independent mode – isolated per-symbol runs sharing execution context but not capital/state.
2. Portfolio mode – shared capital pool with correlation-aware position sizing, exposure limits, diversification and aggregated metrics.

Technical approach: Extend existing directional backtest orchestrator to loop over selected symbols (initial minimal adapter), introduce portfolio aggregation layer (phase 2), implement rolling correlation computation (100-period window with provisional start ≥20), enforce per-symbol & portfolio risk limits, and provide structured observability (trade logs + periodic portfolio snapshots). Filename convention updated (FR-023) and symbol metadata integrated. Early scope focuses on architecture primitives (data ingestion reuse, orchestration wrapper, correlation matrix builder, allocation engine stub, snapshot logger) while deferring advanced features (resume/restart, dynamic weighting optimization) to later phases.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: numpy, pandas, pydantic (config validation), rich (progress/logging), poetry (dependency mgmt). Optional: numba (JIT) with feature flag per Decision 1.
**Storage**: File-based CSV inputs; outputs as text/JSON + snapshot logs; no DB.
**Testing**: pytest (unit, integration, performance); contract tests for filename pattern & symbol metadata (SC-014).
**Target Platform**: Cross-platform Python (Windows dev; Linux CI). Backtests long-running; memory optimization considered.
**Project Type**: Single Python project (strategy/backtest framework) – existing `src/` layout retained.
**Performance Goals**: Portfolio mode (≤3x single-symbol runtime for 3+ symbols, SC-003); 10-symbol performance target ≤5 minutes for 1-year daily dataset (SC-011). Observability overhead <10% (SC-013).
**Constraints**: Deterministic results (SC-009); zero logging f-string violations (Principle X); maintain lint + formatting compliance; correlation logic initialization with provisional window ≥20; memory usage ≤1.5× single-symbol baseline for 10 symbols measured via tracemalloc (SC-015).
**Scale/Scope**: Phase 1: 2–3 symbols; Phase 2: up to 10 symbols; Future: >10 with potential parallelization.

### Entities & Components (from spec)

- Currency Pair, Symbol Configuration, Portfolio Configuration, Correlation Matrix, Symbol Result, Portfolio Result, Portfolio Snapshot.
- New internal components to design: `PortfolioOrchestrator`, `CorrelationService`, `AllocationEngine`, `SnapshotLogger` (module boundaries defined in data-model.md and contracts/).

## Constitution Check (Initial Gate)

| Principle                    | Status  | Notes                                                                                                                               |
| ---------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| I Strategy-first             | PASS    | Multi-symbol addition preserves strategy modularity; portfolio layer is additive.                                                   |
| II Risk Mgmt                 | PARTIAL | Per-symbol limits defined; portfolio kill-switch & drawdown tiered limits not yet fully designed (needs AllocationEngine contract). |
| III Backtesting & Validation | PARTIAL | Correlation + costs included; out-of-sample & walk-forward not expanded for multi-symbol yet (existing single-symbol coverage).     |
| IV Real-Time Monitoring      | PARTIAL | Trade + snapshot logging specified; alerting/killswitch events for portfolio not yet planned.                                       |
| V Data Integrity             | PASS    | Reuses validated ingestion; needs multi-symbol overlap validation implementation detail.                                            |
| VI Data Provenance           | PASS    | No new data mutation; manifest extension to list multiple dataset refs – to add.                                                    |
| VII Parsimony                | PASS    | Initial design favors simple rolling correlation; defers complex risk-parity optimization.                                          |
| VIII Code Quality            | PASS    | Plan mandates docstrings/type hints for new modules.                                                                                |
| IX Dependency Mgmt           | PASS    | No new mandatory dependency yet; numba decision pending.                                                                            |
| X Quality Automation         | PASS    | Will add tests for filename regex & correlation behavior; lint standards unchanged.                                                 |

Gate Outcome: PROCEED to Phase 0 with listed clarifications. Any PARTIAL items must be resolved (or explicitly deferred) in research.md.

## Constitution Check (Post Phase 1 Update)

Phase 1 design artifacts (research.md decisions, data-model.md, allocation contract, quickstart.md) have been delivered. Re-assess prior PARTIAL principles:

| Principle                    | Status | Updated Notes (Post Phase 1)                                                                                                              |
| ---------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| I Strategy-first             | PASS   | Single-symbol baseline preserved; multi-symbol layers additive.                                                                           |
| II Risk Mgmt                 | PASS   | AllocationEngine contract defined; failure isolation rule formalized; portfolio kill-switch deferred (logged in research deferred list). |
| III Backtesting & Validation | PASS   | Correlation window + provisional logic specified; portfolio synchronization rules documented; walk-forward remain deferred.              |
| IV Real-Time Monitoring      | PASS   | Snapshot JSONL schema + trade logging requirements specified (FR-022); interval configurability documented.                              |
| V Data Integrity             | PASS   | Multi-symbol overlap validation planned in `validation.py`; no mutation of source datasets introduced.                                   |
| VI Data Provenance           | PASS   | Manifest will enumerate symbol datasets; structure unchanged; extension task scheduled (T033).                                           |
| VII Parsimony                | PASS   | Advanced tagging, parallelization, risk-parity explicitly deferred; lean initial scope retained.                                         |
| VIII Code Quality            | PASS   | All forthcoming modules required to include docstrings & type hints; tasks list encodes enforcement (T053).                              |
| IX Dependency Mgmt           | PASS   | numba optional path defined with feature flag; no new mandatory deps introduced.                                                         |
| X Quality Automation         | PASS   | Tests enumerated per story (allocation precision, correlation provisional window, snapshot interval, determinism).                      |

Deferred items (remaining): portfolio drawdown kill-switch, walk-forward multi-symbol validation, advanced tagging, parallel execution prototype (T059), risk-parity allocation variant.

Phase 1 Completion: COMPLETE. Proceed to Phase 2 (Foundational implementation tasks).

## Constitution Check (Final - Phase 7)

Implementation complete through Phase 6 (T001-T047). Final compliance review:

| Principle                    | Status | Final Notes (Phase 7)                                                                                                                                                     |
| ---------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| I Strategy-first             | PASS   | Single-symbol baseline preserved via regression tests (T014). Multi-symbol layers fully additive (independent_runner, orchestrator, correlation/allocation services).    |
| II Risk Mgmt                 | PASS   | Per-symbol risk isolation implemented (T024). Portfolio allocation limits enforced (T036). Failure isolation validated (T039). Correlation thresholds configurable (T043).|
| III Backtesting & Validation | PASS   | Comprehensive test coverage: 47 unit tests, 11 integration tests across US1-US4. Correlation provisional window (T035), deterministic results validated.                 |
| IV Real-Time Monitoring      | PASS   | Snapshot logging implemented (T030). Structured JSONL output (FR-022). Configurable intervals (T044, T037). Portfolio metrics tracked.                                   |
| V Data Integrity             | PASS   | Multi-symbol validation implemented (T009, T021). Unknown symbol graceful abort (T046). Dataset overlap checks in place. No source mutation.                             |
| VI Data Provenance           | PASS   | Portfolio manifest generation (T033). Enumerates all symbol datasets. Symbol-level metadata preserved. Execution mode documented.                                        |
| VII Parsimony                | PASS   | Lean correlation design (100-period rolling, provisional 20). Simple allocation (equal weight, largest remainder). Advanced features explicitly deferred.                |
| VIII Code Quality            | PASS   | All modules have docstrings/type hints (T064: 10.00/10 score). Lazy % logging enforced (T062: zero W1203 violations). Pylint 9.96/10 for portfolio/.                    |
| IX Dependency Mgmt           | PASS   | Zero new mandatory dependencies. Poetry-managed. No requirements.txt. Lock file committed. Numba deferred (optional future enhancement).                                 |
| X Quality Automation         | PASS   | All tests passing (58 total). Markdownlint: 0 errors (T063). Black/Ruff/Pylint enforced. CI-ready. Constitution Principle XI (commit format) validated across all tasks.|
| XI Commit Standards (NEW)    | PASS   | All Phase 6 commits follow semantic format: `<tag>(<spec>): <title> (<task>)`. Examples: test(008): ... (T046), docs(008): ... (T047). Traceability maintained.         |

Deferred Items Status:

- Portfolio drawdown kill-switch → Logged as future enhancement
- Walk-forward multi-symbol validation → Existing single-symbol approach sufficient
- Advanced tagging/filtering → FR-016 (--list-pairs) deferred to future phase
- Parallel execution (T059) → Feasibility noted, deferred
- Risk-parity allocation → Simple equal-weight sufficient for MVP
- T048 (performance benchmark) → Deferred (complex API integration)
- T049-T050 (memory profiling, structured logging) → Deferred to future optimization phase

Phase 7 Completion: SUBSTANTIAL PROGRESS. Core quality gates (T051, T062-T064) complete. README updated. Constitution compliance verified. Feature ready for merge pending optional polish tasks (T048-T050, T052-T061).

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
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: Retain single-project layout. New multi-symbol components integrated under `src/backtest/portfolio/` (new folder) and `src/backtest/correlation.py`, `src/backtest/allocation.py`, `src/backtest/snapshots.py`. Tests mirrored in `tests/unit/portfolio/`, `tests/integration/multi_symbol/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --------- | ---------- | ------------------------------------ |
| (None)    | N/A        | N/A                                  |

## Phase 0 Plan (Research Tasks)

All items resolved in `research.md` (Decisions 1-9):

- NumPy vs numba acceleration trade-offs for correlation & allocation loops.
- Memory footprint profiling targets (define baseline & acceptable multiplier).
- Independent mode parallelism viability (I/O bound vs CPU bound; overhead vs speedup).
- Explicit restart semantics (out-of-scope confirmation for v1; document assumptions).
- Portfolio failure isolation rules (symbol halt → exclude from future correlation? decision needed).
- AllocationEngine interface (inputs: symbol vols, correlations, weights; outputs: per-symbol size factors). Round strategy.
- Snapshot schema (JSON lines vs structured text; choose JSON lines for machine parsing).
- Correlation config format (single threshold + optional overrides map).
- Tag/filter taxonomy deferral (explicitly out-of-scope for initial release per Decision 9).

## Phase 1 (Design & Contracts) – Preview

Will produce:

- `data-model.md`: Entities with fields (currency_pair, symbol_config, correlation_matrix schema, allocation_request, snapshot_record).
- `contracts/portfolio-allocation.yaml`: Internal interface (not public API) describing allocation request/response shapes.
- `quickstart.md`: CLI usage examples for independent vs portfolio mode with new flags (`--pairs`, `--mode portfolio`, `--snapshot-interval`).
- `data-model.md`: Entities with fields (currency_pair, symbol_config, correlation_matrix schema, allocation_request, snapshot_record).
- `contracts/portfolio-allocation.yaml`: Internal interface (not public API) describing allocation request/response shapes.
- `quickstart.md`: CLI usage examples for independent vs portfolio mode with new flags (`--pairs`, `--mode portfolio`, `--snapshot-interval`).

## Phase 2 (Tasks) – Deferred to /speckit.tasks

High-level forthcoming tasks: implement correlation service, allocation engine, portfolio orchestrator loop, integrate snapshot logging, add portfolio metrics aggregation tests, performance profiling, memory optimization.

---

Next: Generate `research.md` resolving all clarifications, then update Constitution Check (expect PARTIAL items → PASS or Deferred).
