# Data Model: Performance Optimization

**Branch**: 007-performance-optimization  
**Date**: 2025-11-05  
**Source Spec**: ./spec.md

## Overview

Defines entities and validation rules supporting optimized backtest orchestration: loading, slicing, caching, simulation, profiling, benchmarking.

## Entities

### BacktestJob

| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| job_id | str | yes | non-empty, unique | UUID or timestamp-based |
| started_at | datetime | yes | timezone-aware | ISO8601 serialization |
| ended_at | datetime | no | >= started_at | Set when complete |
| parameters | dict[str, any] | yes | keys snake_case | Strategy + run flags |
| data_frac | float | yes | 0 < value <= 1 | Fraction of dataset used |
| deterministic | bool | yes | | Seeds RNG if true |
| max_workers | int | yes | >=1 | Capped by logical cores |
| benchmark_path | str | no | writable path | Destination for JSON artifact |

### DatasetSlice

| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| total_rows | int | yes | >0 | Raw dataset row count |
| selected_rows | int | yes | >0 <= total_rows | After fraction slicing |
| first_ts | int | yes | epoch ms | Monotonic increase |
| last_ts | int | yes | epoch ms >= first_ts | |
| columns | list[str] | yes | subset allowed | [timestamp, open, high, low, close, volume] |
| dtypes | dict[str,str] | yes | matches columns | e.g., float32 for prices |
| fraction | float | yes | 0< <=1 | Mirrors BacktestJob.data_frac |

### IndicatorCache

| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| dataset_id | str | yes | non-empty | Reference to underlying slice |
| indicators | dict[tuple(str,int), ndarray] | yes | periods >0 | Key: (type, period) |
| created_at | datetime | yes | | Timestamp of first population |
| lazy_mode | bool | yes | | If true compute on demand |

### TradeEntryRecord

| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| entry_index | int | yes | >=0 < selected_rows | Index into slice |
| side | int | yes | value in {1,-1} | 1 long, -1 short |
| entry_price | float | yes | >0 | float32 |
| sl_price | float | no | >0 | May be NaN if not set |
| tp_price | float | no | >0 | May be NaN if not set |
| trail_mult | float | no | >=0 | 0 disables trailing |
| size | float | yes | >0 | Units or lots |

### TradeSimulationResult

| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| entry_index | int | yes | sync with TradeEntryRecord | |
| exit_index | int | yes | >= entry_index | -1 indicates unresolved (error) |
| exit_price | float | yes | >0 | Price of fill |
| pnl | float | yes | | Float32; tolerance checks vs baseline |
| exit_reason | str | yes | enum {TP, SL, TRAIL, CLOSE} | |
| duration_bars | int | yes | >=1 | exit_index - entry_index |
| trailing_used | bool | yes | | Derived from trail_mult |

### ProfilingReport

| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| job_id | str | yes | matches BacktestJob.job_id | |
| phases | dict[str,float] | yes | keys in {ingest, scan, simulate} | seconds per phase |
| hotspots | list[tuple(str,float)] | yes | length >=1 | function name + percent |
| generated_at | datetime | yes | | |

### BenchmarkRecord

| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| job_id | str | yes | unique | Reference |
| total_time_s | float | yes | >0 | Wall-clock |
| data_load_s | float | yes | >=0 | part of phases |
| simulation_s | float | yes | >=0 | part of phases |
| memory_peak_mb | float | yes | >=0 | RSS or estimate |
| trades_simulated | int | yes | >=0 | |
| speedup_vs_baseline | float | no | >=1 | Baseline stored externally |
| fidelity_pass | bool | yes | | PnL tolerance satisfied |

## Relationships

- BacktestJob 1..1 → DatasetSlice
- BacktestJob 1..1 → BenchmarkRecord
- BacktestJob 1..1 (optional) → ProfilingReport
- BacktestJob 1..N → TradeEntryRecord
- TradeEntryRecord 1..1 → TradeSimulationResult
- DatasetSlice 1..1 → IndicatorCache

## State Transitions

BacktestJob: CREATED → RUNNING → (SIMULATING) → COMPLETE | FAILED

- FAILED set when fidelity check or critical exception aborts run.

TradeSimulationResult: PENDING → EXITED

- Vectorized batch sets EXITED for all trades simultaneously; unresolved trades should trigger error handling.

## Validation Rules Summary

- Fraction must be enforced prior to indicator cache population.
- Memory peak calculation triggered after simulation completion.
- Fidelity pass requires aggregate metrics within tolerance (PnL ≤0.01%, win rate ≤0.1pp).

## Open Questions

None (clarifications resolved in research).

## Notes

Model favors simple numeric types (int64 indices, float32 prices) aligned with performance goals.
