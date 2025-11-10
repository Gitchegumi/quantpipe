# Contract: Indicator Enrichment Endpoint (Spec 009)

## Summary

Computes ONLY requested indicators on an existing immutable core ingestion result, returning a separate enriched dataset while preserving original core columns unchanged.

## Endpoint

| Method | Path    | Auth | Idempotent | Streaming |
|--------|---------|------|------------|-----------|
| POST   | /enrich | N/A  | Yes (pure function over inputs) | No |

## Request

### Body Parameters

| Name | Type | Required | Constraints | Description |
|------|------|----------|-------------|-------------|
| core_ref | DataFrame | Yes | MUST contain core columns | Source core dataset (FR-018 immutability) |
| indicators | list[str] | Yes | unique names | Indicator identifiers to compute (FR-006) |
| params | dict[str, dict] | No | optional | Per-indicator parameter overrides |
| strict | bool | No | default True | Unknown names abort early if True (FR-007) |

**Implementation Notes:**

* `core_ref` accepts a pandas DataFrame directly (not IngestionResult wrapper)
* `params` structure: `{"indicator_name": {"param_key": value}}` for per-indicator tuning
* `strict=True` (default) raises `UnknownIndicatorError` before any computation
* `strict=False` collects failures and continues with valid indicators

### Indicator Registry Contract

| Field | Type | Notes |
|-------|------|-------|
| name | str | Unique identifier exposed to API |
| requires | list[str] | Core columns or other indicators required |
| provides | list[str] | Columns appended when computed |
| compute(df, **opts) | function | Pure transform adding columns |
| version | str | Semantic indicator version for audit |

## Processing Logic

1. Validate indicator list uniqueness (FR-021)
2. Resolve indicator existence via registry (FR-026)
3. If strict and any unknown -> fail before computing (FR-007)
4. Determine dependency order (topological sort by `requires`)
5. Execute compute functions in order, accumulating appended columns
6. Collect successes vs failures (strict=False only)
7. Return enriched dataset object maintaining original core reference (FR-018, FR-024)

## Response

### JSON Metadata Schema

| Field | Type | Description |
|-------|------|-------------|
| indicators_applied | list[str] | Successfully computed indicator names |
| failed_indicators | list[str] | Unknown or failed indicators (empty if strict=True) |
| core_columns_unchanged | bool | True if hash of core columns matches pre-computation (SC-010) |
| runtime_seconds | float | Total enrichment runtime |
| registry_backend | string | Implementation name (e.g., "builtin") |
| params | object | Echo of request params (filtered) |

### Data Structure (In-Memory)

**Return Type:** `EnrichmentResult` (dataclass)

| Field | Type | Description |
|-------|------|-------------|
| enriched | DataFrame | New DataFrame with core + indicator columns |
| indicators_applied | list[str] | Successfully computed indicator names |
| failed_indicators | list[tuple[str, Exception]] | Failed indicators with exceptions (empty if strict=True) |
| runtime_seconds | float | Total enrichment computation time |

**Implementation Details:**

* `enriched` DataFrame contains all core columns plus new indicator columns
* Original `core_ref` DataFrame is never modified (immutability guarantee)
* `failed_indicators` is a list of tuples: `(indicator_name, exception_object)`
* All fields accessible via dot notation: `result.enriched`, `result.indicators_applied`, etc.

## Errors

| Code | HTTP | Condition | Message Pattern |
|------|------|-----------|-----------------|
| ENRICH_DUP_INDICATOR | 400 | Duplicate indicator name | "Duplicate indicator names: ..." |
| ENRICH_UNKNOWN_INDICATOR | 422 | Unknown indicator (strict=True) | "Unknown indicator(s): ..." |
| ENRICH_DEPENDENCY_CYCLE | 500 | Cyclic dependency in registry | "Indicator dependency cycle detected" |
| ENRICH_COMPUTE_FAILURE | 500 | Indicator compute raised | "Indicator failed: name=..., error=..." |
| ENRICH_CORE_INVALID | 400 | Core ref missing required columns | "Invalid core dataset: missing ..." |

## Performance & Non-Functional

* Indicator runtime excluded from ingestion timing (FR-005 separation)
* Only requested indicators present (SC-003 specificity)
* No mutation of core (SC-010 immutability)
* Registry pluggable (FR-026)

## Example Request (Pseudo-Python)

```python
from src.io.enrich import enrich

# Basic usage with strict validation
result = enrich(
    core_ref=ingestion_df,
    indicators=["ema20", "ema50", "atr14"],
    strict=True,
)
print("Applied:", result.indicators_applied)
print("Enriched shape:", result.enriched.shape)

# With custom parameters
result_custom = enrich(
    core_ref=ingestion_df,
    indicators=["ema20"],
    params={"ema20": {"period": 30}},  # Override default period
    strict=True,
)

# Non-strict mode (collect failures)
result_soft = enrich(
    core_ref=ingestion_df,
    indicators=["ema20", "unknown_indicator", "atr14"],
    strict=False,
)
print("Applied:", result_soft.indicators_applied)     # ['ema20', 'atr14']
print("Failed:", result_soft.failed_indicators)       # [('unknown_indicator', UnknownIndicatorError(...))]
```

## Extensibility Hooks

| Hook | Purpose |
|------|---------|
| registry backend | Swap registry implementation (in-memory -> dynamic loading) |
| compute function signature | Allow context injection (e.g., GPU backend) |
| enriched DataFrame builder | Support lazy evaluation / deferred computation |

## Validation Checklist

* [ ] Core hash unchanged after enrichment
* [ ] Only requested indicators appended
* [ ] Unknown indicators rejected (strict=True)
* [ ] Duplicate names raise error
* [ ] Dependency ordering stable & deterministic
