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

### Multi-Strategy Support

Run multiple strategies simultaneously with weighted portfolio aggregation:

```powershell
# Register and list strategies
poetry run python -m src.cli.run_backtest --register-strategy alpha --strategy-module my_strategies.alpha
poetry run python -m src.cli.run_backtest --list-strategies

# Execute specific strategies with custom weights
poetry run python -m src.cli.run_backtest `
--data price_data/processed/eurusd/test.csv `
--strategies alpha beta `
--weights 0.6 0.4

# Equal-weight fallback (no weights specified)
poetry run python -m src.cli.run_backtest `
--data price_data/processed/eurusd/test.csv `
--strategies alpha beta gamma
```

See `specs/006-multi-strategy/spec.md` for details on strategy registration, filtering, and risk management.

Example (signals only):

```powershell
poetry run python -m src.cli.run_backtest --data price_data/processed/eurusd/test.csv --dry-run
```

## Performance Optimization

The backtesting engine is optimized for large datasets (millions of candles):

**Key Achievements**:

- **Runtime**: ≤20 minutes for 6.9M candles / 17.7k trades (target met)
- **Memory**: ≤1.5× raw dataset footprint with threshold monitoring
- **Vectorization**: 10×+ speedup via numpy-based batch processing
- **Fidelity**: Exact result preservation (price ≤1e-6, PnL ≤0.01%)

**Features**:

- Partial dataset iteration: `--data-frac 0.25` for quick validation
- Profiling: `--profile` flag generates hotspot analysis + benchmark JSON
- Progress tracking: Real-time phase timing with elapsed/remaining estimates

**Quick Example**:

```powershell
# Profile with first 25% of data
poetry run python -m src.cli.run_backtest `
--data price_data/processed/eurusd/full.csv `
--direction BOTH `
--data-frac 0.25 `
--profile
```

See `docs/performance.md` for complete optimization guide, benchmark schema, and aggregation utilities.

## Documentation & Resources

| Audience                       | Where to Look                      |
| ------------------------------ | ---------------------------------- |
| Deeper strategy rationale      | `docs/strategies.md`               |
| Backtesting & dataset workflow | `docs/backtesting.md`              |
| Repository layout overview     | `docs/structure.md`                |
| Contributing / dev setup       | `CONTRIBUTING.md`                  |
| Full original specification    | `specs/001-trend-pullback/spec.md` |
| Additional feature specs       | `specs/` directory                 |

## Data Expectations (Summary)

Minimum columns: `timestamp,open,high,low,close,volume` (chronological, UTC). Build standardized partitions before split-mode testing; details in Backtesting docs.

## Why Separate Docs?

The README remains a fast on-ramp. All contributor, performance, and extended methodological details have been relocated to keep first-use success under five minutes.

## License

Proprietary – All Rights Reserved.

## Governance

See `CONTRIBUTING.md` for quality gates and contribution workflow. Architectural principles live in `.specify/memory/constitution.md`.
