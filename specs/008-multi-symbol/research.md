# Phase 0 Research: Multi-Symbol Support

Date: 2025-11-06
Branch: 008-multi-symbol
Spec Reference: specs/008-multi-symbol/spec.md (FR-001..FR-023, SC-001..SC-014)

## Decisions & Rationale

### 1. numba Adoption Strategy

- **Decision**: Defer mandatory numba; implement optional acceleration hooks (feature flag `ENABLE_NUMBA` environment var or CLI `--jit`) with graceful fallback to pure numpy/pandas.
- **Rationale**: Keeps dependency surface minimal (Constitution Principle IX) and avoids complexity until correlation/allocation bottlenecks profiled.
- **Alternatives**: Immediate hard dependency (risk: environment friction), Cython modules (higher maintenance), pure Python only (potential performance ceiling). Optional approach balances flexibility and simplicity.

### 2. Memory Target Thresholds

- **Decision**: Establish baseline memory footprint for single-symbol run; set multi-symbol target <= (1.0 + 0.15 \* (n-1)) × baseline for n symbols (approx linear growth with modest overhead). Document measurement method using `tracemalloc` peak.
- **Rationale**: Provides concrete performance guardrail; scalable expectation while allowing correlation matrix overhead.
- **Alternatives**: Fixed absolute MB cap (less adaptive), no target (risk of silent bloat), aggressive per-symbol budget (premature optimization).

### 3. Parallelization Approach (Independent Mode)

- **Decision**: Phase 1 sequential loop; Phase 2 evaluate multiprocessing using `ProcessPoolExecutor` only if measured wall-clock speedup >30% for ≥4 symbols and memory duplication acceptable. Avoid threads due to GIL and CPU-bound simulation.
- **Rationale**: Minimizes complexity early; data ingestion already heavy—profiling first prevents over-engineering.
- **Alternatives**: Immediate multiprocessing (risk of debugging overhead), async I/O (inapplicable), threading (limited benefit).

### 4. Resume/Restart Behavior

- **Decision**: Explicitly OUT-OF-SCOPE for initial release. Document that interrupted runs must be restarted; no partial state store.
- **Rationale**: Complexity (checkpointing signals/executions) unnecessary until first stable portfolio release.
- **Alternatives**: Implement incremental checkpoints (adds serialization design), WAL-style logging (overhead), no stance (unclear expectations).

### 5. Failure Isolation (Runtime) in Portfolio Mode

- **Decision**: If a symbol hard-fails mid-run (data corruption, unrecoverable error), mark symbol inactive; exclude from further correlation computations and allocation; continue portfolio with remaining symbols while logging event and adjusting diversification ratio.
- **Rationale**: Preserves continuity; avoids invalid correlations; deterministic removal logged.
- **Alternatives**: Abort entire run (less resilient), attempt auto-repair (complex), continue including stale data (invalid metrics).

### 6. AllocationEngine Interface

- **Decision**: Interface inputs: `symbols: list[str]`, `volatility: dict[str,float]`, `correlation_matrix: dict[tuple[str,str], float]`, `base_weights: dict[str,float] | None`, `capital: float`. Output: `allocations: dict[str,float]` (capital per symbol). Rounding: allocate using float math then round to 2 decimal places for reporting; enforce sum == capital (adjust largest remainder).
- **Rationale**: Clear separation of risk logic; extendable for risk-parity variant.
- **Alternatives**: Inline allocation in orchestrator (tight coupling), streaming adjustments (premature), matrix-based solver library (adds dependency).

### 7. Snapshot Log Format

- **Decision**: JSON Lines (`.jsonl`) with each line: `{ "t": ISO8601, "positions": {sym: size}, "unrealized": {sym: pnl_r}, "portfolio_pnl": float, "exposure": float, "diversification_ratio": float, "corr_window": int }`.
- **Rationale**: Machine-parsable, append-friendly, easy ingestion into analysis tools.
- **Alternatives**: Plain text (harder to parse), single monolithic JSON (memory spike), CSV (nested structures awkward).

### 8. Correlation Threshold Configuration

- **Decision**: Single float `correlation_threshold` (default 0.8) with optional override map: `{ "EURUSD:GBPUSD": 0.75 }`. Normalized pair key ordering (lexicographic) for stable lookup.
- **Rationale**: Simple default; extensible for specific pair tuning.
- **Alternatives**: Full matrix config (verbose), dynamic adaptive threshold (complex), no overrides (less flexible).

### 9. Symbol Selection Filters/Tags

- **Decision**: Defer advanced tagging; scope limited to explicit symbol list passed via CLI. Add placeholder for future filter flags.
- **Rationale**: Avoid speculative complexity; user can enumerate symbols directly.
- **Alternatives**: Implement volatility class or liquidity filters now (premature without dataset annotations).

## Out-of-Scope (Explicit)

- Checkpoint/restart mid-run state.
- Dynamic rebalancing during run (weight updates mid-stream).
- Live data feed integration.
- Advanced tagging/filter taxonomy.
- Parallel execution in initial version.

## Risk Mitigations

- Missing dataset or symbol failure → abort (portfolio) or isolate (independent) per spec; runtime failure isolation rule implemented per Decision 5.
- Correlation instability early window handled by provisional logic (spec FR-010).
- Logging overhead constrained (<10% target) validated with benchmark harness.

## Open Deferred Items (Post-Phase Targets)

- Implement optional numba path once profiling report shows >15% CPU in correlation/allocation loops.
- Introduce risk-parity allocation variant.
- Portfolio-level drawdown kill-switch (extension of Risk Principle II).

## Constitution Compliance Summary (Post-Research)

| Principle          | Status | Updated Notes                                                                  |
| ------------------ | ------ | ------------------------------------------------------------------------------ |
| II Risk Mgmt       | PASS   | Runtime failure isolation & allocation interface defined.                      |
| III Backtesting    | PASS   | Correlation + cost modeling; walk-forward remains future enhancement (logged). |
| IV Monitoring      | PASS   | Snapshot JSONL schema decided; trade logging specified.                        |
| IX Dependency Mgmt | PASS   | numba optional (not core).                                                     |

All NEEDS CLARIFICATION resolved; proceed to Phase 1 design artifacts.
