# Quickstart: Multi-Strategy Backtesting

This guide shows how to register strategies, run a multi-strategy backtest, and inspect aggregated portfolio results.

## 1. Register Strategies (CLI)

### List Registered Strategies

View all currently registered strategies:

```powershell
poetry run python -m src.cli.run_backtest --list-strategies
```

Output example:

```text
Registered Strategies (2):
------------------------------------------------------------
  trend_pullback
    Tags: trend, pullback
    Version: 1.0.0

  momentum_core
    Tags: momentum
    Version: 1.2.0
```

### Register a New Strategy

Register a strategy from a Python module:

```powershell
poetry run python -m src.cli.run_backtest \
  --register-strategy my_strategy \
  --strategy-module src.strategy.my_strategy \
  --strategy-tags trend experimental \
  --strategy-version 0.1.0
```

**Note**: Current implementation uses in-memory registry. Persistent storage will be added in future release.

### Strategy Module Requirements

Your strategy module must expose a `run()` or `execute()` function:

```python
# src/strategy/my_strategy.py

def run(candles):
    """
    Execute strategy logic and return result dict.
    
    Args:
        candles: List of candle data with indicators.
    
    Returns:
        Dictionary with keys: pnl, max_drawdown, exposure
    """
    # Strategy logic here
    return {
        "pnl": 150.0,
        "max_drawdown": 0.08,
        "exposure": {"EURUSD": 0.02},
    }
```

## 2. Run Multi-Strategy Backtest

```powershell
poetry run python -m trading_strategies.cli.run_backtest --strategies trend_pullback momentum_core mean_revert \
  --weights trend_pullback=0.4 momentum_core=0.4 mean_revert=0.2 --aggregate --global-drawdown 0.25 \
  --dataset price_data/processed/eurusd/eurusd_2024.csv
```

Flags:

- `--strategies` comma-separated strategy ids
- `--weights` key=value pairs (sum ≈ 1.0) optional (defaults equal-weight)
- `--aggregate` enable aggregated portfolio metrics output
- `--no-aggregate` produce only per-strategy outputs
- `--global-drawdown` portfolio drawdown threshold (fraction of starting equity)

## 3. Configuration Overrides

Override default strategy parameters per-strategy:

```python
# In orchestrator call or config file
user_overrides = {
    "trend_pullback": {"ema_fast": 12, "ema_slow": 50},
    "momentum_core": {"rsi_length": 10},
}

from src.strategy.config_override import apply_strategy_overrides

# Apply overrides for specific strategy
config = apply_strategy_overrides(
    strategy_name="trend_pullback",
    base_config=default_params,
    user_overrides=user_overrides
)
```

## 4. Outputs

Generated files (conceptual):

- Per-strategy metrics: `results/<run_id>/<strategy_id>_metrics.json`
- Aggregated portfolio: `results/<run_id>/portfolio_aggregate.json`
- Run manifest: `results/<run_id>/run_manifest.json`

## 5. Deterministic Repeatability

Repeat the same command (same dataset, strategies, weights, and risk limits) to produce identical metrics (excluding timestamps). The manifest includes `deterministic_run_id` hash.

## 6. Handling Failures

- Per-strategy risk breach → strategy halts; others continue.
- Global drawdown breach → all strategies halt, partial results preserved.
- Unrecoverable system error → global abort logged; partial outputs retained.

## 7. Validation & Quality

Run tests and quality gates:

```powershell
poetry run pytest
poetry run black src/ tests/
poetry run ruff check src/ tests/
poetry run pylint src/ --score=yes
markdownlint-cli2 "**/*.md" "!poetry.lock"
```

## 8. Next Steps & Future Enhancements

### Deferred Features

**Correlation Analysis (FR-022)**: Strategy correlation matrix and diversification metrics are deferred to a future phase. Current implementation includes a `correlation_status: 'deferred'` placeholder in aggregated metrics. See `spec.md` for detailed rationale.

### Roadmap

- Add correlation matrix computation and inter-strategy correlation tracking
- Implement dynamic weighting algorithms (adaptive, volatility-based)
- Expand aggregation metrics (e.g., diversification score, tail risk)
- Add persistent strategy registry storage
