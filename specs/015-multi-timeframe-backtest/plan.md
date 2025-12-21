# Implementation Plan: Multi-Timeframe Backtesting

**Branch**: `015-multi-timeframe-backtest` | **Date**: 2025-12-20 | **Spec**: [spec.md](file:///e:/GitHub/trading-strategies/specs/015-multi-timeframe-backtest/spec.md)

## Summary

Enable the backtester to run strategies on timeframes other than 1-minute by implementing OHLCV resampling from 1-minute data. Users can specify timeframe via CLI (`--timeframe 15m`), config file, or Python API. The system correctly aggregates OHLCV data, marks incomplete bars, caches results, and recomputes indicators on resampled data.

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: Polars (for vectorized resampling), existing pandas/numpy
**Storage**: `.time_cache/` directory for resampled Parquet files
**Testing**: pytest (existing test infrastructure in `tests/unit/`, `tests/integration/`)
**Target Platform**: Windows/Linux CLI + Python API
**Performance Goals**: Resampling ≤5s for 6.9M rows; 50%+ speedup for higher TF backtests
**Constraints**: Maintain backward compatibility (default `1m`); no strategy code changes required

## Constitution Check

### _GATE: Pass_

| Principle                      | Status  | Notes                                      |
| ------------------------------ | ------- | ------------------------------------------ |
| I. Strategy-First Architecture | ✅ Pass | New module follows modular design          |
| II. Risk Management            | ✅ Pass | No changes to risk controls                |
| III. Backtesting & Validation  | ✅ Pass | Comprehensive tests planned                |
| V. Data Integrity              | ✅ Pass | `bar_complete` flag preserves transparency |
| VIII. Code Quality             | ✅ Pass | Type hints, docstrings, PEP8 compliance    |
| IX. Dependency Management      | ✅ Pass | No new dependencies                        |
| X. Linting                     | ✅ Pass | Black, Ruff, Pylint compliance             |
| XI. Commit Standards           | ✅ Pass | Semantic commits with task references      |
| XII. Task Tracking             | ✅ Pass | tasks.md will track progress               |

## Project Structure

### Documentation (this feature)

```text
specs/015-multi-timeframe-backtest/
├── spec.md              ✓ Created
├── plan.md              ✓ This file
├── research.md          ✓ Created
├── data-model.md        ✓ Created
├── quickstart.md        ✓ Created
└── tasks.md             → Created by /speckit.tasks
```

### Source Code

```text
src/
├── data_io/
│   ├── timeframe.py         [NEW] Timeframe parsing & validation
│   ├── resample.py          [NEW] OHLCV resampling logic
│   └── resample_cache.py    [NEW] Disk caching for resampled data
├── cli/
│   └── run_backtest.py      [MODIFY] Add --timeframe argument
└── backtest/
    └── orchestrator.py      [MODIFY] Integrate resampling before indicators

tests/
└── unit/
    ├── test_timeframe.py        [NEW] Timeframe parsing tests
    ├── test_resample.py         [NEW] Resampling correctness tests
    └── test_resample_cache.py   [NEW] Cache behavior tests
tests/
└── integration/
    └── test_timeframe_backtest.py  [NEW] End-to-end timeframe tests
```

---

## Proposed Changes

### Data I/O Layer

#### [NEW] [timeframe.py](file:///e:/GitHub/trading-strategies/src/data_io/timeframe.py)

Create timeframe parsing module with:

- `Timeframe` dataclass: `period_minutes`, `original_input`, `is_valid`
- `parse_timeframe(tf_str: str) -> Timeframe`: Parse "15m", "2h", "1d" formats
- `validate_timeframe(tf: Timeframe) -> None`: Raise ValueError if invalid
- Regex validation: `^(\d+)(m|h|d)$`

---

#### [NEW] [resample.py](file:///e:/GitHub/trading-strategies/src/data_io/resample.py)

Create OHLCV resampling module with:

- `resample_ohlcv(df: pl.DataFrame, target_minutes: int) -> pl.DataFrame`
  - Use Polars `group_by_dynamic()` with `every=f"{target_minutes}m"`
  - Aggregate: `open.first()`, `high.max()`, `low.min()`, `close.last()`, `volume.sum()`
  - Compute `bar_complete = count == target_minutes`
- Drop incomplete leading/trailing bars (per spec clarification)
- Return Polars DataFrame with `bar_complete` column added

---

#### [NEW] [resample_cache.py](file:///e:/GitHub/trading-strategies/src/data_io/resample_cache.py)

Create caching module with:

- `get_cache_path(instrument, tf_minutes, start, end, data_hash) -> Path`
  - Returns `.time_cache/{instrument}_{tf}m_{start}_{end}_{hash8}.parquet`
- `load_cached_resample(cache_path) -> pl.DataFrame | None`
  - Returns None if cache miss
- `save_cached_resample(df, cache_path) -> None`
- `resample_with_cache(df, instrument, tf_minutes) -> pl.DataFrame`
  - Wrapper that checks cache first, resamples if miss, saves result

---

### CLI Layer

#### [MODIFY] [run_backtest.py](file:///e:/GitHub/trading-strategies/src/cli/run_backtest.py)

Add timeframe CLI integration:

- Add `--timeframe` argument to argparse (default: `"1m"`)
- Parse and validate timeframe early in `main()`
- Pass timeframe to orchestrator/data pipeline
- Log selected timeframe

---

### Backtest Layer

#### [MODIFY] [orchestrator.py](file:///e:/GitHub/trading-strategies/src/backtest/orchestrator.py)

Integrate resampling into backtest flow:

- Add `timeframe_minutes` parameter to `run_backtest()` and `run_vectorized_backtest()`
- After ingestion, before indicator computation:
  - If `timeframe_minutes > 1`: call `resample_with_cache()`
  - Emit warning if incomplete bars > 10% threshold
- Pass resampled data to indicator dispatcher

---

### Test Layer

#### [NEW] [test_timeframe.py](file:///e:/GitHub/trading-strategies/tests/unit/test_timeframe.py)

Unit tests for timeframe parsing:

- Valid inputs: `"1m"`, `"5m"`, `"15m"`, `"1h"`, `"2h"`, `"4h"`, `"8h"`, `"1d"`
- Arbitrary integers: `"7m"`, `"13m"`, `"90m"`, `"120m"`
- Invalid inputs: `"0m"`, `"-5m"`, `"1.5h"`, `"90s"`, `"abc"`, `""`
- Conversion correctness: `"2h"` → 120 minutes, `"1d"` → 1440 minutes

---

#### [NEW] [test_resample.py](file:///e:/GitHub/trading-strategies/tests/unit/test_resample.py)

Unit tests for resampling correctness:

- Hand-crafted 1-minute slices → verify OHLCV aggregation
- Gap handling: missing minutes → `bar_complete=False`
- Incomplete edge bars: first/last bars dropped
- Property test: `1m → 5m → 15m` equals `1m → 15m` (associativity)
- Empty input handling

---

#### [NEW] [test_resample_cache.py](file:///e:/GitHub/trading-strategies/tests/unit/test_resample_cache.py)

Unit tests for caching:

- Cache hit: second call loads from disk
- Cache miss: first call computes and saves
- Cache key: different timeframes create different cache files
- Cache invalidation: different data hash creates new cache

---

#### [NEW] [test_timeframe_backtest.py](file:///e:/GitHub/trading-strategies/tests/integration/test_timeframe_backtest.py)

Integration tests for end-to-end flow:

- Run backtest at 1m, 5m, 15m, 1h → verify no errors
- Metrics schema unchanged across timeframes
- Higher TF runs faster than 1m (wall-clock time comparison)
- CLI argument parsing works correctly

---

## Verification Plan

### Automated Tests

**Run all new unit tests:**

```bash
poetry run pytest tests/unit/test_timeframe.py -v
poetry run pytest tests/unit/test_resample.py -v
poetry run pytest tests/unit/test_resample_cache.py -v
```

**Run integration tests:**

```bash
poetry run pytest tests/integration/test_timeframe_backtest.py -v
```

**Run full test suite to ensure no regressions:**

```bash
poetry run pytest tests/ -v --ignore=tests/performance
```

**Lint checks:**

```bash
poetry run ruff check src/data_io/timeframe.py src/data_io/resample.py src/data_io/resample_cache.py
poetry run black --check src/data_io/timeframe.py src/data_io/resample.py src/data_io/resample_cache.py
```

### Manual Verification

1. **CLI smoke test** (user can validate):

   ```bash
   python -m src.cli.run_backtest --direction LONG --data price_data/processed/eurusd/test --timeframe 15m
   ```

   - Expected: Backtest completes successfully with 15m bars
   - Output should show timeframe in logging

2. **Cache verification**:

   - Run same command twice
   - Second run should show "Loading from cache" log message
   - Check `.time_cache/` directory contains Parquet file

3. **Invalid timeframe rejection**:

   ```bash
   python -m src.cli.run_backtest --direction LONG --data price_data/processed/eurusd/test --timeframe 90s
   ```

   - Expected: Clear error message about invalid format

---

## Telemetry (FR-014)

Add logging for:

- `INFO: Resampling to {tf}m timeframe ({n} bars → {m} bars)`
- `INFO: Resample cache hit for {instrument}_{tf}m`
- `WARNING: {pct}% of bars are incomplete (threshold: 10%)`
- `INFO: Resample time: {sec:.2f}s`
