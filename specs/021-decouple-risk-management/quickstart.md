# Quickstart: Decouple Risk Management

**Feature**: 021-decouple-risk-management
**Date**: 2024-12-24

## Overview

This guide shows how to use the new decoupled risk management system after implementation.

---

## Basic Usage

### 1. Run Backtest with Default Risk Config

```bash
python -m src.cli.run_backtest \
  --strategy trend_pullback \
  --pair EURUSD \
  --direction LONG
```

This uses the default risk config (0.25% risk, 2× ATR stop, 2:1 TP).

### 2. Switch to Fixed 3:1 Risk Ratio

```bash
python -m src.cli.run_backtest \
  --strategy trend_pullback \
  --pair EURUSD \
  --direction LONG \
  --risk-pct 0.25 \
  --stop-policy ATR --atr-mult 2.0 \
  --tp-policy RiskMultiple --rr-ratio 3.0
```

### 3. Use Trailing Stop (No Fixed TP)

```bash
python -m src.cli.run_backtest \
  --strategy trend_pullback \
  --pair EURUSD \
  --direction LONG \
  --risk-pct 0.25 \
  --stop-policy ATR_Trailing --atr-mult 2.0 --atr-period 14 \
  --tp-policy None
```

### 4. Use Fixed Pip Stop (50 pips)

```bash
python -m src.cli.run_backtest \
  --strategy trend_pullback \
  --pair EURUSD \
  --direction LONG \
  --risk-pct 0.25 \
  --stop-policy FixedPips --fixed-pips 50 \
  --tp-policy RiskMultiple --rr-ratio 2.0
```

### 5. Use JSON Config File

Create `risk_config.json`:

```json
{
  "risk_pct": 0.25,
  "stop_policy": { "type": "ATR_Trailing", "multiplier": 2.0, "period": 14 },
  "take_profit_policy": { "type": "None" },
  "position_sizer": { "type": "RiskPercent" },
  "max_position_size": 10.0
}
```

Run with config file:

```bash
python -m src.cli.run_backtest \
  --strategy trend_pullback \
  --pair EURUSD \
  --direction LONG \
  --risk-config risk_config.json
```

---

## Policy Options

### Stop Policies

| Type           | Description          | Required Params        |
| -------------- | -------------------- | ---------------------- |
| `ATR`          | Fixed ATR-based stop | `multiplier`, `period` |
| `ATR_Trailing` | Trailing ATR stop    | `multiplier`, `period` |
| `FixedPips`    | Fixed pip distance   | `pips`                 |

### Take-Profit Policies

| Type           | Description                 | Required Params |
| -------------- | --------------------------- | --------------- |
| `RiskMultiple` | TP at N× risk distance      | `rr_ratio`      |
| `None`         | No take-profit (trail only) | -               |

### Position Sizers

| Type          | Description                            |
| ------------- | -------------------------------------- |
| `RiskPercent` | Size based on risk % and stop distance |

---

## Verifying Risk Config

Check backtest output for risk labeling:

```text
Backtest Summary
================
Strategy: trend_pullback
Risk Manager: ATR_Trailing (risk_pct=0.25, atr_mult=2.0)
...
```

---

## Migrating Existing Strategies

Existing strategies continue working unchanged. The system uses a legacy adapter that:

1. Reads stops/targets from existing `TradeSignal` objects
2. Optionally overrides with RiskManager output if `--risk-config` is provided

No changes required to strategy code.
