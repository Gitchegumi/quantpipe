# Trading Strategies

Algorithmic FX trading strategies with a reproducible backtesting framework.

## Overview

Implements a trend pullback continuation strategy: identify prevailing trend, wait for a measured retracement (pullback), confirm with reversal + momentum context, then evaluate R‑multiple risk-managed entries. The repository also provides a general-purpose backtesting harness, dataset partition tooling (test/validation), and risk management primitives.

## Quick Start (3 Commands)

```powershell
# 1. Install dependencies (requires Poetry)
poetry install

# 2. Run a sample backtest (adjust path to your CSV)
poetry run python -m src.cli.run_backtest --data price_data/processed/eurusd/test.csv --direction LONG

# 3. (Optional) JSON output
poetry run python -m src.cli.run_backtest `
--data price_data/processed/eurusd/test.csv `
--direction BOTH `
--output-format json > results.json
```

If you have only raw data, first build processed partitions (see Backtesting docs below).

## Basic CLI Usage

| Flag              | Values                | Default    | Purpose                                               |
| ----------------- | --------------------- | ---------- | ----------------------------------------------------- |
| `--data`          | PATH                  | (required) | Input CSV (timestamp, open, high, low, close, volume) |
| `--direction`     | `LONG` `SHORT` `BOTH` | `LONG`     | Trade direction mode                                  |
| `--output-format` | `text` `json`         | `text`     | Output format                                         |
| `--dry-run`       | (flag)                | off        | Emit signals only (no execution)                      |

Example (signals only):

```powershell
poetry run python -m src.cli.run_backtest --data price_data/processed/eurusd/test.csv --dry-run
```

## Documentation & Resources

| Audience                       | Where to Look                      |
| ------------------------------ | ---------------------------------- |
| Deeper strategy rationale      | `docs/strategies.md`               |
| Backtesting & dataset workflow | `docs/backtesting.md`              |
| Repository layout overview     | `docs/structure.md`                |
| Contributing / dev setup       | `CONTRIBUTIONS.md`                 |
| Full original specification    | `specs/001-trend-pullback/spec.md` |
| Additional feature specs       | `specs/` directory                 |

## Data Expectations (Summary)

Minimum columns: `timestamp,open,high,low,close,volume` (chronological, UTC). Build standardized partitions before split-mode testing; details in Backtesting docs.

## Why Separate Docs?

The README remains a fast on-ramp. All contributor, performance, and extended methodological details have been relocated to keep first-use success under five minutes.

## License

Proprietary – All Rights Reserved.

## Governance

See `CONTRIBUTIONS.md` for quality gates and contribution workflow. Architectural principles live in `.specify/memory/constitution.md`.
