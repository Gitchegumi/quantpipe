# Quickstart: Optimized & Decoupled Ingestion (Spec 009)

> Goal: Demonstrate fast core ingestion (P1), opt‑in indicator enrichment (P2), and dual output modes (P3) with performance measurement.

## Prerequisites

* Python 3.11 environment (Poetry managed)
* Raw candle CSV (uniform cadence, UTC timestamps) located under `price_data/raw/<symbol>/...`
* Baseline dataset ~6.9M rows (for timing illustration)
* Ensure feature branch `009-optimize-ingestion` checked out

## 1. Core Ingestion (Fast Columnar Mode)

**Performance Note**: The implemented ingestion pipeline targets ≤120 seconds for ~6.9M rows (SC-001), with a stretch goal of ≤90 seconds (SC-012). All operations use vectorized pandas/numpy to avoid per-row iteration. For performance validation, run `poetry run pytest tests/performance/benchmark_ingestion.py -m performance`.

```python
from trading_strategies.backtest.ingest import ingest

result = ingest(
    path="price_data/raw/eurusd/eurusd_2024.csv",
    timeframe_minutes=1,
    mode="columnar",      # High-performance DataFrame path
    downcast=True,         # Optional memory reduction
)

core_df = result.data
print("Runtime (s):", result.metrics.runtime_seconds)
print("Rows out:", result.metrics.total_rows_output)
print("Gaps inserted:", result.metrics.gaps_inserted)
```

Checklist validation:

* Core columns only: `timestamp_utc, open, high, low, close, volume, is_gap`
* Runtime ≤ 120s (SC-001) baseline target for 6.9M rows
* Throughput ≥3.45M rows/min expected
* ≤5 progress updates (SC-008)
* All operations vectorized (no `.iterrows()` / `.itertuples()`)

**Actual Implementation**: The current code uses `src.io.ingestion.ingest_ohlcv_data()` which provides:

* Vectorized gap detection via numpy diff operations
* Vectorized deduplication with pandas `drop_duplicates()`
* Comprehensive metrics: runtime, throughput, gaps, duplicates
* Static analysis enforcement (no per-row loops)

See `docs/performance.md` for detailed performance documentation.

## 2. Iterator Mode (Legacy Compatibility)

```python
result_iter = ingest(
    path="price_data/raw/eurusd/eurusd_2024.csv",
    timeframe_minutes=1,
    mode="iterator",      # Materialized object sequence
    downcast=False,
)

for i, candle in enumerate(result_iter.data):
    if i < 3:
        print(candle)
    else:
        break
```

Expectations:

* Objects yield attributes matching schema
* Slower than columnar (FR-009) but enables drop-in legacy usage

## 3. Indicator Enrichment (Opt-In)

**Actual Implementation**: Uses `src.io.enrich.enrich()` function with the following final API:

```python
from src.io.enrich import enrich

# Basic enrichment with multiple indicators
enrichment_result = enrich(
    core_ref=result.data,  # Pass the DataFrame directly, not the IngestionResult
    indicators=["ema20", "ema50", "atr14"],
    strict=True,  # Fast-fail on unknown indicators
)

enriched_df = enrichment_result.enriched
print("Applied:", enrichment_result.indicators_applied)
print("Runtime (s):", enrichment_result.runtime_seconds)
print("New columns:", [c for c in enriched_df.columns if c not in result.data.columns])
```

**Available Built-in Indicators:**

* `ema20` - 20-period Exponential Moving Average
* `ema50` - 50-period Exponential Moving Average
* `atr14` - 14-period Average True Range
* `stoch_rsi` - Stochastic RSI oscillator

**With Custom Parameters:**

```python
enrichment_result = enrich(
    core_ref=result.data,
    indicators=["ema20"],
    params={"ema20": {"period": 30}},  # Override default period
    strict=True,
)
```

Validation:

* Only requested columns appear (SC-003) ✓
* Core hash unchanged (SC-010) ✓
* Unknown indicator raises `UnknownIndicatorError` before any computation if `strict=True` (FR-007) ✓
* Returns `EnrichmentResult` with `.enriched` DataFrame, `.indicators_applied` list, `.failed_indicators` list, `.runtime_seconds` float

## 4. Handling Unknown Indicators (Non-Strict)

**Non-strict mode** collects failures and continues with valid indicators:

```python
from src.io.enrich import enrich

enrichment_result = enrich(
    core_ref=result.data,
    indicators=["ema20", "bogus_indicator", "atr14"],
    strict=False,
)

print("Applied:", enrichment_result.indicators_applied)  # ['ema20', 'atr14']
print("Failed:", enrichment_result.failed_indicators)    # [('bogus_indicator', UnknownIndicatorError(...))]

# Only successful indicators are added as columns
assert "ema20" in enrichment_result.enriched.columns
assert "atr14" in enrichment_result.enriched.columns
assert "bogus_indicator" not in enrichment_result.enriched.columns
```

**Behavior:**

* Valid indicators compute successfully
* Invalid indicators logged as warnings
* `failed_indicators` list contains tuples of `(indicator_name, exception)`
* No partial computation - each indicator is atomic

## 5. Measuring Performance (Harness Example)

Minimal ad-hoc timing (replace with formal test harness integration):

```python
import time
start = time.perf_counter()
result_perf = ingest(
    path="price_data/raw/eurusd/eurusd_2024.csv",
    timeframe_minutes=1,
    mode="columnar",
    downcast=True,
)
elapsed = time.perf_counter() - start
rows = result_perf.metrics.total_rows_output
throughput = rows / elapsed
print(f"Elapsed: {elapsed:.2f}s, Throughput: {throughput:.0f} rows/s")
if elapsed <= 90:
    print("Stretch goal candidate (SC-012)")
```

## 6. Registry Operations (Pluggable Indicators)

**Actual Implementation**: Uses `src.io.indicators.registry` for registering custom indicators.

```python
from src.io.indicators.registry import register_indicator
import pandas as pd

# Example: Simple rate-of-change indicator
def compute_roc(df: pd.DataFrame, period: int = 1) -> dict[str, pd.Series]:
    """Compute rate of change over specified period."""
    close = df["close"].astype("float64")
    roc_series = (close / close.shift(period) - 1.0).fillna(0.0)
    return {f"roc{period}": roc_series}

# Register the indicator
register_indicator(
    name="roc1",
    requires=["close"],
    provides=["roc1"],
    compute=compute_roc,
    version="1.0.0",
)

# Use the custom indicator
from src.io.enrich import enrich
custom_result = enrich(
    core_ref=result.data,
    indicators=["roc1"],
    params={"roc1": {"period": 1}},
    strict=True,
)
print("Custom Applied:", custom_result.indicators_applied)
assert "roc1" in custom_result.enriched.columns
```

Registry rules:

* Must declare `requires` dependencies (list of column names needed)
* Must declare `provides` (list of column names created)
* `compute` function signature: `(df: pd.DataFrame, **params) -> dict[str, pd.Series]`
* Returns dict mapping column name → pandas Series
* Version string used for audit trail
* All parameters passed via `params` dict in `enrich()` call

## 7. Immutability Verification

**Actual Implementation**: Core hash verification ensures enrichment never mutates the input DataFrame.

```python
from src.io.hash_utils import compute_dataframe_hash

CORE_COLUMNS = ["timestamp_utc", "open", "high", "low", "close", "volume", "is_gap"]

# Hash before enrichment
before_hash = compute_dataframe_hash(result.data, CORE_COLUMNS)

# Perform enrichment
from src.io.enrich import enrich
enrichment_result = enrich(
    core_ref=result.data,
    indicators=["ema20", "ema50", "atr14"],
    strict=True,
)

# Hash after enrichment (on the enriched DataFrame)
after_hash = compute_dataframe_hash(enrichment_result.enriched, CORE_COLUMNS)

# Verify core columns unchanged
assert before_hash == after_hash, "Core dataset mutated!"
print("✓ Core immutability verified")
```

**How it works:**

* `compute_dataframe_hash()` creates a deterministic hash of specified columns
* Enrichment creates a copy of the input DataFrame (`.copy()`)
* New indicator columns added only to the copy
* Original DataFrame remains untouched
* Comprehensive unit tests validate this behavior (see `tests/unit/test_enrich_immutability.py`)

## 8. Failure Scenarios Quick Table

| Scenario | Trigger | Expected |
|----------|---------|----------|
| Non-UTC timestamps | Input file tz != UTC | Ingestion error (abort) |
| Cadence deviation > tolerance | >2% missing intervals | Ingestion error before gap fill |
| Unknown indicator strict | Name not in registry | Enrichment error (no partial columns) |
| Duplicate indicator name | Provided twice | Validation error |
| Core mutation attempt | Indicator modifies core | Exception / test failure |

## 9. Performance Tuning Tips

* Prefer columnar mode for bulk simulations
* Enable Arrow backend (auto-detected) for speed; logs warn if fallback (FR-025)
* Use downcast only after confirming indicators tolerate reduced precision
* Batch enrichment (request multiple indicators together) to minimize repeated passes

## 10. Next Steps / Extensions

* Add multi-symbol ingestion extension point (`symbol` column)
* Introduce GPU acceleration path (optional, FR-028 future)
* Formalize benchmark harness under `tests/performance/`

## Validation Checklist Snapshot

* [ ] P1: Fast ingestion ≤120s baseline
* [ ] P2: Indicator enrichment selective & immutable core
* [ ] P3: Dual modes functional (iterator vs columnar)
* [ ] Stretch: ≤90s candidate verified

---
Generated as part of Phase 1 artifacts for Spec 009. Aligns with functional requirements FR-001..FR-028 and success criteria SC-001..SC-012.
