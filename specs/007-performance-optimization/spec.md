# Feature Specification: Performance Optimization: Backtest Orchestrator & Trade Simulation

**Feature Branch**: `007-performance-optimization`
**Created**: 2025-11-05
**Status**: Approved (post-analysis refinement 2025-11-05)
**Input**: User description (Issue #15) summarised: Reduce large backtest runtime (millions of candles; ~17.7k trades) from hours to minutes via improved data handling, caching, batched trade simulation, performance profiling, scalable parallel execution, and benchmark tracking while preserving result fidelity.

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Fast Large Backtest Execution (Priority: P1)

As a quantitative researcher, I want a single large backtest (millions of candles) to complete in minutes (≤20m target; stretch 10–15m) instead of hours so I can iterate strategy parameters the same day.

**Why this priority**: Directly unlocks rapid research cycles and is the core value driver.

**Independent Test**: Run a representative full-dataset backtest; measure total wall-clock time versus success criteria without enabling any optional secondary features.

**Acceptance Scenarios**:

1. **Given** a dataset of ≥6.9M candles and default parameters, **When** the researcher starts a backtest, **Then** the job finishes within the defined maximum time threshold for a single run.
2. **Given** identical inputs on two consecutive runs in deterministic mode, **When** executed, **Then** aggregate results (PnL, trade counts, win rate) match within defined tolerances.

---

### User Story 2 - Performance Bottleneck Insight (Priority: P2)

As a performance engineer, I want a profiling and phase timing report so I can identify remaining hotspots and prevent regressions.

**Why this priority**: Enables continuous improvement and guards against future slowdowns.

**Independent Test**: Enable profiling flag; validate output artifact lists phase durations (ingest, scan, simulate) and top hotspots ranked by time percentage.

**Acceptance Scenarios**:

1. **Given** profiling is enabled, **When** a backtest completes, **Then** a profiling artifact exists containing phase breakdown and hotspot ranking.
2. **Given** two profiling runs after an optimization change, **When** compared, **Then** the targeted phase shows reduced time ≥ documented improvement.

---

### User Story 3 - Partial Dataset Iteration (Priority: P3)

As a strategist, I want to run a fraction (e.g., 0.2) of the dataset to quickly validate directional improvements before committing to full runs. I want to specify the portion via an interactive prompt or command-line flag.

**Why this priority**: Accelerates exploratory tuning while conserving time/resources and allows for variation in test data while conducting experiments.

**Independent Test**: Invoke dataset fraction prompt or CLI flag; ensure only the specified fraction of rows is processed (confirmed by benchmark record) and runtime scales down proportionally.

**Acceptance Scenarios**:

1. **Given** a fraction flag of 0.25 and portion flag of 2, **When** the backtest starts, **Then** only the second 25% of chronological rows are processed and logged as such.
2. **Given** fraction input omitted at interactive prompt, **When** user accepts default, **Then** system does not prompt for portion and processes 100% of rows.

---

### Edge Cases

- Fraction input = 0 (system should re-prompt; must not proceed with zero rows).
- Fraction input > 1 or negative (reject and re-prompt with guidance).
- Dataset extremely large (≥15M rows) should still avoid memory exhaustion; system streams/chunks without crash.
- Trade enters and exits on same bar (immediate resolution recorded correctly).
- Overlapping trades large active set does not degrade asymptotically back to per-trade full scans.
- No derived indicators requested (system skips caching stage gracefully).
- Parallel worker count set higher than available logical cores (system caps or warns without failure).
- Missing profiling flag (system runs without creating profiling artifact).
- Invalid tolerance configuration (system falls back to documented defaults).

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST provide optional per-run performance profiling producing phase timings (ingest, signal scan, trade simulation) and hotspot list when enabled via a user flag.
- **FR-002**: System MUST allow specifying a dataset fraction (0–1 inclusive) interactively and via a flag; slicing MUST occur before derived computations or simulation. MUST also support selecting a specific portion index (e.g., second quartile) when fraction < 1 via a `--portion` flag or interactive prompt.
- **FR-003**: System MUST load large candle datasets (≥10M rows) using a column-limited, typed representation containing only required price/volume/time fields for the run. Loader MUST enforce explicit dtypes (e.g., float64 for prices, int32 for indices) and reject unexpected/unused columns.
- **FR-004**: System MUST cache derived indicator series for reuse across parameter combinations within a single run eliminating redundant recomputation.
- **FR-005**: System MUST perform batched trade simulation avoiding per-trade full-dataset iteration; runtime MUST scale sub-linearly compared to baseline O(trades × bars) approach. Scaling target: optimized_sim_time ≤ 0.30 × baseline_sim_time on reference dataset (~17.7k trades).
- **FR-006**: System MUST preserve result fidelity: exit index, exit price, PnL, and classification flags must match baseline within defined tolerances (price ≤ 1e-6 absolute difference; indices exact).
- **FR-007**: System MUST support streaming or batched persistent writing of intermediate result sets (configurable batch size) to prevent unbounded in-memory growth; intermediate buffer peak MUST remain ≤ 1.1× raw dataset footprint.
- **FR-008**: System MUST support configurable parallel execution of independent parameter sets up to a maximum worker count without duplicating large static data unnecessarily.
- **FR-008a**: System MUST expose a `--max-workers` flag; when requested workers exceed logical cores, system MUST cap to core count and emit a single warning.
- **FR-009**: System MUST offer deterministic mode ensuring repeated runs with identical inputs produce statistically identical outputs within tolerances.
- **FR-010**: System MUST throttle progress/log output so that logging overhead does not materially increase total runtime (e.g., bounded update frequency).
- **FR-011**: System MUST generate a benchmark record per run including dataset rows processed, trades simulated, phase times, wall-clock total, and success criteria pass/fail flags.
- **FR-012**: System MUST validate fraction input and reject invalid values with a clear prompt before proceeding.
- **FR-013**: System MUST record memory footprint peak and flag if exceeding configured threshold (e.g., >1.5× raw dataset footprint) in benchmark record.
- **FR-014**: System MUST embed pass/fail flags for each success criterion in the benchmark record (keyed by criterion id, e.g., SC-001).
- **FR-015**: System MUST provide an interactive fraction prompt fallback when `--data-frac` missing; empty input defaults to 1.0 and skips portion prompt.
- **FR-016**: System MUST validate hotspot count (≥10) in profiling artifact when profiling enabled.
- **FR-017** (Non-Functional): All new modules MUST follow logging standards (lazy `%` formatting) and include complete docstrings + type hints (constitution compliance).

### Key Entities _(include if feature involves data)_

- **Backtest Job**: Represents a single execution request; attributes: job id, start/end time, parameters, fraction used.
- **Dataset Slice**: Logical subset of chronological price data; attributes: total rows available, rows selected, first/last timestamp.
- **Indicator Cache**: Collection of derived time series keyed by logical descriptor; metadata: source dataset id, parameter signature list.
- **Trade Entry Record**: Structured data for each planned trade; attributes: entry index, side, initial risk parameters, sizing.
- **Trade Simulation Result**: Outcome attributes: exit index, exit reason, exit price, holding duration, PnL, flags.
- **Profiling Report**: Timing summary: phase durations, hotspot percentages, generation timestamp.
- **Benchmark Record**: Aggregated metrics per job: dataset rows processed, trades simulated, wall-clock time, phase breakdown, memory peak, scaling efficiency, fidelity checks.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Single full dataset backtest (~6.9M candles; ~17.7k trades) completes within ≤ 20 minutes (initial target) and stretch goal 10–15 minutes after advanced optimizations (measured wall-clock; exclude data download).
- **SC-002**: Trade simulation phase speedup ≥ 10× (baseline_sim_time / optimized_sim_time ≥ 10.0) on reference dataset.
- **SC-003**: Data loading + fraction slicing for ≥ 10M rows finishes in ≤ 60 seconds wall-clock (load_time + slice_time ≤ 60s).
- **SC-004**: Indicator caching reduces repeated indicator compute time by ≥ 80%: (baseline_repeat_time - cached_repeat_time) / baseline_repeat_time ≥ 0.80.
- **SC-005**: Parallel execution with up to 4 workers achieves ≥ 70% efficiency (ideal time divided by actual time ≥ 0.70) for independent parameter batches.
- **SC-006**: Aggregate PnL difference versus baseline ≤ 0.01%; win rate difference ≤ 0.1 percentage points; mean holding duration difference ≤ 1 bar. Deterministic dual-run reproducibility must satisfy same tolerances.
- **SC-007**: Benchmark record stored for 100% of runs, containing required fields and passing schema validation.
- **SC-008**: Profiling artifact generated when enabled includes top ≥10 hotspots each with percentage of total simulated time and per-phase breakdown (ingest, scan, simulate). <10 hotspots fails criterion.
- **SC-009**: Peak resident memory during simulation ≤ 1.5× raw dataset memory footprint (defined by row_count × bytes_per_selected_columns). Benchmark record MUST include `memory_ratio` = peak_bytes / raw_bytes.
- **SC-010**: Fraction prompt default accepted when user presses Enter without input (defaults to 1.0 and skips portion prompt); invalid entry triggers re-prompt ≤ 2 attempts before aborting gracefully with clear message.
- **SC-011**: Parallel efficiency ≥ 70%: efficiency = ideal_time_single_worker / (actual_time_parallel × workers) ≥ 0.70 for up to 4 workers.
- **SC-012**: Worker cap warning emitted exactly once when requested workers > logical cores.

## Assumptions

- Baseline runtime measurements exist or will be captured prior to optimization for comparison.
- Dataset structure consistent (chronological ordering, no duplicate timestamps required for accurate simulation).
- Price/volume columns sufficient for defined strategy set; extended columns (e.g., spreads) treated as optional future scope.
- Deterministic mode excludes non-deterministic sources (random sampling, time-of-day dependent operations).
- Parallel workload comprises independent parameter sets without shared mutable state requiring synchronization.
- Memory threshold calculation uses estimated bytes per row derived from column dtypes.

## Dependencies & Out of Scope

**Dependencies**: Accurate baseline metrics; existing orchestrator capable of producing trade entries; current strategy parameter grid generation.

**Out of Scope**: Introduction of new strategy logic, external monitoring integration, GPU acceleration, persistent historical profiling database; Parquet ingestion flag (deferred future revision); event-driven simulation mode stub (future exploration unless formally added later).

## Acceptance Testing Approach

- Phase timing test: Run with profiling enabled; verify presence and integrity of profiling report.
- Fidelity test: Compare baseline vs optimized run outputs; assert tolerances.
- Scaling test: Execute runs with worker counts 1..4; compute efficiency metric.
- Fraction slicing test: Run with multiple fraction values (0.25, 0.5, 1.0); confirm processed row counts.
- Memory usage test: Capture peak memory; verify threshold compliance.
- Caching test: Measure repeated indicator computation time before and after caching enablement.

## Edge Case Test Matrix (Linkable)

| Case               | Input                   | Expected Handling                | Outcome Metric        |
| ------------------ | ----------------------- | -------------------------------- | --------------------- |
| Zero fraction      | 0                       | Re-prompt user                   | No run initiated      |
| Over fraction      | 1.2                     | Re-prompt user                   | Valid input required  |
| Same-bar exit      | Entry + immediate SL/TP | Recorded single-bar duration (duration == 1) | Fidelity maintained |
| Large overlap      | Many active trades      | Batched checks remain performant | Runtime within target (SC-001) |
| Missing indicators | No derived params       | Skip caching stage               | No error              |
| Excess workers     | Workers > cores         | Cap and single warning           | Efficiency maintained |
| Hotspot insuff.    | <10 hotspots            | Flag profiling artifact invalid  | SC-008 failure        |
| Memory threshold   | Peak >1.5× raw          | Flag threshold exceeded in record| Warning emitted       |
| Portion selection  | fraction=0.25 portion=2 | Select second quartile rows      | Rows count matches spec |

## Notes

Specification intentionally avoids implementation technology names (e.g., specific libraries or storage formats) to remain solution-agnostic while describing required outcomes.
