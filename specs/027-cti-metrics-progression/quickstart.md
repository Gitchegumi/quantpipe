# Backtesting CTI Challenges - Quickstart

This guide explains how to use the new CTI Challenge mode to verify your strategy against Prop Firm rules.

## Prerequisites

- Strategy registered in the system (e.g., `simple_momentum`).
- Price data ingested.

## Running in CTI Mode

Use the `--cti-mode` flag to enable CTI rule enforcement.

### 1-Step Challenge

```bash
poetry run python -m src.cli.run_backtest \
    --strategy simple_momentum \
    --pair EURUSD \
    --days 60 \
    --cti-mode 1STEP \
    --account-size 10000
```

### 2-Step Challenge

```bash
poetry run python -m src.cli.run_backtest \
    --strategy simple_momentum \
    --pair EURUSD \
    --days 60 \
    --cti-mode 2STEP \
    --account-size 10000
```

### Instant Funding

```bash
poetry run python -m src.cli.run_backtest \
    --strategy simple_momentum \
    --pair EURUSD \
    --days 365 \
    --cti-mode INSTANT \
    --account-size 10000
```

## Interpreting Results

The output report will now contain two new sections:

1. **Challenge Status**:

   - **PASSED**: Strategy met profit target without violations.
   - **FAILED (Daily Loss)**: Strategy exceeded daily loss limit.
   - **FAILED (Max Drawdown)**: Strategy exceeded total drawdown.

2. **Scaling Report** (For long-term tests):

   - Shows history of "Lives" (Attempts).
   - If a drawdown resets the account, a new life begins at Tier 1.
   - Summary of Successes/Failures per Tier.

   ```text
   Scaling Report:
   Life 1 | Tier 1 ($10k) | PASSED | Duration: 40d | PnL: +$1,050
   Life 2 | Tier 2 ($20k) | PASSED | Duration: 65d | PnL: +$2,100
   Life 3 | Tier 3 ($40k) | FAILED | Duration: 12d | PnL: -$2,500
   Life 4 | Tier 1 ($10k) | ACTIVE | Duration: 5d  | PnL: +$200
   ```
