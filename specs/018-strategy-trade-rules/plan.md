# Implementation Plan: Strategy Trade Rules & Indicator Exposure

**Branch**: `018-strategy-trade-rules` | **Date**: 2025-12-22 | **Spec**: [spec.md](file:///e:/GitHub/trading-strategies/specs/018-strategy-trade-rules/spec.md)
**Input**: Feature specification from `/specs/018-strategy-trade-rules/spec.md`

## Summary

This plan addresses Issue #38 with two key changes:

1. **One Trade at a Time** (Strategy-Controlled): Add `max_concurrent_positions` to `StrategyMetadata`, add `filter_overlapping_signals()` utility, and have the backtest pipeline respect strategy's declared limit
2. **Indicator Exposure**: Update `TrendPullbackStrategy.get_visualization_config()` to include `rsi14` in oscillators

---

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: NumPy (vectorized operations), pytest (testing)
**Storage**: N/A (in-memory arrays)
**Testing**: pytest with existing unit and integration test patterns
**Target Platform**: Linux/Windows (cross-platform)
**Project Type**: Single project (src/tests structure)
**Performance Goals**: No significant slowdown from filtering (O(n) complexity acceptable)
**Constraints**: Must maintain backward compatibility with existing tests

---

## Constitution Check

| Gate                        | Status  | Notes                                         |
| --------------------------- | ------- | --------------------------------------------- |
| Risk Management Integration | ✅ Pass | Position limits enhance risk control          |
| Backtesting & Validation    | ✅ Pass | Adds position-aware filtering to simulation   |
| Code Quality Standards      | ✅ Pass | Will use lazy logging, type hints, docstrings |
| Dependency Management       | ✅ Pass | No new dependencies                           |
| Task Tracking               | ✅ Pass | Will follow tasks.md workflow                 |

---

## Project Structure

### Documentation (this feature)

```text
specs/018-strategy-trade-rules/
├── spec.md              # Feature specification
├── plan.md              # This implementation plan
└── tasks.md             # Task list (via /speckit.tasks)
```

### Source Code (changes)

```text
src/
├── strategy/
│   ├── base.py                   # [MODIFY] Add max_concurrent_positions to StrategyMetadata
│   └── trend_pullback/
│       └── strategy.py           # [MODIFY] Add rsi14 to oscillators
└── backtest/
    └── signal_filter.py          # [NEW] filter_overlapping_signals() utility

tests/
├── unit/
│   ├── test_signal_filtering.py  # [NEW] Unit tests for filtering function
│   ├── test_strategy_metadata.py # [NEW] Tests for max_concurrent_positions
│   └── test_visualization_config.py  # [EXISTING] Verify no regression
└── integration/
    └── test_one_trade_at_time.py # [NEW] Integration test for position gating
```

---

## Proposed Changes

### Component 1: Strategy Metadata Enhancement

#### [MODIFY] [base.py](file:///e:/GitHub/trading-strategies/src/strategy/base.py)

Add `max_concurrent_positions` field to `StrategyMetadata`:

```python
@dataclass(frozen=True)
class StrategyMetadata:
    """Metadata describing a strategy's requirements and characteristics.

    Attributes:
        name: Unique strategy identifier.
        version: Semantic version string.
        required_indicators: List of indicator names this strategy needs.
        tags: Classification tags for filtering/grouping.
        max_concurrent_positions: Maximum simultaneous open positions allowed.
            Default is 1 (one trade at a time). Set to None for unlimited.
    """

    name: str
    version: str
    required_indicators: list[str]
    tags: list[str] = None
    max_concurrent_positions: int | None = 1  # NEW: Default = one at a time
```

**Rationale**: This is strategy-declared behavior. A trend-following strategy may want one position at a time, while a mean-reversion strategy might allow multiple. The backtest pipeline will read this value and apply filtering accordingly.

---

### Component 2: Signal Filtering Utility

#### [NEW] [signal_filter.py](file:///e:/GitHub/trading-strategies/src/backtest/signal_filter.py)

New module with a pure function for filtering overlapping signals:

```python
"""Signal filtering utilities for position management.

Provides functions to filter signals based on strategy constraints
like max concurrent positions.
"""

import numpy as np


def filter_overlapping_signals(
    signal_indices: np.ndarray,
    exit_indices: np.ndarray | None = None,
    max_concurrent: int = 1,
) -> np.ndarray:
    """Filter signals to enforce max concurrent positions.

    Args:
        signal_indices: Sorted array of entry candle indices
        exit_indices: Optional array of known exit indices (same length).
            If None, assumes each trade reserves a window until next signal.
        max_concurrent: Maximum concurrent positions (default: 1)

    Returns:
        Filtered array with signals respecting concurrency limit
    """
```

**Usage in backtest pipeline**: The orchestrator will call this after signal generation, passing the strategy's `max_concurrent_positions` value.

---

### Component 3: Strategy Implementation Update

#### [MODIFY] [strategy.py](file:///e:/GitHub/trading-strategies/src/strategy/trend_pullback/strategy.py)

**Change 1**: Ensure metadata explicitly declares `max_concurrent_positions=1`:

```python
@property
def metadata(self) -> StrategyMetadata:
    return StrategyMetadata(
        name="trend-pullback",
        version="1.0.0",
        required_indicators=["ema20", "ema50", "atr14", "rsi14", "stoch_rsi"],
        tags=["trend-following", "pullback", "momentum"],
        max_concurrent_positions=1,  # One trade at a time
    )
```

**Change 2**: Add `rsi14` to oscillators in `get_visualization_config()`:

```python
oscillators=[
    IndicatorDisplayConfig(name="stoch_rsi", label="Stoch RSI"),
    IndicatorDisplayConfig(name="rsi14", label="RSI 14"),  # ADD
],
```

---

### Component 4: Backtest Pipeline Integration

The backtest orchestrator needs to call the filter after signal generation. This should be added where `scan_vectorized()` results are processed, before `BatchSimulation.simulate()`:

```python
# After signal generation
signal_indices = strategy.scan_vectorized(...)

# Apply strategy's position limit
max_concurrent = strategy.metadata.max_concurrent_positions
if max_concurrent is not None and max_concurrent > 0:
    from src.backtest.signal_filter import filter_overlapping_signals
    signal_indices = filter_overlapping_signals(
        signal_indices,
        max_concurrent=max_concurrent
    )
```

---

## Verification Plan

### Automated Tests

#### Unit Tests (New)

**File**: `tests/unit/test_signal_filtering.py`

| Test                                     | Purpose                                            |
| ---------------------------------------- | -------------------------------------------------- |
| `test_filter_empty_array`                | Empty input returns empty output                   |
| `test_filter_single_signal`              | Single signal passes through unchanged             |
| `test_filter_non_overlapping`            | Widely-spaced signals all pass                     |
| `test_filter_overlapping_removes_second` | Two adjacent signals → first kept, second filtered |
| `test_filter_multiple_overlapping`       | Cluster of 5 signals → only first kept             |
| `test_filter_preserves_sorted_order`     | Output remains sorted ascending                    |

**Run command**:

```bash
poetry run pytest tests/unit/test_signal_filtering.py -v
```

**File**: `tests/unit/test_strategy_metadata.py`

| Test                                   | Purpose                 |
| -------------------------------------- | ----------------------- |
| `test_metadata_default_max_concurrent` | Default is 1            |
| `test_metadata_custom_max_concurrent`  | Can set to other values |
| `test_metadata_unlimited_concurrent`   | None means unlimited    |

**Run command**:

```bash
poetry run pytest tests/unit/test_strategy_metadata.py -v
```

#### Integration Tests (New)

**File**: `tests/integration/test_one_trade_at_time.py`

| Test                                      | Purpose                                      |
| ----------------------------------------- | -------------------------------------------- |
| `test_simulation_respects_one_trade_rule` | Verify at most one position open at any time |
| `test_continuous_trading_after_exit`      | New signal allowed after position exits      |

**Run command**:

```bash
poetry run pytest tests/integration/test_one_trade_at_time.py -v
```

#### Existing Tests (Verification)

| Test File                      | Command                                                        | Purpose                  |
| ------------------------------ | -------------------------------------------------------------- | ------------------------ |
| `test_visualization_config.py` | `poetry run pytest tests/unit/test_visualization_config.py -v` | No regression            |
| Full suite                     | `poetry run pytest tests/ -v --tb=short`                       | Overall regression check |

### Manual Verification

1. **Run backtest with visualization**:

   ```bash
   poetry run python -m src.cli.run_backtest --pair EURUSD --dataset test --visualize
   ```

   - Verify RSI14 appears as an oscillator panel
   - Verify trade count is reasonable (filtered)

---

## Complexity Tracking

No constitution violations. All changes follow established patterns.
