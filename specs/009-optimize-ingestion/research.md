# Research: Optimize & Decouple Ingestion Process (Spec 009)

## Overview

This document captures resolutions of all technical questions, provides rationale for chosen approaches, and lists alternatives considered for the ingestion refactor and indicator decoupling.

## Decisions & Rationale

### D1: Columnar Backend Fallback

* **Decision**: Use pandas with Arrow dtype backend when available; fallback silently to standard pandas dtypes with a single warning + performance metrics logged.
* **Rationale**: Maintains portability (CI/Linux without Arrow compiled extras) while still enabling speedups locally. Early failure would block contributors.
* **Alternatives Considered**:
  * Mandatory Arrow (Rejected: reduces portability, increases setup friction)
  * Abstraction layer switching DataFrame implementations (Rejected: increases complexity prematurely)

### D2: Indicator Registry Model

* **Decision**: Implement a pluggable registry with explicit `register_indicator(name, func, metadata)` API.
* **Rationale**: Clean separation, easy unit testing, and avoids implicit filesystem scanning/security concerns.
* **Alternatives Considered**:
  * Static hard-coded list (Rejected: inflexible, editing core file for each indicator)
  * Dynamic plugin auto-discovery (Rejected: added complexity, potential security vetting required)

### D3: Performance Targets

* **Decision**: Baseline ≤120s (hard requirement) and stretch ≤90s (tracked post baseline); optional future GPU path ≤75s.
* **Rationale**: Staged optimization prevents scope creep while stimulating future performance improvement.
* **Alternatives Considered**:
  * Single aggressive ≤60s target (Rejected: risk of premature micro-optimization)
  * No stretch target (Rejected: leaves future optimization unstructured)

### D4: Duplicate Timestamp Handling

* **Decision**: Retain first occurrence; discard subsequent duplicates; log count + sample of duplicates.
* **Rationale**: Determinism and minimal memory overhead; preserves earliest price action.
* **Alternatives Considered**: Aggregation (OHLC combine), last occurrence retention (less intuitive for forward gap fill alignment).

### D5: Gap Fill Strategy

* **Decision**: Vectorized reindex over full expected time range; forward-fill close → replicate to open/high/low; volume=0; `is_gap=True`.
* **Rationale**: Fast, transparent, reproducible; preserves price continuity without artificial volatility.
* **Alternatives Considered**: Interpolation (rejected: would fabricate intra-gap movement), leaving NaNs (rejected: complicates downstream indicator pipelines).

### D6: Output Modes

* **Decision**: Columnar DataFrame fast path plus optional iterator using `itertuples(name=None)`; Candle object creation lazily.
* **Rationale**: Enables high-performance simulation while supporting legacy consumers.
* **Alternatives Considered**: Only DataFrame (breaks legacy), only objects (slow).

### D7: Memory Optimization

* **Decision**: Optional downcast to float32 via `downcast=True` parameter; default keeps float64.
* **Rationale**: Avoids precision surprises unless explicitly requested; reduces memory ~50% for numeric columns.
* **Alternatives Considered**: Always downcast (risk for precision-sensitive indicators), no downcast option (misses memory win).

### D8: Indicator Enrichment Contract

* **Decision**: Single function `enrich_indicators(df, indicators: list[str], **params)` returning new DataFrame with added columns; registry provides mapping name→callable.
* **Rationale**: Simple, explicit contract; easy mocking; deterministic column naming (`{name}_{period}` convention if period parameter exists).
* **Alternatives Considered**: Class-based indicator objects (more boilerplate), decorator-driven auto-registration (less explicit).

### D9: Immutability Enforcement

* **Decision**: Enrichment returns copy (or view with new columns) leaving original core DataFrame checksum unchanged; tests compare hash of core columns.
* **Rationale**: Prevents accidental mutation affecting strategy comparisons.
* **Alternatives Considered**: In-place augmentation (risk of hidden coupling), deep copy always (higher memory cost).

### D10: Progress Reporting

* **Decision**: Stage-level progress tasks (Read, Gap Fill, Finalize) using rich; ≤5 updates.
* **Rationale**: Clear UX; minimal overhead; aligns with constitution monitoring principle.
* **Alternatives Considered**: Row-wise (excessive overhead), silent (poor user feedback).

## Unresolved / Deferred Items

* GPU acceleration pathway design (deferred until baseline and stretch targets validated)
* Multi-symbol batch ingestion (explicitly out of current scope; design sketch below)

### Multi-Symbol Extension Design (T075, FR-022)

**Status**: Future enhancement (out of spec 009 scope)

**Motivation**: Current ingestion processes one symbol at a time. Multi-symbol backtesting (spec 008) orchestrates multiple single-symbol ingestion calls, which could benefit from batch processing to amortize I/O and progress overhead.

**Proposed API Extension**:

```python
def ingest_multi_symbol(
    symbol_paths: dict[str, Path],  # symbol_name -> CSV path
    cadence: str = "1T",
    fill_gaps: bool = True,
    mode: OutputMode = "columnar",
    parallel: bool = False,  # CPU parallelism via multiprocessing
) -> dict[str, pd.DataFrame]:
    """Ingest multiple symbols in batch.
    
    Args:
        symbol_paths: Mapping of symbol names to CSV file paths
        cadence: Expected time interval (e.g., "1T" for 1 minute)
        fill_gaps: Whether to synthesize missing candles
        mode: Output mode (columnar or iterator)
        parallel: Enable parallel processing across symbols
    
    Returns:
        Dictionary mapping symbol names to ingested DataFrames
        
    Performance Target: 
        - 3 symbols × 6.9M rows each in ≤180s (≤60s per symbol avg)
        - Memory: Peak ≤ 2× single-symbol baseline
        
    Design Considerations:
        - Independent processing per symbol (no cross-symbol dependencies)
        - Shared progress bar with per-symbol stages
        - Error isolation: one symbol failure doesn't stop others
        - Aggregated metrics summary (total rows, throughput, failures)
    """
    pass
```

**Implementation Notes**:

1. **Progress Reporting**: Single progress bar with composite stages:
   * `[EURUSD] Reading...` → `[GBPUSD] Reading...` → etc.
   * Aggregate: "Ingesting 3 symbols • 20.7M rows total"

2. **Memory Management**: Process symbols sequentially by default (memory-safe); `parallel=True` opts into higher memory for speed

3. **Error Handling**: Collect failures in result dict with exception details; return successfully processed symbols

4. **Metrics Aggregation**: Single summary with per-symbol breakdown:

   ```json
   {
     "total_symbols": 3,
     "successful": 2,
     "failed": 1,
     "total_rows": 13800000,
     "total_runtime_seconds": 167.3,
     "aggregate_throughput_rows_per_sec": 82500,
     "per_symbol": {
       "EURUSD": {"rows": 6900000, "runtime": 49.8, "status": "ok"},
       "GBPUSD": {"rows": 6900000, "runtime": 51.2, "status": "ok"},
       "USDJPY": {"rows": 0, "runtime": 0.5, "status": "error", "error": "MissingColumnsError: ..."}
     }
   }
   ```

5. **Compatibility**: Extend, don't replace `ingest_candles()`. Single-symbol ingestion remains primary API.

**Alternatives Considered**:

* **Parallel by default**: Rejected (memory pressure, unpredictable peak usage)
* **Single DataFrame output**: Rejected (symbols need separate time indices)
* **Streaming generator**: Deferred (adds API complexity for marginal benefit)

**Success Criteria Extension** (if implemented in future spec):

* **MSC-001**: 3-symbol batch ≤180s (≤60s per symbol average)
* **MSC-002**: Memory peak ≤ 2× single-symbol baseline
* **MSC-003**: Progress updates ≤ 5 × N_symbols stages
* **MSC-004**: Error isolation: failures don't prevent other symbols
* **MSC-005**: Metrics include per-symbol breakdown + aggregate

**Implementation Effort**: Estimated 8-13 tasks (similar to Phase 3 scope)

**References**: Spec 008 (multi-symbol backtesting) demonstrates demand pattern; performance optimization in spec 007 provides parallel processing patterns.

## Validation Strategy

1. Performance Harness: run ingestion 3x, compute mean + variance; assert mean ≤120s and variance ≤10%.
2. Stretch Tracking: after baseline pass, enable optimizer flag set and re-run; record improvements aiming ≤90s.
3. Functional: gap count equals expected missing intervals; duplicates removed count logged.
4. Registry: unknown indicator raises validation error, zero side-effects.
5. Immutability: hash(original core cols) == hash(post-enrichment core cols).
6. Optional downcast memory check via RSS sampling.

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Fallback path slower than expected | Miss performance target | Early benchmarking; adjust data types |
| Registry misuse (duplicate names) | Silent overwrite | Enforce uniqueness, raise exception |
| Downcast precision loss | Indicator accuracy degradation | Default off; doc warnings |
| Large time range expansion | Memory spike during reindex | Stream timeframe or chunk ingestion (future) |

## Alternatives Summary Table

| Decision | Alternatives | Reason Rejected |
|----------|-------------|-----------------|
| Arrow optional | Mandatory Arrow | Setup friction, portability |
| Pluggable registry | Static list | Inflexible growth |
| Gap forward-fill | Interpolation | Fabricated movement |
| Iterator option | Objects only | Performance loss |
| Optional downcast | Always downcast | Precision risk |

## Final State

All clarifications resolved; baseline ready for Phase 1 design artifacts.
