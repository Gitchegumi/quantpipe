# Research: Test Cleanup and Integration Fixes

**Feature**: 012-cleanup-tests
**Date**: 2025-12-18
**Purpose**: Resolve all NEEDS CLARIFICATION items and document technical decisions

## Research Findings

### 1. Root Cause of Failing Tests

**Decision**: Migrate `test_both_mode_backtest.py` from legacy ingestion to vectorized API

**Rationale**:

- The failing tests use `legacy_ingestion.ingest_candles()` which yields `Candle` objects
- The orchestrator's `run_backtest()` now expects Polars DataFrames (after 011-optimize-batch-simulation)
- Datetime handling breaks when pandas Timestamps are converted in the Candle → orchestrator path

**Alternatives considered**:

1. **Fix legacy_ingestion datetime handling** - Rejected: adds complexity to deprecated module
2. **Patch orchestrator to accept Candle lists** - Rejected: violates the vectorized architecture intent
3. **Migrate tests to new API** - Chosen: aligns with project direction, removes deprecated dependency

### 2. Redundant Test Identification

**Decision**: Remove 6-10 tests per existing inventory analysis

**Rationale**:

- Inventory (`_inventory_removed.txt`) was generated 2025-10-30 after Phase 3 tests added
- Analysis confirms overlap between:
  - `test_indicators_basic.py` (6 tests) ↔ `test_indicators_core.py`
  - `test_risk_manager_rounding.py` (3-4 tests) ↔ `test_risk_sizing_*.py`

**Alternatives considered**:

1. **Keep all tests** - Rejected: increases CI time, maintenance burden
2. **Remove more tests (>30%)** - Rejected: may lose edge case coverage
3. **Remove targeted redundant tests** - Chosen: maintains coverage, reduces duplication

### 3. Legacy Ingestion Migration Scope

**Decision**: Focus on `test_both_mode_backtest.py` first, defer others

**Rationale**:

- 8 test files use legacy_ingestion, but only 4 tests are currently failing
- Other tests (test_directional_backtesting.py, etc.) still pass despite deprecated imports
- Migrating all would expand scope beyond issue #29 requirements

**Alternatives considered**:

1. **Migrate all 8 files** - Rejected: scope creep, not required for CI to pass
2. **Remove legacy_ingestion module** - Rejected: may break passing tests unexpectedly
3. **Fix failing tests only** - Chosen: minimal change to restore CI

### 4. Test Consolidation Strategy

**Decision**: Defer consolidation to future issue

**Rationale**:

- Inventory suggests creating `test_indicators_consolidated.py` with parameterized tests
- However, this adds new code rather than just removing redundant tests
- Beyond scope of issue #29 which focuses on cleanup, not refactoring

**Alternatives considered**:

1. **Consolidate now** - Rejected: adds complexity, beyond issue scope
2. **Create follow-up issue for consolidation** - Chosen: clean separation of concerns
3. **Never consolidate** - Rejected: would leave identified improvement undone

## Technical Context Resolved

| Item              | Resolution                                                     |
| ----------------- | -------------------------------------------------------------- |
| Language/Version  | Python 3.11 (from constitution)                                |
| Testing Framework | pytest with markers                                            |
| Ingestion Path    | Use `ingest_ohlcv_data()` + `enrich()`, not `legacy_ingestion` |
| Test Structure    | Maintain existing tests/ hierarchy                             |
| CI Requirement    | All tests must pass with exit code 0                           |

## No NEEDS CLARIFICATION Remaining

All unknowns resolved through codebase analysis.
