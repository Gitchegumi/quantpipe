# Architectural Refactor: Strategy-Driven Indicators

## Problem Statement

The current codebase has hardcoded indicator fields in the Candle model (`ema20`, `ema50`, `atr`, `rsi`, `stoch_rsi`). This violates the Strategy-First architecture principle because:

1. **Indicators are coupled to the data model** - any strategy needing different indicators must modify the core Candle class
2. **Parameters are ignored** - strategy parameters like `ema_fast` and `ema_slow` don't actually control which indicators are computed
3. **Backtest orchestration hardcodes indicator selection** - should query the strategy instead
4. **Not extensible** - adding new strategies with different indicators requires model changes

## Solution Architecture

### 1. Flexible Candle Model (✅ DONE)

Changed Candle from hardcoded fields to flexible indicators dict:

```python
@dataclass(frozen=True)
class Candle:
    timestamp_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    indicators: dict[str, float] = field(default_factory=dict)
    is_gap: bool = False
    
    # Backward compatibility properties
    @property
    def ema20(self) -> float | None:
        return self.indicators.get("ema20")
```

### 2. Strategy Interface (✅ DONE)

Created `Strategy` protocol requiring strategies to declare their indicator requirements:

```python
class Strategy(Protocol):
    @property
    def metadata(self) -> StrategyMetadata:
        """Returns metadata including required_indicators list."""
    
    def generate_signals(self, candles: list, parameters: dict) -> list:
        """Generate signals from candles with indicators populated."""
```

### 3. Concrete Strategy Implementation (✅ DONE)

Implemented `TrendPullbackStrategy` that declares its indicators:

```python
@property
def metadata(self) -> StrategyMetadata:
    return StrategyMetadata(
        name="trend-pullback",
        version="1.0.0",
        required_indicators=["ema20", "ema50", "atr14", "stoch_rsi"],
        tags=["trend-following", "pullback", "momentum"],
    )
```

### 4. Backtest Orchestration (✅ DONE)

Updated `run_backtest.py` to query strategy for indicators:

```python
strategy = TREND_PULLBACK_STRATEGY
required_indicators = strategy.metadata.required_indicators

enrichment_result = enrich(
    core_ref=ingestion_result,
    indicators=required_indicators,
    strict=True,
)
```

## Remaining Work

### High Priority

1. **Update all Candle construction sites** - ~50+ locations across tests and prod code
   - Tests: `tests/unit/test_reversal_patterns.py`, etc.
   - Legacy ingestion: `partition_loader.py`, `independent_runner.py`, `run_long_backtest.py`

2. **Remove old `ingest_candles()` references** - 3 files still importing it
   - `src/io/partition_loader.py`
   - `src/backtest/portfolio/independent_runner.py`
   - `src/cli/run_long_backtest.py`

3. **Update fixtures** - Test fixtures creating Candle objects

### Low Priority

1. **Consider dynamic indicator registration** - Allow strategies to register custom indicators at runtime
2. **Parameter-driven indicator periods** - Map `ema_fast=10` to dynamically register `ema10` indicator
3. **Multi-strategy indicator deduplication** - When running multiple strategies, compute union of indicators once

## Migration Strategy

### Option A: Big Bang (Risky)

Update all files at once. High risk of breaking everything.

### Option B: Incremental with Deprecation (Recommended)

1. Keep backward compatibility properties on Candle (✅ done)
2. Update new code to use `indicators` dict
3. Gradually migrate tests and legacy code
4. Add deprecation warnings to property access
5. Remove properties in future version

## Testing Checklist

- [ ] Unit tests pass with new Candle model
- [ ] Integration tests pass
- [ ] Backtest CLI works end-to-end
- [ ] Legacy ingestion paths still work
- [ ] Indicator enrichment flow validated
- [ ] Strategy metadata correctly declares indicators

## Files Modified

- ✅ `src/models/core.py` - Flexible Candle model
- ✅ `src/strategy/base.py` - Strategy protocol
- ✅ `src/strategy/trend_pullback/strategy.py` - Concrete strategy
- ✅ `src/cli/run_backtest.py` - Strategy-driven orchestration
- ⚠️ `src/io/partition_loader.py` - Still uses ingest_candles
- ⚠️ `src/backtest/portfolio/independent_runner.py` - Still uses ingest_candles
- ⚠️ `src/cli/run_long_backtest.py` - Still uses ingest_candles
- ⚠️ `tests/**/*.py` - Many tests use old Candle constructor

## Decision Points

**Q: Should we update all files now or incrementally?**
A: INCREMENTAL - The backward compatibility properties allow existing code to continue working while we migrate gradually.

**Q: What about the old ingest_candles function?**
A: DEPRECATE - Mark as deprecated, update callers to use new two-stage pipeline (ingest_ohlcv_data + enrich).

**Q: How do we handle dynamic indicator periods (ema_fast parameter)?**
A: FUTURE WORK - For now, strategies must request specific indicator names ("ema20"). Future enhancement: dynamic registration based on parameters.
