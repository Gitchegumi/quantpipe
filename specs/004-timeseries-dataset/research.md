# Phase 0 Research: Time Series Dataset Preparation

**Date**: 2025-10-30
**Branch**: 004-timeseries-dataset

## Decisions Summary

### Dataset Integrity Handling

- **Decision**: Report-only gaps/overlaps; do not alter prices or timestamps.
- **Rationale**: Preserves raw fidelity critical for backtest reproducibility; avoids introducing synthetic bias.
- **Alternatives Considered**:
  - Forward-fill short gaps: rejected (may distort true price path)
  - Linear interpolation: rejected (creates artificial intermediate states)
  - Uniform resampling: rejected (complexity, potential drift)

### Split Strategy

- **Decision**: Deterministic chronological 80/20 (floor for test size, remainder validation).
- **Rationale**: Reflects production-like forward evaluation; avoids data leakage from future periods.
- **Alternatives**:
  - Random split: rejected (breaks temporal dependence)
  - Rolling window cross-validation: deferred (future enhancement)

### Minimum Data Threshold

- **Decision**: 500-row minimum to create split.
- **Rationale**: Ensures validation partition has statistically meaningful sample (>100 rows typical) for metrics.
- **Alternatives**:
  - Any size allowed: rejected (unstable validation metrics)
  - Higher threshold (1000): rejected (unnecessarily excludes smaller but still usable symbol histories)

### Time Zone Normalization

- **Decision**: Normalize timestamps to UTC.
- **Rationale**: Removes ambiguity across data sources; simplifies comparison.
- **Alternatives**:
  - Keep original zones: rejected (complex multi-zone analysis)
  - Convert to exchange-local: deferred (not needed for current backtest scope)

### Metadata Scope

- **Decision**: Include row counts, time span, gap/overlap counts, schema version (implicit), partition boundaries.
- **Rationale**: Supports audit, reproducibility, and downstream analytics.
- **Alternatives**:
  - Minimal counts only: rejected (insufficient diagnostic power)

### Performance Target

- **Decision**: Build ≤ 2 minutes for ~1M total rows.
- **Rationale**: Interactive usability threshold; aligns with existing environment capabilities.
- **Alternatives**:
  - Stricter target (≤1 min): deferred (optimize later if needed)

### Logging Approach

- **Decision**: Structured logger with lazy formatting; summary table at end.
- **Rationale**: Aligns with constitution; aids CI parsing.
- **Alternatives**:
  - Ad-hoc prints: rejected (inconsistent, harder to test)

### Backtest Integration Mode

- **Decision**: Backtest loads test partition for model setup (if needed) and validation partition strictly for evaluation metrics.
- **Rationale**: Emulates real-world scenario (train-then-evaluate) though current strategies may be rule-based.
- **Alternatives**:
  - Single combined dataset: rejected (no holdout evaluation)

### File Output Format

- **Decision**: CSV for partitions, JSON for per-symbol metadata and consolidated summary.
- **Rationale**: Human-readable; integrates with existing pipeline; avoids new dependencies.
- **Alternatives**:
  - Parquet: deferred (consider if performance becomes issue)

## Open Items (Deferred for Future Iterations)

- Rolling window or expanding evaluation schemes.
- Parquet/feather adoption for speed.
- Advanced quality repair (filling, anomaly detection).
- Multi-symbol temporal alignment for portfolio strategies.

## Research Completion

All clarifications resolved; no remaining NEEDS CLARIFICATION markers. Proceed to Phase 1 design.
