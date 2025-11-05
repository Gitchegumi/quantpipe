# Implementation Plan: Performance Optimization: Backtest Orchestrator & Trade Simulation

**Branch**: `007-performance-optimization` | **Date**: 2025-11-05 | **Spec**: `specs/007-performance-optimization/spec.md`
**Input**: Feature specification from `/specs/007-performance-optimization/spec.md`

## Summary

Optimize backtest orchestration and trade simulation to reduce single-run wall-clock time (6.9M–10M candles; ~17.7k trades) from hours to ≤20 minutes (stretch 10–15) by introducing: efficient typed data loading & early slicing, indicator caching, batched/event-driven trade simulation (vectorization + optional JIT), profiling & benchmarking artifacts, controlled parallelism, and memory footprint management while preserving numerical fidelity.

## Technical Context

**Language/Version**: Python 3.11 (confirmed by constitution)  
**Primary Dependencies**: numpy, pandas, pydantic, rich (existing). Optional: numba (JIT) as performance enhancer (fallback to pure vectorization).  
**Storage**: File-based time series (CSV current). Parquet/Arrow deferred to Phase 2 (pyarrow optional).  
**Testing**: pytest (existing suite: unit/integration/performance). Add performance benchmark tests (timing assertions) and fidelity comparison tests.  
**Target Platform**: Local developer workstation / CI runners (Windows/macOS/Linux) with multi-core CPU; no GPU reliance initial phase.  
**Project Type**: Single Python package with CLI orchestration.  
**Performance Goals**: Trade simulation phase ≥10× speedup; full run ≤20m (stretch 10–15m); data load + slice ≤60s; parallel efficiency ≥70% at 4 workers.  
**Constraints**: Memory peak ≤1.5× raw dataset footprint; deterministic mode reproducibility; zero new mandatory dependencies unless justified by >5× additional speed versus pure vectorization.  
**Scale/Scope**: Datasets up to 10–15M candles; trades 15k–25k; indicator cache periods up to ~50 period definitions per run.

## Constitution Check (Pre-Design Gate)

| Principle                          | Status | Notes                                                              |
| ---------------------------------- | ------ | ------------------------------------------------------------------ |
| Strategy-First Architecture        | PASS   | Optimization does not alter strategy isolation.                    |
| Risk Management Integration        | PASS   | Simulation preserves risk parameters; no removal.                  |
| Backtesting & Validation           | PASS   | Adds fidelity tests and benchmarks; enhances validation.           |
| Real-Time Performance Monitoring   | PASS   | Profiling + progress throttling aligns with observability.         |
| Data Integrity & Security          | PASS   | No new external data sources; will add gap validation hooks later. |
| Data Version Control & Provenance  | PASS   | Benchmark includes manifest reference; unchanged workflow.         |
| Model Parsimony & Interpretability | PASS   | Performance layer does not add opaque model complexity.            |
| Code Quality & Documentation       | PASS   | Plan mandates docstrings, type hints for new modules.              |
| Dependency Management              | PASS   | Optional numba (not mandatory); parquet deferred.                  |
| Code Quality Automation            | PASS   | Will extend tests; existing tooling unchanged.                     |
| Risk Management Standards          | PASS   | Simulation preserves existing controls.                            |
| Development Workflow               | PASS   | Research → Design → Validation maintained.                         |

Gate Result: PASS (dependency choices resolved: optional numba; deferred parquet).

## Project Structure

### Documentation (this feature)

```text
specs/007-performance-optimization/
├── plan.md          # Implementation plan (this file)
├── research.md      # Decisions & rationale (Phase 0)
├── data-model.md    # Entities & validation (Phase 1)
├── quickstart.md    # Usage & adoption guide (Phase 1)
├── contracts/       # CLI contract specs (Phase 1)
└── tasks.md         # Generated later by /speckit.tasks (not in this command)
```

### Source Code (repository root)

```text
src/
├── backtest/
│   ├── orchestrator.py        # Existing: will integrate optimized flow
│   ├── execution.py           # Existing: trade execution logic (to refactor for batch)
│   ├── metrics.py             # Existing: unchanged except faster inputs
│   ├── indicator_cache.py     # NEW: caching & precomputation utilities
│   ├── trade_sim_batch.py     # NEW: vectorized/JIT batch simulation
│   ├── profiling.py           # NEW: profiling + benchmark artifact writer
│   ├── chunking.py            # NEW: chunked data slice utilities
│   └── parallel.py            # NEW: worker orchestration utilities
│
├── cli/
│   └── run_backtest.py        # Extend flags: --profile --data-frac --max-workers --deterministic --benchmark-out
│
tests/
├── unit/
│   ├── test_indicator_cache.py
│   ├── test_trade_sim_batch.py
│   ├── test_chunking.py
│   └── test_profiling.py
├── integration/
│   ├── test_full_run_fraction.py
│   ├── test_full_run_deterministic.py
│   └── test_parallel_efficiency.py
└── performance/
    ├── test_trade_sim_speed.py   # Asserts speedup vs baseline fixture
    └── test_memory_peak.py       # Monitors memory threshold
```

**Structure Decision**: Retain single-package architecture; add targeted new modules under `src/backtest/` to preserve modular boundaries while avoiding widespread refactors.

## Complexity Tracking

| Violation                             | Why Needed                                 | Simpler Alternative Rejected Because               |
| ------------------------------------- | ------------------------------------------ | -------------------------------------------------- |
| Optional numba dependency             | ≥10–50× speed improvements for inner loops | Pure numpy loops slower; Python loops unacceptable |
| Optional pyarrow dependency (Phase 2) | Columnar IO speed & lower memory footprint | CSV reading too slow for ≥10M rows; caching delays |

## Phase 0: Research & Clarification Targets

NEEDS CLARIFICATION Items: None (all resolved in research.md).

Research Tasks: Completed (see `research.md`).

Deliverable: `research.md` consolidating decisions (Decision / Rationale / Alternatives). (Completed)

## Phase 1: Design & Contracts (Post-Research)

Artifacts:
Artifacts:

- `data-model.md`: Formalize entities (BacktestJob, DatasetSlice, IndicatorCache, TradeEntryRecord, TradeSimulationResult, BenchmarkRecord, ProfilingReport) and validation rules.
- `contracts/cli-performance.md`: CLI contract table with flag semantics, types, defaults, validation.
- `quickstart.md`: Step-by-step enabling profiling, fraction slicing, deterministic mode, interpreting benchmark artifacts.
- Update agent context (run script) to record new module names without leaking implementation details.

## Phase 2: Implementation Sequencing (High-Level)

1. Introduce indicator cache & deterministic seed path (low risk).
2. Add batch trade simulation (vectorized baseline).
3. Integrate optional numba JIT acceleration layer.
4. Add profiling & benchmark artifact writer.
5. Implement fraction slicing & chunking utilities.
6. Add parallel parameter set execution and efficiency tests.
7. (Deferred) Parquet/Arrow integration behind feature flag.

## Risk & Mitigation

| Risk                           | Impact | Mitigation                                                |
| ------------------------------ | ------ | --------------------------------------------------------- |
| JIT dependency complexity      | Medium | Keep optional; fallback to pure vectorization             |
| Numerical drift due to float32 | Low    | Use tolerance tests vs baseline double precision snapshot |
| Parallel memory duplication    | Medium | Use shared read-only arrays; document copy strategy       |
| Over-optimization premature    | Medium | Enforce benchmark thresholds before deeper changes        |
| Logging overhead persists      | Low    | Implement update frequency gating (e.g., every N trades)  |

## Benchmark Plan

Synthetic datasets: 1M, 5M, 10M bars. Metrics captured: load time, simulation time, total time, memory peak, speedup multiplier vs baseline. Store under `results/benchmarks/` (to be added in tasks phase).

## Definition of Done (Planning Scope)

Phase 0 & 1 artifacts created; constitutional gate re-check passes (no blocking violations); dependency decisions documented; tasks ready for generation.
