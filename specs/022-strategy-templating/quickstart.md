# Quickstart: Strategy Templating Framework

**Feature**: 022-strategy-templating
**Date**: 2025-12-26

## Creating a New Strategy

### Step 1: Scaffold the Strategy

Generate a new strategy template using the scaffold command:

```powershell
poetry run python -m src.cli.scaffold_strategy my_strategy
```

This creates:

```text
src/strategy/my_strategy/
├── __init__.py
├── strategy.py
└── signal_generator.py
```

### Step 2: Customize the Template

Open `src/strategy/my_strategy/strategy.py` and look for `# TODO:` markers:

```python
class MyStrategy:
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="my_strategy",
            version="1.0.0",
            required_indicators=["ema20"],  # TODO: Add your indicators
            tags=["custom"],
        )

    def generate_signals(self, candles: list, parameters: dict) -> list:
        # TODO: Implement your signal generation logic
        signals = []
        # Your logic here...
        return signals
```

### Step 3: Test Your Strategy

Run a basic backtest to verify the strategy works:

```powershell
poetry run python -m src.cli.run_backtest \
    --strategy my_strategy \
    --data price_data/EURUSD_15m.csv \
    --manifest price_data/manifest.yaml
```

## Validation Errors

If your strategy is missing required components, you'll see clear error messages:

```text
StrategyValidationError: Strategy 'my_strategy' failed validation

Errors:
  - Missing required method: generate_signals(candles, parameters) -> list

Expected signature:
  def generate_signals(self, candles: list, parameters: dict) -> list:
      ...
```

## Reference Strategy

Study `src/strategy/simple_momentum/` for a complete working example:

```python
from src.strategy.simple_momentum import SimpleMomentumStrategy

# This strategy:
# - Uses EMA crossover for trend detection
# - Generates LONG signals when fast EMA > slow EMA
# - Includes complete documentation
```

## Common Tasks

### Add a New Indicator

1. Add indicator name to `required_indicators` in metadata
2. Access it in `generate_signals()` via candle attributes

```python
required_indicators=["ema20", "rsi14"]  # Add here

def generate_signals(self, candles, parameters):
    for candle in candles:
        ema = candle.ema20  # Access indicator value
        rsi = candle.rsi14
```

### Implement Vectorized Scanning

For better performance with large datasets:

```python
def scan_vectorized(
    self,
    close: np.ndarray,
    indicator_arrays: dict[str, np.ndarray],
    parameters: dict,
    direction: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    # Return (signal_indices, stop_prices, target_prices, position_sizes)
    ...
```

## Next Steps

- Read [Strategy Authoring Guide](file:///e:/GitHub/trading-strategies/docs/strategy_authoring.md) for detailed lifecycle documentation
- Review `src/strategy/trend_pullback/` for a production strategy example
- Run `poetry run pytest tests/integration/test_strategy_*.py -v` to see test patterns
