# Feature Specification: Optimize & Decouple Ingestion Process

**Feature Branch**: `009-optimize-ingestion`
**Created**: 2025-11-07
**Status**: Draft
**Input**: User description: "Optimize and Decouple Ingestion Process. Ingestion currently takes ~7 minutes for 6.9M candles due to row-wise work and strategy-specific calculations mixed into the pipeline. Refactor the ingestion layer to (1) speed it up via vectorization/Arrow and (2) fully decouple indicators (e.g., StochRSI) from ingestion so strategies can opt in to only what they need. Use GitHub cli to review issue #20 for further details."

**Scope Summary (Plain Language)**: Provide a faster, lean ingestion stage that outputs only core market data plus gap flags, and move all indicator calculations to an optional, post-ingestion step selectable per strategy. The result enables performance gains, reduced memory footprint, and clearer separation of concerns.

**Out of Scope**: Persisting data to new storage formats, adding new indicators, multi-symbol batching, distributed ingestion.

**Assumptions**:

1. Baseline hardware: commodity 8-core CPU, 16GB RAM workstation; baseline runtime ≈ 7 minutes for 6.9M candles.
2. Input data cadence is uniform (e.g., 1‑minute) for a single symbol per ingestion call.
3. Indicator calculations can tolerate being invoked on fully materialized columnar data after ingestion.
4. Existing strategy code can adapt to receiving core frame + optional enrichment layer without breaking.
5. Performance target measured using same dataset & environment as baseline.
6. A high-end GPU (RTX 4080) is available but NOT required for baseline targets; any GPU acceleration (e.g., via alternative data frame libraries) is a future, optional enhancement outside current scope.

**Decisions (Clarifications Resolved)**:

* Columnar acceleration backend is OPTIONAL with graceful fallback (warning + performance metrics logged). Strict mode may be added later but not required for baseline.
* Indicator registration uses a PLUGGABLE REGISTRY (explicit registration API) – static core set + ability to register additional indicators programmatically.
* Stretch performance target adopted: aspirational ≤90 seconds runtime tracked as secondary goal once ≤2:00 baseline met.

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

### User Story 1 - Fast Core Ingestion (Priority: P1)

Strategy maintainer ingests a large historical dataset (≈6.9M uniform candles) and receives a clean, normalized core dataset containing only timestamp, OHLCV, and gap flag in ≤2 minutes.

**Why this priority**: Directly addresses current performance bottleneck; unlocks faster iteration and benchmarking for all downstream features.

**Independent Test**: Time the ingestion of baseline dataset; verify only core columns produced; confirm runtime ≤ target threshold without requiring indicator modules.

**Acceptance Scenarios**:

1. **Given** baseline raw candle file, **When** ingestion is invoked, **Then** output includes only core columns and completes within target time.
2. **Given** unsorted input rows, **When** ingestion runs, **Then** output is chronologically ordered and stable.
3. **Given** duplicate timestamps, **When** ingestion runs, **Then** duplicates are resolved by deterministic rule (e.g., keep first occurrence) and logged.

---

### User Story 2 - Opt-In Indicator Enrichment (Priority: P2)

Strategy author requests only selected indicators (e.g., EMA20, EMA50, ATR14) after ingestion; system computes and returns enriched dataset without repeating ingestion work or adding unrequested metrics.

**Why this priority**: Eliminates unnecessary preprocessing; reduces wasted compute and memory for strategies not needing full indicator sets.

**Independent Test**: Invoke enrichment on core dataset with specified indicator list; verify only requested indicator columns appear; ingestion timing unaffected.

**Acceptance Scenarios**:

1. **Given** core ingestion output and indicator selection, **When** enrichment runs, **Then** only requested indicator columns are appended.
2. **Given** empty indicator selection, **When** enrichment runs, **Then** output equals input (no mutation aside from possible metadata).
3. **Given** unsupported indicator name, **When** enrichment runs, **Then** a clear validation error is returned (no partial computation).

---

### User Story 3 - Dual Output Modes (Priority: P3)

Performance-focused user selects a fast columnar frame output for simulation; another user opts for materialized iterator of candle objects for legacy code paths.

**Why this priority**: Supports migration without forcing immediate refactors while enabling high-performance path for new strategies.

**Independent Test**: Request each mode independently; confirm outputs conform to defined contract; timings show columnar mode faster than object materialization.

**Acceptance Scenarios**:

1. **Given** ingestion invoked with columnar mode, **When** completed, **Then** a frame-like structure is returned with defined schema.
2. **Given** ingestion invoked with materialized mode, **When** iterated, **Then** each element yields a candle representation matching schema and iteration completes without excessive memory overhead.
3. **Given** invalid mode flag, **When** invoked, **Then** a validation error is raised and no partial data returned.

---

Additional stories deferred (multi-symbol batching, streaming ingestion) – explicitly out of current scope.

### Edge Cases

* Missing time segments at start or end of dataset (ensure gap detection vs. outside-range exclusion).
* Entirely empty input file (return empty structured output gracefully).
* Duplicate timestamps within raw data (deterministic resolution and log entry).
* Non-uniform cadence (reject with clear error if cadence mismatch exceeds tolerance threshold).
* Memory pressure on very large datasets (allow optional type downcast mode while preserving correctness metrics).
* Unexpected additional columns in input (ignore unless required; do not fail ingestion).
* Indicator request referencing same column name twice (reject duplication to avoid ambiguous overwrite).
* Timezone inconsistencies (input assumed UTC; any non-UTC timestamps flagged and rejected).

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

* **FR-001**: Ingestion MUST produce only core columns: timestamp, open, high, low, close, volume, gap flag.
* **FR-002**: Ingestion MUST complete processing of the 6.9M-row baseline dataset in ≤ 2 minutes on assumed hardware.
* **FR-003**: Ingestion MUST stabilize ordering (chronological) and resolve duplicates deterministically (first occurrence retained, others discarded and logged).
* **FR-004**: Gap detection & filling MUST be performed via batch/columnar operations (no per-row loops) and mark synthesized rows with gap flag and zero volume.
* **FR-005**: Indicator computations MUST occur only after ingestion in a separate enrichment step, never inside core ingestion execution.
* **FR-006**: Indicator enrichment MUST accept a list of requested indicator identifiers and append only those metrics to the dataset.
* **FR-007**: Enrichment MUST validate requested indicators and fail fast with a clear message on unknown identifiers (no partial success).
* **FR-008**: System MUST provide two output modes: (a) columnar frame structure and (b) iterable candle objects, selectable via explicit parameter.
* **FR-009**: Columnar mode MUST outperform materialized iteration mode (time per million rows) by a measurable margin (≥25% faster) under baseline test.
* **FR-010**: Ingestion MUST expose minimal progress reporting (stage-level only) without per-row updates.
* **FR-011**: System MUST allow optional type downcasting mode for numeric fields to reduce memory footprint while preserving required precision assumptions.
* **FR-012**: Ingestion MUST validate uniform cadence; if cadence deviation exceeds tolerance (e.g., >2% missing intervals), MUST raise a descriptive error.
* **FR-013**: Ingestion MUST gracefully handle empty input (return empty structured output with metadata indicating zero rows processed).
* **FR-014**: Ingestion MUST reject non-UTC timestamps with a clear error and not proceed.
* **FR-015**: System MUST log summary metrics: total rows input, rows output, gaps synthesized, duplicates removed, total runtime.
* **FR-016**: Performance test harness MUST allow repeatable timing runs over baseline dataset.
* **FR-017**: No strategy-specific indicator logic MUST remain inside ingestion layer (enforced via code-level separation rule).
* **FR-018**: Indicator enrichment MUST NOT mutate original core dataset in-place (returns new or clearly enriched view preserving base schema).
* **FR-019**: System MUST provide clear contract documentation for indicator identifier names and their required input columns.
* **FR-020**: Ingestion MUST fail fast on missing required core columns in input with descriptive error listing missing columns.
* **FR-021**: Duplicate indicator names in request MUST raise validation error prior to computation.
* **FR-022**: System SHOULD support future multi-symbol ingestion via extension points without current implementation (document extension placeholder).
* **FR-023**: Ingestion MUST avoid row-wise loops over data size > threshold (automated static check or benchmark evidence).
* **FR-024**: Core output MUST be immutable by enrichment routines (enforcement via copy-on-write or contract – technology-agnostic).
* **FR-028**: Implementation MUST NOT require presence of discrete GPU; GPU acceleration MAY be added later as an optional enhancement path without altering core contracts.

Clarification-derived requirements:

* **FR-025**: System MUST provide optional columnar acceleration; if unavailable MUST fall back to standard path and emit a performance capability warning.
* **FR-026**: System MUST implement a pluggable indicator registry allowing explicit registration/unregistration of indicator providers.
* **FR-027**: System SHOULD track a stretch ingestion runtime metric aiming for ≤90 seconds on baseline dataset after achieving ≤2:00 requirement.

### Key Entities *(include if feature involves data)*

* **CoreCandleRecord**: Represents a single normalized input unit with timestamp, open, high, low, close, volume, gap flag.
* **IngestionResult**: Encapsulates core dataset, summary metrics (row counts, runtime, gap count, duplicate count), and mode metadata (columnar vs. materialized).
* **IndicatorEnrichmentRequest**: Specifies list of indicator identifiers and optional parameters (e.g., periods) following a documented naming contract.
* **EnrichedDataset**: Output structure combining Core dataset with appended indicator columns; preserves original core columns unchanged.
* **PerformanceMetrics**: Captures timing and throughput statistics for benchmark harness (rows/sec, total runtime, memory usage snapshot).

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

* **SC-001**: Ingestion runtime for baseline dataset reduced from ~7:00 to ≤2:00 (≥71% improvement) consistently over 3 consecutive runs.
* **SC-002**: Columnar output mode processes ≥3.5M rows/minute (throughput) under baseline conditions.
* **SC-003**: Indicator enrichment adds only requested columns with zero extraneous additions (audited in test – 100% specificity).
* **SC-004**: Duplicate timestamp resolution produces deterministic results (idempotent re-run yields identical dataset – verified by hash comparison).
* **SC-005**: Gap fill correctness: inserted gap row count equals expected missing interval count (tolerance 0 discrepancies).
* **SC-006**: Memory footprint peak during ingestion ≤ baseline peak minus 25% (measured resident memory reduction).
* **SC-007**: No per-row loop constructs present in performance-critical path (static scan + benchmark validation).
* **SC-008**: Progress reporting limited to ≤5 total updates per ingestion run (stage-level only).
* **SC-009**: Failure on unknown indicator name occurs before any enrichment side effects (test: no partial new columns created).
* **SC-010**: Core dataset immutability preserved (hash of core columns unchanged after enrichment – verified in test).
* **SC-011**: Benchmark harness produces reproducible timing variance ≤10% across three runs.
* **SC-013** (Optional/Future): With optional GPU acceleration layer (if implemented later), ingestion runtime target ≤75 seconds on baseline dataset without degrading correctness.
* **SC-012**: Stretch goal: After baseline (≤2:00) is achieved, further optimization reduces runtime to ≤90 seconds within two subsequent optimization iterations.

Stretch criterion added (see SC-012) following clarification decisions.

## Dependencies & Risks (Optional)

* Dependency: Baseline raw data availability for timing comparisons.
* Risk: Aggressive downcasting could reduce numerical precision affecting certain indicators (mitigated by opt-in design).
* Risk: Overly complex plugin model could delay delivery (clarification needed to choose simplest viable path).
* Risk: Premature GPU dependency introduction (e.g., cuDF) could violate current no-new-deps guideline; deferred until clear ROI beyond stretch CPU goals.
* Benefit (Future): Optional GPU path offers additional 15–25% runtime reduction potential for large datasets once dependency policy allows.

## Removed Open Questions

All prior clarification questions resolved; no outstanding open questions.

## Readiness Statement

Specification provides user-centric stories, testable functional requirements (including resolved clarifications), and measurable success criteria (including stretch goal). Ready for planning phase.
