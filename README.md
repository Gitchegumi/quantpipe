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

## Multi-Symbol Portfolio Backtesting

Run backtests across multiple currency pairs with independent or portfolio execution modes:

### Independent Mode (Default)

Each symbol runs in isolation with separate capital and risk limits:

```powershell
# Run 3 symbols independently
poetry run python -m src.cli.run_backtest `
--direction BOTH `
--pair EURUSD GBPUSD USDJPY `
--portfolio-mode independent
```

**Features:**

- Separate $10,000 capital per symbol
- Isolated risk management
- Failures don't affect other symbols
- Aggregated summary statistics

### Portfolio Mode

Shared capital pool with correlation tracking and dynamic allocation:

```powershell
# Run portfolio mode with custom correlation threshold
poetry run python -m src.cli.run_backtest `
--direction BOTH `
--pair EURUSD GBPUSD USDJPY `
--portfolio-mode portfolio `
--correlation-threshold 0.75 `
--snapshot-interval 50
```

**Features:**

- Shared capital pool ($10,000 total)
- Dynamic allocation based on volatility
- Correlation matrix tracking (100-candle rolling window)
- Diversification metrics (ratio, effective assets)
- Periodic snapshots (JSONL format)

### Symbol Filtering

Exclude specific symbols at runtime:

```powershell
# Run all pairs except GBPUSD
poetry run python -m src.cli.run_backtest `
--direction LONG `
--pair EURUSD GBPUSD USDJPY NZDUSD `
--disable-symbol GBPUSD
```

Invalid symbols (missing datasets) are automatically skipped with warnings.

### CLI Flags Reference

| Flag                      | Values                 | Default     | Purpose                            |
| ------------------------- | ---------------------- | ----------- | ---------------------------------- |
| `--pair`                  | EURUSD GBPUSD ...      | (required)  | Currency pairs to backtest         |
| `--portfolio-mode`        | independent, portfolio | independent | Execution mode                     |
| `--disable-symbol`        | EURUSD ...             | (none)      | Exclude symbols from execution     |
| `--correlation-threshold` | 0.0-1.0                | 0.8         | Portfolio correlation warning level|
| `--snapshot-interval`     | integer                | 50          | Snapshot frequency (candles)       |

See `specs/008-multi-symbol/quickstart.md` for detailed examples and output formats.

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

## Ingestion Architecture

The data ingestion layer is designed for high performance and modularity, separating core data loading from optional indicator computation.

### Two-Stage Pipeline

**Stage 1: Core Ingestion** (`src/io/ingestion.py`)

- Loads raw OHLCV data from CSV files
- Vectorized operations: sort → deduplicate → validate cadence → fill gaps → enforce schema
- Outputs **only core columns**: `timestamp`, `open`, `high`, `low`, `close`, `volume`, `is_gap`
- Performance: ~138k rows/second sustained (6.9M candles in ≤120s)
- Arrow backend with automatic fallback for optimal performance

**Stage 2: Indicator Enrichment** (`src/indicators/enrich.py`)

- **Opt-in**: Strategies select only needed indicators (e.g., `ema_20`, `atr_14`, `stochrsi`)
- Pluggable registry for built-in and custom indicators
- Preserves core data immutability (hash verification)
- Strict mode: fast-fail on unknown indicators
- Non-strict mode: collect errors, compute what's possible

### Key Benefits

- **Performance**: 83× faster than previous monolithic approach (7.22s vs ~2min for 1M rows)
- **Modularity**: Strategies only pay for indicators they use
- **Memory**: ≥25% reduction via selective enrichment
- **Maintainability**: Clear separation of concerns (data vs computation)

### Quick Example

```python
from src.io.ingestion import ingest_candles
from src.indicators.enrich import enrich_with_indicators

# Stage 1: Fast core ingestion
core_df = ingest_candles("price_data/raw/eurusd/2024.csv")
# Result: timestamp, open, high, low, close, volume, is_gap

# Stage 2: Selective enrichment
enriched_df = enrich_with_indicators(
    core_df,
    indicators=["ema_20", "ema_50", "atr_14"],
    strict=True  # Fail if any indicator unavailable
)
# Result: core columns + ema_20 + ema_50 + atr_14
```

### Adding Custom Indicators

See `src/indicators/README.md` for complete guide with:

- 5-step development process (compute → test → register → use → document)
- Code templates with type hints and validation
- Common pitfalls (mutation, row loops, NaN handling)
- Development checklist

**Core Principles**:

- **Vectorized**: No per-row loops (enforced by Ruff linting)
- **Immutable**: Never modify input arrays
- **NaN-aware**: Propagate NaN for gaps/invalid data
- **Validated**: Check inputs, raise clear errors

See `specs/009-optimize-ingestion/` for detailed architecture documentation.

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
