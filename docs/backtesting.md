# Backtesting & Dataset Methodology

This document explains how datasets are prepared and how the backtesting framework evaluates strategies.

## Goals

- Deterministic, reproducible results
- Clear separation between calibration ("test") and evaluation ("validation")
- Transparent risk and performance metrics

## Data Preparation Workflow

1. Place raw symbol data under `price_data/raw/<symbol>/` (CSV files).

2. **If using MetaTrader format** (no headers, format: `date,time,open,high,low,close,volume`):

   Convert to standard format first:

   ```powershell
   poetry run python scripts/convert_mt_format.py price_data/raw/eurusd price_data/raw_converted/eurusd
   ```

   Then use the converted files in `price_data/raw_converted/<symbol>/` for the next step.

3. Run dataset builder to normalize, sort, and partition:

   ```powershell
   # If you converted MT format files:
   poetry run quantpipe ingest --symbol eurusd --raw-path price_data/raw_converted

   # If you already have standard format files (with timestamp,open,high,low,close,volume header):
   poetry run quantpipe ingest --symbol eurusd
   ```

4. Generated structure:

   ```text
   price_data/processed/<symbol>/
     test/<symbol>_test.csv         # Earliest 80%
     validate/<symbol>_validation.csv   # Most recent 20%
     metadata.json    # Row counts, time span, integrity info
   ```

### Partition Logic

- 80/20 chronological split (floor-based index boundary)
- Prevents look-ahead leakage
- Validation partition always represents most recent market conditions

### Integrity Checks

| Check           | Description                                     |
| --------------- | ----------------------------------------------- |
| Chronology      | Timestamps strictly increasing                  |
| Column Presence | `timestamp,open,high,low,close,volume` required |
| Gaps            | Logged if missing intervals detected            |
| Row Counts      | Stored in metadata for reproducibility audits   |

## Backtest Modes

| Mode       | Command                      | Purpose                                             |
| ---------- | ---------------------------- | --------------------------------------------------- |
| Single run | `quantpipe backtest`         | Run on any CSV file                                 |
| Split-mode | `src.cli.run_split_backtest` | Automatically evaluate test & validation partitions |

### Single-Symbol Baseline Behavior

The backtesting framework maintains full backward compatibility for single-symbol
runs. All existing single-symbol functionality continues to work unchanged:

- **Filename patterns**: Single-symbol outputs use the established naming convention
  `backtest_{direction}_{YYYYMMDD}_{HHMMSS}.{ext}` without symbol tags (for backward
  compatibility). Symbol tags are optional for single-symbol runs.

- **Metrics calculations**: All metrics (win rate, average R, max drawdown, etc.)
  are computed using the same algorithms as before multi-symbol support.

- **Determinism**: Single-symbol runs produce identical results across repeated
  executions with the same inputs and parameters.

- **Output formats**: Both text and JSON output formats remain unchanged.

Multi-symbol functionality (introduced in feature 008-multi-symbol) is purely
additive and does not modify single-symbol execution paths. Regression tests
ensure this invariant is maintained.

### Example Split Run

```powershell
poetry run python -m src.cli.run_split_backtest --symbol eurusd --direction LONG
```

## Execution Model

- Event-loop processes candles sequentially
- Strategy produces signals (enter/hold/exit)
- Risk module sizes position & applies ATR-based stops
- Metrics aggregator records trade + equity statistics

## Metrics (Glossary)

| Metric           | Meaning                     | Notes                          |
| ---------------- | --------------------------- | ------------------------------ |
| Trades           | Count of closed trades      | Excludes open positions at end |
| Win Rate         | Wins / Trades (%)           | Rounded to 1 decimal           |
| Average R        | Mean R-multiple per trade   | R = (PnL / initial risk)       |
| Expectancy       | Average R including losers  | Indicator of edge              |
| Max Drawdown (R) | Peak-to-trough in R units   | Risk-centric perspective       |
| Profit Factor    | Gross wins / gross losses   | >1 suggests positive edge      |
| Sharpe Est       | Approx risk-adjusted return | Simplified estimator           |

## Determinism & Reproducibility

| Aspect        | Mechanism                                |
| ------------- | ---------------------------------------- |
| Data          | Fixed processed partitions               |
| Parameters    | Pydantic model with explicit defaults    |
| Outputs       | Structured text + optional JSON          |
| Repeatability | Identical input yields identical metrics |

## Result Outputs

- Text summary (default) prints core metrics
- JSON (via `--output-format json`) enables downstream parsing & aggregation

## Extending Metrics

When adding a new metric:

1. Add calculation in `src/backtest/metrics.py`
2. Include in JSON serialization (if general purpose)
3. Update this glossary table

## Common Pitfalls

| Pitfall                 | Avoidance                                     |
| ----------------------- | --------------------------------------------- |
| Using raw data directly | Always run dataset builder first              |
| Mixed timezone data     | Normalize to UTC before ingestion             |
| Overlapping partitions  | Chronological split prevents this             |
| Silent parameter drift  | Centralize parameter changes in config models |

---

For strategy-specific logic see `docs/strategies.md`.
