# Data Model: Optimize & Decouple Ingestion (Spec 009)

## Entities

### CoreCandleRecord

| Field | Type | Constraints | Notes |
|-------|------|------------|-------|
| timestamp_utc | datetime (UTC) | NOT NULL, strictly increasing | Source ordering enforced; duplicates removed (first kept) |
| open | float64 (or float32 if downcast) | NOT NULL | Filled for gaps using prev close |
| high | float64 | NOT NULL | Equals open for gap synthetic rows |
| low | float64 | NOT NULL | Equals open for gap synthetic rows |
| close | float64 | NOT NULL | Forward-filled for gap rows |
| volume | float64 | NOT NULL | 0.0 for gap synthetic rows |
| is_gap | bool | NOT NULL | True on synthetic inserted rows |

Validation Rules:

* UTC enforcement: reject non-UTC timestamps.
* Duplicate timestamp resolution: retain first; log others.
* Cadence consistency: deviation >2% missing intervals triggers error (prior to gap fill).

### IngestionResult

| Field | Type | Constraints | Notes |
|-------|------|------------|-------|
| data | DataFrame[CoreCandleRecord] | NOT NULL | Core output (immutable contract) |
| metrics.total_rows_input | int | >=0 | Raw row count prior to filtering |
| metrics.total_rows_output | int | >=0 | After gap fill + duplicate removal |
| metrics.gaps_inserted | int | >=0 | Count of gap synthetic rows |
| metrics.duplicates_removed | int | >=0 | Count of discarded duplicates |
| metrics.runtime_seconds | float | >0 | Wall-clock runtime |
| mode | enum {columnar, iterator} | NOT NULL | Selected output mode |
| downcast_applied | bool | NOT NULL | Memory optimization flag |

### IndicatorEnrichmentRequest

| Field | Type | Constraints | Notes |
|-------|------|------------|-------|
| indicators | list[str] | unique, non-empty names | Registry validates existence |
| params | dict[str, Any] | optional | Periods, smoothing factors, etc. |
| strict | bool | default False | If True, unknown indicator error aborts immediately |

### EnrichedDataset

| Field | Type | Constraints | Notes |
|-------|------|------------|-------|
| core | DataFrame[CoreCandleRecord] | NOT NULL | Original reference (unchanged) |
| enriched | DataFrame | NOT NULL | New DataFrame with indicator columns |
| indicators_applied | list[str] | subset of requested | Successfully computed indicators |
| failed_indicators | list[str] | empty if strict | Names that failed (only if strict=False) |

### PerformanceMetrics

| Field | Type | Constraints | Notes |
|-------|------|------------|-------|
| run_id | uuid | unique | For reproducibility logs |
| rows | int | >=0 | Input size |
| runtime_seconds | float | >0 | Timing measurement |
| throughput_rows_per_sec | float | >0 | Derived metric |
| memory_peak_mb | float | >0 | Peak resident memory sample |
| acceleration_backend | enum {arrow, pandas} | NOT NULL | Which path used |

## Relationships

* IngestionResult.data -> feeds IndicatorEnrichmentRequest.indicators processing.
* EnrichedDataset.core is pointer (not copied) to IngestionResult.data ensuring immutability.
* PerformanceMetrics captured per ingestion run and referenced in logs/tests.

## State Transitions

1. RawFrame (CSV read) -> OrderedFrame (sorted, duplicates tagged) -> GapFilledFrame (gaps inserted) -> CoreFrame (schema restricted) -> IngestionResult.
2. CoreFrame + IndicatorEnrichmentRequest -> EnrichedDataset.

## Derived Fields

* throughput_rows_per_sec = rows / runtime_seconds
* gaps_inserted = (expected_intervals - original_intervals) computed during gap fill.

## Error Conditions

| Condition | Trigger | Handling |
|-----------|--------|----------|
| Non-UTC timestamp | Any timestamp timezone != UTC | Raise ingestion error (abort) |
| Missing required columns | Absent OHLCV columns | Raise ingestion error |
| Excess cadence deviation | Missing intervals >2% before gap insertion | Raise ingestion error |
| Unknown indicator | Not in registry | If strict=True raise; else accumulate failed list |
| Duplicate indicator name | Provided twice in request | Raise validation error |
| Mutation attempt | Enrichment tries to alter core columns | Test failure / raise exception |

## Immutability Contract

* CoreFrame columns hash (timestamp_utc, open, high, low, close, volume, is_gap) MUST remain unchanged after enrichment.

## Extensibility Notes

* Multi-symbol future: extend CoreCandleRecord with `symbol` field; adjust ordering to (symbol, timestamp_utc).
* GPU path: PerformanceMetrics.acceleration_backend may add `gpu` value; runtime sampling unchanged.

## OpenAPI-like Schemas (Refer to contracts for full definitions)

* POST /ingest (params: path, timeframe_minutes, mode, downcast) -> IngestionResult
* POST /enrich (body: indicators[], params) -> EnrichedDataset

(Full contract definitions in `contracts/`.)
