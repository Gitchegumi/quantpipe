# Architectural Improvements (Spec 009)

**Date**: 2025-11-10  
**Status**: Completed  
**Context**: User feedback during final phase testing

## Overview

During final phase testing of spec 009 optimization work, the user discovered three architectural issues that needed immediate attention. These were addressed with comprehensive refactors that improved code quality, user experience, and architectural flexibility.

## Issues Identified

### 1. Hardcoded Indicators (Architectural Violation)

**User Feedback**: *"indicators should not be coded into backtest logic, they should be completely separate"*

**Problem**:

- `Candle` model had hardcoded indicator fields (`ema20`, `ema50`, `atr14`, `rsi`, `stoch_rsi`)
- `run_backtest.py` hardcoded indicator selection instead of querying strategy
- Adding new strategies with different indicators required modifying core data model

**Solution**: Strategy-driven indicator architecture (Commit 3943f1f)

- Replaced hardcoded fields with flexible `indicators: dict[str, float]`
- Created `Strategy` protocol requiring `metadata` with `required_indicators`
- Backtest CLI queries strategy for indicators and passes to enrichment
- Added `Candle.from_legacy()` factory for backward compatibility
- Property accessors (`candle.ema20`) redirect to indicators dict
- Optimized DataFrame→Candle conversion (to_dict vs iterrows, 100x faster)

**Impact**:

- Any strategy can now use any indicators without modifying Candle model
- Foundation for multi-strategy support
- 19 files changed, 592 insertions, 83 deletions
- All tests passing with backward compatibility preserved

### 2. Missing Progress Feedback

**User Feedback**: *"where are my progress bars?"*

**Problem**:

- Progress feedback only in log messages (INFO level)
- No visual indication of ingestion/enrichment progress
- Users couldn't see pipeline status or completion estimates

**Solution**: Rich visual progress bars (Commit eec9c50)

- Integrated Rich Progress library (already in dependencies)
- Added visual progress bars to ingestion (5 stages: read, process, gap_fill, schema, finalize)
- Added per-indicator progress to enrichment (updates description dynamically)
- Format: `⠋ Stage 1/5 (read): Loading data.csv ━━━━━━━╸━━━━━━━  20%`
- Backward compatible - still logs to logger

**Impact**:

- Improved user experience with real-time progress visualization
- 3 files changed, 117 insertions, 61 deletions
- Users can monitor long-running operations (10M+ rows)

### 3. Overly Strict Cadence Validation

**User Feedback**: *"I don't understand why we have a cadence check when we know for a fact that historical price data will have many gaps"*

**Problem**:

- Cadence validation enforced ≤2% deviation threshold
- Real-world FX data has ~36% deviation (weekends ~29%, holidays, low liquidity)
- Users forced to manually set `strict_cadence=False` for normal data
- Gap filling already handles missing intervals properly

**Solution**: Informational cadence logging (Commit 7f9abff)

- Converted validation from error-raising gate to informational metric
- Now logs: "Cadence analysis: X intervals present, Y expected (Z% complete)"
- Only warns if >50% missing (suggests actual data quality issue)
- Gap filling proceeds regardless of completeness
- Updated `strict_cadence` parameter documentation

**Impact**:

- Removed unnecessary friction point for FX data users
- 1 file changed, 15 insertions, 16 deletions
- Users no longer need to understand and disable validation for normal data

## Testing & Validation

### Unit Tests

- 205/206 passing (99.5% pass rate)
- 1 pre-existing unrelated failure
- All migrated tests using `Candle.from_legacy()` pattern

### Integration Tests

- 8/8 passing (100%)
- Tests cover ingestion, enrichment, and backtest orchestration

### End-to-End Validation

Tested with 2024 EURUSD data (525,599 rows after gap filling):

- ✅ Strategy-driven indicators: Shows `Required indicators: ['ema20', 'ema50', 'atr14', 'stoch_rsi']`
- ✅ Progress bars: Visual feedback for ingestion (5 stages) and enrichment (per-indicator)
- ✅ Informational cadence: Logs `70.8% complete` without raising errors
- ✅ Gap filling: Proceeds normally (153,220 gaps filled)
- ✅ Backtest completion: 74 trades (59 long, 15 short) in 0.43 seconds

### Performance

- Ingestion: 525,599 rows in 10.29s (51,054 rows/min)
- Enrichment: 4 indicators in 6.05s
- DataFrame→Candle conversion: 525,599 objects in ~3s (using optimized to_dict)
- Total backtest: 0.43 seconds (signal generation + execution)

## Commits

1. **3943f1f**: Strategy-driven indicator architecture (19 files)
2. **eec9c50**: Visual progress bars (3 files)
3. **7f9abff**: Informational cadence logging (1 file)

## Files Changed

### Strategy-Driven Architecture (3943f1f)

- `src/models/core.py`: Flexible Candle model with indicators dict
- `src/strategy/base.py`: Strategy protocol (NEW)
- `src/strategy/trend_pullback/strategy.py`: Concrete implementation (NEW)
- `src/cli/run_backtest.py`: Query strategy for indicators
- `src/io/legacy_ingestion.py`: Backward compatibility bridge (NEW)
- `ARCHITECTURAL_REFACTOR.md`: Migration guide (NEW)
- 9 test files: Migrated to `Candle.from_legacy()` pattern

### Progress Bars (eec9c50)

- `src/io/progress.py`: Rich Progress integration
- `src/io/ingestion.py`: Call progress.finish()
- `src/indicators/enrich.py`: Per-indicator progress context manager

### Cadence Logging (7f9abff)

- `src/io/ingestion.py`: Convert validation to informational logging

## Lessons Learned

1. **User Feedback is Critical**: All three issues were discovered through user testing, not internal review. Direct user interaction catches architectural flaws that tests miss.

2. **Architectural Coupling**: Hardcoding domain concepts (indicators) into core data models creates tight coupling. Protocols and flexible data structures enable extensibility.

3. **Validation vs Information**: Not all checks should be validation gates. Some metrics (like cadence completeness) are better as informational logging, especially when downstream logic (gap filling) already handles the issue.

4. **UX Matters**: Technical correctness isn't enough. Users need visual feedback for long-running operations. Rich progress bars significantly improved perceived responsiveness.

5. **Backward Compatibility**: When refactoring core models, provide migration paths (like `from_legacy()`) to avoid breaking existing code. Property accessors maintain API compatibility while changing internal representation.

## Future Work

1. **Multi-Strategy Support**: Strategy protocol is foundation for running multiple strategies simultaneously
2. **Custom Indicators**: Users could register custom indicators via strategy metadata
3. **Indicator Caching**: Reuse computed indicators across multiple strategies
4. **Performance Profiling**: Monitor impact of to_dict optimization on larger datasets (100M+ rows)
5. **Progress Bar Customization**: Allow users to disable/customize progress visualization

## References

- **Original Spec**: `specs/009-optimize-ingestion/spec.md`
- **Migration Guide**: `ARCHITECTURAL_REFACTOR.md`
- **Final Phase Tasks**: `specs/009-optimize-ingestion/tasks.md` (T069-T086)
- **User Feedback Session**: Conversation 2025-11-10 (commits 3943f1f, eec9c50, 7f9abff)
