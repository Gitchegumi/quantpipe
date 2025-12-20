# Feature Specification: Multi-Symbol Concurrent Backtest

**Feature Branch**: `013-multi-symbol-backtest`
**Created**: 2025-12-18
**Status**: Approved
**Input**: Issue #28 - Fix multi-symbol pathing and run backtests on multiple pairs with concurrent PnL computation

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Run Multi-Symbol Backtest with Concurrent PnL (Priority: P1)

An operator specifies multiple currency pairs via CLI (e.g., `--pair EURUSD USDJPY`) and runs a backtest that processes both symbols concurrently, computing a single aggregated PnL as if both pairs are traded simultaneously with shared capital. The system starts with a default account balance of $2,500 and tracks combined equity across all symbols.

**Why this priority**: This is the core issue - currently multi-symbol runs only backtest the first pair. Users need concurrent execution across all specified pairs with unified PnL tracking to simulate realistic multi-instrument trading.

**Independent Test**: Execute backtest with `--pair EURUSD USDJPY --dataset test`; verify both symbols produce trades; verify combined PnL reflects concurrent trading; verify account starts at $2,500.

**Acceptance Scenarios**:

1. **Given** processed Parquet files exist for EURUSD and USDJPY, **When** the operator runs `--pair EURUSD USDJPY --dataset test`, **Then** the system loads both datasets and runs backtests on both symbols (not just the first).
2. **Given** both symbols generate signals at overlapping timestamps, **When** trades are executed, **Then** PnL is computed as if both positions are held concurrently with shared capital allocation.
3. **Given** no explicit account balance is provided, **When** the backtest runs, **Then** the system uses a default starting balance of $2,500.

---

### User Story 2 - Verify Dataset Path Construction for Multi-Symbol (Priority: P1)

An operator uses the auto-path construction feature with `--pair EURUSD USDJPY --dataset test` and the system correctly constructs paths for each symbol as `price_data/processed/<pair>/<dataset>/<pair>_<dataset>.parquet`.

**Why this priority**: Path construction is foundational - without correct paths for each symbol, multi-symbol backtests cannot load data for all specified pairs.

**Independent Test**: Run CLI with multiple pairs and verify each symbol's Parquet file is found and loaded via correct path construction.

**Acceptance Scenarios**:

1. **Given** `--pair EURUSD USDJPY --dataset test`, **When** the CLI resolves paths, **Then** paths resolve to `price_data/processed/eurusd/test/eurusd_test.parquet` AND `price_data/processed/usdjpy/test/usdjpy_test.parquet`.
2. **Given** one symbol's Parquet file exists and another is missing, **When** fallback is enabled, **Then** the system attempts to load `.csv` for the missing symbol while continuing with Parquet for the other.

---

### User Story 3 - End-to-End Parquet Pipeline Verification (Priority: P2)

An operator runs a single-symbol backtest using Parquet files and verifies the full pipeline (ingest → enrich → scan → simulate → metrics) works correctly with Parquet-loaded data.

**Why this priority**: Parquet support must work end-to-end before multi-symbol is validated. This ensures the data format is correctly processed through all stages.

**Independent Test**: Run `--pair EURUSD --dataset test` with Parquet file; verify ingestion, indicator enrichment, signal scanning, trade simulation, and metrics calculation all complete successfully.

**Acceptance Scenarios**:

1. **Given** a Parquet file for EURUSD, **When** the backtest runs with default settings, **Then** all five pipeline stages complete without errors.
2. **Given** Parquet data is loaded, **When** indicators are enriched, **Then** EMA, ATR, and RSI columns are correctly calculated.
3. **Given** progress bars are enabled, **When** the pipeline executes, **Then** progress bars display cleanly without corruption or overlap.

---

### Edge Cases

- **Missing Parquet file for one symbol**: System should warn and skip that symbol (or fallback to CSV if available).
- **Empty dataset for one symbol**: System should log warning and continue with remaining symbols.
- **Single symbol specified**: System should behave identically to current single-symbol path (regression protection).
- **Mismatched timestamps across symbols**: For concurrent PnL, only overlapping time ranges should be considered for aggregation.
- **Zero trades generated for one symbol**: That symbol contributes $0 to PnL but is still included in summary.
- **Parquet file exists but is corrupt**: System should report clear error and abort loading for that symbol.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST iterate over all pairs specified via `--pair` flag and run backtests on each (not just the first pair).
- **FR-002**: System MUST compute aggregated PnL across all symbols as if positions are held concurrently with shared capital.
- **FR-003**: System MUST use a default account balance of $2,500 when no balance is explicitly specified.
- **FR-004**: System MUST construct dataset paths correctly for each symbol: `price_data/processed/<pair_lowercase>/<dataset>/<pair_lowercase>_<dataset>.parquet`.
- **FR-005**: System MUST attempt fallback to `.csv` extension when `.parquet` file is not found.
- **FR-006**: System MUST validate all specified pair datasets exist before execution begins (fail-fast validation).
- **FR-007**: System MUST preserve single-symbol behavior exactly when only one pair is specified (no regressions).
- **FR-008**: System MUST report per-symbol results AND combined portfolio results in output.
- **FR-009**: System MUST handle Parquet files correctly through entire pipeline: ingestion → enrichment → scanning → simulation → metrics.
- **FR-010**: System MUST display progress bars cleanly for each symbol and overall portfolio during execution.

### Key Entities

- **Account Balance**: Shared capital pool for concurrent trading simulation (default: $2,500).
- **Symbol Dataset Path**: Auto-constructed path pattern for each currency pair's data file.
- **Multi-Symbol Result**: Aggregated result containing per-symbol results and combined portfolio metrics.
- **Portfolio PnL**: Combined profit/loss computed as if all symbols are traded concurrently.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Running `--pair EURUSD USDJPY --dataset test` executes backtests on BOTH symbols (verified via trade count > 0 for each).
- **SC-002**: Combined PnL output reflects concurrent trading across all symbols with shared $2,500 starting balance.
- **SC-003**: Path construction produces correct paths for 100% of specified symbols.
- **SC-004**: Single-symbol runs produce identical results to pre-change baseline (regression test passes).
- **SC-005**: Parquet files load and process through all pipeline stages without data corruption.
- **SC-006**: Code quality maintains Pylint score ≥9.5/10.
- **SC-007**: Fallback from Parquet to CSV works transparently when Parquet is missing.

## Assumptions

- The $2,500 default account balance is fixed for this iteration; future issues will add CLI parameter support.
- Multi-symbol runs in this iteration are "independent mode" per spec 008 (no correlation-based position sizing yet).
- The current vectorized backtest path is the primary execution target.
- Position sizing across multiple symbols will use equal allocation unless otherwise specified.
