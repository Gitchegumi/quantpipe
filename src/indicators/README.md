# Indicators Package

This package provides a pluggable indicator registry system for selective computation of technical indicators on ingested market data.

## Architecture

The indicators package is designed with separation of concerns:

- **Core ingestion** (`src/io/ingestion.py`): Produces only normalized OHLCV + `is_gap` data
- **Indicator enrichment** (`src/indicators/enrich.py`): Computes only requested indicators
- **Registry system** (`src/indicators/registry/`): Manages indicator specifications and dependencies

## Built-in Indicators

The following indicators are available by default:

- **EMA** (Exponential Moving Average): `ema20`, `ema50`, `ema200`
- **ATR** (Average True Range): `atr14`
- **StochRSI** (Stochastic RSI): `stochrsi`

## Usage

### Basic Enrichment

```python
from trading_strategies.backtest.ingest import ingest
from trading_strategies.backtest.enrich import enrich

# Ingest core data
result = ingest(
    path="price_data/raw/eurusd/eurusd_2024.csv",
    timeframe_minutes=1,
    mode="columnar"
)

# Enrich with selected indicators
enriched = enrich(
    core_ref=result,
    indicators=["ema20", "ema50", "atr14"],
    strict=True
)
```

### Adding Custom Indicators

To add a new indicator:

1. **Define the computation function**:

    ```python
    def compute_roc(df, period=1):
        """Compute rate of change."""
        close = df["close"].astype("float64")
        return {f"roc{period}": (close / close.shift(period) - 1.0).fillna(0.0)}
    ```

2. **Register the indicator**:

    ```python
    from trading_strategies.backtest.indicators.registry import register_indicator

    register_indicator(
        name="roc1",
        requires=["close"],
        provides=["roc1"],
        compute=compute_roc,
        version="1.0.0"
    )
    ```

3. **Use it in enrichment**:

    ```python
    enriched = enrich(
        core_ref=result,
        indicators=["roc1"],
        strict=True
    )
    ```

## Indicator Contract

Each indicator must provide:

- **name** (str): Unique identifier
- **requires** (List[str]): Dependencies (core columns or other indicators)
- **provides** (List[str]): Output column names
- **compute** (Callable): Function that takes DataFrame and returns Dict[str, Series]
- **version** (str): Semantic version for audit trail

## Dependency Resolution

The registry automatically resolves indicator dependencies using topological sort.
For example, if indicator `stochrsi` requires `rsi14`, and `rsi14` requires `close`,
the registry will compute them in order: `rsi14` → `stochrsi`.

## Error Handling

### Strict Mode (default: False)

- `strict=True`: Abort immediately on unknown indicator
- `strict=False`: Accumulate failures and return partial results

### Example

```python
# Non-strict: continue on unknown indicators
enriched = enrich(
    core_ref=result,
    indicators=["ema20", "bogus_indicator"],
    strict=False
)
print(enriched.indicators_applied)  # ["ema20"]
print(enriched.failed_indicators)   # ["bogus_indicator"]
```

## Immutability Guarantee

The enrichment process **never mutates** the core dataset. A hash verification
is performed to ensure core columns remain unchanged.

## Performance Considerations

- **Batch indicators**: Request multiple indicators together to minimize passes
- **Vectorization**: All built-in indicators use vectorized operations (no row loops)
- **Selective computation**: Only requested indicators are computed

## Testing

See `tests/unit/test_indicator_registry.py` for registry tests and
`tests/unit/test_enrich_*.py` for enrichment behavior tests.

## Future Enhancements

- Dynamic plugin discovery from filesystem
- GPU-accelerated indicator computation
- Parallel indicator computation for independent indicators
- Indicator result caching
