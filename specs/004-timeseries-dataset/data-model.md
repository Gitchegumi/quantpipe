# Data Model: Time Series Dataset Preparation

**Branch**: 004-timeseries-dataset | **Date**: 2025-10-30

## Entities

### SymbolRawDataset

Represents merged raw time series for one symbol.

- symbol: string (unique identifier; directory name under `price_data/raw/`)
- timestamps: ordered array/datetime index (strictly increasing after sort)
- columns: set of price field identifiers (e.g., open, high, low, close, volume)
- source_files: list of file paths merged
- gap_count: integer (number of detected temporal gaps over expected cadence)
- overlap_count: integer (number of duplicate timestamps before dedup)
- start_timestamp: datetime
- end_timestamp: datetime
- total_rows: integer
- schema_version: string (semantic identifier for expected columns, e.g., v1)

Validation Rules:

- timestamps must be strictly increasing post-merge.
- duplicate timestamps counted then resolved by keeping first occurrence (report-only; no alteration beyond dedup necessity for ordering).
- required columns present according to schema_version mapping.

### ProcessedPartition

Represents partition slice (test or validation).

- symbol: string
- partition_type: enum {test, validation}
- start_timestamp: datetime
- end_timestamp: datetime
- row_count: integer
- sequence_index_start: integer (0-based offset in raw merged dataset)
- sequence_index_end: integer (inclusive end index)

Validation Rules:

- partition ranges contiguous and non-overlapping.
- test precedes validation chronologically.
- combined row_count equals SymbolRawDataset.total_rows.

### MetadataRecord

Per-symbol metadata JSON artifact.

- symbol: string
- total_rows: integer
- test_rows: integer
- validation_rows: integer
- start_timestamp: datetime
- end_timestamp: datetime
- validation_start_timestamp: datetime
- gap_count: integer
- overlap_count: integer
- canonical_timezone: string (UTC)
- build_timestamp: datetime
- schema_version: string

Validation Rules:

- test_rows + validation_rows equals total_rows.
- validation_start_timestamp equals partition_type=validation.start_timestamp.
- canonical_timezone == 'UTC'.

### BuildSummary

Aggregate run summary.

- build_timestamp: datetime
- symbols_processed: list`<string>`
- symbols_skipped: list`<SkippedSymbol>`
- total_rows_processed: integer
- total_test_rows: integer
- total_validation_rows: integer
- duration_seconds: float

### SkippedSymbol

- symbol: string
- reason: enum {insufficient_rows, schema_mismatch, read_error}
- details: string (human-readable explanation)

## Relationships

- SymbolRawDataset 1---\* ProcessedPartition (two partitions expected when sufficient rows)
- MetadataRecord 1---1 SymbolRawDataset (descriptive, generated post-split)
- BuildSummary aggregates many MetadataRecord entries (indirect through symbols_processed)

## State Transitions

1. Raw discovery → SymbolRawDataset merged
2. Validation checks pass → Partitioning executed
3. Partitioning complete → MetadataRecord persisted
4. All symbols processed → BuildSummary finalized

## Partition Algorithm Parameters

- split_ratio_test: 0.8 (floor applied to test rows)
- min_rows_threshold: 500
- timezone: UTC

## Error Handling Semantics

- Non-fatal per-symbol failures produce SkippedSymbol entries; pipeline continues.
- Fatal I/O error on summary write aborts build (build summary absent).

## Determinism Guarantees

- Sorting ensures consistent row ordering.
- Floor split produces stable test size given same input.
- Metadata includes timestamp enabling reproducibility auditing.

## Notes

No mutation of price values (no forward-fill, interpolation).
