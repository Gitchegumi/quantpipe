# Research: Multi-Strategy Support

**Date**: 2025-11-03  
**Branch**: 006-multi-strategy  
**Spec**: ./spec.md

## Decisions & Rationale

### 1. Monitoring / Structured Metrics

- **Decision**: Add aggregated structured metrics fields: `strategies_count`, `runtime_seconds`, `aggregate_volatility`, `drawdown_pct`, `net_exposure_by_instrument`, `weights_applied`, `global_abort_triggered` (boolean), `risk_breaches` (list), `deterministic_run_id`.
- **Rationale**: Enables reproducibility, performance tracking, and alignment with monitoring principle without heavy external tooling.
- **Alternatives Considered**:
  - Full observability stack (Prometheus/OpenTelemetry): Overkill for offline batch runs
  - Minimal PnL-only metrics: Insufficient for portfolio insight

### 2. Reliability Target

- **Decision**: Batch run reliability target: ≥99% successful completion across 100 consecutive multi-strategy runs (excluding intentional aborts due to configured drawdown).
- **Rationale**: Ensures orchestration robustness while acknowledging controlled risk-triggered halts.
- **Alternatives Considered**:
  - 95% (too low, hides intermittent orchestration issues)
  - 99.9% (premature strictness without production scale)

### 3. Correlation Monitoring Deferral

- **Decision**: Defer correlation computation to future phase; record placeholder in RunManifest with `correlation_status: deferred`.
- **Rationale**: Initial focus is enabling multi-strategy execution and aggregation; correlation adds computational overhead and requires cross-strategy returns time series alignment.
- **Alternatives Considered**:
  - Implement now (risks schedule slippage)
  - Omit entirely (loses future risk management expansion path)

### 4. Global Abort Criteria

- **Decision**: Limit to global drawdown breach or unrecoverable system error.
- **Rationale**: Prevents premature termination and preserves per-strategy resilience testing.
- **Alternatives Considered**:
  - Include single-strategy fatal error (reduces resilience observation)
  - Add volatility spike abort (adds complexity w/o immediate benefit)

### 5. Weighting Fallback Logic

- **Decision**: Validate provided weights sum (≈1.0 tolerance 1e-6); if absent or invalid → equal-weight assignment. Log fallback decision.
- **Rationale**: Ensures deterministic aggregation and avoids silent misallocation.
- **Alternatives Considered**:
  - Reject run on invalid weights (hurts usability)
  - Normalize arbitrary set silently (reduces transparency)

### 6. Determinism Mechanism

- **Decision**: Use seeded random (if any stochastic elements later) + ordered strategy execution + manifest hash; store `deterministic_run_id = sha256(manifest + seed)`.
- **Rationale**: Guarantees reproducibility claim in success criteria.
- **Alternatives Considered**:
  - Omit explicit hash (less traceability)

## Resolved NEEDS CLARIFICATION

- Monitoring metrics detail
- Reliability target
- Correlation deferral rationale
- Global abort criteria specifics

### Structured Metrics Schema (Finalized)

| Field | Type | Description |
| ----- | ---- | ----------- |
| strategies_count | int | Number of strategies executed in the run |
| instruments_count | int | Distinct instruments across all strategies |
| runtime_seconds | float | Wall-clock runtime from first strategy start to aggregation completion |
| aggregate_pnl | float | Weighted portfolio PnL (unit: strategy-defined base currency) |
| max_drawdown_pct | float | Maximum portfolio-level drawdown percentage |
| volatility_annualized | float | Annualized portfolio return volatility (stub initial) |
| net_exposure_by_instrument | dict[str, float] | Net (long-short) exposure per instrument post-aggregation |
| weights_applied | list[float] | Final normalized weights used for aggregation |
| global_drawdown_limit | float | Configured global drawdown threshold (if provided) |
| global_abort_triggered | bool | True if run terminated due to global drawdown or unrecoverable error |
| risk_breaches | list[str] | Strategy identifiers that breached local risk limits |
| deterministic_run_id | str | Stable run identifier (hash) for reproducibility |
| manifest_hash_ref | str | Reference hash tying aggregated output to RunManifest |
| correlation_status | str | 'deferred' placeholder until correlation implemented |

Logging: one structured JSON line at aggregation completion + persisted JSON artifact including these fields.

## Non-Functional Targets

- Aggregation metrics generation ≤5s after last strategy
- Reliability ≥99% successful multi-strategy runs (excluding configured risk aborts)
- Memory growth ≤10% per additional strategy (informational target; not gating)

## Implementation Notes

- Structured metrics emitted via logging and written into aggregated JSON.
- Memory sampling: lightweight peak RSS captured via optional psutil presence; if unavailable, fallback to Python `resource` (Unix) or omit metric on Windows gracefully.
- RunManifest extended with: `strategies`, `weights`, `global_drawdown_limit`, `correlation_status`, `deterministic_run_id`.
- Aggregation module contract: inputs (list[StrategyResult], weights, global limits), outputs (PortfolioAggregate, manifest updates).

## Future Considerations

- Correlation matrix + diversification metrics (Phase N)
- Optional volatility-based dynamic weighting
- Cross-strategy risk rebalancing triggers

## References

- Project Constitution (Principles I, II, IV, X)
- Existing single-strategy backtest orchestration modules for extension pattern
