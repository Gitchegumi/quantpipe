# Performance Optimization Guide

## Overview

This document tracks performance improvements for the backtesting engine, focusing on reducing runtime for large datasets (millions of candles) from hours to minutes.

**Goal**: Reduce backtest runtime from ~88 minutes to ≤20 minutes (stretch goal: 10-15 minutes) for 6.9M candles / 17.7k trades.

## Baseline Metrics

Performance baseline captured on 2025-11-05 before optimization (Issue #15):

| Metric | Baseline | Target | Current Status |
|--------|----------|--------|----------------|
| Full run time (6.9M candles, 17.7k trades) | 88 min (5,280s) | ≤20 min | In Progress (Phase 3 MVP) |
| Simulation phase time | 1,200s | ≤360s (≥10× speedup) | Optimized (vectorized) |
| Signal scan time | 3,600s | ≤1,080s | Optimized (progress tracking) |
| Load + slice time (10M rows) | 480s | ≤60s | Pending (Phase 5) |
| Memory peak ratio | 1.4× | ≤1.5× | Within bounds |
| Parallel efficiency (4 workers) | N/A | ≥70% | Pending (Phase 6) |

## Optimization Phases

### Phase 3: User Story US1 (Fast Execution) - MVP

**Status**: In Progress

**Optimizations Implemented**:

1. **Vectorized Batch Trade Simulation** (FR-005, SC-002)
   - Replaced O(trades × bars) iteration with numpy-based exit scanning
   - Target: ≥10× speedup, ≤0.30× baseline simulation time
   - Implementation: `src/backtest/trade_sim_batch.py`

2. **Indicator Caching** (FR-004, SC-004)
   - Lazy-computed cache eliminates redundant indicator calculations
   - Target: ≥80% reduction in repeated compute time
   - Implementation: `src/backtest/indicator_cache.py`

3. **Phase Timing Instrumentation** (FR-012)
   - Tracks ingest, scan, simulate phase durations
   - Progress bars with elapsed/remaining time estimates
   - Implementation: `src/backtest/profiling.py`, integrated in `orchestrator.py`

4. **Fidelity Validation** (FR-006, SC-006)
   - Ensures optimizations preserve result accuracy
   - Tolerances: price ≤1e-6, PnL ≤0.01%, indices exact
   - Implementation: `src/backtest/fidelity.py`

**Test Coverage**:

- Unit tests: `tests/unit/test_indicator_cache.py`, `test_fidelity.py`, `test_profiling.py`
- Performance tests: `tests/performance/test_memory_peak.py`
- Integration tests: Pending

### Phase 4: User Story US2 (Profiling) - Pending

- Profiling flag (--profile) with cProfile integration
- Hotspot extraction (≥10 functions, FR-016)
- Phase timing breakdowns in benchmark artifacts

### Phase 5: User Story US3 (Dataset Fractions) - Pending

- Dataset fraction flag (--data-frac 0.0-1.0)
- Portion selection (first/middle/last, --portion)
- Load + slice timing validation (≤60s for 10M rows)

## Before/After Timing

### Baseline (Pre-Optimization)

```text
Phase          Time (s)   % Total
---------------------------------
Load           480        9%
Scan           3,600      68%
Simulate       1,200      23%
---------------------------------
TOTAL          5,280      100%
```

### Phase 3 MVP (Target)

```text
Phase          Time (s)   % Total   Speedup
--------------------------------------------
Load           480        40%       1.0×  (pending Phase 5)
Scan           360        30%       10.0× (optimized)
Simulate       360        30%       3.3×  (vectorized batch)
--------------------------------------------
TOTAL          1,200      100%      4.4×
```

**Progress**: Simulation optimized with vectorized approach. Full timing validation pending integration tests.

## Usage

### Running Optimized Backtests

```bash
# Standard optimized run
poetry run python -m src.cli.run_backtest \
  --data ./price_data/processed/eurusd/test/eurusd_test.csv \
  --direction BOTH

# With profiling enabled (Phase 4)
poetry run python -m src.cli.run_backtest \
  --data ./price_data/processed/eurusd/test/eurusd_test.csv \
  --direction BOTH \
  --profile \
  --benchmark-out ./results/benchmarks/run_001.json

# Deterministic mode for reproducibility
poetry run python -m src.cli.run_backtest \
  --data ./price_data/processed/eurusd/test/eurusd_test.csv \
  --direction BOTH \
  --deterministic
```

### Interpreting Benchmark Records

Benchmark records are stored in `results/benchmarks/` as JSON files with schema:

```json
{
  "dataset_rows": 6922364,
  "trades_simulated": 17724,
  "phase_times": {
    "scan": 360.5,
    "simulate": 120.3
  },
  "wall_clock_total": 480.8,
  "memory_peak_mb": 2048.0,
  "memory_ratio": 1.42
}
```

## Benchmarks

Benchmark records are stored in `results/benchmarks/` as JSON files.
