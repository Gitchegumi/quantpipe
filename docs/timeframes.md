# Multi-Timeframe Backtesting

This document describes how to use the multi-timeframe backtesting feature to run strategies on timeframes other than 1-minute.

## Quick Start

```bash
# Run backtest with 15-minute timeframe
poetry run quantpipe backtest \
    --pair EURUSD \
    --direction LONG \
    --timeframe 15m

# Run with 1-hour timeframe
poetry run quantpipe backtest \
    --pair EURUSD \
    --direction BOTH \
    --timeframe 1h
```

## Supported Timeframes

| Format | Description | Examples                              |
| ------ | ----------- | ------------------------------------- |
| `Xm`   | X minutes   | `1m`, `5m`, `15m`, `30m`, `7m`, `90m` |
| `Xh`   | X hours     | `1h`, `2h`, `4h`, `8h`                |
| `Xd`   | X days      | `1d`, `2d`                            |

**Note**: X must be a positive integer ≥ 1. Arbitrary values like `7m` or `90m` are fully supported.

## Configuration

### CLI Arguments

```bash
--timeframe 15m    # Specify timeframe (default: 1m)
--config config.yaml  # Load defaults from YAML file
```

### Config File

Create a `backtest_config.yaml` file:

```yaml
# Default timeframe for backtesting
timeframe: "15m"

# Default trading direction
direction: "BOTH"

# Default dataset
dataset: "test"
```

Use with: `--config backtest_config.yaml`

**CLI takes precedence**: If you specify `--timeframe 5m` with a config that has `timeframe: "15m"`, the CLI value (`5m`) is used.

## How It Works

1. **Data Ingestion**: 1-minute OHLCV data is loaded from Parquet/CSV
2. **Resampling**: Data is aggregated to target timeframe using:
   - Open: first open in period
   - High: max high in period
   - Low: min low in period
   - Close: last close in period
   - Volume: sum of volume in period
3. **Caching**: Resampled data is cached in `.time_cache/` for faster repeated runs
4. **Indicators**: Technical indicators are computed on resampled data
5. **Strategy Execution**: Strategy runs on the resampled bars

## Caching

Resampled data is automatically cached to `.time_cache/` directory:

```text
.time_cache/
├── EURUSD_15m_20000602_20210113_abc12345.parquet
├── EURUSD_1h_20000602_20210113_abc12345.parquet
└── ...
```

Cache keys include:

- Instrument name
- Timeframe
- Date range
- Data hash (for invalidation)

**Second runs are instant** when using the same parameters.

## Data Quality

### Incomplete Bars

When source data has gaps (missing 1-minute bars), the resulting bar is marked with `bar_complete=False`. A warning is logged if >10% of bars are incomplete.

### Edge Bars

Incomplete bars at the start/end of the dataset are automatically dropped to ensure data quality.

## Performance

| Timeframe | Bars (6.9M 1m source) | Speedup       |
| --------- | --------------------- | ------------- |
| 1m        | 6,922,364             | 1x (baseline) |
| 5m        | 1,488,347             | ~4x           |
| 15m       | 500,086               | ~14x          |
| 1h        | 125,000               | ~55x          |

Higher timeframes process significantly faster due to fewer bars.

## Examples

### Basic Usage

```bash
# 5-minute backtest
poetry run quantpipe backtest --pair EURUSD --direction LONG --timeframe 5m

# 4-hour backtest
poetry run quantpipe backtest --pair GBPUSD --direction SHORT --timeframe 4h
```

### Custom Timeframes

```bash
# 7-minute bars (custom)
poetry run quantpipe backtest --pair USDJPY --timeframe 7m --direction BOTH

# 90-minute bars (1.5 hours)
poetry run quantpipe backtest --pair EURUSD --timeframe 90m --direction LONG
```

### With Config File

```bash
# Use config file defaults
poetry run quantpipe backtest --config backtest_config.yaml

# Override config timeframe with CLI
poetry run quantpipe backtest --config backtest_config.yaml --timeframe 1h
```
