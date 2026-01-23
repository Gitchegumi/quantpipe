# Quickstart: quantpipe CLI

## Installation

Run from the project root:

```bash
# Using pip
pip install -e .

# Using Poetry (recommended for dev)
poetry install
```

## Usage

### Run a Backtest

```bash
# Basic run
quantpipe backtest --direction LONG --pair EURUSD --timeframe 5m

# With explicit data
quantpipe backtest --data price_data/EURUSD_2023.csv

# Multi-strategy
quantpipe backtest --strategies trend-pullback rsi-reversal --weights 0.6 0.4
```

### Help

```bash
# General help
quantpipe --help

# Backtest command help
quantpipe backtest --help
```
