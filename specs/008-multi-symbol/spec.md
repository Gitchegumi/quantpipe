# Feature Specification: Multi-Symbol Support

**Feature Branch**: `008-multi-symbol`
**Created**: 2025-11-06
**Status**: Draft
**Input**: User description: "I would like to work on multi-symbol support. This is from the second list item of issue #2. The simulation should be able to run as if both symbols are being traded at the same time, and also as of both symbols are being traded independently."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Single Symbol Backtest (Priority: P1)

An operator selects a single currency pair (e.g., EURUSD) from processed dataset files and runs a backtest that evaluates strategy performance exclusively on that one symbol. The operator views metrics and results specific to that symbol.

**Why this priority**: This maintains existing functionality as the foundation—single-symbol backtesting must continue to work independently and serves as the baseline for multi-symbol capabilities.

**Independent Test**: Execute backtest with one currency pair specified; verify results contain only that symbol's trades, metrics, and position history; confirm output format matches current single-symbol backtest structure.

**Acceptance Scenarios**:

1. **Given** a processed dataset for EURUSD exists, **When** the operator runs a backtest specifying only EURUSD, **Then** the system produces results containing EURUSD trades and metrics only.
2. **Given** multiple processed datasets exist (EURUSD, GBPUSD, USDJPY), **When** the operator specifies USDJPY only, **Then** only USDJPY data is loaded and backtested.

---

### User Story 2 - Run Multiple Symbols Independently (Priority: P2)

An operator selects multiple currency pairs (e.g., EURUSD, GBPUSD, USDJPY) and runs a backtest that evaluates each symbol independently—treating each as a separate backtest with its own isolated state, positions, metrics, and risk limits. The operator views per-symbol results in separate output files or sections.

**Why this priority**: Enables parallel evaluation of multiple instruments without complication of correlation or portfolio-level aggregation. Users can assess each symbol's standalone performance in a single execution.

**Independent Test**: Execute backtest with 3 currency pairs; verify each produces distinct result artifacts (trades, metrics, positions); verify no state leakage between symbols (e.g., EURUSD signal doesn't affect GBPUSD position).

**Acceptance Scenarios**:

1. **Given** processed datasets for EURUSD, GBPUSD, and USDJPY exist, **When** the operator runs a multi-symbol backtest with all three specified independently, **Then** the system produces three separate result outputs with isolated metrics.
2. **Given** one symbol (GBPUSD) triggers a risk limit breach, **When** backtesting continues, **Then** only GBPUSD halts further trade generation while EURUSD and USDJPY continue processing normally.
3. **Given** a strategy generates signals on multiple symbols at the same timestamp, **When** execution simulates trades, **Then** each symbol's position is managed independently without cross-symbol state sharing.

---

### User Story 3 - Run Multiple Symbols as Portfolio (Priority: P3)

An operator selects multiple currency pairs (e.g., EURUSD, GBPUSD, USDJPY) and runs a backtest that evaluates them as a unified portfolio—simulating concurrent trading where capital is shared, correlation checks are performed, exposure limits apply across all symbols, and aggregated portfolio metrics (combined PnL, drawdown, diversification ratio, cross-pair correlation) are calculated. The operator views both individual symbol results and portfolio-level aggregated metrics.

**Why this priority**: Provides realistic portfolio simulation reflecting how multiple symbols would be traded together with shared capital and risk management. This is the advanced multi-symbol capability enabling diversification analysis.

**Independent Test**: Execute portfolio backtest with 3 currency pairs; verify individual symbol results exist; verify portfolio metrics include combined PnL, correlation matrix, aggregate drawdown, and total exposure; confirm correlation checks affect position sizing or signal filtering.

**Acceptance Scenarios**:

1. **Given** processed datasets for EURUSD, GBPUSD, and USDJPY exist, **When** the operator runs a portfolio backtest, **Then** the system produces per-symbol results plus a portfolio-level metrics output including correlation matrix, combined equity curve, and aggregate drawdown.
2. **Given** high correlation detected between EURUSD and GBPUSD during execution, **When** both symbols generate simultaneous long signals, **Then** the system applies correlation-adjusted position sizing or filters redundant signals according to correlation limits.
3. **Given** portfolio-level exposure limit is reached across all symbols, **When** any symbol generates a new signal, **Then** the system rejects the signal or scales position size to remain within portfolio exposure threshold.
4. **Given** shared capital pool with fixed initial value, **When** symbols compete for capital allocation, **Then** the system allocates capital per symbol according to specified weighting strategy (equal-weight, risk-parity, custom weights) and enforces capital constraints.

---

### User Story 4 - Currency Pair Selection & Filtering (Priority: P3)

An operator uses CLI flags to specify a subset of available currency pairs (by symbol name or tag/filter) to include in a backtest run, optionally excluding others. The operator can also request independent mode (isolated per-symbol) or portfolio mode (aggregated).

**Why this priority**: Provides operational control—users can focus evaluation on relevant symbol subsets and choose between independent or portfolio execution modes.

**Independent Test**: Invoke CLI with list of symbols and mode flag; verify only selected symbols run and mode (independent vs portfolio) matches request.

**Acceptance Scenarios**:

1. **Given** 5 processed datasets exist (EURUSD, GBPUSD, USDJPY, AUDUSD, NZDUSD), **When** the operator selects 2 symbols via CLI in independent mode, **Then** only those 2 execute with isolated results.
2. **Given** selection includes an unknown symbol name, **When** execution starts, **Then** the system aborts gracefully with a clear validation error listing unknown/missing symbols.
3. **Given** operator specifies portfolio mode without providing symbol weights, **When** backtest runs, **Then** system defaults to equal-weight allocation across selected symbols.

---

### Edge Cases

- Symbol produces zero trades (should still output metrics with zeros and appear in portfolio aggregation if applicable).
- One symbol's data file is corrupt or missing candles (independent mode: skip that symbol with warning and continue; portfolio mode: abort entire run with clear list of failing symbols to preserve deterministic composition).
- Symbols have mismatched time ranges (portfolio mode requires overlapping time range; system uses intersection of timestamps or reports validation error if insufficient overlap).
- Currency-specific spread/commission models differ across symbols (system applies per-symbol cost model correctly; portfolio metrics reflect aggregated costs).
- All selected symbols breach risk limits simultaneously (all trading halts; partial results preserved).
- Portfolio exposure limit prevents any symbol from taking positions (all signals rejected; zero-trade results for all symbols).
- Correlation matrix calculation with insufficient data (system reports warning and skips correlation checks or uses default uncorrelated assumption).
- Duplicate symbol identifiers in selection list (reject with clear error or deduplicate with warning).
- Empty symbol selection list (error: must select ≥1 symbol).
- Large number (≥10) symbols in portfolio mode (performance target; results should complete within success criteria limits).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support loading and processing price data for multiple currency pairs within a single backtest execution.
- **FR-002**: System MUST provide CLI option to specify one or more currency pairs by symbol name (e.g., `--pair EURUSD GBPUSD USDJPY`).
- **FR-003**: System MUST support two execution modes selectable via CLI flag: "independent" (isolated per-symbol backtests) and "portfolio" (unified portfolio simulation).
- **FR-004**: System MUST isolate per-symbol state (positions, PnL tracking, indicators) in independent mode so no symbol can mutate another's state.
- **FR-005**: System MUST generate per-symbol result outputs (metrics, trades, positions) in both independent and portfolio modes.
- **FR-006**: System MUST generate aggregated portfolio metrics output in portfolio mode including combined PnL, aggregate drawdown, total exposure, correlation matrix, and diversification ratio.
- **FR-007**: System MUST validate availability of processed datasets for all selected symbols before execution and abort with clear error if any are missing.
- **FR-008**: System MUST apply symbol-specific spread and commission models (configurable per currency pair) when simulating trades.
- **FR-009**: System MUST enforce per-symbol risk limits (e.g., max position size, daily loss threshold) in both modes; in independent mode, limits apply only to that symbol; in portfolio mode, limits apply per-symbol plus portfolio-level limits.
- **FR-010**: System MUST calculate and apply correlation checks in portfolio mode using a rolling 100-period window of synchronized per-symbol returns; before 100 periods are available it MUST use a provisional window equal to the number of accumulated periods (minimum 20 required to start applying correlation logic) to detect correlated symbol pairs and adjust position sizing or filter redundant signals based on configurable correlation thresholds.
 **Correlation Matrix**: Rolling correlation coefficients computed per candle: provisional window size (<100, minimum 20) until 100 periods accumulated, then fixed 100-period window thereafter; used for diversification metrics, redundancy filtering, and risk adjustments.
 **SC-006**: Portfolio mode correlation checks reduce redundant simultaneous signals on highly correlated pairs (correlation >0.8 using provisional window once ≥20 periods, and 100-period window thereafter) by at least 50% compared to uncorrelated treatment.
- **FR-013**: System MUST synchronize timestamps across symbols in portfolio mode, processing only overlapping time ranges and aligning candles to common intervals.
- **FR-014**: System MUST log symbol-level lifecycle events (start, halt, error, risk breach) distinctly in both modes.
- **FR-015**: System MUST provide validation phase that checks for unknown symbols, missing datasets, and invalid configuration before execution.
- **FR-016**: System MUST allow listing available currency pairs (based on processed datasets) via CLI without running a backtest.
- **FR-017**: System MUST produce deterministic results (same inputs produce identical per-symbol and portfolio outputs).
- **FR-018**: System MUST ensure that failure of one symbol's data processing (in independent mode) does not terminate other symbols unless data corruption is systemic.
- **FR-019**: System MUST produce a run manifest listing symbols executed, execution mode, dataset paths, spread/commission models, risk limits, weighting strategy, and correlation settings.
- **FR-020**: System MUST calculate diversification metrics in portfolio mode including portfolio volatility, diversification ratio (portfolio volatility / average symbol volatility), and contribution of each symbol to portfolio risk.
- **FR-021**: System MUST abort portfolio-mode execution if any selected symbol fails validation (missing dataset, structural corruption, incompatible timeframe) and report all offending symbols; in independent mode only failing symbols are skipped while others proceed.
- **FR-022**: System MUST log every executed trade (symbol, timestamp, side, size, entry price, applied spread/commission cost, correlation adjustment flag/reason) and produce a configurable periodic portfolio snapshot (default every 50 candles) containing: timestamp, per-symbol open positions summary, per-symbol unrealized PnL, portfolio aggregated PnL, portfolio exposure, current correlation matrix (or latest), diversification ratio, and any risk limit statuses. Snapshot interval MUST be configurable via CLI (e.g., `--snapshot-interval 50`) with minimum 1; logging MUST be structured to allow parsing (JSON lines or clearly delimited text) and MUST avoid exceeding performance success criteria.
- **FR-023**: System MUST generate output artifact filenames using pattern `backtest_<direction>_<symbol|multi>_<YYYYMMDD>_<HHMMSS>.txt|.json`; for single-symbol runs `<symbol>` MUST be lowercase symbol name (e.g., eurusd), for any multi-symbol (independent batch or portfolio) run MUST use `multi`. System MUST include a `Symbols:` line in run metadata listing all executed symbols (single: `Symbol: EURUSD`; multi: `Symbols: EURUSD, GBPUSD, USDJPY`).

### Key Entities

- **Currency Pair**: Represents a tradable instrument (e.g., EURUSD, GBPUSD) with associated symbol name, processed dataset file path, spread model, and commission model.
- **Symbol Configuration**: Per-symbol settings including risk limits (max position size, stop-loss parameters), spread value or spread model, commission rate or commission model, and optional custom indicator parameters.
- **Portfolio Configuration**: Settings for portfolio mode including capital allocation weights per symbol, correlation threshold for filtering, portfolio-level exposure limit, capital pool size, and weighting strategy (equal-weight, risk-parity, custom).
- **Correlation Matrix**: Rolling 100-period correlation coefficients between synchronized symbol return series (updated each candle after the first 100) used for diversification metrics, redundancy filtering, and risk adjustments.
- **Symbol Result**: Output artifact for one symbol containing trades, metrics, position history, equity curve, and drawdown data.
- **Portfolio Result**: Output artifact in portfolio mode containing aggregated metrics, correlation matrix, diversification ratio, combined equity curve, aggregate drawdown, per-symbol contribution to portfolio risk, and total exposure over time.
- **Portfolio Snapshot**: Periodic state capture (default every 50 candles) including timestamp, current positions, unrealized per-symbol and portfolio PnL, exposure, diversification ratio, and correlation matrix reference used for monitoring/log parsing (not a final result artifact but an observability feed).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operators can execute backtests on single symbols with identical results to current baseline (regression test passes).
- **SC-002**: Operators can execute independent multi-symbol backtests with 3+ symbols and receive isolated per-symbol results within 2x the time of a single-symbol backtest of equivalent duration.
- **SC-003**: Operators can execute portfolio-mode backtests with 3+ symbols and receive both per-symbol results and portfolio-level metrics (correlation matrix, aggregate drawdown, diversification ratio) within 3x the time of a single-symbol backtest of equivalent duration.
- **SC-004**: System correctly applies symbol-specific spread/commission models with verification via trade cost calculations matching expected values per symbol.
- **SC-005**: System detects and reports missing processed datasets for all selected symbols with 100% accuracy before execution starts.
- **SC-006**: Portfolio mode correlation checks reduce redundant simultaneous signals on highly correlated pairs (correlation >0.8) by at least 50% compared to uncorrelated treatment.
- **SC-007**: Portfolio exposure limits prevent total exposure from exceeding configured threshold with 100% enforcement accuracy.
- **SC-008**: Capital allocation across symbols in portfolio mode sums to 100% of available capital with <0.01% allocation error.
- **SC-009**: System produces deterministic results with identical outputs for repeated runs with same inputs (100% reproducibility).
- **SC-010**: CLI listing command returns all available currency pairs based on processed datasets within 1 second.
- **SC-011**: System handles 10 symbols in portfolio mode without exceeding 5-minute total runtime for a 1-year daily dataset (approximately 250 candles per symbol).
- **SC-012**: Per-symbol risk limit breaches halt only the affected symbol in independent mode and do not affect other symbols (100% isolation verification).
- **SC-013**: Observability logging (trade logs + 50-candle snapshots) adds <10% runtime overhead versus a run with logging disabled (benchmark on 3-symbol 1-year daily dataset) and each trade log contains all required fields (symbol, timestamp, side, size, price, cost, correlation-adjustment flag/reason) with 100% presence; snapshot interval configurable and honored (validated at 50 and a custom value like 25).
- **SC-014**: Output artifacts follow naming convention exactly (regex: `^backtest_(long|short|both)_(multi|[a-z0-9]{6})_\d{8}_\d{6}\.(txt|json)$`) and metadata symbol line lists all symbols with correct case and ordering (single: one symbol; multi: count matches selection). Validation test confirms for single and multi runs.

## Clarifications

### Session 2025-11-06

- Q: What correlation lookback window should be used for portfolio mode correlation checks? → A: Rolling 100-period window.
- Q: How should the system behave if a selected symbol fails validation in portfolio mode? → A: Abort entire portfolio run with error listing all failing symbols.
- Q: What observability granularity should be provided? → A: Log each executed trade plus portfolio snapshot every 50 candles (configurable interval).
