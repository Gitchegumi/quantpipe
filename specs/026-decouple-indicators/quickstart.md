# Quickstart: Custom Strategy Indicators

## Defining a Custom Indicator

To use a custom indicator in your strategy, define the calculation function and expose it via `get_custom_indicators`.

### 1. Define the Calculation Function

The function must accept a Polars DataFrame and return it with the new column appended.

```python
import polars as pl

def my_custom_momentum(df: pl.DataFrame, period: int = 10, output_col: str = "mom") -> pl.DataFrame:
    return df.with_columns(
        (pl.col("close") / pl.col("close").shift(period) - 1).alias(output_col)
    )
```

### 2. Register in Strategy

Override `get_custom_indicators` in your strategy class.

```python
from src.strategy.base import Strategy

class MyStrategy(Strategy):
    def get_custom_indicators(self):
        return {
            "my_momentum": my_custom_momentum
        }

    def generate_signals(self, df):
        # Use the custom indicator
        # Note: 'my_momentum' is available as a column if requested in config
        pass
```

### 3. Use in Configuration

Reference the indicator by name (and optional params) in your config/presets.

```yaml
indicators:
  - "ema_20"
  - "my_momentum(period=14)"
```

## Overriding Global Indicators

You can replace a standard indicator by registering the same name.

```python
def my_better_rsi(df, **kwargs):
    # ... custom logic ...
    return df

class MyStrategy(Strategy):
    def get_custom_indicators(self):
        return {
            "rsi": my_better_rsi
        }
```
