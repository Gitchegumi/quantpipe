# Feature Specification: Scan & Simulation Performance Optimization

**Feature Branch**: `010-scan-sim-perf`
**Created**: 2025-11-11
**Status**: Draft
**Input**: User description: "Optimize scan (currently ~25+ mins) & simulation (18+ mins / 84,938 trades). Centralize indicator ownership in strategy only (backtest/io/util must not define indicators). Improve scan & simulation throughput; implement issue #21 goals."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Accelerated Market Scan (Priority: P1)

Quantitative analyst initiates a backtest run on a large historical dataset (≈6.9M candles) and the scan phase completes in a dramatically reduced time without altering the set of generated trade signals versus the baseline.

**Why this priority**: Scan phase is the current dominant time cost (≈25+ minutes). Improving it unlocks faster iteration and broader exploratory research within the same compute window.

**Independent Test**: Run the scan phase alone on the baseline dataset and measure duration and signal equivalence compared to a recorded baseline output file.

**Acceptance Scenarios**:

1. **Given** a recorded baseline dataset and baseline signal output, **When** the optimized scan is executed, **Then** the duration is ≤12 minutes and signals (timestamps & count) match baseline exactly.
2. **Given** a dataset containing duplicate timestamps, **When** the scan runs, **Then** duplicates are ignored without performance degradation.

---

### User Story 2 - Strategy-Owned Indicators (Priority: P2)

Strategy author specifies the complete indicator set within the strategy definition; backtest orchestration, IO, and generic utilities do not introduce, alter, or filter indicators, ensuring consistent, auditable signal creation.

**Why this priority**: Eliminates hidden coupling and side effects, improves transparency and reproducibility of performance results.

**Independent Test**: Audit code paths during a run to confirm no indicator declarations or mutations occur outside strategy; diff indicator list from strategy against runtime usage.

**Acceptance Scenarios**:

1. **Given** a strategy declaring indicators A, B, C, **When** a full run completes, **Then** only A, B, C appear in scan and simulation phases.
2. **Given** removal of indicator B from the strategy, **When** the run executes, **Then** B is absent everywhere without residual references or errors.

---

### User Story 3 - Efficient Trade Simulation (Priority: P3)

Performance engineer runs the simulation phase for ≈84,938 trades and observes a significant reduction in wall-clock time while producing identical trade outcomes (entry/exit timestamps, PnL) compared to baseline.

**Why this priority**: Simulation currently costs ≈18+ minutes, limiting workflow throughput after scan improvements.

**Independent Test**: Execute simulation with a fixed baseline signal set; measure elapsed time and validate trade result equivalence within defined tolerance.

**Acceptance Scenarios**:

1. **Given** a baseline signal set producing ≈84,938 trades, **When** simulation runs post-optimization, **Then** elapsed time is ≤8 minutes and net PnL difference ≤0.5%.
2. **Given** zero generated signals (edge condition), **When** simulation runs, **Then** it completes in <10 seconds without errors.

---

[Additional user stories may be added if scope expands to multi-strategy batching or cross-symbol parallelism, but these are out of current scope to preserve focus.]

### Edge Cases

- Extremely large dataset (>10M candles) still processes within proportional time (no super-linear degradation).
- Duplicate timestamps policy: keep first occurrence, discard subsequent duplicates; log total duplicates removed and first/last duplicate timestamp. (Prevents inflation and preserves determinism.)
- Missing indicator values at start of dataset (warm-up) do not produce false signals.
- Strategy declares zero indicators: system runs and produces zero indicator-derived signals without error.
- Memory pressure scenario (limited RAM) does not lead to catastrophic failure; run aborts gracefully with logged reason if minimum resources unavailable.
- Progress indicators do not materially slow processing (overhead ≤1% of total runtime). If progress emission is disabled, core performance metrics remain unchanged.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

The list below supersedes earlier draft items; duplicate FR-008 removed and clarified numbering extended to new FRs (011–014).

- **FR-001 (Scan Performance)**: Complete the scan phase on the baseline 6.9M-candle dataset in ≤12 minutes while producing identical signal timestamps and counts to the recorded baseline.
- **FR-002 (Allocation Efficiency)**: Eliminate per-record dynamic data structure creation during scanning; total Python object allocations during scan MUST be ≤1,500 per million candles (baseline measurement script records ~4,800). Signals only materialized after candidate batch identification.
- **FR-003 (Indicator Mapping)**: Provide an auditable one-to-one mapping of strategy-declared indicators to those used in scan & simulation. Mapping format: `indicator_names[]` (ordered exactly as strategy declaration). No extras, no omissions.
- **FR-004 (Strategy Ownership Isolation)**: No indicators are defined, mutated, or filtered outside the strategy layer. Indicator registry (canonical) is read-only elsewhere.
- **FR-005 (Simulation Performance)**: Reduce simulation phase runtime for ≈84,938 trades to ≤8 minutes while maintaining trade outcome equivalence (entry/exit timestamps) and net PnL variance ≤0.5% versus baseline.
- **FR-006 (Deterministic Mode Controls)**: Deterministic runs MUST fix: random seeds (if any), stable ordering of signal generation, single-threaded critical sections for ordering, and environment capture (Python version, OS, CPU model) embedded in report. Three consecutive deterministic runs produce identical signals & trades.
- **FR-007 (Performance Report Core)**: Provide a performance report including: scan_duration_sec, simulation_duration_sec, peak_memory_mb, signal_count, trade_count, equivalence verification status.
- **FR-008 (Duplicate Timestamp Handling)**: Handle input datasets containing duplicate timestamps by retaining the first occurrence only, discarding subsequent duplicates, and logging a concise summary (count removed + first/last duplicate timestamp) without increasing signal or trade counts.
- **FR-009 (Graceful Memory Abort)**: If available memory below configured `MEMORY_MIN_MB`, abort preprocessing gracefully within <3s, emitting structured log: `{event:"memory_abort", required_mb, available_mb, timestamp}` and no partial artifacts.
- **FR-010 (Zero Indicator Strategy)**: Strategies may declare zero indicators; scan and simulation complete without error and produce zero indicator-derived signals.
- **FR-011 (Progress Cadence & Overhead)**: Emit progress updates at intervals not exceeding the minimum of (120s wall-clock OR 2% completion). MUST always emit a final 100% update. Progress overhead (time spent emitting) ≤1% of total phase runtime.
- **FR-012 (Manifest Provenance)**: PerformanceReport MUST include dataset manifest provenance: `manifest_path`, `manifest_sha256`, `candle_count` matching the manifest file to satisfy Constitution Principle VI.
- **FR-013 (Indicator Mapping Artifact)**: PerformanceReport MUST include `indicator_names[]` exactly matching declared strategy indicators (order preserved) to enable audit tests.
- **FR-014 (Allocation Reduction Target)**: Scan MUST achieve ≥70% reduction in Python object allocations per million candles vs baseline (baseline recorded by allocation capture script). Allocation reduction percentage included in report.

No critical ambiguities remain requiring clarification after these additions; measurable thresholds now defined (time, allocation counts, memory abort behavior, progress overhead).

### Key Entities *(include if feature involves data)*

- **Candle**: Represents a single time-based price record (timestamp, open, high, low, close). Source of raw market data for scanning and simulation.
- **Indicator Registry**: Canonical ordered list of indicator definitions declared solely by a strategy (names + semantic meaning). Immutable outside strategy layer.
- **TradeSignal**: Represents a potential trade entry decision (timestamp reference, directional attributes, risk parameters). Semantics unchanged post-optimization.
- **SimulationResult**: Aggregated outcomes per executed trade (entry/exit timestamps, PnL metrics, stop/take outcomes) plus batch-level performance summary.
- **PerformanceReport**: Summary artifact containing all required performance & provenance metrics (see FR-007, FR-011–FR-014).

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: Scan duration ≤12 minutes on baseline 6.9M-candle dataset (≥50% improvement from ~25+ minutes baseline).
- **SC-002**: Simulation duration ≤8 minutes for ≈84,938 trades (≥55% improvement from ~18+ minutes baseline).
- **SC-003**: Signal equivalence: 100% matching timestamps and counts versus baseline (no false additions or omissions).
- **SC-004**: Trade result equivalence: net PnL variance ≤0.5% and count/exit timing variance ≤0.5% versus baseline.
- **SC-005**: Peak memory usage during scan reduced by ≥30% compared to baseline (measured via profiling tool before/after).
- **SC-006**: Indicator ownership audit passes: zero indicator declarations or mutations outside strategy layer across code paths.
- **SC-007**: Deterministic benchmark runs produce identical performance report metrics (±1% tolerance for timing noise) across three consecutive executions.
- **SC-008**: Progress updates appear at least every 2 minutes during scan and simulation phases and reflect completion percentage within ±5% accuracy.

- **SC-009**: PerformanceReport includes `manifest_path`, `manifest_sha256`, `candle_count`; checksum matches manifest file.
- **SC-010**: Allocation count during scan reduced ≥70% vs baseline (baseline captured by allocation baseline script). Value and reduction percentage recorded.
- **SC-011**: Indicator mapping artifact `indicator_names[]` matches strategy declarations exactly (order & cardinality).
- **SC-012**: Graceful memory abort emits structured log and terminates phase within <3s of detection.
- **SC-013**: Progress overhead (time inside emission logic / total phase time) ≤1%. Final 100% emission always present.

---

All success criteria are technology-agnostic, user/value focused, and objectively measurable.

## Clarifications

### Session 2025-11-11

- Q: What is the required handling policy for duplicate timestamps encountered during scan? → A: Keep first occurrence, discard later duplicates, log summary.
- Q: How should progress tracking be standardized for scan/simulation phases? → A: Stage-level coarse progress updates ≤2 min apart or ≤2% completion increments, low overhead.
- Q: How is allocation efficiency measured? → A: Tracemalloc snapshot comparison before/after scan; baseline captured by dedicated script; threshold defined in FR-002 & FR-014.
- Q: What constitutes deterministic controls? → A: Seed fixation (if randomness introduced), stable iteration order, single-thread ordering for signal generation, invariant environment metadata.
- Q: How is manifest provenance enforced? → A: PerformanceReport fields validated against manifest file and checksum verified in tests.

## Non-Functional Requirements

- **Performance**: Meet FR-001, FR-005 timing; allocation reduction ≥70%; memory reduction ≥30%.
- **Determinism**: Deterministic mode produces identical signals/trades & ≤1% timing variance across three runs.
- **Provenance**: Manifest fields embedded per FR-012; checksum validation mandatory.
- **Progress UX**: Cadence rules + final emission per FR-011; overhead ≤1%.
- **Logging Compliance**: All new logging uses lazy `%` formatting (Constitution Principle X); no f-string interpolation in logging calls.
- **Resource Abort**: Graceful memory abort structure defined (FR-009) with validation test.
- **Indicator Integrity**: Mapping artifact (FR-013) prevents silent indicator drift.
