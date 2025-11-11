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

### Functional Requirements (Renumbered & Clarified 2025-11-07)

NOTE: Previous identifiers retained in parentheses for traceability.

* **FR-001**: Ingestion MUST produce only core columns: timestamp, open, high, low, close, volume, `is_gap` flag. (Old FR-001; column name standardized.)
* **FR-002**: Ingestion MUST complete processing of the 6.9M-row baseline dataset in ≤120 seconds (wall-clock) on baseline hardware (8-core CPU, 16GB RAM). (Old FR-002)
* **FR-003**: Ingestion MUST stabilize ordering chronologically and resolve duplicate timestamps deterministically (retain first occurrence; log count & sample). (Old FR-003)
* **FR-004**: Gap detection & fill MUST use batch/columnar operations (no per-row loops) and synthesized gap rows MUST have `is_gap=1`, volume=0. (Old FR-004)
* **FR-005**: Indicator computations MUST occur only after ingestion in a separate enrichment step; ingestion layer MUST NOT import indicator modules. (Old FR-005 + enforcement)
* **FR-006**: Indicator enrichment MUST accept a list of indicator identifiers and append only those metrics. (Old FR-006)
* **FR-007**: Enrichment MUST validate requested indicators and fail fast (strict mode) on unknown identifiers with zero partial columns. (Old FR-007)
* **FR-008**: System MUST provide two output modes: (a) columnar DataFrame (Arrow-enabled if available) and (b) iterable candle objects. (Old FR-008)
* **FR-009**: Columnar mode MUST achieve ≥25% faster median wall-clock runtime (3-run median) vs iterator mode on baseline dataset. (Old FR-009 clarified protocol)
* **FR-010**: Ingestion MUST emit progress stages (≤5): read, sort, dedupe, gaps, finalize; no per-row logging. (Old FR-010 clarified)
* **FR-011**: Optional numeric downcasting MUST preserve precision: absolute difference per field ≤1e-6 and no overflow; rows failing threshold remain original dtype. (Old FR-011)
* **FR-012**: Uniform cadence validation MUST compute deviation = (missing_intervals / expected_intervals)*100; if >2.0% raise CadenceDeviationError (descriptive). (Old FR-012 formula)
* **FR-013**: Empty input MUST yield empty structured output (0 rows) with metrics populated (rows_in=0, rows_out=0, runtime). (Old FR-013)
* **FR-014**: Non-UTC timestamps MUST trigger fast-fail with error containing offending timezone codes list. (Old FR-014)
* **FR-015**: Summary metrics MUST include: rows_in, rows_out, gaps_synthesized, duplicates_removed, runtime_seconds, throughput_rows_per_sec, backend, downcast_applied(bool). (Old FR-015 + throughput)
* **FR-016**: Performance harness MUST support repeatable runs: 1 warm-up + 3 measured runs; record variance (%) and median. (Old FR-016 clarified)
* **FR-017**: Ingestion layer MUST NOT contain strategy indicator logic nor import indicator computation modules (static audit). (Old FR-017)
* **FR-018**: Indicator enrichment MUST NOT mutate original core dataset (validated by hash of core columns; returns enriched copy). (Old FR-018)
* **FR-019**: System MUST document indicator identifier contract (name, required input columns, parameters) in registry docs. (Old FR-019)
* **FR-020**: Missing core columns MUST raise MissingColumnsError with payload {"missing": [list], "expected": [list]}. (Old FR-020 clarified)
* **FR-021**: Duplicate indicator names MUST raise DuplicateIndicatorsError before computation. (Old FR-021)
* **FR-022**: System SHOULD expose extension points for future multi-symbol ingestion (placeholder documented). (Old FR-022)
* **FR-023**: Ingestion MUST avoid row-wise loops over datasets >100K rows (static scan disallowing iterrows/itertuples). (Old FR-023 + threshold)
* **FR-024**: Core output MUST remain immutable under enrichment (copy-on-write or view). (Old FR-024)
* **FR-025**: Optional columnar acceleration: if Arrow unavailable MUST fall back & emit warning {"backend":"pandas","expected":"arrow","impact":"performance","advice":"install pyarrow"}. (Old FR-025 clarified)
* **FR-026**: Pluggable indicator registry MUST allow registration/unregistration + dependency resolution (topological order). (Old FR-026)
* **FR-027**: System SHOULD track stretch runtime metric (≤90s) artifact JSON {"baseline_seconds","stretch_target_seconds","latest_seconds"}. (Old FR-027 clarified)
* **FR-028**: Implementation MUST NOT require discrete GPU; absence of GPU libs MUST NOT degrade baseline goals (test simulates missing CUDA). (Old FR-028 clarified)

### Non-Functional Requirements (Added 2025-11-07)

* **NFR-001**: Benchmark protocol (FR-009) uses 3 measured runs + 1 warm-up; median reported; variance ≤10% else flag.
* **NFR-002**: Memory footprint measurement (SC-006) samples RSS pre, peak, post; improvement ≥25% documented.
* **NFR-003**: Progress violation (>5 stages or unknown stage) raises ProgressContractError (test failure).
* **NFR-004**: Logging MUST use lazy % formatting; CI script enforces no f-string logging (Principle X).
* **NFR-005**: Throughput metric (rows/sec) logged; ≥58,333 rows/sec (3.5M/min) on baseline dataset.
* **NFR-006**: Arrow fallback warning MUST match schema in FR-025; metrics backend reflects fallback.
* **NFR-007**: Cadence deviation error includes expected_intervals, missing_intervals, deviation_percent (2 decimals).
* **NFR-008**: Core immutability verified via SHA256 hash of concatenated timestamp/OHLCV/is_gap columns pre/post enrichment.
* **NFR-009**: Benchmark artifacts stored under `results/benchmarks/` named `ingestion_run_<timestamp>.json`.
* **NFR-010**: GPU independence test asserts identical backend metrics when GPU libs absent.

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

* **SC-001**: Baseline ingestion runtime reduced from ~420s to ≤120s (≥71% improvement) median of 3 measured runs.
* **SC-002**: Columnar throughput ≥3.5M rows/min (≥58,333 rows/sec) median; variance ≤10%.
* **SC-003**: Indicator enrichment adds only requested columns (specificity 100%).
* **SC-004**: Duplicate resolution deterministic (dataset hash identical across repeated runs).
* **SC-005**: Gap fill correctness: synthesized gap row count equals expected missing intervals (0 tolerance).
* **SC-006**: Memory peak reduced by ≥25% vs baseline (RSS sampling) during ingestion.
* **SC-007**: No per-row loops detected (static scan passes; zero disallowed constructs).
* **SC-008**: Progress updates exactly match defined stages (≤5); violation triggers test failure.
* **SC-009**: Unknown indicator fast-fail occurs with zero partial columns created.
* **SC-010**: Core dataset hash (SHA256) unchanged after enrichment.
* **SC-011**: Benchmark variance ≤10%; artifacts persisted per NFR-009.
* **SC-012**: Stretch goal runtime ≤90s achieved within two optimization iterations post baseline.
* **SC-013** (Future Optional): If GPU acceleration added, runtime ≤75s without correctness regression.

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

Specification updated with clarified Functional Requirements, added Non-Functional Requirements, standardized terminology (`is_gap`), defined benchmark & precision protocols, and ordered success criteria. Ready for remediation tasks & implementation.
