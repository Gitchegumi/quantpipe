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

This guide shows how to add a new technical indicator to the system.

#### Step 1: Create the Computation Function

Create a new file in `src/indicators/` (e.g., `src/indicators/roc.py`):

```python
"""Rate of Change (ROC) indicator implementation."""

import pandas as pd


def compute_roc(df: pd.DataFrame, period: int = 1) -> dict[str, pd.Series]:
    """Compute Rate of Change indicator.
    
    ROC measures the percentage change in price over a given period.
    
    Args:
        df: DataFrame with 'close' column
        period: Number of periods to look back (default: 1)
        
    Returns:
        Dictionary with single Series: roc{period}
        
    Raises:
        ValueError: If 'close' column missing or period < 1
    """
    # Validate inputs
    if "close" not in df.columns:
        msg = "ROC indicator requires 'close' column"
        raise ValueError(msg)
    if period < 1:
        msg = f"ROC period must be ≥1, got {period}"
        raise ValueError(msg)
    
    # Compute indicator (vectorized)
    close = df["close"].astype("float64")
    roc = (close / close.shift(period) - 1.0).fillna(0.0)
    
    return {f"roc{period}": roc}
```

**Key Requirements:**

- **Type hints**: All parameters and return type annotated
- **Docstring**: Complete PEP 257 docstring with Args, Returns, Raises
- **Validation**: Check required columns present, validate parameters
- **Vectorization**: Use pandas operations (no row loops)
- **Immutability**: Never mutate input DataFrame
- **NaN handling**: Return reasonable defaults or NaN for invalid periods

#### Step 2: Add Tests

Create test file `tests/unit/test_roc_indicator.py`:

```python
"""Unit tests for ROC indicator."""

import pandas as pd
import pytest

from src.indicators.roc import compute_roc


def test_roc_basic():
    """Test ROC basic calculation."""
    df = pd.DataFrame({
        "close": [100.0, 110.0, 105.0, 115.0]
    })
    result = compute_roc(df, period=1)
    
    assert "roc1" in result
    assert len(result["roc1"]) == 4
    # First value should be 0 (no prior value)
    assert result["roc1"].iloc[0] == 0.0
    # Second value: (110-100)/100 = 0.10
    assert result["roc1"].iloc[1] == pytest.approx(0.10)


def test_roc_missing_column():
    """Test ROC raises error for missing close column."""
    df = pd.DataFrame({"open": [100.0, 110.0]})
    
    with pytest.raises(ValueError, match="requires 'close' column"):
        compute_roc(df, period=1)


def test_roc_invalid_period():
    """Test ROC raises error for invalid period."""
    df = pd.DataFrame({"close": [100.0, 110.0]})
    
    with pytest.raises(ValueError, match="period must be ≥1"):
        compute_roc(df, period=0)
```

#### Step 3: Register the Indicator

Option A: **Manual Registration** (for testing/prototyping):

```python
from src.indicators.registry import register_indicator
from src.indicators.roc import compute_roc

register_indicator(
    name="roc1",
    requires=["close"],
    provides=["roc1"],
    compute=lambda df: compute_roc(df, period=1),
    version="1.0.0"
)
```

Option B: **Built-in Registration** (recommended for production):

Add to `src/indicators/builtin/__init__.py`:

```python
from src.indicators.roc import compute_roc

# ... existing imports ...

def register_builtin_indicators():
    """Register all built-in indicators."""
    # ... existing registrations ...
    
    # Rate of Change (ROC)
    register_indicator(
        name="roc1",
        requires=["close"],
        provides=["roc1"],
        compute=lambda df: compute_roc(df, period=1),
        version="1.0.0"
    )
    
    register_indicator(
        name="roc5",
        requires=["close"],
        provides=["roc5"],
        compute=lambda df: compute_roc(df, period=5),
        version="1.0.0"
    )
```

#### Step 4: Use the Indicator

```python
from src.io.ingestion import ingest_ohlcv_data
from src.indicators.enrich import enrich

# Ingest core data
result = ingest_ohlcv_data(
    path="price_data/raw/eurusd/eurusd_2024.csv",
    timeframe_minutes=1
)

# Enrich with ROC indicator
enriched = enrich(
    core_ref=result,
    indicators=["roc1", "roc5"],
    strict=True
)

# Access computed indicators
df = enriched.to_dataframe()
print(df[["timestamp_utc", "close", "roc1", "roc5"]].head())
```

#### Step 5: Document in Registry

Add entry to `src/indicators/README.md` Built-in Indicators section:

```markdown
- **ROC** (Rate of Change): `roc1`, `roc5`
```

### Indicator Development Checklist

- [ ] Computation function with complete docstring
- [ ] Type hints for all parameters and return
- [ ] Input validation (columns, parameters)
- [ ] Vectorized implementation (no row loops)
- [ ] Unit tests (basic, edge cases, errors)
- [ ] Registration in builtin or manual
- [ ] Documentation in README.md
- [ ] Verified with `ruff check` and `pylint` (≥8.0)

### Common Pitfalls

1. **Mutating input DataFrame**: Always create new Series, never modify input
2. **Row loops**: Use `.shift()`, `.rolling()`, `.ewm()` instead of `.iterrows()`
3. **Missing validation**: Always check required columns exist
4. **Poor NaN handling**: Consider what NaN means for your indicator
5. **No tests**: Indicators without tests will break

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
