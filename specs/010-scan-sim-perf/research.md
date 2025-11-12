# Research: Scan & Simulation Performance Optimization (Spec 010)

**Date**: 2025-11-11  
**Purpose**: Resolve clarifications and capture architectural performance decisions prior to implementation.

## Decisions Summary

| ID  | Decision                                                                                               | Rationale                                                                    | Alternatives Considered                                                                                | Outcome / Next Step                                           |
| --- | ------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------- |
| D1  | Embed dataset manifest reference in PerformanceReport (path, SHA256, candle_count)                     | Satisfies provenance (Constitution VI) and reproducibility with low overhead | Storing full manifest copy inside report (larger, redundant); no manifest link (violates Constitution) | Add fields to PerformanceReport model & report generator      |
| D2  | Defer numba adoption until profiling shows ≥25% speedup potential                                      | Avoid premature dependency; measure baseline first                           | Immediate numba integration (adds complexity); Cython rewrite (high setup cost)                        | Implement pure NumPy version; create optional experiment task |
| D3  | Use columnar NumPy arrays + int32 indices + preallocation for simulation                               | Minimizes Python object churn; better cache locality                         | Continue per-loop Python objects; Pandas row iteration (slow)                                          | Implement extraction helper `_to_arrays()` early              |
| D4  | Progress emission every ~16,384 items or ≤120s, plus final flush                                       | Coarse updates reduce I/O overhead (<1% time) while giving user visibility   | Per-item updates (too noisy); no progress until end (poor UX)                                          | Implement progress dispatcher with stride & time checks       |
| D5  | Duplicate timestamps: keep first, discard rest; log count + first/last duplicate timestamp             | Deterministic, prevents signal inflation, enables audit                      | Hard fail (blocks runs); merge values (unjustified semantics)                                          | Implement dedupe pass before scan                             |
| D6  | Determinism: capture env metadata (Python version, OS, CPU) + fixed seed for any stochastic components | Reproducible benchmarks & equivalence                                        | Ignore environment (harder to reproduce); random seeds each run                                        | Add metadata capture function in performance module           |
| D7  | Memory tracking via `tracemalloc` or `psutil` (if available fallback) at key checkpoints               | Quantify memory improvements robustly                                        | Manual observation only; OS-level logs                                                                 | Implement lightweight memory sampler API                      |
| D8  | Batch simulation: vectorize stop/take profit evaluation; early exit loops per trade                    | Reduces Python loop overhead; keeps logic correctness                        | Maintain current per-trade iterative loop                                                              | Prototype vectorized path after baseline capture              |
| D9  | Indicator ownership audit test (strategy vs runtime used set)                                          | Guarantees adherence to Strategy-First principle                             | Manual review only                                                                                     | Implement test comparing declared vs used indicator names     |
| D10 | Performance thresholds stored in constants for clarity & future tuning                                 | Centralizes target numbers for tests & reporting                             | Hard-coded scattered literals                                                                          | Create `performance_targets.py` module                        |
| D11 | Mandatory Polars adoption replacing pandas preprocessing                                              | Columnar speed + memory efficiency; unified path                             | Keep pandas only (slower); optional gating (delays benefits)                                          | Implement Polars LazyFrame pipeline immediately               |
| D12 | Parquet conversion of CSV on ingest with compression (zstd)                                           | Faster repeated IO + smaller footprint                                       | Keep CSV only (higher IO); gzip CSV (less efficient random access)                                   | Build conversion + manifest schema fingerprint                |

## Detailed Rationale & Notes

### Dataset Manifest Linkage (D1)

Include: `manifest_path` (relative), `manifest_sha256`, `candle_count` in PerformanceReport. Enables reconstruction of benchmark context.

### numba Deferral Criteria (D2)

Adopt numba only if profiling (wall-clock) shows simulation inner loop >40% of total runtime and numba prototype yields ≥25% improvement. Keep dependency optional.

### Columnar Extraction (D3)

Single pass building arrays with `np.fromiter` or `np.asarray` depending on source container. Ensure dtypes: `float64` for prices & indicators; `int32` for indices when count < 2^31.

### Progress Emission (D4)

Use stride = 2^14 (16384) iterations; maintain `last_time` to ensure update if >120s elapsed. Provide percentage, elapsed, estimated remaining.

### Dedupe Policy (D5)

Pre-scan: build dictionary first-seen index; skip subsequent occurrences; log summary. Do not alter price series ordering, just filter duplicates out of arrays.

### Deterministic Benchmarking (D6)

Capture: Python version, platform, CPU info (if available), start time UTC, commit hash. Provide stable ordering of signals/trades.

### Memory Tracking (D7)

Sample peak after array extraction and after simulation. Use `tracemalloc.start()` plus `get_traced_memory()`; fallback to `psutil.Process().memory_info().rss` if available.

### Batch Simulation (D8)

Precompute arrays for SL/TP percentages; evaluate candidate exit conditions using vectorized comparisons; record earliest condition per trade.

### Indicator Ownership Audit (D9)

Collect indicator names from strategy definition; runtime collects used indicator keys; assert set equality.

### Performance Targets Module (D10)

Provide constants: `SCAN_MAX_SECONDS`, `SIM_MAX_SECONDS`, `MEM_PEAK_REDUCTION_TARGET`, `PROGRESS_MAX_INTERVAL_SECONDS`, `PROGRESS_MAX_PERCENT_DRIFT`, plus Polars thresholds (`POLARS_MIN_SPEEDUP_PCT=20`, `POLARS_MIN_MEM_REDUCTION_PCT=15`).

### Mandatory Polars Adoption (D11)

Adopt Polars immediately for ingestion & preprocessing using LazyFrame. Pandas retained only for legacy verification tests. All performance targets and future optimizations consider Polars baseline.

### Parquet Conversion Strategy (D12)

On initial run: detect CSV raw input, convert to Parquet (compression=zstd, target row group size tuned for memory vs speed, e.g., 128MB). Store schema fingerprint & checksum in manifest. Subsequent runs load Parquet directly, enabling predicate & projection pushdown in Polars.

## Alternatives Rejected Summary

- Per-iteration Python loops for signals (too slow).
- Hard failing on duplicates (reduces usability).
- Immediate numba integration (complexity risk).
- Verbose per-item progress updates (excessive overhead).
- Omitting manifest linkage (violates provenance principle).

## Open Risks & Mitigations

| Risk                             | Impact               | Mitigation                                                         |
| -------------------------------- | -------------------- | ------------------------------------------------------------------ |
| Memory sampling overhead         | Slight slowdown      | Limited checkpoints (2–3); disable in perf-critical loops          |
| Vectorized simulation complexity | Potential logic bug  | Start with equivalence tests vs legacy path; feature flag fallback |
| Optional numba divergence        | Maintenance overhead | Keep isolated module; document activation conditions               |
| Parquet conversion overhead | Initial one-time cost | Cache Parquet; skip if exists & checksum matches CSV manifest |
| Polars learning curve | Slight dev friction | Documentation & quickstart guidance |

## Next Steps

1. Implement baseline benchmark capture.
2. Add PerformanceReport model & manifest linkage.
3. Columnar extraction utilities & dedupe step.
4. Batch signal generation & equivalence tests.
5. Batch simulation prototype & equivalence tests.
6. Progress dispatcher integration.
7. Memory sampling integration.
8. Indicator ownership audit test.
9. Threshold validation tests (scan, simulation).
10. Optional numba experiment task (after baseline metrics recorded).
11. Parquet conversion & Polars verification tests.
12. Update legacy pandas tests or deprecate if redundant.

All clarifications resolved; proceed to Phase 1 design artifacts.
