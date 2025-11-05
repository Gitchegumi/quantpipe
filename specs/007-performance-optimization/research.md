# Research Decisions: Performance Optimization

**Date**: 2025-11-05  
**Branch**: 007-performance-optimization  
**Spec**: ./spec.md  

## Decision Log Format

Each item includes Decision / Rationale / Alternatives Considered.

## 1. Numba Adoption Scope

- **Decision**: Make `numba` an optional acceleration dependency (not mandatory).
- **Rationale**: Preliminary synthetic benchmark (prior art) shows ~30–70× speedup for tight loops; however constitution emphasizes minimal dependency footprint. Optional approach avoids blocking environments lacking numba while still enabling large gains.
- **Alternatives**: (a) Mandatory numba (higher friction); (b) Pure numpy only (insufficient for inner trade scan); (c) Cython build (higher maintenance).

## 2. Parquet/Arrow Integration Timing

- **Decision**: Defer Parquet to Phase 2 behind `--use-parquet` flag when `pyarrow` present.
- **Rationale**: Focus immediate gains on simulation bottleneck; CSV ingestion currently ~10 min acceptable for first target. Introducing new IO dependency adds complexity without addressing largest hotspot first.
- **Alternatives**: (a) Immediate mandatory Parquet (risk: dependency + migration overhead); (b) Polars adoption (larger dependency change); (c) Remain CSV-only indefinitely (limits scaling >10M rows).

## 3. Data Fraction & Portion Semantics

- **Decision**: Support `--data-frac <0-1>` selecting leading chronological slice. Omit "portion index" concept for now; earlier spec line with portion flag treated as editorial artifact.
- **Rationale**: Simplicity; portion indexing adds complexity to benchmarks and reproducibility without compelling need.
- **Alternatives**: (a) Portion indexing (support nth segment); (b) Random sampling (impacts determinism); (c) Stratified period selection (future enhancement).

## 4. Indicator Cache Granularity

- **Decision**: Cache per (indicator_type, period) arrays once per dataset slice; store in dict keyed by tuple; lazy compute on first request.
- **Rationale**: Avoid upfront compute cost if strategy doesn’t need all periods; memory controlled.
- **Alternatives**: (a) Eager full precompute (potential waste); (b) On-demand recompute (redundant CPU time); (c) External persistent cache (added IO complexity).

## 5. Batch Simulation Approach

- **Decision**: Implement vectorized/JIT batch scanning; future event-driven sweep behind feature flag `--sim-mode event`.
- **Rationale**: Lower implementation risk; aligns with acceptance criteria; event-driven adds complexity for trailing stops.
- **Alternatives**: (a) Immediate event-driven (higher dev time); (b) Keep per-trade loop (fails performance goal); (c) Distributed microservices (scope creep).

## 6. Deterministic Mode Implementation

- **Decision**: Provide `--deterministic` flag seeding numpy RNG and disabling nondeterministic parallel ordering; enforce single thread for sections where order affects floating rounding.
- **Rationale**: Ensures reproducibility of benchmarks.
- **Alternatives**: (a) Always deterministic (reduces perf); (b) No deterministic option (harder validation); (c) Hash-based trade ordering (unnecessary now).

## 7. Benchmark Artifact Format

- **Decision**: JSON file `benchmark_<timestamp>.json` plus optional CSV summary appended to `results/benchmarks/summary.csv`.
- **Rationale**: JSON structured for machine parsing; CSV enables quick human diff.
- **Alternatives**: (a) Only CSV (lose nested phase detail); (b) Only JSON (less convenient diff); (c) Database storage (overkill).

## 8. Memory Footprint Measurement

- **Decision**: Use `tracemalloc` sample + RSS capture (psutil if available; optional) fallback to Python-only metrics.
- **Rationale**: Provides approximate peak; avoids mandatory new dependency (psutil optional).
- **Alternatives**: (a) Mandatory psutil (dependency overhead); (b) No measurement (violates success criteria); (c) External profiler integration (scope increase).

## 9. Logging Throttling Strategy

- **Decision**: Log progress every N trades (default 250) and at phase boundaries; suppress per-trade debug by default.
- **Rationale**: Reduces IO overhead while keeping user informed.
- **Alternatives**: (a) Rich live table (heavier refresh cost); (b) Silent mode only (poor UX); (c) Adaptive logging based on elapsed time (future improvement).

## 10. Parallel Data Sharing Model

- **Decision**: Use read-only numpy arrays passed to worker processes via shared memory (Python multiprocessing shared_memory) when fraction slice size > threshold; else copy small arrays.
- **Rationale**: Minimizes memory overhead for large datasets; complexity gated by size check.
- **Alternatives**: (a) Always copy (high memory); (b) Plasma store (external dependency); (c) Threading (GIL limits speedup).

## Resolved NEEDS CLARIFICATION Summary

- Numba optional
- Parquet deferred

All clarification items resolved; update plan gate may remove conditional status.

## Next Steps

Proceed Phase 1 artifact creation per plan.
