# Feature Specification: Multi-Timeframe Backtesting

**Feature Branch**: `015-multi-timeframe-backtest`
**Created**: 2025-12-20
**Status**: Draft
**Input**: User description: "Enable the backtester to run strategies on timeframes other than 1-minute via resampling from 1-minute OHLCV data"

## Clarifications

### Session 2025-12-20

- Q: What is the default threshold for incomplete bar warnings? → A: 10% (lenient, since gaps are expected in historical price data)
- Q: Where should the resample cache be stored? → A: Project-relative directory `./.time_cache/`
- Q: Should users be able to keep incomplete leading/trailing bars? → A: No, always drop them (no override flag)

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Run Backtest on Higher Timeframe (Priority: P1)

A user wants to backtest their 15-minute strategy without needing separate 15-minute data files. They configure the backtester with `--timeframe 15m` and the system automatically resamples their existing 1-minute data to 15-minute OHLCV bars before running the strategy.

**Why this priority**: This is the core value proposition—enabling strategy validation on design-intended timeframes without data source changes. Most strategies are designed for timeframes other than 1-minute.

**Independent Test**: Can be fully tested by running a backtest with `--timeframe 15m` on existing 1-minute data and verifying the output contains correctly aggregated 15-minute candles.

**Acceptance Scenarios**:

1. **Given** existing 1-minute OHLCV data for EURUSD, **When** user runs `python -m backtest --instrument EURUSD --timeframe 15m`, **Then** the backtest completes successfully with metrics based on 15-minute bars.
2. **Given** a strategy that uses a 20-period EMA, **When** running on 15m timeframe, **Then** the EMA is computed over 20 15-minute bars (not 20 1-minute bars).
3. **Given** 1-minute data with gaps (missing minutes), **When** resampled to 15m, **Then** affected bars are marked with `bar_complete=False`.

---

### User Story 2 - Configure Timeframe via Config File (Priority: P2)

A user wants to set their preferred timeframe in a YAML config file so they don't need to specify it on every CLI invocation. They add `backtest: timeframe: "1h"` to their config and all subsequent runs use hourly bars.

**Why this priority**: Config-driven settings improve workflow efficiency for users who consistently work with the same timeframe.

**Independent Test**: Can be tested by creating a config with `timeframe: "1h"` and verifying the backtest uses hourly bars without CLI flags.

**Acceptance Scenarios**:

1. **Given** a config file with `timeframe: "1h"`, **When** user runs backtest without `--timeframe` flag, **Then** backtest uses 1-hour bars.
2. **Given** a config file with `timeframe: "1h"` and CLI with `--timeframe 5m`, **When** user runs backtest, **Then** CLI takes precedence and uses 5-minute bars.

---

### User Story 3 - Validate Timeframe Performance Improvement (Priority: P3)

A user wants to run faster scans on large datasets. By using higher timeframes (fewer bars to process), they expect reduced simulation runtime while maintaining result validity.

**Why this priority**: Performance optimization is a secondary benefit after correctness. Users need the feature to work correctly before they care about speed.

**Independent Test**: Can be tested by running the same strategy at 1m vs 15m vs 1h and measuring wall-clock time. Higher timeframes should complete faster.

**Acceptance Scenarios**:

1. **Given** a ~6.9M row 1-minute dataset, **When** user runs on 1h timeframe, **Then** simulation completes in significantly less time than 1m timeframe (at least 50% faster).
2. **Given** cached resampled data exists, **When** user runs the same backtest again, **Then** resampling step is skipped and cache is used.

---

### User Story 4 - Use Arbitrary Integer-Minute Timeframes (Priority: P4)

A user has a strategy designed for 7-minute or 90-minute bars. They can specify `--timeframe 7m` or `--timeframe 90m` and the system handles any integer multiple of 1 minute.

**Why this priority**: Flexibility beyond the standard timeframes is valuable but less commonly needed.

**Independent Test**: Can be tested by running with `--timeframe 7m` and verifying output contains correctly aggregated 7-minute bars.

**Acceptance Scenarios**:

1. **Given** valid 1-minute data, **When** user specifies `--timeframe 7m`, **Then** backtest runs with 7-minute bars.
2. **Given** user specifies `--timeframe 90m`, **When** backtest runs, **Then** output uses 90-minute bars (equivalent to 1.5 hours).
3. **Given** user specifies `--timeframe 0m` or `--timeframe -5m`, **When** validation runs, **Then** error is raised with clear message.

---

### Edge Cases

- What happens when the first/last bar is incomplete (not enough 1-minute data to fill the timeframe)?
  - Incomplete leading/trailing bars are always dropped (no override flag provided).
- How does system handle data gaps (missing 1-minute bars within a timeframe period)?
  - Bars are aggregated over available data; `bar_complete` column is set to `False` for affected bars.
- What happens with invalid timeframe formats like "90s", "1.5h", or "abc"?
  - Validation rejects these with clear error messages; only formats like `Xm`, `Xh`, `Xd` where X is a positive integer are accepted.
- How are trading session filters applied after resampling?
  - Session filters apply to resampled bars; bars falling outside the session window are removed.
- What if the source data has no `volume` column?
  - System handles gracefully; volume aggregation is skipped and volume column is set to 0 or NaN.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST accept a `timeframe` parameter via CLI (`--timeframe`), Python API (`timeframe=`), and config file (`backtest.timeframe`).
- **FR-002**: System MUST default to `1m` timeframe when no timeframe is specified (backward compatible).
- **FR-003**: System MUST parse timeframe strings in formats: `Xm` (minutes), `Xh` (hours), `Xd` (days) where X is a positive integer ≥ 1.
- **FR-004**: System MUST reject invalid timeframe formats with descriptive error messages (e.g., `"90s"`, `"0m"`, `"1.5h"`, `"-5m"`).
- **FR-005**: System MUST resample 1-minute OHLCV data to target timeframe using correct aggregation:
  - Open: first open
  - High: max high
  - Low: min low
  - Close: last close
  - Volume: sum volume
  - Count/Trades (if present): sum
- **FR-006**: System MUST align resampled bars to UTC minute boundaries (e.g., 10:00, 10:05, ...).
- **FR-007**: System MUST mark incomplete bars with `bar_complete=False` when any constituent 1-minute bar is missing.
- **FR-008**: System MUST recompute all indicators on the resampled series (not on 1-minute data).
- **FR-009**: System MUST maintain the "one open trade per instrument" invariant at all timeframes.
- **FR-010**: System MUST apply trading session filters after resampling (remove out-of-session bars).
- **FR-011**: System MUST cache resampled datasets on disk in `./.time_cache/` directory, keyed by `{instrument, timeframe, date_range, data_version}` to avoid recomputation.
- **FR-012**: System MUST support minimum timeframe set: `1m, 5m, 15m, 1h, 2h, 4h, 8h, 1d`.
- **FR-013**: System MUST support any positive integer-minute timeframe (e.g., `7m`, `13m`, `90m`, `120m`).
- **FR-014**: System MUST record telemetry: total bars, % incomplete bars, resample time, cache hits/misses, simulation time.
- **FR-015**: System MUST emit warnings when % incomplete bars exceeds a configurable threshold (default: 10%).

### Key Entities

- **Timeframe**: Represents a target aggregation period (e.g., "15m", "1h"). Key attributes: period_minutes, is_valid, format_string.
- **Resampled Bar**: An OHLCV bar aggregated from constituent 1-minute bars. Key attributes: open, high, low, close, volume, bar_complete, timestamp_utc.
- **Resample Cache**: Disk-stored resampled data indexed by instrument, timeframe, date range, and data version.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Users can run backtests on any of the minimum supported timeframes (1m, 5m, 15m, 1h, 2h, 4h, 8h, 1d) without code changes to their strategies.
- **SC-002**: Resampling produces correct OHLCV values as verified by hand-calculated test cases.
- **SC-003**: Simulation runtime at higher timeframes (1h) shows at least 50% reduction compared to 1m timeframe on the same dataset.
- **SC-004**: Cached resample data is reused on subsequent runs (cache hit rate > 90% for repeated runs).
- **SC-005**: 100% of unit tests pass for aggregation correctness, timeframe parsing, and edge cases.
- **SC-006**: 100% of integration tests pass for end-to-end backtest runs at various timeframes.
- **SC-007**: Property tests confirm resample associativity (1m→5m→15m equals 1m→15m).
- **SC-008**: Documentation is updated with timeframe usage examples and caching behavior.

## Assumptions

- The canonical data source remains 1-minute historical OHLCV data; no changes to data ingestion are required.
- All internal processing uses UTC timestamps; downstream localization is out of scope.
- Strategies receive resampled DataFrames with the same column names and dtypes as before—no strategy code changes needed.
- DST/Timezone handling is deferred; system operates in UTC internally.

## Scope Exclusions (Non-Goals)

- Real-time multi-timeframe (MTF) signal fusion (e.g., using 1h trend + 5m entries) is a future enhancement.
- Data source changes or support for non-1-minute base data.
- Sub-minute timeframes (seconds, milliseconds).
- Configurable timestamp alignment (e.g., bar timestamp at open vs close)—default is close of bar.
