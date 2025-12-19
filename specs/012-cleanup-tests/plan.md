# Implementation Plan: Clean Up Tests and Fix Integration Tests

**Branch**: `012-cleanup-tests` | **Date**: 2025-12-18 | **Spec**: [spec.md](file:///e:/GitHub/trading-strategies/specs/012-cleanup-tests/spec.md)
**Input**: Feature specification from `/specs/012-cleanup-tests/spec.md`

## Summary

Fix failing integration tests (primarily `test_both_mode_backtest.py`) caused by datetime handling issues in the deprecated `legacy_ingestion` module, then remove or consolidate redundant tests identified in the existing inventory. The approach is to:

1. Fix the 4 failing tests in `test_both_mode_backtest.py` by migrating to the new vectorized ingestion API
2. Remove 6-10 redundant tests documented in the inventory
3. Document all changes with justifications

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: pytest, polars, pandas, numpy
**Storage**: N/A (test cleanup, no data storage changes)
**Testing**: pytest with markers (integration, unit, local_data)
**Target Platform**: Windows/Linux (CI via GitHub Actions)
**Project Type**: Single project with src/ and tests/ separation
**Performance Goals**: Maintain or improve test execution time (~2.5s for integration)
**Constraints**: Test reduction ≤30%; no regression in code coverage
**Scale/Scope**: ~90 tests total, targeting 4 fixes + 6-10 removals

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Principle                          | Status  | Notes                                     |
| ---------------------------------- | ------- | ----------------------------------------- |
| III. Backtesting & Validation      | ✅ PASS | Tests validate backtest behavior          |
| VIII. Code Quality & Documentation | ✅ PASS | Will maintain PEP 257 docstrings          |
| IX. Dependency Management          | ✅ PASS | Using Poetry, no new dependencies         |
| X. Code Quality Automation         | ✅ PASS | Will run ruff, black, pylint              |
| XI. Commit Message Standards       | ✅ PASS | Will use semantic format `test(012): ...` |

## Project Structure

### Documentation (this feature)

```text
specs/012-cleanup-tests/
├── spec.md              ✅ Created
├── plan.md              ✅ This file
├── research.md          ✅ Created
├── checklists/
│   └── requirements.md  ✅ Created
└── tasks.md             ⏳ Phase 2 (/speckit.tasks)
```

### Source Code (repository root)

```text
tests/
├── integration/
│   ├── test_both_mode_backtest.py  # FIX: 4 failing tests
│   ├── test_directional_backtesting.py  # Uses legacy_ingestion
│   ├── test_single_symbol_regression.py
│   ├── test_us2_short_signal.py
│   └── ...
├── unit/
│   ├── test_indicators_basic.py    # REMOVE REDUNDANT: 6 tests
│   └── test_risk_manager_rounding.py  # REMOVE REDUNDANT: 3-4 tests
└── performance/
    ├── test_dry_run_performance.py
    ├── test_memory_usage.py
    └── test_strategy_backtest_performance.py
```

## Proposed Changes

### Phase 1: Fix Failing Integration Tests

#### [MODIFY] [test_both_mode_backtest.py](file:///e:/GitHub/trading-strategies/tests/integration/test_both_mode_backtest.py)

**Problem**: Tests fail with datetime handling errors when passing candles from `legacy_ingestion.ingest_candles()` to the orchestrator's `run_backtest()` method.

**Root Cause**: The `legacy_ingestion` module yields `Candle` objects with pandas Timestamps, but the vectorized orchestrator expects Polars DataFrames or compatible datetime types.

**Solution**: Migrate tests to use the vectorized API pattern (similar to `test_vectorized_direct.py`):

1. Replace `ingest_candles()` with `ingest_ohlcv_data()` + `enrich()`
2. Pass Polars DataFrame directly to orchestrator instead of list of Candle objects
3. Or update the test to use the CLI fixture pattern from other passing tests

---

### Phase 2: Remove Redundant Tests

#### [MODIFY] [test_indicators_basic.py](file:///e:/GitHub/trading-strategies/tests/unit/test_indicators_basic.py)

Remove 6 redundant tests that duplicate coverage from `test_indicators_core.py`:

- Warm-up period tests (covered by T020-T020c)
- Basic EMA/ATR/RSI calculations (covered by core tests)
- Keep edge case tests: empty array, single value, insufficient data

#### [MODIFY] [test_risk_manager_rounding.py](file:///e:/GitHub/trading-strategies/tests/unit/test_risk_manager_rounding.py)

Remove 3-4 redundant position sizing tests:

- `test_position_size_basic_calculation` (duplicate of T023)
- `test_position_size_caps_at_max_position` (duplicate of T024)
- `test_position_size_very_large_stop` (duplicate of T024)
- Keep: ATR stop, take profit, and risk validation tests

---

### Phase 3: Migrate Other Legacy Tests (If Time Permits)

Consider migrating other tests using `legacy_ingestion` to the new API:

| File                                  | Priority | Legacy References    |
| ------------------------------------- | -------- | -------------------- |
| test_directional_backtesting.py       | Medium   | 1 import             |
| test_us2_short_signal.py              | Medium   | 1 import             |
| test_single_symbol_regression.py      | Low      | 1 import             |
| test_flakiness_smoke.py               | Low      | 1 import in function |
| test_dry_run_performance.py           | Low      | 1 import             |
| test_memory_usage.py                  | Low      | 1 import             |
| test_strategy_backtest_performance.py | Low      | 1 import             |

---

### Phase 4: Documentation

#### [NEW] [removal-notes.md](file:///e:/GitHub/trading-strategies/tests/removal-notes.md)

Document all test removals with justifications per FR-005.

## Verification Plan

### Automated Tests

1. **Run all integration tests** (must pass):

   ```bash
   poetry run pytest tests/integration -v --tb=short
   ```

   - Expected: All tests pass (0 failures)

2. **Run unit tests** (must pass after redundant removals):

   ```bash
   poetry run pytest tests/unit -v --tb=short
   ```

   - Expected: All remaining tests pass

3. **Run full test suite** with collection count:

   ```bash
   poetry run pytest --collect-only -q 2>&1 | Select-Object -Last 5
   ```

   - Expected: Total tests reduced by 6-10 (within ≤30% target)

4. **Verify lint compliance**:

   ```bash
   poetry run ruff check tests/
   poetry run black tests/ --check
   ```

   - Expected: No errors

### Manual Verification

1. **Review removal-notes.md** to confirm each removed test has documented justification
2. **Verify coverage** by comparing before/after test counts (should not exceed 30% reduction)

## Complexity Tracking

No constitution violations requiring justification.
