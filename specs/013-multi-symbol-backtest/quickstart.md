# Quickstart: Multi-Symbol Concurrent Backtest

**Feature**: 013-multi-symbol-backtest

## Running Multi-Symbol Backtests

### Basic Multi-Symbol Run

```bash
# Run backtest on two pairs with default settings
poetry run python -m src.cli.run_backtest \
    --direction LONG \
    --pair EURUSD USDJPY \
    --dataset test
```

### What This Does

1. Loads `price_data/processed/eurusd/test/eurusd_test.parquet`
2. Loads `price_data/processed/usdjpy/test/usdjpy_test.parquet`
3. Runs independent backtests on each symbol
4. Aggregates results with combined PnL (starting balance: $2,500)
5. Outputs per-symbol metrics AND portfolio summary

### Expected Output

```text
================================================================================
                    Multi-Symbol Backtest Results
================================================================================
Symbols: EURUSD, USDJPY
Direction: LONG
Starting Balance: $2,500.00

─────────────────────────────────────────────────────────────────────────────
Symbol: EURUSD
  Trades: 45 | Win Rate: 55.6% | Total R: +12.5
  PnL: +$312.50

Symbol: USDJPY
  Trades: 38 | Win Rate: 52.6% | Total R: +8.2
  PnL: +$205.00

─────────────────────────────────────────────────────────────────────────────
PORTFOLIO SUMMARY
  Total Trades: 83
  Combined PnL: +$517.50
  Final Balance: $3,017.50
================================================================================
```

### Single Symbol (Unchanged)

```bash
# Single symbol works exactly as before
poetry run python -m src.cli.run_backtest \
    --direction LONG \
    --pair EURUSD \
    --dataset test
```

### With JSON Output

```bash
poetry run python -m src.cli.run_backtest \
    --direction LONG \
    --pair EURUSD USDJPY \
    --dataset test \
    --output-format json
```

## Troubleshooting

### "No data file found for --pair X"

Ensure Parquet files exist at:

```text
price_data/processed/<pair>/test/<pair>_test.parquet
```

Or CSV fallback at:

```text
price_data/processed/<pair>/test/<pair>_test.csv
```

### One Symbol Fails, Others Continue

Multi-symbol runs are fault-tolerant. If one symbol's data is missing or corrupt:

- Warning logged for failed symbol
- Other symbols continue processing
- Summary shows which symbols succeeded/failed
