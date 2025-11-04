# Feature Specification: Multi-Strategy Support

**Feature Branch**: `006-multi-strategy`
**Created**: 2025-11-03
**Status**: Draft
**Input**: User description: "Set the app up to handle multiple strategies. Provide a way to program multiple strategies, backtest multiple strategies, and show results either with each strategy run on its own or as if the strategies were run together. Requirements: strategy registry/manager; strategy isolation (separate state & risk limits per strategy); strategy selection/filtering in backtesting CLI; portfolio-level metrics aggregation (individual & combined); strategy-specific configuration management."

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Run Multiple Strategies Together (Priority: P1)

An operator selects several existing trading strategies and runs a single backtest execution that evaluates all of them concurrently against the same historical price dataset while keeping each strategy's internal state, parameters, and risk limits isolated. After completion, the operator views both individual strategy performance metrics and aggregated portfolio metrics (combined PnL, drawdown, exposure) across all participating strategies.

**Why this priority**: This is the core value driver: simultaneous evaluation with portfolio aggregation enables comparative and combined performance insight and is the minimum viable multi-strategy capability.

**Independent Test**: Execute a backtest with ≥2 strategies using identical market data; verify each produces distinct results files; verify a separate aggregated portfolio metrics output is generated without cross-strategy state contamination.

**Acceptance Scenarios**:

1. **Given** multiple registered strategies with distinct configs, **When** the operator runs a multi-strategy backtest, **Then** the system produces per-strategy result artifacts and one aggregated portfolio metrics artifact.
2. **Given** strategies with overlapping instruments, **When** conflicting long/short signals occur, **Then** each strategy's position history remains independent and the aggregated portfolio metrics reflect the net combined exposure (see FR clarification for allocation/conflict rules).

---

### User Story 2 - Strategy Registration & Configuration (Priority: P2)

A strategy developer adds a new strategy by providing a unique identifier, default configuration parameters, and risk limits. The system registers the strategy so it becomes discoverable by the backtesting CLI and can be included in multi-strategy runs without modifying core backtest orchestration code.

**Why this priority**: Enables scaling—new strategies can be introduced and governed through consistent configuration and risk isolation.

**Independent Test**: Register a new strategy; list strategies; run a single-strategy backtest; confirm configuration overrides apply only to that strategy.

**Acceptance Scenarios**:

1. **Given** a developer supplies a valid strategy definition and config, **When** it is registered, **Then** it becomes selectable in CLI listing.
2. **Given** a registered strategy with risk limits, **When** a backtest exceeds its per-strategy limit, **Then** that strategy halts further trade generation while others continue.

---

### User Story 3 - Strategy Selection & Filtering (Priority: P3)

An operator uses CLI flags to specify an explicit subset of registered strategies (by name/tag) to include in a backtest run, optionally excluding others. The operator can also request only individual outputs (no aggregation) or both.

**Why this priority**: Provides operational control—users can focus evaluation on relevant subsets and choose output scope.

**Independent Test**: Invoke CLI with list of strategies and aggregation flag; verify only selected strategies run and aggregation produced according to flag.

**Acceptance Scenarios**:

1. **Given** 5 registered strategies, **When** the operator selects 2 via CLI, **Then** only those 2 execute and only their result files (plus optional aggregation) are produced.
2. **Given** selection includes an unknown strategy name, **When** execution starts, **Then** the system aborts gracefully with a clear validation error listing unknown names.

---

### Edge Cases

- Strategy produces zero trades (should still output metrics with zeros and appear in aggregation).
- One strategy breaches its per-strategy risk limit mid-run (its further trade generation stops; others unaffected; aggregation includes its realized results up to halt point).
- Global portfolio drawdown limit breached (all strategies halt further trade generation; existing per-strategy and aggregate results preserved; manifest records global breach).
- Unrecoverable system error or data corruption detected (global abort triggered; partial per-strategy outputs written; manifest records fatal error and abort cause).
- All selected strategies disabled by validation (abort with no partial outputs).
- Conflicting opposing positions on same instrument at same timestamp across strategies (each preserved independently; aggregation nets opposing quantities to yield a single net exposure figure per instrument timestamp).
- Duplicate strategy identifiers at registration (reject with clear error).
- Empty strategy selection list with aggregation requested (error: must select ≥1 strategy).
- Large number (≥20) strategies in run (performance target; results should complete within success criteria limits).

## Business Outcomes (Non-Technical Summary)

The feature enables:

1. Portfolio Perspective: View combined performance across multiple strategies to support allocation and diversification decisions.
2. Risk Transparency: Separate local breaches vs rare global halts provide clearer operational risk signals.
3. Faster Strategy Iteration: Developers register new strategies without codebase rewiring, accelerating experimentation.
4. Audit & Reproducibility: Deterministic runs with manifest linkage and stability targets improve trust and reviewability.
5. Operational Efficiency: Single multi-strategy execution reduces repetitive single-strategy runs and manual aggregation.

These outcomes center on user decision-making and process speed rather than internal implementation mechanics.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST provide a strategy registry allowing registration, listing, and retrieval by unique identifier.
- **FR-002**: System MUST isolate per-strategy state (positions, PnL tracking, indicators) so no strategy can mutate another's state.
- **FR-003**: System MUST enforce per-strategy configurable risk limits (e.g., max position size, daily loss threshold) halting only the offending strategy upon breach.
- **FR-004**: System MUST support CLI selection of one or more strategies by name and/or tag filters.
- **FR-005**: System MUST generate per-strategy result outputs (metrics, trades, positions) in the existing backtest result format.
- **FR-006**: System MUST generate an aggregated portfolio metrics output combining selected strategies when aggregation is enabled.
- **FR-007**: System MUST allow disabling aggregation (individual outputs only) via CLI flag.
- **FR-008**: System MUST ensure that failure of one strategy during execution does not terminate other strategies (unless global abort condition met).
- **FR-009**: System MUST support strategy-specific configuration overrides supplied at run time without affecting defaults of other strategies.
- **FR-010**: System MUST log strategy-level lifecycle events (start, halt, error, risk breach) distinctly.
- **FR-011**: System MUST provide a validation phase that rejects unknown strategies before execution.
- **FR-012**: System MUST expose portfolio-level metrics including combined PnL, cumulative drawdown, net exposure, total trades, and volatility across all strategies.
- **FR-013**: System MUST aggregate overlapping instrument exposures by netting opposing positions (long vs short) to produce a single net exposure value per instrument per time slice.
- **FR-014**: System MUST apply user-specified per-strategy weights (provided via CLI/config) when computing aggregated portfolio metrics; if weights are omitted, system defaults to equal-weight allocation.
- **FR-015**: System MUST enforce layered risk controls: per-strategy limits plus an optional global portfolio drawdown percentage threshold; breaching the global threshold halts further trade generation for all strategies while preserving completed results.
- **FR-016**: System MUST produce a run manifest listing strategies executed, versions, configs, risk limits, and aggregation settings.
- **FR-017**: System MUST allow listing strategies via CLI without running a backtest.
- **FR-018**: System MUST provide deterministic repeatability (same inputs produce identical per-strategy and aggregated outputs).
- **FR-019**: System MUST handle strategies producing zero trades without error.
- **FR-020**: System MUST fail fast with clear messaging if no valid strategies are selected.
- **FR-021**: System MUST restrict global abort conditions to: (a) configured global portfolio drawdown breach; or (b) unrecoverable system error (e.g., data corruption, required input integrity failure). Single strategy exceptions halt only that strategy while others continue.
- **FR-022**: System MUST produce an aggregated portfolio metrics artifact capturing combined performance, exposure, weighting applied, risk breach summary, and reproducibility linkage—format and exact field naming are implementation details governed by design docs (not mandated by the specification).
- **FR-023**: System MUST provide a reproducibility linkage between aggregated portfolio metrics and the original run manifest (conceptual reference, not prescribing hashing algorithm details here).

### Key Entities _(include if feature involves data)_

- **Strategy**: Conceptual trading logic unit with identifier, default configuration, risk limits, tags.
- **StrategyConfig**: Parameter set applied to a Strategy for a run (overrides allowed). Attributes: name, parameters map, risk limits, tags.
- **StrategyState**: Transient per-run state (positions, indicators cache, trade history) isolated per strategy.
- **StrategyResult**: Output artifact summarizing metrics, trades, positions, and risk events for one strategy.
- **PortfolioAggregate**: Combined metrics artifact: net PnL, cumulative drawdown, volatility, exposure vectors, trade counts, allocation assumptions.
- **RunManifest**: Metadata linking strategies, configs, timestamps, data sources, aggregation mode, clarifications resolution.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Operator can run ≥3 strategies concurrently and receive both individual and aggregated outputs in a single execution without errors.
- **SC-002**: Aggregated portfolio metrics file generated ≤5 seconds after final strategy completes (for baseline dataset ≤1M price rows).
- **SC-003**: Adding each additional strategy (up to 10) increases total runtime by ≤15% of single-strategy baseline on identical data.
- **SC-004**: Risk breach in one strategy does not affect execution or metrics generation of others (verified by continued outputs for unaffected strategies 100% of test runs).
- **SC-005**: 100% of selected strategies appear in RunManifest with correct config and risk limit values.
- **SC-006**: Zero-trade strategies still produce valid metrics artifacts (PnL = 0, trades = 0) and are included in aggregation without errors.
- **SC-007**: CLI validation rejects unknown strategy names with a clear message in <1 second before any market data processing begins.
- **SC-008**: Deterministic repeatability: repeated runs with identical inputs produce byte-identical per-strategy and aggregate metric summaries (excluding timestamps) in 3 consecutive test executions.
- **SC-009**: Strategy listing CLI returns registered strategies in <2 seconds for ≤50 strategies.
- **SC-010**: Aggregation logic resolves overlapping instrument exposures according to clarified rule producing consistent net exposure totals across test scenarios.
- **SC-011**: Reliability: High multi-strategy completion rate (target encoded in design; excludes intentional global drawdown aborts) demonstrating orchestration stability.
- **SC-012**: Memory growth awareness: Incremental memory impact per additional strategy remains within a defined informational threshold (tracked, not a release blocker).

### Assumptions

- If user does not supply weights, equal-weight allocation is automatically applied.
- Net exposure aggregation (position netting) is the standardized approach for overlapping instruments.
- Global portfolio drawdown limit is optional; absence of parameter means only per-strategy limits apply.
- Existing single-strategy result format reused for per-strategy outputs.
- Performance targets assume current data ingestion architecture.

## Clarifications

### Session 2025-11-03

- Q: Global abort criteria beyond drawdown? → A: Global abort only on configured portfolio drawdown breach or unrecoverable system error.

All prior clarification markers (FR-013, FR-014, FR-015) previously resolved with net exposure aggregation, user-specified weighting (equal-weight fallback), and layered global drawdown risk limit.

### Additional Clarifications (2025-11-03 Extension)

- Weight validation: Provided weights must match number of selected strategies and sum to 100%; otherwise the system applies an equal-weight fallback and records a warning (FR-014, FR-022).
- Correlation metrics deferred: Field `correlation_status` set to 'deferred' until future phase adds correlation matrix computation (FR-022).
- Structured metrics emission: A single JSON line logged on completion plus persisted aggregated artifact must contain all fields defined in FR-022; volatility_annualized may be placeholder (stub) initially.
- Negative global abort scenario: Breach of a single per-strategy risk limit MUST NOT trigger global abort; only global drawdown or unrecoverable system error qualifies (FR-021).
- Manifest linkage: Aggregated artifact must surface `manifest_hash_ref` identical to RunManifest reference for determinism audits (FR-023).

---

### Traceability

| Requirement   | User Story Link |
| ------------- | --------------- |
| FR-001–FR-007 | Story 1         |
| FR-008–FR-011 | Story 2         |
| FR-012–FR-020 | Story 1 & 3     |

---

### Risks

- Performance degradation with many strategies.
- Potential misconfiguration of user-specified weights (mitigate with validation and default fallback).
- Complexity of layered risk controls (ensure clear halt sequencing and manifest logging).
- Structured metrics instrumentation drift (mitigate via schema test & logging verification).
- Missing manifest hash reference could reduce reproducibility transparency (mitigate with explicit test).

### Out of Scope

- Live trading orchestration.
- Cross-strategy adaptive allocation recalibration mid-run.
- Machine learning ensemble logic.
- Real-time correlation/diversification analytics (deferred placeholder only).

## Aggregated Portfolio Metrics (Conceptual)

The aggregated portfolio metrics artifact expresses a combined view of strategy performance, exposure, weighting applied, risk events, and reproducibility linkage. Exact field names, data types, and logging format are implementation details handled in design documents and tests—not mandated by this specification. Correlation analytics are explicitly deferred and replaced with a placeholder indicator.

Volatility and certain portfolio-level statistics may begin as simplified placeholders, with enhancement planned in later phases.

## Non-Functional Requirements (Conceptual)

1. Performance: Aggregated portfolio metrics become available promptly after strategies finish (baseline target captured in planning docs).
2. Scalability: Adding strategies increases runtime within an acceptable proportional range (defined in design; informs capacity expectations).
3. Reliability: Multi-strategy runs demonstrate high completion rates excluding intentional risk-based halts.
4. Determinism: Re-running the same set of strategies on the same data yields consistent outputs supporting audit and comparison.
5. Resource Awareness: Memory impact growth is monitored to inform future optimization decisions.
6. Transparency: Risk events and weighting decisions are clearly represented for user interpretation.
