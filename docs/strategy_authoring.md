# Strategy Authoring Guide

This guide explains how to create custom trading strategies for the backtesting
framework. You'll learn the strategy lifecycle, required methods, and integration
with indicators and risk management.

## Quick Start

Generate a new strategy scaffold:

```bash
poetry run python -m src.cli.scaffold_strategy my_strategy
```

This creates `src/strategy/my_strategy/` with template files ready to customize.

---

## Strategy Lifecycle

Understanding when each method is called helps you implement strategies correctly.

```text
┌─────────────────────────────────────────────────────────────────┐
│                     BACKTEST EXECUTION                          │
├─────────────────────────────────────────────────────────────────┤
│  1. LOAD         │  Strategy class imported and instantiated    │
│  2. VALIDATE     │  Contract checked (metadata, generate_signals)│
│  3. REGISTER     │  Strategy added to registry                  │
│  4. INDICATORS   │  Required indicators computed for all candles│
│  5. SIGNALS      │  generate_signals() called with candle data  │
│  6. SIMULATE     │  Trades executed based on signals            │
│  7. VISUALIZE    │  get_visualization_config() used for charts  │
└─────────────────────────────────────────────────────────────────┘
```

### Phase Details

1. **Load**: Your strategy module is imported. Class must be instantiable.
2. **Validate**: System checks for required `metadata` property and `generate_signals` method.
3. **Register**: Strategy added to registry for CLI access.
4. **Indicators**: Each indicator in `metadata.required_indicators` is computed.
5. **Signals**: Your `generate_signals()` is called with indicator-enriched candles.
6. **Simulate**: Engine processes your signals, applying stops and targets.
7. **Visualize**: If implemented, `get_visualization_config()` configures charts.

---

## Required Methods

### metadata (property)

Returns `StrategyMetadata` declaring strategy requirements.

```python
from src.strategy.base import StrategyMetadata

@property
def metadata(self) -> StrategyMetadata:
    """Return strategy metadata including required indicators."""
    return StrategyMetadata(
        name="my_strategy",           # Unique identifier (CLI: --strategy my_strategy)
        version="1.0.0",              # Semantic version
        required_indicators=[         # Indicators available on candles
            "ema20",                  # Access via candle.ema20
            "rsi14",                  # Access via candle.rsi14
            "atr14",                  # For stop/target calculation
        ],
        tags=["momentum", "trend"],   # Classification tags
        max_concurrent_positions=1,   # Position limit (None = unlimited)
    )
```

**Required fields**:

- `name`: Non-empty string, unique across all strategies
- `version`: Non-empty string, use semantic versioning
- `required_indicators`: Non-empty list of indicator names

### generate_signals(candles, parameters, direction)

Core method that produces trade signals from candle data.

```python
def generate_signals(
    self,
    candles: list,
    parameters: dict,
    direction: str = "BOTH",
) -> list:
    """Generate trade signals from candle data.

    Args:
        candles: List of Candle objects with indicators populated.
        parameters: Strategy parameters from config.
        direction: "LONG", "SHORT", or "BOTH".

    Returns:
        List of TradeSignal objects.
    """
    from src.models.signals import TradeSignal

    signals = []
    for candle in candles:
        # Access indicator values directly
        ema_fast = candle.ema20
        ema_slow = candle.ema50
        atr = candle.atr14

        # Your signal logic here
        if ema_fast > ema_slow and direction in ("LONG", "BOTH"):
            signals.append(TradeSignal(
                timestamp=candle.timestamp,
                direction="LONG",
                entry_price=candle.close,
                stop_price=candle.close - atr * 2,
                target_price=candle.close + atr * 4,
            ))

    return signals
```

---

## Optional Methods

### get_visualization_config()

Configure how indicators appear in backtest charts.

```python
from src.models.visualization_config import VisualizationConfig, IndicatorDisplayConfig

def get_visualization_config(self) -> VisualizationConfig | None:
    """Return visualization configuration."""
    return VisualizationConfig(
        price_overlays=[
            IndicatorDisplayConfig(name="ema20", color="#FFD700"),
            IndicatorDisplayConfig(name="ema50", color="#32CD32"),
        ],
        oscillators=[
            IndicatorDisplayConfig(name="rsi14", color="#00FFFF"),
        ],
    )
```

### scan_vectorized()

High-performance batch scanning with NumPy arrays.

```python
def scan_vectorized(
    self,
    close: np.ndarray,
    indicator_arrays: dict[str, np.ndarray],
    parameters: dict,
    direction: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Vectorized signal scanning for performance."""
    ema20 = indicator_arrays["ema20"]
    ema50 = indicator_arrays["ema50"]

    # NumPy vectorized comparison
    crossover = (ema20[:-1] <= ema50[:-1]) & (ema20[1:] > ema50[1:])
    indices = np.where(crossover)[0] + 1

    # Return (indices, stops, targets, sizes)
    return indices, stop_prices, target_prices, np.ones(len(indices))
```

---

## Indicator Integration

### Available Indicators

Request indicators by name in `metadata.required_indicators`:

| Indicator | Example                | Description                           |
| --------- | ---------------------- | ------------------------------------- |
| EMA       | `ema20`, `ema50`       | Exponential Moving Average (period N) |
| SMA       | `sma20`, `sma200`      | Simple Moving Average                 |
| RSI       | `rsi14`                | Relative Strength Index               |
| ATR       | `atr14`                | Average True Range                    |
| StochRSI  | `stoch_rsi`            | Stochastic RSI                        |
| Bollinger | `bb_upper`, `bb_lower` | Bollinger Bands                       |

### Accessing Indicators

Indicators are available as candle attributes:

```python
for candle in candles:
    print(candle.ema20)      # EMA value at this candle
    print(candle.rsi14)      # RSI value
    print(candle.timestamp)  # Candle timestamp
    print(candle.close)      # Close price
```

---

## Risk Management Integration

### Position Sizing

The `max_concurrent_positions` metadata field limits simultaneous trades:

```python
StrategyMetadata(
    # ...
    max_concurrent_positions=1,  # Only one trade at a time
    # max_concurrent_positions=None,  # Unlimited positions
)
```

### Stop Loss and Take Profit

Set via TradeSignal:

```python
TradeSignal(
    timestamp=candle.timestamp,
    direction="LONG",
    entry_price=candle.close,
    stop_price=candle.close - atr * 2,      # 2 ATR stop
    target_price=candle.close + atr * 4,    # 4 ATR target (2R)
)
```

### Risk Parameters

Access via `parameters` dict in generate_signals:

```python
stop_mult = parameters.get("stop_atr_multiplier", 2.0)
take_profit_r = parameters.get("take_profit_r", 2.0)
risk_percent = parameters.get("risk_percent", 0.01)  # 1% risk per trade
```

---

## Troubleshooting

### Validation Errors

**"Missing required method: generate_signals"**

- Ensure your class has `def generate_signals(self, candles, parameters):`

**"metadata.required_indicators must not be empty"**

- Add at least one indicator to the list: `["ema20"]`

**"metadata.name must be a non-empty string"**

- Set a unique name: `name="my_strategy"`

### No Signals Generated

1. Check indicator availability: `if hasattr(candle, 'ema20')`
2. Handle NaN values: `if not np.isnan(candle.ema20)`
3. Verify direction filter: `if direction in ("LONG", "BOTH")`

### Import Errors

Use conditional imports to avoid circular dependencies:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.signals import TradeSignal

def generate_signals(self, candles, parameters):
    from src.models.signals import TradeSignal  # Import here
    # ...
```

---

## Examples

See these strategies for reference:

- **Simple momentum**: `src/strategy/simple_momentum/` - Basic EMA crossover
- **Trend pullback**: `src/strategy/trend_pullback/` - Production strategy

Run a backtest:

```bash
poetry run python -m src.cli.run_backtest \
    --strategy simple_momentum \
    --data price_data/EURUSD_15m.csv \
    --manifest price_data/manifest.yaml
```
