# Quickstart: Risk Argument Mapping

## Overview

This feature ensures that CLI arguments for risk management correctly override default values and configuration files.

## Usage

### overriding Risk/Reward Ratio

```bash
# Force R:R to 5.0
python -m src.cli.run_backtest --rr-ratio 5.0 ...
```

### Overriding Max Position Size

```bash
# Limit max trade size to 1.0 lot
python -m src.cli.run_backtest --max-position-size 1.0 ...
```

### Order of Precedence

1. **CLI Arguments** (Highest Priority)
2. **Configuration File** (`--config`)
3. **Hardcoded Defaults** (Lowest Priority)

## Verification

Check the logs at the start of the backtest. You should see a message confirming the active risk parameters:

```text
[INFO] Active Risk Parameters:
  Risk %: 0.25
  Stop Multiplier (ATR): 2.0
  R:R Ratio: 5.0
  Max Position Size: 1.0
  Account Balance: 2500.0
```
