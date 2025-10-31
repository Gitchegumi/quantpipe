# Trading Strategies

Algorithmic FX trading strategies with comprehensive backtesting framework.

## Overview

This project implements a parsimonious trend pullback continuation strategy for FX markets. The strategy identifies high-probability entry points by waiting for pullbacks in the prevailing trend, confirmed by reversal patterns and momentum indicators.

## Quick Start

See [specs/001-trend-pullback/quickstart.md](specs/001-trend-pullback/quickstart.md) for detailed setup and usage instructions.

## Installation

This project uses [Poetry](https://python-poetry.org/) for dependency management.

```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Run tests
poetry run pytest
```

## Running Backtests

### CLI Quick Start

```powershell
# Run backtest on your data
poetry run python -m src.cli.run_backtest `
  --data price_data/EURUSD_15m.csv `
  --direction BOTH

# Long signals only
poetry run python -m src.cli.run_backtest `
  --data price_data/EURUSD_15m.csv `
  --direction LONG

# Dry-run mode (signals only, no execution)
poetry run python -m src.cli.run_backtest `
  --data price_data/EURUSD_15m.csv `
  --dry-run
```

### CLI Options

| Option            | Values                              | Default    | Description                        |
| ----------------- | ----------------------------------- | ---------- | ---------------------------------- |
| `--data`          | PATH                                | Required   | Path to CSV price data file        |
| `--direction`     | `LONG`, `SHORT`, `BOTH`             | `LONG`     | Trade direction mode               |
| `--output`        | PATH                                | `results/` | Output directory for results       |
| `--output-format` | `text`, `json`                      | `text`     | Output format                      |
| `--log-level`     | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO`     | Logging verbosity                  |
| `--dry-run`       | flag                                | -          | Generate signals without execution |

### Data File Format

**CSV Requirements:**

- Columns: `timestamp`, `open`, `high`, `low`, `close`, `volume`
- Timestamp format: ISO 8601 or Unix epoch
- No gaps in data (warnings will be logged)

### Output Examples

**Text Output (default):**

```text
Backtest Results:
  Trades: 42
  Win Rate: 61.9%
  Avg R: 1.24
  Expectancy: 0.87
  Max Drawdown: 3.2R
  Sharpe Estimate: 1.45
```

**JSON Output:**

```powershell
poetry run python -m src.cli.run_backtest `
  --data data.csv `
  --output-format json > results.json
```

## Dataset Preparation and Split-Mode Backtesting

### Overview

The dataset builder creates standardized test/validation partitions for reproducible evaluation. This enables proper out-of-sample testing and prevents look-ahead bias.

**Benefits:**

- **Reproducibility**: Consistent data splits across runs
- **Separation**: Test data for model calibration, validation for performance evaluation
- **Temporal Integrity**: Validation uses most recent 20% of data (realistic forward testing)
- **No Leakage**: Strict chronological split prevents data contamination

### Building Datasets

```powershell
# Build dataset for single symbol
poetry run build-dataset --symbol eurusd

# Build datasets for all symbols
poetry run build-dataset --all

# Custom paths
poetry run build-dataset --symbol eurusd `
  --raw-path price_data/raw `
  --output-path price_data/processed
```

**Output Structure:**

```text
price_data/processed/
└── eurusd/
    ├── test.csv          # 80% earliest data (model calibration)
    ├── validation.csv    # 20% most recent data (performance eval)
    └── metadata.json     # Build metadata (row counts, timestamps, gaps)
```

### Split-Mode Backtesting

Run backtests separately on test and validation partitions:

```powershell
# Basic split-mode backtest
poetry run python -m src.cli.run_split_backtest `
  --symbol eurusd `
  --direction LONG

# With custom processed data path
poetry run python -m src.cli.run_split_backtest `
  --symbol eurusd `
  --direction LONG `
  --processed-path price_data/processed

# JSON output
poetry run python -m src.cli.run_split_backtest `
  --symbol eurusd `
  --direction BOTH `
  --output-format json
```

**Split-Mode Options:**

| Option              | Values                              | Default                     | Description                      |
| ------------------- | ----------------------------------- | --------------------------- | -------------------------------- |
| `--symbol`          | STRING                              | Required                    | Symbol to backtest (e.g. eurusd) |
| `--direction`       | `LONG`, `SHORT`, `BOTH`             | `LONG`                      | Trade direction mode             |
| `--processed-path`  | PATH                                | `price_data/processed`      | Path to processed partitions     |
| `--output`          | PATH                                | `results/`                  | Output directory for results     |
| `--output-format`   | `text`, `json`                      | `text`                      | Output format                    |
| `--log-level`       | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO`                      | Logging verbosity                |

**Split-Mode Output Example:**

```text
================================================================================
SPLIT-MODE BACKTEST RESULTS
================================================================================

RUN METADATA
--------------------------------------------------------------------------------
Run ID:         split_long_eurusd_20250130_100000
Symbol:         eurusd
Direction:      LONG
Start Time:     2025-01-30T10:00:00+00:00
End Time:       2025-01-30T10:05:30+00:00
Duration:       330.00s

================================================================================
TEST PARTITION METRICS
================================================================================

Total Trades:   42
Win Rate:       61.9% (26W / 16L)
Average R:      1.24
Expectancy:     0.87
Sharpe Est:     1.45
Profit Factor:  2.18
Max Drawdown:   3.2R

================================================================================
VALIDATION PARTITION METRICS
================================================================================

Total Trades:   18
Win Rate:       55.6% (10W / 8L)
Average R:      0.92
Expectancy:     0.45
Sharpe Est:     0.98
Profit Factor:  1.45
Max Drawdown:   2.8R
================================================================================
```

### Workflow: From Raw Data to Validated Results

1. **Prepare Raw Data**: Place CSV files in `price_data/raw/<symbol>/`
2. **Build Datasets**: `poetry run build-dataset --symbol <symbol>`
3. **Verify Partitions**: Check `price_data/processed/<symbol>/` for test.csv/validation.csv
4. **Run Split-Mode Backtest**: `poetry run python -m src.cli.run_split_backtest --symbol <symbol>`
5. **Analyze Results**: Compare test vs validation metrics in `results/` directory

### Dataset Requirements

- **Raw Data Format**: CSV with columns `timestamp,open,high,low,close,volume`
- **Minimum Rows**: 500 rows required for split (configurable threshold)
- **Timestamp**: UTC, chronologically ordered
- **Split Ratio**: 80/20 (test/validation) with floor-based deterministic splitting

### Missing Partitions Guard

If you try to run split-mode backtest without building datasets first, you'll see:

```text
Error: Missing partitions for eurusd: ['test', 'validation']
Run: poetry run build-dataset --symbol eurusd
```

**Implementation**: Feature 004-timeseries-dataset (Phase 5 - Tasks T028-T034)

## Project Structure

```text
src/
├── indicators/          # Technical indicators (EMA, ATR, RSI)
├── strategy/            # Trading strategy logic
│   └── trend_pullback/  # Trend pullback continuation strategy
├── risk/                # Position sizing and risk management
├── backtest/            # Backtesting engine
├── models/              # Data models and entities
├── io/                  # Data ingestion and manifest handling
├── cli/                 # Command-line interface
└── config/              # Configuration management

tests/
├── unit/                # Unit tests (<5s, <100 rows, synthetic fixtures)
├── integration/         # Integration tests (<30s, 100-10K rows, real data)
├── performance/         # Performance benchmarks (<120s, >10K rows, full load)
└── fixtures/            # Test data fixtures (6 deterministic CSVs with manifest)
```

## Testing

### Test Organization

Tests are organized into three tiers with distinct runtime and dataset characteristics:

**Unit Tests** (`tests/unit/`):

- **Purpose**: Fast feedback on individual components
- **Runtime Target**: <5 seconds total
- **Dataset Size**: <100 rows (synthetic fixtures)
- **Scope**: Indicators, risk management, models
- **Markers**: `@pytest.mark.unit`

**Integration Tests** (`tests/integration/`):

- **Purpose**: Multi-component interaction validation
- **Runtime Target**: <30 seconds total
- **Dataset Size**: 100-10,000 rows (small real data)
- **Scope**: Strategy signals, backtest orchestration
- **Markers**: `@pytest.mark.integration`

**Performance Tests** (`tests/performance/`):

- **Purpose**: Full system load testing
- **Runtime Target**: <120 seconds total
- **Dataset Size**: >10,000 rows (full production volumes)
- **Scope**: Full-year backtests, memory profiling, throughput
- **Markers**: `@pytest.mark.performance`

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run by tier (selective execution)
poetry run pytest -m unit              # Fast feedback (<5s)
poetry run pytest -m integration       # Multi-component (<30s)
poetry run pytest -m performance       # Full system (<120s)

# Run with coverage
poetry run pytest --cov=src --cov-report=term-missing

# Run specific test file
poetry run pytest tests/unit/test_indicators_consolidated.py -v
```

### Test Fixtures

Deterministic test fixtures are located in `tests/fixtures/` with metadata in `manifest.yaml`:

- **fixture_trend_example.csv**: Uptrend scenario (20 candles)
- **fixture_flat_prices.csv**: Ranging market (20 candles)
- **fixture_spike_outlier.csv**: Volatility spike (20 candles)
- **sample_candles_long.csv**: Long signal scenario (40 candles)
- **sample_candles_short.csv**: Short signal scenario (40 candles)
- **sample_candles_flat.csv**: No signal scenario (40 candles)

Each fixture includes:

- Checksum for integrity validation
- Seed for reproducibility
- Scenario type and indicators covered
- OHLC data validation

### Test Metrics

- **Total Tests**: ~148 tests
- **Coverage**: ≥70% for core modules
- **Pass Rate**: 100% (all new/consolidated tests)
- **Code Quality**: Pylint 9.52/10 (src/), 10.00/10 (tests/)
- **Determinism**: 17 repeatability tests validate bitwise identical results

### Quality Gates

All code changes must pass:

1. **Formatting**: `poetry run black src/ tests/` (88 char lines)
2. **Linting**: `poetry run ruff check src/ tests/` (zero errors)
3. **Quality**: `poetry run pylint src/ --score=yes` (≥8.0/10)
4. **Tests**: `poetry run pytest -m unit` (<5s pass rate)

## Features

- **Trend Detection**: EMA-based trend classification with ranging market filter
- **Pullback Identification**: Price retracement detection with momentum confirmation
- **Reversal Confirmation**: Candle pattern recognition and momentum turn validation
- **Risk Management**: ATR-based stops, position sizing, drawdown protection
- **Backtesting**: Streaming data processing, deterministic results, comprehensive metrics
- **Reproducibility**: Hash-based result verification, data provenance tracking

## Requirements

- Python 3.11+
- Poetry for dependency management

## Development

```bash
# Run linter
poetry run ruff check .

# Format code
poetry run black src/ tests/

# Run pylint
poetry run pylint src/ --score=yes

# Run tests with coverage
poetry run pytest --cov=src
```

## Configuration

The strategy accepts configuration via `src/config/parameters.py` using Pydantic models.

### Core Parameters

**Trend Classification:**

- `ema_fast_period`: Fast EMA period (default: 12)
- `ema_slow_period`: Slow EMA period (default: 50)
- `range_threshold`: Percentage threshold for ranging market detection (default: 0.005 = 0.5%)

**Pullback Detection:**

- `pullback_ema_period`: EMA for pullback reference (default: 12)
- `pullback_threshold`: Minimum retracement percentage (default: 0.003 = 0.3%)
- `pullback_max_age`: Maximum candles since pullback (default: 5)

**Reversal Confirmation:**

- `reversal_candle_types`: Enabled patterns (default: `["hammer", "engulfing"]`)
- `rsi_period`: RSI lookback period (default: 14)
- `rsi_oversold`: Oversold threshold (default: 30)
- `rsi_overbought`: Overbought threshold (default: 70)

**Risk Management:**

- `atr_period`: ATR calculation period (default: 14)
- `atr_stop_multiplier`: ATR multiplier for stop distance (default: 2.0)
- `risk_per_trade`: Risk percentage per trade (default: 0.01 = 1%)
- `max_position_pct`: Maximum position size (default: 0.02 = 2%)

**Exit Logic:**

- `target_r_multiple`: Profit target in R-multiples (default: 3.0)
- `trailing_stop_activation_r`: R-multiple to activate trailing stop (default: 1.5)
- `trailing_stop_distance_r`: Trailing stop distance in R (default: 1.0)

**Optional Filters:**

- `volatility_filter_enabled`: Enable volatility regime filtering (default: False)
- `htf_filter_enabled`: Enable higher timeframe confirmation (default: False)
- `htf_timeframe_multiplier`: HTF multiplier (default: 4)
- `htf_ema_period`: HTF EMA period (default: 50)

### Example Configuration

```python
from src.config.parameters import StrategyParameters

params = StrategyParameters(
    ema_fast_period=12,
    ema_slow_period=50,
    atr_period=14,
    atr_stop_multiplier=2.0,
    risk_per_trade=0.01,
    target_r_multiple=3.0,
)
```

### Environment Variables

Set via `.env` file or environment:

- `LOG_LEVEL`: Logging level (default: `INFO`)
- `DATA_DIR`: Data directory path (default: `./data`)
- `OUTPUT_DIR`: Backtest output directory (default: `./runs`)

## Documentation

- [Feature Specification](specs/001-trend-pullback/spec.md)
- [Implementation Plan](specs/001-trend-pullback/plan.md)
- [Data Model](specs/001-trend-pullback/data-model.md)
- [Quickstart Guide](specs/001-trend-pullback/quickstart.md)

## License

Proprietary - All Rights Reserved

## Constitution Compliance

This project adheres to the [Trading Strategies Constitution](.specify/memory/constitution.md), ensuring:

- Strategy-first architecture
- Integrated risk management
- Comprehensive backtesting and validation
- Real-time performance monitoring
- Data integrity and provenance
- Model parsimony and interpretability
