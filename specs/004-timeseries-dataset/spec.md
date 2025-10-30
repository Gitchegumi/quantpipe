# Feature Specification: Time Series Dataset Preparation

**Feature Branch**: `004-timeseries-dataset`
**Created**: 2025-10-30
**Status**: Draft
**Input**: User description: "Build a time series dataset from price_data directory. Raw data per symbol in `price_data/raw/<symbol>`. Produce processed outputs into `price_data/processed/<symbol>/test` and `price_data/processed/<symbol>/validate`. Perform chronological 80/20 split favoring recent data for validation (contiguous last 20%). Adjust current backtest behavior: instead of converting a single CSV and writing to results, integrate dataset building and operate over processed splits for each symbol."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Chronological Split (Priority: P1)

As a strategy developer I want to automatically create a clean, chronologically split dataset (test + validation) for each available symbol so that model/backtest runs consistently use standardized partitions.

**Why this priority**: Foundational capability; all subsequent backtests and evaluations rely on having properly partitioned data.

**Independent Test**: Execute dataset build for a symbol containing raw price data; verify creation of `processed/<symbol>/test` and `processed/<symbol>/validate` directories with expected 80/20 chronological split and metadata file summarizing counts.

**Acceptance Scenarios**:

1. **Given** raw data files exist for a symbol, **When** the dataset build is triggered, **Then** test and validation directories are created with an 80/20 chronological split (older 80% test, newest 20% validation).
2. **Given** no raw data files for a symbol, **When** build is triggered, **Then** system reports a clear warning and skips that symbol without failing overall build.

---

### User Story 2 - Multi-Symbol Processing (Priority: P2)

As a strategy developer I want to process all available symbols in one run so that I do not have to manually repeat the process per symbol.

**Why this priority**: Improves productivity; reduces manual repetition; ensures consistent partitions across symbols.

**Independent Test**: Initiate build; confirm all symbol subdirectories under `raw/` produce corresponding processed structure; symbols with issues are reported individually.

**Acceptance Scenarios**:

1. **Given** multiple symbol folders under raw, **When** build runs, **Then** each produces a processed dataset split with identical rules and a consolidated summary report.
2. **Given** a subset of symbols have malformed data, **When** build runs, **Then** those are listed in a summary of skipped/errored symbols while others succeed.

---

### User Story 3 - Backtest Integration (Priority: P3)

As a user running backtests I want the backtest tool to operate on the standardized processed partitions instead of individual ad-hoc converted CSVs so that evaluation is reproducible and consistent between runs.

**Why this priority**: Aligns evaluation workflow with standardized data; enhances reproducibility and comparability of results.

**Independent Test**: Run a backtest referencing a symbol; confirm it loads data from processed test/validation partitions and produces separate performance metrics for each partition.

**Acceptance Scenarios**:

1. **Given** processed partitions exist, **When** backtest executes for a symbol, **Then** it uses test data for model calibration/setup and validation data for performance evaluation outputs.
2. **Given** processed partitions are missing, **When** backtest executes, **Then** it provides a clear directive to run dataset build first.

---

### Edge Cases

- Raw data contains gaps or overlapping timestamps: system identifies and reports count of gaps/overlaps; continues with cleaning if feasible.
- Raw data very small (fewer than 10 rows): system aborts split for that symbol and flags it as insufficient for partitioning.
- Multiple raw files per symbol with differing schemas: system flags schema mismatch and skips symbol.
- Time zone inconsistencies detected across files: system normalizes to a stated canonical time zone assumption and records assumption.
- Non-chronological order in raw files: system sorts strictly by timestamp before splitting.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST scan `price_data/raw/` and enumerate symbol subdirectories containing raw price files.
- **FR-002**: System MUST validate each raw file's structure (timestamp, price-related columns) and reject symbols with inconsistent schemas.
- **FR-003**: System MUST merge all valid raw files per symbol into a single chronological dataset with deduplicated timestamps.
- **FR-004**: System MUST perform an 80/20 chronological split per symbol where the earliest 80% of rows become test and the latest 20% become validation (contiguous segments).
- **FR-005**: System MUST write outputs into `price_data/processed/<symbol>/test` and `price_data/processed/<symbol>/validate` preserving original ordering within each partition.
- **FR-006**: System MUST generate a per-symbol metadata summary (row counts, time span, gaps/overlaps statistics) and store it alongside partitions.
- **FR-007**: System MUST produce a consolidated build summary listing success, skipped symbols (with reasons), and aggregate counts.
- **FR-008**: System MUST handle insufficient data (< threshold) by skipping split and recording reason in summary (threshold assumption defined in assumptions).
- **FR-009**: System MUST ensure validation set favors more recent data by using the most recent contiguous 20% of rows.
- **FR-010**: System MUST integrate with backtest workflow so that backtest operations reference processed test/validation partitions instead of single converted CSV outputs.
- **FR-011**: System MUST provide a clear message when backtest invoked for a symbol lacking processed partitions directing user to run the dataset build.
- **FR-012**: System MUST record decisions and assumptions (e.g., canonical time zone) in metadata to maintain reproducibility.

### Key Entities *(include if feature involves data)*

- **Symbol Raw Dataset**: Represents merged raw time series for a financial instrument; attributes: symbol identifier, ordered timestamps, price-related columns, source file list, gap/overlap stats.
- **Processed Partition**: Represents a contiguous chronological subset (test or validation) of a symbol's raw dataset; attributes: partition type, row count, start/end timestamp.
- **Build Summary**: Aggregated outcome of a build run; attributes: timestamp of build, list of symbols processed, list of skipped symbols with reasons, aggregate row counts.
- **Metadata Record**: Per-symbol descriptor; attributes: symbol, total rows, test rows, validation rows, start/end timestamps, canonical time zone, assumptions applied.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of symbols with sufficient valid data produce both test and validation partitions on first build run.
- **SC-002**: Validation partition always contains the most recent contiguous 20% ±1 row (rounding rule documented) of chronological data for each symbol.
- **SC-003**: Build summary reports zero silent failures (all skipped symbols have explicit reasons) in at least 95% of runs with mixed data quality.
- **SC-004**: Backtest runs on a processed symbol produce distinct metrics for test and validation partitions in 100% of executions where partitions exist.
- **SC-005**: Time from initiating dataset build to availability of partitions completes within a threshold suitable for interactive usage (assumed < 2 minutes for 1M combined rows; documented as assumption).

### Assumptions

- Raw files share a common minimal schema including a timestamp column and required price fields (e.g., open/high/low/close, volume) though exact names are standardized elsewhere; mismatches cause skip.
- Insufficient data threshold assumed at < 500 rows (below this not meaningful for split); adjustable later without changing spec intent.
- Canonical time zone assumed UTC; all timestamps normalized accordingly.
- Rounding for 80/20 split uses floor for test size; remainder assigned to validation ensuring validation is most recent.
- Performance expectation (< 2 minutes for 1M rows) considered acceptable interactive threshold.
- No need for randomization due to time series nature; contiguous split preserves temporal integrity.

### Out of Scope

- Advanced feature engineering beyond partitioning (e.g., lag feature generation).
- Data quality repair beyond basic gap/overlap detection and sorting.
- Cross-symbol synchronization or alignment.

## Notes

No [NEEDS CLARIFICATION] markers included; reasonable defaults applied. If future changes require different thresholds or time zone, they can be updated without altering user value proposition.
