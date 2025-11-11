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

### Contract Details (FR-019)

All indicators MUST adhere to the following contract specifications:

#### **Name Identifier**

- **Format**: Lowercase alphanumeric + underscore only (e.g., `ema20`, `stoch_rsi`)
- **Uniqueness**: No two indicators may share the same name
- **Validation**: Enforced by registry at registration time

#### **Required Input Columns**

Indicators declare their dependencies via the `requires` field:

- **Core columns**: Base OHLCV columns (`open`, `high`, `low`, `close`, `volume`, `timestamp`)
- **Gap column**: `is_gap` (boolean flag for synthetic gap rows)
- **Other indicators**: Can depend on output of previously computed indicators
- **Example**: `["close", "high", "low"]` for ATR computation

#### **Provided Output Columns**

Indicators declare their outputs via the `provides` field:

- **Must match**: Column names returned by `compute()` function
- **Naming convention**: Use indicator name as prefix (e.g., `ema20`, `atr14`, `stochrsi_k`)
- **Type guarantee**: All outputs must be numeric (float64 or int64)
- **Example**: `["ema20"]` for 20-period EMA

#### **Parameters**

Indicators accept configuration parameters via the `compute()` function signature:

- **Default values**: All parameters must have defaults (e.g., `period=20`)
- **Type hints**: Strongly recommended for clarity
- **Example**: `def compute_ema(df, period: int = 20) -> dict[str, pd.Series]:`

#### **Computation Function Contract**

The `compute()` function must satisfy:

1. **Input**: Receives pandas DataFrame with required columns
2. **Output**: Returns `Dict[str, pd.Series]` where keys match `provides` field
3. **Immutability**: MUST NOT mutate the input DataFrame
4. **NaN handling**: MAY return NaN for invalid periods (e.g., first N rows)
5. **Vectorization**: SHOULD use vectorized operations (no explicit row loops)
6. **Deterministic**: Same input MUST produce same output

**Example**:

```python
def compute_ema(df: pd.DataFrame, period: int = 20) -> dict[str, pd.Series]:
    """Compute Exponential Moving Average.
    
    Args:
        df: DataFrame with 'close' column
        period: EMA period (default: 20)
        
    Returns:
        Dictionary with single 'ema{period}' Series
    """
    close = df["close"].astype("float64")
    ema = close.ewm(span=period, adjust=False).mean()
    return {f"ema{period}": ema}
```

#### **Version Semantic**

- **Format**: Semantic versioning `X.Y.Z`
- **Increment rules**:
  - **X (major)**: Breaking change to computation logic
  - **Y (minor)**: New parameters or non-breaking enhancement
  - **Z (patch)**: Bug fix without logic change
- **Audit trail**: Version logged in enrichment results

#### **Error Handling**

Indicators SHOULD raise descriptive errors for:

- **Missing columns**: If required columns absent from DataFrame
- **Invalid parameters**: If parameter values out of valid range
- **Type errors**: If input columns have wrong dtype

**Example**:

```python
if "close" not in df.columns:
    raise ValueError("EMA requires 'close' column")
if period < 1:
    raise ValueError(f"EMA period must be ≥1, got {period}")
```

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
