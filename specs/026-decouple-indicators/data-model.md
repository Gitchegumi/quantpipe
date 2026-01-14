# Data Model: Decouple Indicator Registration

## API Schema Changes

### `src.strategy.base.Strategy`

New method signature:

```python
def get_custom_indicators(self) -> dict[str, Callable[[pl.DataFrame, Any], pl.DataFrame]]:
    """
    Define strategy-specific custom indicators.

    Returns:
        Dictionary mapping indicator name to calculation function.
        Function signature: (df: pl.DataFrame, **kwargs) -> pl.DataFrame
    """
    return {}
```

### `src.indicators.dispatcher.calculate_indicators`

Updated signature:

```python
def calculate_indicators(
    df: pl.DataFrame,
    indicators: list[str],
    overrides: dict[str, dict[str, Any]] | None = None,
    custom_registry: dict[str, Callable] | None = None,  # [NEW]
) -> pl.DataFrame:
    ...
```

## Entity Relationships

1. **Strategy** owns **Custom Indicators**.
2. **BacktestEngine** extracts **Custom Indicators** from **Strategy**.
3. **BacktestEngine** passes **Custom Indicators** to **IndicatorDispatcher**.
4. **IndicatorDispatcher** resolves names: **Custom Indicators** (check first) -> **Global Registry** (check second).

## Validation

- Custom indicator names MUST follow standard regex `^[a-z_]+(\(.*\))?$`.
- Collisions with global registry are ALLOWED (strategy overrides global).
