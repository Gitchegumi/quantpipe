# Quickstart: Parallel Indicator Parameter Sweep

**Feature**: 024-parallel-param-sweep

## Basic Usage

### Run a Parameter Sweep

```bash
# Interactive parameter sweep for trend_pullback strategy
poetry run python -m src.cli.run_backtest \
    --pair EURUSD \
    --strategy trend_pullback \
    --direction BOTH \
    --test-range \
    --export results.csv
```

### Example Interactive Session

```text
=== Indicator Parameter Sweep Configuration ===
Press Enter to accept default, or specify value/range (e.g., "10-30 step 5")

--- fast_ema ---
Enter period (20): 10-30 step 5

--- slow_ema ---
Enter period (50): 40-80 step 10

--- atr ---
Enter period (14):

--- stoch_rsi ---
Enter rsi_period (14):
Enter stoch_period (14):
Enter k_smooth (3): 2-4 step 1
Enter d_smooth (3):

Total combinations: 75 (5 × 5 × 1 × 1 × 1 × 3 × 1)
Skipped (fast_ema >= slow_ema): 6

Proceed with 69 valid combinations? [Y/n]: Y

Running sweep with 3 parallel workers...
[████████████████████] 69/69 (100%) - 4m 32s

=== Results (Top 10 by Sharpe Ratio) ===
┌─────┬──────────┬──────────┬────────┬──────────┬─────────┐
│ Rank│ fast_ema │ slow_ema │ Sharpe │ Win Rate │ PnL     │
├─────┼──────────┼──────────┼────────┼──────────┼─────────┤
│ 1   │ 15       │ 60       │ 1.82   │ 58.3%    │ $847.50 │
│ 2   │ 20       │ 70       │ 1.75   │ 56.1%    │ $812.00 │
│ ...                                                     │
└─────────────────────────────────────────────────────────┘
```

### CSV Export Results

When using `--export results.csv`, the output file contains:

```csv
rank,sharpe_ratio,total_pnl,win_rate,trades_count,max_drawdown,error,fast_ema_period,slow_ema_period,k_smooth,d_smooth
1,1.82,847.50,0.583,124,0.15,,15,60,3,3
2,1.75,812.00,0.561,118,0.12,,20,70,3,3
...
```

## CLI Flags

| Flag              | Description                                     |
| ----------------- | ----------------------------------------------- |
| `--test-range`    | Enable interactive parameter sweep mode         |
| `--max-workers N` | Limit parallel workers (default: CPU cores - 1) |
| `--sequential`    | Force sequential execution for debugging        |
| `--export FILE`   | Export results to CSV file                      |

## Range Syntax

| Input          | Interpretation              |
| -------------- | --------------------------- |
| `15`           | Fixed value: [15]           |
| `10-30 step 5` | Range: [10, 15, 20, 25, 30] |
| _(empty)_      | Use default value           |

## Requirements

- Strategy must declare `required_indicators` with semantic names
- Strategy must implement `scan_vectorized()` for performance
- Indicator must be registered with `params` dict in registry
