# Implementation Plan: Fix Backtest Return Calculations

**Branch**: `020-fix-backtest-returns` | **Date**: 2025-12-23 | **Spec**: [spec.md](file:///E:/GitHub/trading-strategies/specs/020-fix-backtest-returns/spec.md)
**Input**: Individual and isolated backtests show 8+R returns when strategy targets 2R take-profit

## Summary

Fix backtest return calculations to honor strategy-defined take-profit targets. Root cause: `BacktestOrchestrator._simulate_batch()` incorrectly uses the first trade's TP percentage for all subsequent trades, and hardcodes the `2.0` R-multiple instead of using the strategy's `target_r_mult` parameter. Portfolio mode works correctly by calculating per-trade TP% using the strategy's target multiplier.

**Technical Approach**:

1. Fix `_simulate_batch()` to remove global SL/TP defaults, rely on per-trade values in entry dicts
2. Replace hardcoded `2.0` with strategy's `target_r_mult` parameter
3. Audit vectorized backtest path (`_run_vectorized_backtest`) to ensure it correctly uses strategy-provided `stop_prices` and `target_prices`
4. Add integration tests comparing individual, isolated, and portfolio modes for R-multiple equivalence

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Polars (vectorized data), NumPy (array operations), pandas (legacy simulation engine)
**Storage**: Parquet files (OHLCV price data)
**Testing**: pytest (unit/integration/performance tests in `tests/` directory)
**Target Platform**: Linux/Windows (cross-platform CLI)
**Project Type**: Single project (trading backtest engine)
**Performance Goals**: Maintain current vectorized performance (≤20min for 6.9M candles, 17.7k trades)
**Constraints**: No breaking changes to existing API, all tests must pass
**Scale/Scope**: Bug fix (3-4 files modified, 50-100 LOC changed total)

## Constitution Check

**Principle III: Backtesting & Validation** ✅

- Change supports realistic backtest results by honoring strategy TP constraints
- Improves statistical validity by eliminating inflated R-multiples

**Principle X: Code Quality** ✅

- Fixes hardcoded magic numbers (`2.0` → strategy parameter)
- Maintains docstring accuracy (functions already document SL/TP logic)

**No violations identified**. This is a correctness fix aligning code with documented behavior.

## Proposed Changes

### Phase 1: Fix Old Batch Simulation Path

#### [MODIFY] [orchestrator.py](file:///e:/GitHub/trading-strategies/src/backtest/orchestrator.py)

**Function**: `BacktestOrchestrator._simulate_batch()` (lines 130-256)

**Changes**:

1. **Line 186**: Replace hardcoded `2.0` with strategy's `target_r_mult`
   - Add parameter to function signature: `target_r_mult: float = 2.0`
   - Update calculation: `take_profit_pct = (risk_distance * target_r_mult) / entry_price`
2. **Lines 211-215**: Remove global SL/TP parameters from `simulate_trades_batch()` call

   - Before:

     ```python
     results = simulate_trades_batch(
         entries=entries,
         price_data=price_data,
         stop_loss_pct=entries[0]["stop_loss_pct"],  # WRONG
         take_profit_pct=entries[0]["take_profit_pct"],  # WRONG
     )
     ```

   - After:

     ```python
     results = simulate_trades_batch(
         entries=entries,
         price_data=price_data,
         # Removed: SL/TP now come from per-trade entry dicts
     )
     ```

3. **Update call sites**: Ensure all calls to `_simulate_batch()` pass `target_r_mult` from strategy

**Rationale**: `simulate_trades_batch()` already supports per-trade SL/TP via `entry.get("stop_loss_pct", stop_loss_pct)`, but the orchestrator was overriding this with global defaults, causing all trades to use the first trade's percentages.

---

#### [MODIFY] [trade_sim_batch.py](file:///e:/GitHub/trading-strategies/src/backtest/trade_sim_batch.py)

**Function**: `simulate_trades_batch()` (lines 27-188)

**Changes**:

1. **Lines 30-31**: Make SL/TP parameters optional with `None` defaults

   - Before:

     ```python
     def simulate_trades_batch(
         entries: List[Dict[str, Any]],
         price_data: pd.DataFrame,
         stop_loss_pct: float = 0.02,
         take_profit_pct: float = 0.04,
     )
     ```

   - After:

     ```python
     def simulate_trades_batch(
         entries: List[Dict[str, Any]],
         price_data: pd.DataFrame,
         stop_loss_pct: Optional[float] = None,  # Deprecated, use per-trade
         take_profit_pct: Optional[float] = None,  # Deprecated, use per-trade
     )
     ```

2. **Lines 102-103**: Update fallback logic to error if per-trade values missing

   - Before:

     ```python
     sl_pct = entry.get("stop_loss_pct", stop_loss_pct)
     tp_pct = entry.get("take_profit_pct", take_profit_pct)
     ```

   - After:

     ```python
     sl_pct = entry.get("stop_loss_pct")
     tp_pct = entry.get("take_profit_pct")
     if sl_pct is None or tp_pct is None:
         # Fallback to global params if provided (legacy support)
         sl_pct = sl_pct or stop_loss_pct
         tp_pct = tp_pct or take_profit_pct
         if sl_pct is None or tp_pct is None:
             raise ValueError(f"Missing SL/TP for entry at index {entry.get('entry_index')}")
     ```

**Rationale**: Enforce per-trade SL/TP while maintaining backward compatibility for existing code that still passes global defaults.

---

### Phase 2: Audit Vectorized Path

#### [VERIFY] [batch_simulation.py](file:///e:/GitHub/trading-strategies/src/backtest/batch_simulation.py)

**Functions to audit**:

- `BatchSimulation.simulate()` (lines 136-244)
- `_simulate_vectorized()` (lines 355-625)

**Verification**:

1. Confirm `stop_prices` and `target_prices` arrays from `ScanResult` are passed directly to `sim_eval.simulate_trades_vectorized()`
2. Confirm no R-multiple calculations or price modifications occur between strategy output and trade execution
3. Grep for any hardcoded `2.0` or percentage calculations

**Expected finding**: Vectorized path is already correct (passes arrays directly)

---

#### [VERIFY] [orchestrator.py](file:///e:/GitHub/trading-strategies/src/backtest/orchestrator.py)

**Function**: `_run_vectorized_backtest()` (lines 633-866)

**Verification**:

1. Confirm lines 1614-1615 pass `stop_prices` and `target_prices` from `scan_result` directly to `BatchSimulation.simulate()`
2. No intermediate transformations

**Expected finding**: Vectorized path is correct, no changes needed

---

### Phase 3: Update Portfolio Mode for Consistency

#### [VERIFY] [portfolio_simulator.py](file:///e:/GitHub/trading-strategies/src/backtest/portfolio/portfolio_simulator.py)

**Function**: `_simulate_symbol_vectorized()` (lines 246-381)

**Verification**:

- Lines 318-320 calculate TP% using `self.target_r_mult` ✅ CORRECT
- This is the working reference implementation

**No changes needed** - portfolio mode is the gold standard

---

## Verification Plan

### Automated Tests

#### 1. **Unit Test**: Verify `_simulate_batch()` Per-Trade SL/TP

**File**: Create `tests/unit/test_simulate_batch_fix.py`

**Test cases**:

1. `test_simulate_batch_respects_per_trade_sltp()`: Create 3 entries with different SL/TP percentages (2%, 5%, 10%), verify each uses its own values
2. `test_simulate_batch_target_r_mult_from_strategy()`: Mock strategy with `target_r_mult=3.0`, verify trades exit at 3R
3. `test_simulate_batch_no_global_defaults()`: Call `simulate_trades_batch()` with no global SL/TP, verify it uses per-trade values

**Run command**:

```bash
cd e:\GitHub\trading-strategies
poetry run pytest tests/unit/test_simulate_batch_fix.py -v
```

---

#### 2. **Integration Test**: Multi-Mode R-Multiple Equivalence

**File**: Modify `tests/integration/test_multi_symbol_backtest.py`

**New test**: `test_individual_isolated_portfolio_rmult_equivalence()`

- Run same strategy (2R TP) on same data in all three modes
- Verify average R-multiple for winners is within 5% across modes
- Verify no winning trades exceed 2.2R in any mode

**Run command**:

```bash
poetry run pytest tests/integration/test_multi_symbol_backtest.py::test_individual_isolated_portfolio_rmult_equivalence -v
```

---

#### 3. **Regression Test**: Existing Tests Must Pass

**Files to verify**:

- `tests/integration/test_backtest_split_mode.py`
- `tests/integration/test_directional_backtesting.py`
- `tests/integration/test_portfolio_flow.py`
- `tests/unit/test_backtest_orchestrator.py`

**Run command**:

```bash
poetry run pytest tests/ -k "backtest or portfolio or simulation" --tb=short
```

---

### Manual Verification

#### 4. **CLI Test**: Before/After Comparison

**Steps**:

1. Checkout current branch (with bug)
2. Run backtest:

   ```bash
   python -m src.cli.run_backtest --direction BOTH --data price_data/processed/EURUSD_1m.parquet --pairs EURUSD --dataset processed --output results_before.json

   ```

3. Note maximum R-multiple from output
4. Apply fix, run again:

   ```bash
   python -m src.cli.run_backtest --direction BOTH --data price_data/processed/EURUSD_1m.parquet --pairs EURUSD --dataset processed --output results_after.json
   ```

5. Compare: `results_after.json` should show max R ≤ 2.2R

**User confirms**: Maximum R-multiple is now reasonable (≤2.2R vs. previous 8+R)

---

### Success Criteria Verification

| Criterion                                | Test Method                        | Pass Condition                     |
| ---------------------------------------- | ---------------------------------- | ---------------------------------- |
| SC-001: No winning trades exceed 2.2R    | Integration test                   | All winning trades ≤ 2.2R          |
| SC-002: Mode equivalence                 | Integration test                   | ±5% avg R-multiple across modes    |
| SC-003: No calculations in orchestration | Code inspection                    | Grep shows no hardcoded multiples  |
| SC-004: All existing tests pass          | Regression test suite              | 100% pass rate                     |
| SC-005: Statistical equivalence          | Integration test + manual CLI test | Same data/strategy → same avg R±5% |

---

## Project Structure

### Documentation (this feature)

```text
specs/020-fix-backtest-returns/
├── plan.md              # This file
├── research.md          # Root cause analysis (completed)
├── spec.md              # Feature specification (completed)
├── checklists/
│   └── requirements.md  # Quality checklist (completed)
└── (tasks.md will be generated by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── back test/
│   ├── orchestrator.py          # MODIFY: Fix _simulate_batch()
│   ├── trade_sim_batch.py       # MODIFY: Make SL/TP optional
│   ├── batch_simulation.py      # VERIFY: Confirm correctness
│   └── portfolio/
│       └── portfolio_simulator.py  # VERIFY: Reference implementation
├── cli/
│   └── run_backtest.py           # VERIFY: Ensure target_r_mult passed
└── strategy/
    └── trend_pullback/
        └── strategy.py            # VERIFY: Has target_r_mult parameter

tests/
├── unit/
│   ├── test_backtest_orchestrator.py    # Existing (regression)
│   └── test_simulate_batch_fix.py       # NEW: Per-trade SL/TP tests
└── integration/
    ├── test_multi_symbol_backtest.py    # MODIFY: Add equivalence test
    ├── test_portfolio_flow.py           # Existing (regression)
    └── test_directional_backtesting.py  # Existing (regression)
```

**Structure Decision**: Single Python project with `src/` for production code and `tests/` for test suites. This is a targeted bug fix affecting 2 files with modifications and 3 files requiring verification audits.

## Complexity Tracking

**No constitutional violations**. This is a correctness fix, not a new feature or architectural change.
