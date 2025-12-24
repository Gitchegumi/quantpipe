# Research: Fix Backtest Return Calculations

**Date**: 2025-12-23
**Feature**: 020-fix-backtest-returns

## Problem Statement

Individual and isolated multi-symbol backtests show overly optimistic returns (8+R) when the strategy is configured for 2R take-profit targets. Portfolio mode (fix completed) correctly honors the 2R constraint.

## Root Cause Analysis

### Code Path Comparison

**Portfolio Mode (WORKING)**:

- Uses: `PortfolioSimulator._simulate_symbol_vectorized()` → `simulate_trades_batch()`
- Location: `src/backtest/portfolio/portfolio_simulator.py:246-381`
- Exit Price Logic:

  ```python
  sl_pct = risk_dist / sig_entry
  tp_pct = (risk_dist * self.target_r_mult) / sig_entry  # Uses strategy parameter
  ```

- Each signal's TP is calculated individually using `self.target_r_mult` (2.0)
- Stop/target prices passed per-trade to `simulate_trades_batch()`

**Individual/Isolated Mode (BROKEN)**:

- Uses: `BacktestOrchestrator.run_backtest()` → Two possible paths:
  1. Old path: `_simulate_batch()` → `simulate_trades_batch()`
  2. New path: `_run_vectorized_backtest()` → `BatchSimulation.simulate()`

### Bug #1: `BacktestOrchestrator._simulate_batch()` (Old Path)

**Location**: `src/backtest/orchestrator.py:130-256`

**Issue**: Lines 211-215 use the **FIRST trade's TP percentage** as the default for ALL subsequent trades:

```python
results = simulate_trades_batch(
    entries=entries,
    price_data=price_data,
    stop_loss_pct=entries[0]["stop_loss_pct"],  # ❌ WRONG: Uses first trade's SL%
    take_profit_pct=entries[0]["take_profit_pct"],  # ❌ WRONG: Uses first trade's TP%
)
```

While line 186 calculates per-trade TP%:

```python
take_profit_pct = (risk_distance * 2.0) / entry_price  # 2R target
```

The`simulate_trades_batch()` function (lines 100-103 in `trade_sim_batch.py`) DOES support per-trade SL/TP:

```python
sl_pct = entry.get("stop_loss_pct", stop_loss_pct)
tp_pct = entry.get("take_profit_pct", take_profit_pct)
```

BUT the orchestrator is passing GLOBAL defaults instead of relying on per-trade values in the entry dicts.

**Impact**: If the first signal has high volatility/wide stops (e.g., 5% SL → 10% TP for 2R), but subsequent trades have tighter stops (e.g., 1% SL → 2% TP), those trades will still use the 10% TP, resulting in:

- R-multiple = 10% / 1% = **10R** instead of expected **2R**

### Bug #2: Hardcoded 2.0 R-Multiple

**Location**: `src/backtest/orchestrator.py:186`

```python
take_profit_pct = (risk_distance * 2.0) / entry_price  # 2R target
```

The value `2.0` is **hardcoded** instead of using the strategy's `target_r_mult` parameter. This violates FR-005 (all exit logic must come from strategy).

### Vectorized Path Analysis

The newer `_run_vectorized_backtest()` path uses:

- `BatchScan._scan_signals()` → gets `stop_prices` and `target_prices` from `strategy.scan_vectorized()`
- `BatchSimulation.simulate()` → uses these arrays directly

**Status**: This path appears correct based on grep results showing `target_prices` arrays being passed through from strategy to simulation. However, needs verification.

## Decision: Fix Approach

### Option A: Fix Old Path (`_simulate_batch`)

**Changes**:

1. Remove global SL/TP parameters from `simulate_trades_batch()` call
2. Ensure per-trade `stop_loss_pct` and `take_profit_pct` are in entry dicts
3. Replace hardcoded `2.0` with strategy's `target_r_mult`

**Pros**: Minimal changes, fixes immediate bug
**Cons**: Old path may be deprecated (vectorized path is preferred)

### Option B: Deprecate Old Path, Fix Vectorized Path

**Changes**:

1. Remove `_simulate_batch()` entirely
2. Ensure all `run_backtest()` calls use `_run_vectorized_backtest()`
3. Verify vectorized path honors strategy `stop_prices` and `target_prices`

**Pros**: Simplifies codebase, removes redundant code
**Cons**: Higher risk if vectorized path has undiscovered bugs

### Option C (RECOMMENDED): Fix Both Paths for Safety

**Changes**:

1. Fix old path as described in Option A
2. Audit vectorized path to confirm correctness
3. Add integration tests comparing old vs. new vs. portfolio modes

**Pros**: Maximum safety, comprehensive fix
**Cons**: More work upfront

## Rationale for Option C

Given that:

- Portfolio mode works correctly
- User reported 8+R bug exists (evidence of real-world failure)
- Multiple code paths exist (old batch, new vectorized)
- Constitution Principle III requires comprehensive testing

We should fix all paths and verify equivalence to ensure no regression.

## Verification Strategy

1. **Code Inspection**: Confirm stop_prices/target_prices flow from strategy → simulation without modification
2. **Unit Tests**: Mock strategy with known 2R targets, verify simulation results ≤ 2.2R
3. **Integration Tests**: Run same strategy/data in individual, isolated, portfolio modes → compare R-multiple distributions
4. **Regression Tests**: Verify existing tests still pass

## Technologies Confirmed

- **Language**: Python 3.11+
- **Primary Framework**: Polars (vectorized data), NumPy (array operations)
- **Simulation**: `BatchSimulation`, `PortfolioSimulator`, `simulate_trades_batch`
- **Testing**: pytest (confirmed via grep showing `tests/` directory structure)
- **Key Files**:
  - `src/backtest/orchestrator.py` (old path)
  - `src/backtest/batch_simulation.py` (new path)
  - `src/backtest/portfolio/portfolio_simulator.py` (working reference)
  - `src/backtest/trade_sim_batch.py` (shared simulation engine)
  - `src/cli/run_backtest.py` (orchestration entry point)

## Next Steps

1. Create `plan.md` with detailed file-by-file changes
2. Create `data-model.md` (if needed - likely minimal for bug fix)
3. Create `quickstart.md` with before/after examples
4. Update agent context files with findings
