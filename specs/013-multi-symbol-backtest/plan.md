# Implementation Plan: Multi-Symbol Concurrent Backtest

**Branch**: `013-multi-symbol-backtest` | **Date**: 2025-12-18 | **Spec**: [spec.md](file:///e:/GitHub/trading-strategies/specs/013-multi-symbol-backtest/spec.md)
**Input**: Feature specification from `/specs/013-multi-symbol-backtest/spec.md`

## Summary

Fix multi-symbol pathing in CLI so `--pair EURUSD USDJPY` runs backtests on ALL specified pairs (not just the first), with PnL computed as if both pairs are traded concurrently. Uses $2,500 default account balance with equal allocation across symbols.

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: Polars, Pandas, Rich (progress bars)
**Storage**: Parquet files (`price*data/processed/<pair>/<dataset>/<pair>*<dataset>.parquet`)
**Testing**: pytest via `poetry run pytest`
**Target Platform**: Windows/Linux CLI
**Project Type**: Single project
**Performance Goals**: Same as single-symbol backtest (vectorized Polars path)
**Constraints**: Pylint ≥9.5/10, Poetry for all Python commands

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Principle                 | Status  | Notes                                |
| ------------------------- | ------- | ------------------------------------ |
| IX. Dependency Management | ✅ PASS | Poetry used for all commands         |
| X. Code Quality           | ✅ PASS | Pylint ≥9.5/10 target in SC-006      |
| VIII. Documentation       | ✅ PASS | Docstrings required                  |
| XI. Commit Standards      | ✅ PASS | Semantic commits with spec/task refs |

## Project Structure

### Documentation (this feature)

```text
specs/013-multi-symbol-backtest/
├── spec.md              ✅ Created
├── plan.md              ✅ This file
├── research.md          ✅ Created (5 decisions)
├── data-model.md        ✅ Created
├── quickstart.md        ✅ Created
└── tasks.md             🔜 Next: /speckit.tasks
```

### Source Code (repository root)

```text
src/
├── cli/
│   └── run_backtest.py        # MODIFY: Multi-symbol loop
├── backtest/
│   └── portfolio/
│       └── independent_runner.py  # MODIFY: Vectorized path + Parquet
├── models/
│   └── directional.py         # EXISTS: BacktestResult with multi-symbol fields
└── data_io/
    └── formatters.py          # EXISTS: format_multi_symbol_* functions

tests/
├── integration/
│   └── test_multi_symbol_build.py   # EXISTS: 13 tests
│   └── test_multi_symbol_backtest.py  # NEW: Multi-symbol CLI tests
└── unit/
    └── test_path_construction.py  # NEW: Path construction tests
```

---

## Proposed Changes

### Component 1: CLI Multi-Symbol Loop

#### [MODIFY] [run_backtest.py](file:///e:/GitHub/trading-strategies/src/cli/run_backtest.py)

**Lines 393-436**: Extend path construction to build paths for ALL pairs:

- Loop over `args.pair` instead of using `args.pair[0]`
- Build list of `(pair, path)` tuples for each symbol
- Validate all paths exist before proceeding

**Lines 630-660**: Replace single-pair execution with multi-symbol flow:

- When `len(args.pair) > 1`: Use multi-symbol runner pattern
- When `len(args.pair) == 1`: Keep existing single-symbol path (regression protection)
- Add `DEFAULT_ACCOUNT_BALANCE = 2500.0` constant

**New function** `run_multi_symbol_backtest()`:

- Iterate over pairs, load each dataset with Parquet/CSV fallback
- Run `BacktestOrchestrator.run_backtest()` for each
- Aggregate results into multi-symbol `BacktestResult`
- Compute combined PnL with equal capital allocation

---

### Component 2: IndependentRunner Modernization

#### [MODIFY] [independent_runner.py](file:///e:/GitHub/trading-strategies/src/backtest/portfolio/independent_runner.py)

**Line 15**: Replace `from src.data_io.legacy_ingestion import ingest_candles` with:

```python
from src.data_io.ingestion import ingest_ohlcv_data
```

**Lines 144-146**: Update `_run_symbol_backtest()` to use Polars:

```python
# Old: candles = list(ingest_candles(dataset_path))
# New:
ingestion_result = ingest_ohlcv_data(
    path=dataset_path,
    timeframe_minutes=1,
    mode="columnar",
    use_arrow=dataset_path.suffix.lower() == ".parquet",
    return_polars=True,
)
enriched_df = ingestion_result.data
```

**Lines 172-184**: Update `_get_dataset_path()` to support Parquet with CSV fallback:

```python
def _get_dataset_path(self, pair: CurrencyPair, dataset: str = "test") -> Path:
    base_path = self.data_dir / pair.code.lower() / dataset
    filename_base = f"{pair.code.lower()}_{dataset}"

    parquet_path = base_path / f"{filename_base}.parquet"
    if parquet_path.exists():
        return parquet_path

    csv_path = base_path / f"{filename_base}.csv"
    return csv_path  # Caller validates existence
```

---

## Verification Plan

### Automated Tests

#### Existing Tests (Regression Protection)

```bash
# Run existing multi-symbol tests
poetry run pytest tests/integration/test_multi_symbol_build.py -v

# Run existing vectorized backtest tests
poetry run pytest tests/integration/test_vectorized_direct.py -v
```

#### New Tests to Create

**File**: `tests/integration/test_multi_symbol_backtest.py`

| Test                                     | Description                                        |
| ---------------------------------------- | -------------------------------------------------- |
| `test_multi_symbol_both_pairs_executed`  | Verify `--pair EURUSD USDJPY` runs on BOTH symbols |
| `test_multi_symbol_aggregated_pnl`       | Verify combined PnL reflects both symbols          |
| `test_multi_symbol_default_balance`      | Verify $2,500 default balance used                 |
| `test_single_symbol_unchanged`           | Verify single-pair behavior unchanged              |
| `test_multi_symbol_parquet_fallback_csv` | Verify CSV fallback when Parquet missing           |

**File**: `tests/unit/test_path_construction.py`

| Test                                 | Description                       |
| ------------------------------------ | --------------------------------- |
| `test_path_construction_single_pair` | Verify path for single pair       |
| `test_path_construction_multi_pair`  | Verify paths for multiple pairs   |
| `test_path_parquet_preferred`        | Verify Parquet checked before CSV |

Run new tests:

```bash
poetry run pytest tests/integration/test_multi_symbol_backtest.py tests/unit/test_path_construction.py -v
```

### Manual Verification

1. **Multi-Symbol Run** (requires test data):

   ```bash
   poetry run python -m src.cli.run_backtest \
       --direction LONG \
       --pair EURUSD USDJPY \
       --dataset test
   ```

   Expected: Both symbols appear in output with trades for each.

2. **Single-Symbol Regression**:

   ```bash
   poetry run python -m src.cli.run_backtest \
       --direction LONG \
       --pair EURUSD \
       --dataset test
   ```

   Expected: Identical output to before changes.

### Code Quality

```bash
# Pylint check (target ≥9.5/10)
poetry run pylint src/cli/run_backtest.py src/backtest/portfolio/independent_runner.py --score=yes

# Ruff check
poetry run ruff check src/cli/ src/backtest/portfolio/
```

---

## Complexity Tracking

No constitution violations requiring justification.
