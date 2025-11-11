# Contract: Ingestion Endpoint (Spec 009)

## Summary

Provides high‑performance ingestion of a single symbol's uniformly cadenced OHLCV candle data, producing a normalized core dataset with gap synthesis and duplicate resolution. Indicators are explicitly excluded.

## Endpoint

| Method | Path       | Auth | Idempotent | Streaming |
|--------|------------|------|------------|-----------|
| POST   | /ingest    | N/A  | Yes (same input yields same output) | No |

## Request

### Query / Body Parameters

| Name | In | Type | Required | Constraints | Description |
|------|----|------|----------|-------------|-------------|
| path | body | string (filepath) | Yes | Existing readable CSV file | Absolute or repo‑relative path to raw candle file |
| timeframe_minutes | body | int | Yes | >0 | Expected cadence (e.g., 1) for validation & gap synthesis |
| mode | body | enum {columnar, iterator} | Yes | One of allowed | Output representation format (FR-008) |
| downcast | body | bool | No | default false | Apply numeric type downcasting for memory saving (FR-011) |

### File Format Expectations

| Column | Required | Notes |
|--------|----------|-------|
| timestamp | Yes | UTC ISO8601 or epoch seconds; MUST be UTC (FR-014) |
| open | Yes | Numeric |
| high | Yes | Numeric |
| low | Yes | Numeric |
| close | Yes | Numeric |
| volume | Yes | Numeric |
| (others) | No | Ignored unless promoted later |

## Processing Stages

1. Read -> raw frame
2. Sort -> chronological order (FR-003)
3. Detect duplicates -> log & remove (FR-003)
4. Cadence validation -> error if >2% missing intervals (FR-012)
5. Gap synthesis (FR-004)
6. Column restriction -> core schema (FR-001)
7. Optional downcast (FR-011)
8. Metrics collection (FR-015, FR-016)
9. Mode adaptation (columnar vs iterator) (FR-008, FR-009)

## Response

Content-Type: application/json (metadata) + in‑memory structure (DataFrame or iterator) not serialized fully here.

### JSON Metadata Schema

| Field | Type | Description |
|-------|------|-------------|
| metrics.total_rows_input | int | Raw rows before processing |
| metrics.total_rows_output | int | Rows after gap fill & duplicate removal |
| metrics.gaps_inserted | int | Count of synthetic gap rows |
| metrics.duplicates_removed | int | Count of discarded duplicates |
| metrics.runtime_seconds | float | Total wall-clock runtime |
| mode | string | Echo of request.mode |
| downcast_applied | bool | Echo / computed result |
| acceleration_backend | string | {arrow,pandas} chosen path (FR-025) |
| stretch_runtime_candidate | bool | True if runtime ≤90s (FR-027 / SC-012) |

### Data Structure (In-Memory)

| Column | Type | Notes |
|--------|------|-------|
| timestamp_utc | datetime64[ns, UTC] | Sorted, unique |
| open | float32/64 | Gap rows derived from prev close |
| high | float32/64 | = open for gap rows |
| low | float32/64 | = open for gap rows |
| close | float32/64 | Forward-filled for gap rows |
| volume | float32/64 | 0.0 for gap rows |
| is_gap | bool | True on synthetic rows |

**Columnar Mode (`mode="columnar"`):**

Returns the full DataFrame with all 7 core columns. Optimized for:

- Batch processing and vectorized operations
- Direct indicator enrichment
- Memory-efficient storage (especially with downcast=True)
- Performance: ≥25% faster than iterator mode (SC-004)

**Iterator Mode (`mode="iterator"`):**

Returns a `DataFrameIteratorWrapper` that yields `CoreCandleRecord` objects row-by-row:

```python
@dataclass(frozen=True)
class CoreCandleRecord:
    """Immutable single candle record from iterator mode.
    
    Attributes:
        timestamp_utc: UTC timestamp of the candle
        open: Opening price
        high: Highest price during the interval
        low: Lowest price during the interval
        close: Closing price
        volume: Trading volume (0.0 for synthetic gap rows)
        is_gap: True if this is a synthetic gap-fill row
    """
    timestamp_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_gap: bool
```

Iterator mode characteristics:

- Streaming consumption: process one candle at a time
- Lower memory footprint for large datasets
- Suitable for sequential processing pipelines
- Can be iterated multiple times (creates new iterator each time)
- Implements `__len__()` for size queries without full iteration

Example usage:

```python
# Columnar mode (default)
result = ingest_ohlcv_data(path="data.csv", timeframe_minutes=1, mode="columnar")
df = result.data  # pandas DataFrame
print(df.head())

# Iterator mode
result = ingest_ohlcv_data(path="data.csv", timeframe_minutes=1, mode="iterator")
for candle in result.data:
    print(f"{candle.timestamp_utc}: O={candle.open} H={candle.high}")
```

## Errors

| Code | HTTP | Condition | Message Pattern |
|------|------|-----------|-----------------|
| INGEST_NONUTC | 400 | Non-UTC timestamp detected | "Non-UTC timestamps detected: ..." |
| INGEST_MISSING_COLS | 400 | Required columns absent | "Missing required columns: open, high, ..." |
| INGEST_CADENCE_DEVIATION | 422 | >2% missing intervals pre-gap | "Cadence deviation exceeds tolerance (...%)" |
| INGEST_FILE_NOT_FOUND | 404 | Path unreadable | "Input file not found: ..." |
| INGEST_BAD_MODE | 400 | Mode not in allowed set | "Invalid mode: ..." |
| INGEST_EMPTY | 200 | Empty input file | metrics reflect zero rows |
| INGEST_ACCEL_WARN | 200 | Columnar backend unavailable | Warning emitted in logs (FR-025) |

## Performance Metrics & Success Criteria Mapping

| Metric | Source | Success Criteria |
|--------|--------|------------------|
| runtime_seconds | metrics.runtime_seconds | SC-001 (≤120s), SC-012 (≤90s stretch) |
| throughput_rows_per_sec | derived | SC-002 (≥3.5M rows/min) |
| gaps_inserted | metrics.gaps_inserted | SC-005 correctness |
| core_hash_stable | test harness | SC-010 immutability |

## Example Request (Pseudo-Python)

```python
result = ingest(
    path="price_data/raw/eurusd/eurusd_2024.csv",
    timeframe_minutes=1,
    mode="columnar",
    downcast=True,
)
core_df = result.data  # DataFrame
print(result.metrics.runtime_seconds)
```

## Non-Functional Constraints

- ≤5 progress updates (SC-008)
- No per-row loops in critical path (FR-023 / SC-007)
- Indicator logic excluded (FR-005, FR-017)
- Backend fallback emits warning (FR-025)

## Extensibility Hooks

| Hook | Purpose |
|------|---------|
| acceleration_backend selection | Future GPU insertion without contract change (FR-028) |
| mode enum | Potential future streaming mode |
| schema restrict step | Add `symbol` column for multi-symbol (FR-022) |

## Validation Checklist

- [ ] Columns restricted to core set
- [ ] Runtime threshold met
- [ ] Duplicate resolution deterministic
- [ ] Gap count matches expected missing intervals
- [ ] Acceleration backend reported
- [ ] No indicator columns present
