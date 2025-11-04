# Quickstart: Multi-Strategy Backtesting

This guide shows how to register strategies, run a multi-strategy backtest, and inspect aggregated portfolio results.

## 1. Register / Extend Strategies

Strategies are modules under `src/strategy/`. Each must expose an interface (e.g., `generate_signals`, `apply_risk`, `finalize`). Add new strategy, then update registry configuration.

Example (conceptual):

```python
# src/strategy/my_strategy.py
class MyStrategy(StrategyBase):
    id = "my_strategy"
    def generate_signals(self, data_slice):
        ...
```

## 2. List Available Strategies (CLI)

```powershell
poetry run python -m trading_strategies.cli.run_backtest --list-strategies
```

## 3. Run Multi-Strategy Backtest

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

## 8. Next Steps

- Add correlation matrix (future extension)
- Implement dynamic weighting
- Expand aggregation metrics (e.g., diversification score)
