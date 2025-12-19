# Research: Multi-Symbol Concurrent Backtest

**Feature**: 013-multi-symbol-backtest
**Date**: 2025-12-18

## Decision 1: Multi-Symbol Execution Path

**Decision**: Wire CLI to use existing `IndependentRunner` pattern for multi-symbol runs, enhanced with vectorized Polars path and concurrent PnL aggregation.

**Rationale**:

- `IndependentRunner` already implements per-symbol isolation with result aggregation
- Existing infrastructure handles failures gracefully (skip failed, continue others)
- CLI currently bypasses this by only using `args.pair[0]` at line 631

**Alternatives Considered**:

- Sequential loop in CLI main() - rejected: duplicates IndependentRunner logic
- Parallel multi-process execution - deferred: adds complexity, not required by spec

---

## Decision 2: Path Construction for Multi-Symbol

**Decision**: Extend current path construction logic (lines 393-436) to iterate over all pairs in `args.pair`, constructing paths for each.

**Rationale**:

- Path pattern already works: `price_data/processed/<pair>/<dataset>/<pair>_<dataset>.parquet`
- Parquet-first with CSV fallback already implemented
- Just needs to loop instead of `args.pair[0]`

**Alternatives Considered**:

- Single combined data file - rejected: not how data is organized
- Manifest-based loading - deferred: separate spec 006 concern

---

## Decision 3: Concurrent PnL Computation

**Decision**: Aggregate PnL by summing per-symbol R-multiples after individual backtests complete. Use fixed $2,500 starting balance with equal allocation.

**Rationale**:

- R-multiple approach is already used throughout codebase
- Equal allocation = $1,250 per symbol for 2 symbols, etc.
- Per-symbol isolation maintained per existing `IndependentRunner` pattern

**Alternatives Considered**:

- Time-synchronized concurrent simulation - rejected: complex, not required for independent mode
- Risk-parity allocation - deferred: future spec enhancement

---

## Decision 4: Vectorized Path Integration

**Decision**: Update `IndependentRunner` to use Polars vectorized path instead of legacy `ingest_candles`.

**Rationale**:

- Current `IndependentRunner._run_symbol_backtest` uses `ingest_candles` (legacy)
- CLI uses `ingest_ohlcv_data` with `return_polars=True`
- Need consistency for performance and Parquet support

**Alternatives Considered**:

- Keep legacy path for multi-symbol - rejected: inconsistent, slower

---

## Decision 5: Account Balance Default

**Decision**: Add `DEFAULT_ACCOUNT_BALANCE = 2500.0` constant, use for multi-symbol PnL computation.

**Rationale**:

- User explicitly requested $2,500 default
- Future work will add `--account-balance` CLI flag
- Constant makes future parameterization easy

**Alternatives Considered**:

- No default (require explicit) - rejected: user wants default for now
