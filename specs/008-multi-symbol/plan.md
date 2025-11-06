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
**Primary Dependencies**: numpy, pandas, pydantic (config validation), rich (progress/logging), poetry (dependency mgmt). Potential optional: numba (JIT) – NEEDS CLARIFICATION (adopt now or phase later?)
**Storage**: File-based CSV inputs; outputs as text/JSON + snapshot logs; no DB.
**Testing**: pytest (unit, integration, performance); contract tests for filename pattern & symbol metadata (SC-014).
**Target Platform**: Cross-platform Python (Windows dev; Linux CI). Backtests long-running; memory optimization considered.
**Project Type**: Single Python project (strategy/backtest framework) – existing `src/` layout retained.
**Performance Goals**: Portfolio mode (≤3x single-symbol runtime for 3+ symbols, SC-003); 10-symbol performance target ≤5 minutes for 1-year daily dataset (SC-011). Observability overhead <10% (SC-013).
**Constraints**: Deterministic results (SC-009); zero logging f-string violations (Principle X); maintain lint + formatting compliance; correlation logic initialization with provisional window ≥20; memory usage scalable to 10 symbols with acceptable peak (<1.5× single-symbol baseline) – NEEDS CLARIFICATION (exact memory threshold).
**Scale/Scope**: Phase 1: 2–3 symbols; Phase 2: up to 10 symbols; Future: >10 with potential parallelization – NEEDS CLARIFICATION (parallel execution strategy & scheduling).

### Entities & Components (from spec)

- Currency Pair
- Symbol Configuration
- Portfolio Configuration
- Correlation Matrix
- Symbol Result
- Portfolio Result
- Portfolio Snapshot
- Currency Pair, Symbol Configuration, Portfolio Configuration, Correlation Matrix, Symbol Result, Portfolio Result, Portfolio Snapshot.
- New internal components to design: `PortfolioOrchestrator`, `CorrelationService`, `AllocationEngine`, `SnapshotLogger` – NEEDS CLARIFICATION (final module boundaries and naming).

### Unknowns (NEEDS CLARIFICATION)

List of current ambiguities requiring Phase 0 research resolution:

- Optional numba adoption strategy (hard dependency vs graceful fallback)
- Memory target thresholds for multi-symbol runs (define quantitative SC?)
- Parallelization approach for independent mode (threading vs multiprocessing vs sequential) initial release
- Resume/restart behavior (partial progress recovery) – currently out-of-scope? Decide explicit OUT-OF-SCOPE list
- Failure isolation in portfolio mode beyond validation (runtime symbol halt impact on portfolio metrics?)
- AllocationEngine strategy interfaces (risk-parity formula, capital rounding rules)
- Snapshot log format (JSON lines vs plain text) – finalize schema
- Correlation threshold configuration format (single float vs per-pair matrix overrides)
- Symbol selection filters/tags (future: liquidity class, volatility tier) – confirm scope now

1. Optional numba adoption strategy (hard dependency vs graceful fallback).
2. Memory target thresholds for multi-symbol runs (define quantitative SC?).
3. Parallelization approach for independent mode (threading vs multiprocessing vs sequential) initial release.
4. Resume/restart behavior (partial progress recovery) – currently out-of-scope? Decide explicit OUT-OF-SCOPE list.
5. Failure isolation in portfolio mode beyond validation (runtime symbol halt impact on portfolio metrics?).
6. AllocationEngine strategy interfaces (risk-parity formula, capital rounding rules).
7. Snapshot log format (JSON lines vs plain text) – finalize schema.
8. Correlation threshold configuration format (single float vs per-pair matrix overrides).
9. Symbol selection filters/tags (future: liquidity class, volatility tier) – confirm scope now.

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

For each NEEDS CLARIFICATION item above create a research decision entry in `research.md`:

- NumPy vs numba acceleration trade-offs for correlation & allocation loops.
- Memory footprint profiling targets (define baseline & acceptable multiplier).
- Independent mode parallelism viability (I/O bound vs CPU bound; overhead vs speedup).
- Explicit restart semantics (out-of-scope confirmation for v1; document assumptions).
- Portfolio failure isolation rules (symbol halt → exclude from future correlation? decision needed).
- AllocationEngine interface (inputs: symbol vols, correlations, weights; outputs: per-symbol size factors). Round strategy.
- Snapshot schema (JSON lines vs structured text; choose JSON lines for machine parsing).
- Correlation config format (single threshold + optional overrides map).
- Tag/filter taxonomy deferral (explicitly out-of-scope for initial release).
- NumPy vs numba acceleration trade-offs for correlation & allocation loops.
- Memory footprint profiling targets (define baseline & acceptable multiplier).
- Independent mode parallelism viability (I/O bound vs CPU bound; overhead vs speedup).
- Explicit restart semantics (out-of-scope confirmation for v1; document assumptions).
- Portfolio failure isolation rules (symbol halt → exclude from future correlation? decision needed).
- AllocationEngine interface (inputs: symbol vols, correlations, weights; outputs: per-symbol size factors). Round strategy.
- Snapshot schema (JSON lines vs structured text; choose JSON lines for machine parsing).
- Correlation config format (single threshold + optional overrides map).
- Tag/filter taxonomy deferral (explicitly out-of-scope for initial release).

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
