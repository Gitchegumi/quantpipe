# Baseline Test Failures Report

**Date**: 2025-10-29  
**Feature Branch**: `002-directional-backtesting`  
**Python Version**: 3.10.16  
**Pytest Version**: 7.4.4  

---

## Executive Summary

Before implementing directional backtesting feature (LONG/SHORT/BOTH modes), baseline test suite was executed to verify existing codebase health. **This report documents pre-existing test failures and errors that are NOT caused by the new feature implementation.**

**Results**: 186 tests total

- ✅ **110 passed** (59.1%)
- ❌ **72 failed** (38.7%)
- ⚠️ **3 errors** (1.6%)
- ⏭️ **1 skipped** (0.5%)

**Status**: Failures are existing technical debt. New feature implementation will proceed with awareness of these issues but will NOT address them (out of scope).

---

## Failure Categories

### 1. Model Schema Mismatches (Most Common)

**Pattern**: Tests use outdated model field names that don't match current `core.py` schema.

#### Candle Model Issues (16 failures + 3 errors)

- **Error**: `Candle.__init__() got an unexpected keyword argument 'pair'`
- **Current Schema**: `Candle` does not have a `pair` field (see `src/models/core.py:18-66`)
- **Affected Tests**:
  - `tests/unit/test_reversal_patterns.py` (13 failures)
  - `tests/performance/test_long_signal_perf.py` (3 errors, 1 failure)

#### TradeExecution Model Issues (11 failures)

- **Errors**:
  - `TradeExecution.__init__() got an unexpected keyword argument 'fill_entry_price'`
  - `TradeExecution.__init__() got an unexpected keyword argument 'entry_timestamp'` (should be `open_timestamp`)
- **Affected Tests**:
  - `tests/unit/test_metrics_zero.py` (7 failures)
  - `tests/integration/test_significance.py` (3 failures)
  - `tests/performance/test_memory_usage.py` (3 failures)
  - `tests/performance/test_throughput.py` (2 failures)

### 2. Risk Manager API Signature Changes (24 failures)

**Pattern**: Test functions use old parameter names that don't match current implementation.

- `calculate_position_size()` expects different parameters than `stop_distance_pips`
- `calculate_atr_stop()` expects different parameters than `atr`
- `calculate_take_profit()` expects different parameters than `r_multiple`
- `validate_risk_limits()` parameter `current_drawdown_r` should be `current_drawdown_pct`

**Affected**: All 24 tests in `tests/unit/test_risk_manager_rounding.py`

### 3. CSV Data Parsing Issues (8 failures)

**Error**: `ValueError: time data "timestamp_utc open" doesn't match format "%Y.%m.%d %H:%M"`

**Root Cause**: CSV header row is being parsed as data in `preprocess_metatrader_csv()` (see `src/cli/run_long_backtest.py:46`)

**Affected**: All 8 tests in `tests/integration/test_us1_long_signal.py::TestUS1LongSignalIntegration`

### 4. Indicator Calculation Discrepancies (5 failures)

**Pattern**: EMA calculations don't match expected test values; validation error messages have different wording than test regex patterns.

- `test_ema_basic_calculation`: Got `11.25`, expected `11.0`
- `test_ema_period_equals_length`: Got `22.5`, expected `20.0`
- `test_ema_empty_array`: Raises `ValueError` (correct) but test expects different exception handling
- `test_atr_mismatched_lengths`: Error message mismatch
- `test_nan_values`, `test_inf_values`, `test_invalid_period`: Regex patterns don't match actual error messages

### 5. Manifest Handling Errors (3 failures)

- `test_manifest_checksum_mismatch`, `test_manifest_successful_load`: `Path.write_text()` got unexpected keyword argument `mode` (Python 3.10 compatibility issue)
- `test_manifest_date_range_inverted`: Missing required fields `start_date`, `end_date`

### 6. Metrics Field Name Mismatch (1 failure)

- `test_zero_trades`: `MetricsSummary` object has no attribute `expectancy_r` (should be `expectancy`)

### 7. Statistical Test Non-Determinism (1 failure)

- `test_permutation_test_expectancy_positive_edge`: Assertion `p_value < 0.05` failed (got `0.509`)
  - **Note**: Statistical tests can be non-deterministic; may be false positive

### 8. Reproducibility Hash Non-Determinism (1 failure)

- `test_multiple_finalizations`: Hash values don't match between runs
  - **Likely Cause**: `datetime.utcnow()` called multiple times (see deprecation warnings)

### 9. Function Signature Change (1 failure)

- `test_signal_generation_throughput_estimate`: `classify_trend()` got unexpected keyword argument `lookback_candles`

---

## Warnings Summary

### Deprecation Warnings (26 occurrences)

- `datetime.datetime.utcnow()` is deprecated (Python 3.12+)
  - **Action Required**: Replace with `datetime.now(datetime.UTC)` before upgrading Python

### Unknown Pytest Markers (4 occurrences)

- `@pytest.mark.slow` not registered in `pytest.ini` or `pyproject.toml`
  - **Location**: `tests/performance/test_memory_usage.py`, `tests/performance/test_throughput.py`

### Runtime Warnings (11 occurrences)

- `RuntimeWarning: divide by zero encountered in divide` (RSI calculations)
- `RuntimeWarning: overflow encountered in divide`
- `RuntimeWarning: invalid value encountered in divide`
  - **Location**: `src/indicators/basic.py:187`

---

## Impact on Feature Implementation

### ✅ Safe to Proceed

- **Zero failures in new feature areas**: Models (DirectionMode, ConflictEvent, DirectionalMetrics), orchestrator, formatters
- **All failures are pre-existing**: None caused by directional backtesting specification or planning
- **Passing tests indicate**: Core data ingestion (186 tests collected), short signal generation (4/4 passed in `test_us2_short_signal.py`), zero-trades handling (9/9 passed), manifest validation (7/13 passed)

### ⚠️ Recommendations

1. **Create separate technical debt tickets** for each failure category (do NOT address during this feature)
2. **Prioritize schema migration**: Update all tests to match `core.py` current field names
3. **Fix CSV parsing regression**: Header row handling in `preprocess_metatrader_csv()`
4. **Register pytest markers**: Add `slow` marker to `pyproject.toml`
5. **Migrate datetime calls**: Replace `utcnow()` before Python 3.12 upgrade

---

## Next Steps

1. ✅ **Proceed with Phase 1 code review tasks** (T005-T007)
2. ✅ **Begin Phase 2 implementation** (foundational models, orchestrator, formatters)
3. 📋 **Track technical debt separately** (not blocking for this feature)
4. 🧪 **Ensure new tests use current model schemas** (avoid repeating existing errors)

---

## Test Command

```bash
poetry run pytest -v --tb=short
```

**Execution Time**: 26.93 seconds  
**Command Exit Code**: 1 (expected due to failures)
