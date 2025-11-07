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
* Multi-symbol batch ingestion (explicitly out of current scope)

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
