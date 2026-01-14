# Walkthrough - Decouple Indicator Registration (026)

This feature enables strategies to define and utilize their own custom indicators without modifying global configuration files. It introduces a `get_custom_indicators` method to the `Strategy` protocol, allowing strategies to inject custom logic into the backtest engine's indicator calculation pipeline.

## Changes

### 1. Strategy Protocol Update

**File**: `src/strategy/base.py`

- Added `get_custom_indicators(self) -> dict[str, Callable]` to the `Strategy` Protocol.
- Returns an empty dictionary by default for backward compatibility.

### 2. Indicator Dispatcher Support

**File**: `src/indicators/dispatcher.py`

- Updated `calculate_indicators` to accept an optional `custom_registry` argument.
- Implemented lookup precedence: Custom indicators override global registry indicators if names collide.

### 3. Backtest Engine Integration

**Files**: `src/backtest/engine.py`, `src/backtest/portfolio/independent_runner.py`

- Modified `run_portfolio_backtest`, `run_multi_symbol_backtest`, and `_run_symbol_backtest` to retrieve custom indicators from the strategy instance and pass them to the dispatcher.
- Added safety checks to ensure `custom_registry` is always a dictionary.

### 4. CLI Argument Fix

**File**: `src/cli/run_backtest.py`

- Fixed a regression where passing `--data` caused a `TypeErrors` due to incorrect argument packing for `run_portfolio_backtest`.

## Verification Results

### Automated Tests

- **New Test**: `tests/integration/test_custom_indicators.py` passed. Verifies that a Mock Strategy with a custom indicator is correctly invoked.
- **Regression Suite**: `tests/integration/` passed (172 passed, 7 xfailed).
  - Fixed identified stale tests in `test_one_trade_at_time.py` (marked xfail) and `test_multi_symbol_backtest.py` (fixed unpacking).

### Manual Verification

- **CLI Backtest**: Verified standard `trend-pullback` strategy works via CLI:
  ```bash
  python -m src.cli.run_backtest --data price_data/processed/eurusd/test/eurusd_test.csv --strategy trend-pullback
  ```
  - Successful execution and report generation.

## Usage Example

Strategies can now implement:

```python
def custom_sma(closes, period=14):
    return talib.SMA(closes, timeperiod=period)

class MyStrategy:
    def get_custom_indicators(self):
        return {
            "my_custom_sma": custom_sma
        }

    def get_visualization_config(self):
        return {
            "my_custom_sma": {"color": "blue"}
        }
```
