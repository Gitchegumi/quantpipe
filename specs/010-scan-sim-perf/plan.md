# Implementation Plan: Scan & Simulation Performance Optimization

**Branch**: `010-scan-sim-perf` | **Date**: 2025-11-11 | **Spec**: `specs/010-scan-sim-perf/spec.md`
**Input**: Feature specification produced via `/speckit.specify` and clarified via `/speckit.clarify`.

**Note**: Populated by `/speckit.plan` workflow.

## Summary

Accelerate scan (≥50% time reduction) and simulation (≥55% time reduction) on large datasets while preserving exact signal and trade semantics. Enforce strategy-owned indicator model; provide deterministic & transparent performance reporting with consistent progress updates (≤2 min or ≤2% increments). Technical approach: columnar NumPy arrays for candles & indicators, batch signal indices generation, O(1) duplicate timestamp handling, prebuilt lookup tables (`ts_to_index`, `price_data` arrays), batched simulation with vectorized stop/target evaluation, low-overhead progress emission.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11 (confirmed by constitution)
**Primary Dependencies**: numpy, polars, pandas (legacy fallback only), pydantic, rich (progress/logging), pytest; optional numba (defer until baseline measured). Polars is now the canonical columnar engine.
**Storage**: Parquet (converted from CSV during ingestion) + Polars LazyFrame/DataFrame for preprocessing; legacy CSV path retained only for one-time conversion; Arrow memory model leveraged implicitly via Polars.
**Testing**: pytest (unit, integration, performance), contract-style tests for indicator ownership.
**Target Platform**: Local workstation / CI runners (Windows, Linux) - CPU only.
**Project Type**: Single Python package under `src/`.
**Performance Goals**: Scan ≤12 min on 6.9M candles; Simulation ≤8 min on ≈84,938 trades; Progress overhead ≤1%; Memory reduction ≥30% peak vs baseline; Deterministic repeat runs ±1% timing variance.
**Constraints**: Avoid per-iteration Python object churn; keep allocations amortized; maintain identical results; no external service calls; logging conforms to lazy formatting rules.
**Scale/Scope**: Single-symbol large dataset first; multi-symbol batching deferred; no GPU acceleration in this phase.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution compliance gates (Principles I–XI):

| Principle | Gate | Status | Notes |
|-----------|------|--------|-------|
| I Strategy-First | Indicators owned by strategy only | PASS | FR-004/SC-006 enforce |
| II Risk Mgmt | No change to risk layer | PASS | Simulation equivalence preserves controls |
| III Backtesting & Validation | Must retain signal/trade semantics | PASS (planned) | Equivalence tests & baseline fixtures |
| IV Real-Time Monitoring | Progress & metrics required | PASS | FR-011/SC-008 define cadence |
| V Data Integrity | Dedup timestamps with audit logging | PASS | FR-008 updated policy |
| VI Data Provenance | Dataset manifest reference required | PASS | FR-012 ensures manifest_path & manifest_sha256 captured |
| VII Parsimony | Minimize indicators & complexity | PASS | Strategy-owned & no redundant calcs |
| VIII Code Quality | Docstrings, types, ≤88 chars | PASS (to enforce) | Add lint gate tasks |
| IX Dependency Mgmt | Poetry only, no new deps w/o justification | PASS | NumPy/pandas existing; numba deferred |
| X Quality Automation | Black/Ruff/Pylint/Markdownlint pass | PASS (planned) | Add pre-commit suggestions |
| XI Commit Standards | Semantic format with spec/task IDs | PASS | Will tag tasks Txxx |

Resolved: Dataset manifest linkage (VI) now formalized via FR-012 (PerformanceReport includes manifest_path, manifest_sha256, candle_count).

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
├── strategy/              # Strategy definitions & indicator declarations (ownership locus)
├── backtest/              # Orchestrator & simulation engine (to be optimized)
├── indicators/            # Indicator computation utilities (pure functions)
├── models/                # Pydantic models: Candle, TradeSignal, PerformanceReport
├── io/                    # Data ingestion (CSV parsing, manifest reference)
└── risk/                  # Risk management (untouched by performance changes)

tests/
├── unit/                  # Fine-grained tests (batch signal gen, dedupe set)
├── integration/           # End-to-end scan + simulation equivalence tests
├── performance/           # Timing & memory benchmarks vs baseline
└── contract/              # Indicator ownership enforcement tests
```

**Structure Decision**: Retain single-project layout; introduce batch-oriented modules under `backtest/` (e.g., `batch_scan.py`, `batch_simulation.py`) and new performance test modules.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Mandatory Polars adoption | Required columnar speed & memory benefits | Pandas only path slower & higher memory |
| Optional numba (deferred) | Potential future speed > pure NumPy | Baseline may suffice; premature complexity |

No other violations anticipated.

## Phase 0: Research

### Objectives

Resolve remaining clarifications (dataset manifest linkage, mandatory Polars & Parquet adoption, optional numba timing) and gather best-practice guidance for large array processing, progress emission efficiency, deterministic benchmarking, and Polars optimization patterns.

### Research Tasks

- R1: Research best way to reference dataset manifest in performance report for reproducibility (filename + SHA256 + date).
- R2: Evaluate cost/benefit of introducing numba for batch simulation vs pure NumPy (threshold criteria for adoption).
- R3: Best practices for large-scale NumPy memory management (avoid intermediate copies; use views; dtype selection).
- R4: Efficient progress update emission strategies (frequency heuristics; minimizing console I/O overhead).
-- R5: Deterministic performance benchmarking methodology (warm-up runs, environment isolation, CPU affinity guidelines).
-- R6: Polars + Parquet conversion strategy (partitioning, compression settings, schema evolution).
-- R7: Polars optimization best practices (lazy queries vs eager, predicate pushdown, projection minimization).

### Decisions & Rationale (to be mirrored in `research.md`)

- D1 Manifest linkage: Include manifest path (relative), SHA256, and recorded row count in `PerformanceReport` for reproducibility. Rationale: Satisfies Constitution Principle VI; lightweight metadata.
- D2 numba adoption: Defer until post-baseline profiling; adopt only if ≥25% additional speed on simulation inner loop. Rationale: Avoid premature optimization and dependency overhead.
-- D3 Memory management: Use `np.asarray` once; preallocate arrays; prefer int32 indices; avoid Python per-item accumulation.
-- D4 Progress emission: Use coarse modulo stride (≈16K elements) + time-based fallback (≤120s) to maintain ≤1% overhead.
-- D5 Determinism: Fix seeds (if any), freeze parameters, disable adaptive logging, capture environment metadata (Python version, OS, CPU model) in report.
-- D11 Mandatory Polars adoption: Replace pandas preprocessing with Polars LazyFrame; pandas retained only for legacy verification.
-- D12 Parquet conversion: First ingest converts CSV→Parquet (compression=zstd, tuned row group) + schema fingerprint persisted.
-- D13 Allocation baseline methodology: Baseline via `scripts/ci/profile_scan_allocations.py` (tracemalloc snapshots) -> allocations per million candles.
-- D14 Progress overhead computation: Measure cumulative time in dispatcher vs phase runtime; enforce ≤1% threshold (FR-011 / SC-013).
-- D15 Manifest provenance enforcement: Validation test compares manifest checksum & path to PerformanceReport (FR-012).
-- D16 Indicator mapping artifact: PerformanceReport includes ordered `indicator_names[]` enabling direct audit (FR-013).
All NEEDS CLARIFICATION resolved.

## Phase 1: Design & Contracts

### Data Model (`data-model.md`)

Entities:

- Candle: timestamp_utc, open, high, low, close (float64); indicator fields (float64, optional NaN warm-up).
- Indicator Registry: names: list[str]; version: str; ordered canonical declaration source for indicators.
- TradeSignal: id, timestamp_utc, direction, stop_loss_pct, take_profit_pct, strategy_id.
- SimulationResult: trade_id, entry_timestamp, exit_timestamp, pnl, exit_reason.
- PerformanceReport: scan_duration_sec, simulation_duration_sec, peak_memory_mb, manifest_path, manifest_sha256, candle_count, signal_count, trade_count, equivalence_verified(bool), progress_emission_count, progress_overhead_pct, indicator_names[], deterministic_mode(bool), allocation_count_scan, allocation_reduction_pct, duplicate_timestamps_removed, duplicate_first_ts?, duplicate_last_ts?, created_at.

Validation rules: timestamp strictly increasing after dedupe; pct fields within (0, 1]; NaN indicators allowed only in warm-up region; memory metrics non-negative.

### Contracts (`contracts/`)

Internal (non-network) pseudo-API interface definitions (OpenAPI style for documentation):

- POST /internal/scan: inputs (dataset_manifest_ref, strategy_id, parameters) → {signal_count, duration_sec, progress_samples[]}
- POST /internal/simulate: inputs ({strategy_id, signals_ref, slippage_pips}) → {trade_count, duration_sec, pnl_summary}
- GET /internal/performance-report/{run_id}: returns PerformanceReport JSON.

These serve as design contracts for modular function boundaries; not exposed externally.

### Quickstart (`quickstart.md` outline)

1. Prepare dataset & manifest
2. Run baseline benchmark capture script
3. Execute optimized scan (command example via CLI)
4. Execute optimized simulation
5. View performance report & equivalence summary
6. Interpreting progress updates & reproducibility data.

### Agent Context Update

Will run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType copilot` after creating `research.md` and `data-model.md` to synchronize new architecture notes.

## Phase 2: Preparatory Planning (pre-tasks)

High-level implementation sequence (tasks to be enumerated separately):

1. Parquet conversion module (CSV → Parquet) with manifest update
2. Polars ingestion & LazyFrame pipeline (projection & filtering)
3. Baseline profiling harness & performance report scaffolding (Polars path)
4. Columnar extraction utilities & dedupe policy implementation (Polars → NumPy)
5. Batch signal generation (long/short unify) with index return
6. Batch simulation engine with preallocated arrays
7. Indicator ownership enforcement tests & contract tests
8. Deterministic benchmarking script & environment capture
9. Progress emission abstraction & integration
10. Performance comparison & target validation (scan, simulation, memory, allocations, progress overhead)
11. Documentation & quickstart finalization (Polars + Parquet as default)
12. Optional numba experiment (contingent on profiling results; gated after allocation & timing targets met)
13. Allocation reduction validation & determinism multi-run confirmation

Re-check Constitution gates after Phase 1 artifacts exist (Principle VI now PASS via FR-012; verify Principle X logging compliance in new modules).
