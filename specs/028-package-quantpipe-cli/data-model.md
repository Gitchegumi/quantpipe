# CLI Interface Model

**Feature**: `package-quantpipe-cli`

## Commands

### `quantpipe backtest`

Primary command for running backtests. Inherits all functionality from the legacy `src.cli.run_backtest`.

#### Arguments

| Argument          | Type     | Default        | Description                           |
| ----------------- | -------- | -------------- | ------------------------------------- |
| `--direction`     | str      | LONG           | Trading direction (LONG, SHORT, BOTH) |
| `--data`          | path     | None           | Path to CSV price data                |
| `--strategy`      | str/list | trend-pullback | Strategy name(s)                      |
| `--pair`          | str/list | EURUSD         | Currency pair(s)                      |
| `--timeframe`     | str      | 1m             | Timeframe for backtesting             |
| `--output`        | path     | results        | Output directory                      |
| `--output-format` | str      | text           | Output format (text, json)            |
| `--dry-run`       | flag     | False          | Signal-only mode                      |
| `--config`        | path     | None           | Config file path                      |

_(Includes all other existing arguments: `--risk-config`, `--blackout-sessions`, etc.)_

## Future Commands (Planned)

- `quantpipe optimize` (Parameter sweep - currently part of backtest args as `--test-range`)
- `quantpipe verify` (Data verification)
