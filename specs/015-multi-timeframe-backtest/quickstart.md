# Quickstart: Multi-Timeframe Backtesting

## Basic Usage

```bash
# Run backtest on 15-minute timeframe
python -m src.cli.run_backtest --direction LONG --data price_data/processed/eurusd/test --timeframe 15m

# Run backtest on 1-hour timeframe
python -m src.cli.run_backtest --direction LONG --data price_data/processed/eurusd/test --timeframe 1h

# Run backtest on 4-hour timeframe
python -m src.cli.run_backtest --direction BOTH --data price_data/processed/eurusd/test --timeframe 4h
```

## Supported Timeframe Formats

| Format  | Example                  | Minutes           |
| ------- | ------------------------ | ----------------- |
| Minutes | `1m`, `5m`, `15m`, `30m` | 1, 5, 15, 30      |
| Hours   | `1h`, `2h`, `4h`, `8h`   | 60, 120, 240, 480 |
| Days    | `1d`                     | 1440              |

Any positive integer multiple of 1 minute is supported (e.g., `7m`, `90m`, `120m`).

## Configuration File

```yaml
# config.yaml
backtest:
  timeframe: "15m"
```

Then run without `--timeframe` flag:

```bash
python -m src.cli.run_backtest --direction LONG --data price_data/processed/eurusd/test
```

## Caching Behavior

Resampled data is cached in `.time_cache/` to avoid recomputation:

- Cache key: `{instrument}_{timeframe}_{date_range}_{data_hash}`
- First run: Resample + cache (slower)
- Subsequent runs: Load from cache (faster)

To clear cache:

```bash
rm -rf .time_cache/
```

## Python API

```python
from src.backtest.orchestrator import BacktestOrchestrator
from src.data_io.ingestion import ingest_ohlcv_data
from src.data_io.resample import resample_ohlcv
from src.data_io.timeframe import parse_timeframe

# Load 1-minute data
result = ingest_ohlcv_data("path/to/data.parquet", timeframe_minutes=1, return_polars=True)

# Resample to 15 minutes
tf = parse_timeframe("15m")
resampled = resample_ohlcv(result.data, tf.period_minutes)

# Run backtest on resampled data
orch = BacktestOrchestrator(direction_mode=DirectionMode.LONG)
backtest_result = orch.run_backtest(resampled, pair="EURUSD", run_id="test-15m")
```

## Incomplete Bar Warnings

When >10% of bars are incomplete (missing constituent 1-minute data), a warning is emitted:

```text
WARNING: 12.5% of bars are incomplete (data gaps detected)
```

Adjust threshold via config:

```yaml
backtest:
  incomplete_bar_threshold: 0.15 # 15%
```
