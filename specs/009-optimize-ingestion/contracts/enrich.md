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
| core_ref | object (IngestionResult reference) | Yes | MUST be valid ingestion output | Source core dataset (FR-018 immutability) |
| indicators | list[str] | Yes | unique names | Indicator identifiers to compute (FR-006) |
| params | dict[str, Any] | No | optional | Global / per-indicator tunables |
| strict | bool | No | default False | Unknown names abort early if True (FR-007) |

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

| Component | Type | Notes |
|-----------|------|-------|
| core | DataFrame[CoreCandleRecord] | Unchanged reference |
| enriched | DataFrame | New DataFrame with indicator columns only |

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
enriched = enrich(
    core_ref=ingestion_result,
    indicators=["ema20", "ema50", "atr14"],
    params={"ema": {"method": "exponential"}},
    strict=True,
)
print(enriched.indicators_applied)
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
