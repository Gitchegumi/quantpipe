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

```python
from trading_strategies.backtest.enrich import enrich

selected = ["ema20", "ema50", "atr14"]

enriched = enrich(
    core_ref=result,
    indicators=selected,
    params={"ema": {"method": "exponential"}},
    strict=True,
)

enriched_df = enriched.enriched
print("Applied:", enriched.indicators_applied)
print("Columns added:", set(enriched_df.columns) - set(result.data.columns))
```

Validation:

* Only requested columns appear (SC-003)
* Core hash unchanged (SC-010)
* Unknown indicator would raise before partial work if strict=True (FR-007)

## 4. Handling Unknown Indicators (Non-Strict)

```python
soft = enrich(
    core_ref=result,
    indicators=["ema20", "bogus_indicator"],
    strict=False,
)
print("Applied:", soft.indicators_applied)
print("Failed:", soft.failed_indicators)
```

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

```python
from trading_strategies.backtest.indicators.registry import register_indicator

# Example: Simple rate-of-change indicator

def compute_roc(df, period=1):
    close = df["close"].astype("float64")
    return {f"roc{period}": (close / close.shift(period) - 1.0).fillna(0.0)}

register_indicator(
    name="roc1",
    requires=["close"],
    provides=["roc1"],
    compute=compute_roc,
    version="1.0.0",
)

custom = enrich(core_ref=result, indicators=["roc1"], strict=True)
print("Custom Applied:", custom.indicators_applied)
```

Registry rules:

* Must declare `requires` dependencies
* `compute` returns dict of column_name -> Series
* Version string used for audit

## 7. Immutability Verification

```python
import hashlib

before_hash = hashlib.sha256(result.data[["timestamp_utc","open","high","low","close","volume","is_gap"]].to_string().encode()).hexdigest()
_ = enrich(core_ref=result, indicators=["ema20"], strict=True)
after_hash = hashlib.sha256(result.data[["timestamp_utc","open","high","low","close","volume","is_gap"]].to_string().encode()).hexdigest()
assert before_hash == after_hash, "Core dataset mutated!"
```

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
