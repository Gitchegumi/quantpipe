# Feature Specification: Directional Backtesting System

**Feature Branch**: `002-directional-backtesting`  
**Created**: 2025-10-29  
**Status**: Draft  
**Input**: User description: "I need to implement the logic for LONG, SHORT, and BOTH direction back testing and allow run_backtest.py to manage all backtesting"

## Clarifications

### Session 2025-10-29

- Q: How should the system break ties when BOTH mode generates long and short signals at the exact same timestamp? → A: Reject both signals and skip the opportunity (indicates choppy market/indecision, not suitable for trade entry)
- Q: What format should output filenames use when saving results? → A: backtest*{direction}*{YYYYMMDD}\_{HHMMSS}.{ext}
- Q: What information should be logged when rejecting conflicting signals in BOTH mode? → A: Timestamp and currency pair only
- Q: What signal details should dry-run mode output? → A: Essential fields: timestamp, pair, direction, entry_price, stop_price
- Q: How should combined metrics be calculated from separate long and short trades in BOTH mode? → A: Aggregate all trades together (combined win_rate, avg_r, etc.)

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Execute LONG-Only Backtest (Priority: P1)

User wants to run a backtest that only processes long trade signals on historical data to evaluate strategy performance in bullish scenarios.

**Why this priority**: Core MVP functionality; enables validation of long-side strategy performance independently.

**Independent Test**: Execute backtest with `--direction LONG` flag on historical dataset containing both bullish and bearish setups → system generates only long signals, executes them, and outputs performance metrics (win rate, average R, drawdown).

**Acceptance Scenarios**:

1. **Given** historical price data with uptrend opportunities, **When** user runs `run_backtest.py --direction LONG --data <path>`, **Then** system generates only long signals using generate_long_signals(), executes each signal, and outputs text-formatted performance report.
2. **Given** dataset with mixed trend conditions, **When** LONG-only backtest executes, **Then** short signals are not generated regardless of bearish setups detected.
3. **Given** LONG backtest completes successfully, **When** user reviews output, **Then** metrics include trade_count, win_rate, avg_r, sharpe_estimate, max_drawdown_r, and execution metadata.

---

### User Story 2 - Execute SHORT-Only Backtest (Priority: P2)

User wants to run a backtest that only processes short trade signals on historical data to evaluate strategy performance in bearish scenarios.

**Why this priority**: Enables directional symmetry testing; critical for validating strategy works in downtrends.

**Independent Test**: Execute backtest with `--direction SHORT` flag on historical dataset containing bearish setups → system generates only short signals, executes them, and outputs performance metrics.

**Acceptance Scenarios**:

1. **Given** historical price data with downtrend opportunities, **When** user runs `run_backtest.py --direction SHORT --data <path>`, **Then** system generates only short signals using generate_short_signals(), executes each signal, and outputs text-formatted performance report.
2. **Given** dataset with mixed trend conditions, **When** SHORT-only backtest executes, **Then** long signals are not generated regardless of bullish setups detected.
3. **Given** SHORT backtest completes successfully, **When** user reviews output, **Then** metrics match LONG backtest structure for comparison.

---

### User Story 3 - Execute BOTH Directions Backtest (Priority: P3)

User wants to run a backtest that processes both long and short signals to evaluate full strategy performance across all market conditions.

**Why this priority**: Represents complete strategy validation; enables real-world performance assessment.

**Independent Test**: Execute backtest with `--direction BOTH` flag on historical dataset → system generates both long and short signals, manages position conflicts, executes trades, and outputs combined performance metrics.

**Acceptance Scenarios**:

1. **Given** historical price data with mixed trend opportunities, **When** user runs `run_backtest.py --direction BOTH --data <path>`, **Then** system generates both long and short signals, executes non-conflicting trades, and outputs combined performance report.
2. **Given** simultaneous long and short signal opportunities, **When** BOTH mode processes them, **Then** system applies conflict resolution logic to prevent simultaneous opposing positions in same pair.
3. **Given** BOTH mode backtest completes, **When** user reviews metrics, **Then** output includes direction-specific breakdowns (long_only_metrics, short_only_metrics, combined_metrics).

---

### User Story 4 - Output Results in JSON Format (Priority: P4)

User wants to output backtest results in machine-readable JSON format for programmatic analysis, integration with external tools, or automated reporting pipelines.

**Why this priority**: Enables automation and integration; supports data-driven workflow.

**Independent Test**: Run any backtest with `--output-format json` flag → system outputs valid JSON with complete backtest metadata, signals, executions, and metrics.

**Acceptance Scenarios**:

1. **Given** completed backtest, **When** user specifies `--output-format json`, **Then** system outputs valid JSON containing run_metadata, metrics_summary, and optional signal/execution lists.
2. **Given** JSON output generated, **When** parsed by external tool, **Then** all fields conform to documented schema (timestamps in ISO 8601 UTC, numeric metrics with proper types).
3. **Given** backtest fails or has zero trades, **When** JSON output requested, **Then** system outputs error/status structure with meaningful diagnostic information.

---

### User Story 5 - Generate Signals Without Execution (Dry-Run Mode) (Priority: P5)

User wants to generate trade signals without executing them to validate signal logic, tune parameters, or debug strategy behavior before full backtest.

**Why this priority**: Supports development workflow; enables rapid iteration without execution overhead.

**Independent Test**: Run backtest with `--dry-run` flag → system generates signals only, outputs signal list with timestamps and parameters, but skips execution simulation.

**Acceptance Scenarios**:

1. **Given** any direction mode, **When** user adds `--dry-run` flag, **Then** system loads data, generates signals according to direction, outputs signal details, but does not call simulate_execution().
2. **Given** dry-run mode with JSON output, **When** backtest completes, **Then** JSON contains signals array with signal metadata but empty executions array.
3. **Given** dry-run output reviewed, **When** user validates signal frequency and parameters, **Then** user can proceed to full execution backtest with confidence.

---

### Edge Cases

- Dataset with no qualifying signals for specified direction → backtest completes with zero trades, metrics reflect insufficient data status.
- BOTH mode detects long and short signals at different timestamps → earlier signal EXECUTES (timestamp-first wins), later signal SUPPRESSED (skipped without execution).
- BOTH mode detects simultaneous long and short signals at identical timestamp → REJECT BOTH signals (indicates choppy market/indecision), log conflict with timestamp and currency pair, continue processing without executing either signal.
- Data file path does not exist → system exits with clear error message before attempting data load.
- Invalid direction parameter provided → argument parser rejects with usage help message.
- Execution simulation encounters incomplete candle data (trade cannot exit) → log warning, exclude incomplete trade from metrics.
- JSON output contains NaN or Infinity values from empty metric sets → serialize as null or "NaN" string per JSON compatibility.
- User specifies both dry-run and JSON output → system outputs JSON with signals but no executions.
- Multiple backtests run sequentially with same output directory → timestamped filenames (backtest*{direction}*{YYYYMMDD}\_{HHMMSS}.{ext}) prevent overwrites.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST accept `--direction` argument with values {LONG, SHORT, BOTH} to control which signal generation function is invoked.
- **FR-002**: System MUST route LONG direction to generate_long_signals() function from signal_generator module.
- **FR-003**: System MUST route SHORT direction to generate_short_signals() function from signal_generator module.
- **FR-004**: System MUST route BOTH direction to invoke both generate_long_signals() and generate_short_signals() functions.
- **FR-005**: System MUST accept `--data` argument specifying path to CSV price data file and validate file exists before processing.
- **FR-006**: System MUST accept `--output-format` argument with values {text, json} to control output format (default: text).
- **FR-007**: System MUST accept `--dry-run` flag to generate signals without executing them (signal-only mode).
- **FR-008**: System MUST load historical candle data using existing data ingestion module for specified data file.
- **FR-009**: System MUST execute each generated signal using simulate_execution() function from backtest.execution module.
- **FR-010**: System MUST aggregate trade executions into performance metrics using existing metrics calculation logic.
- **FR-011**: System MUST output text-formatted results containing metrics summary, run metadata, and key statistics when text format selected.
- **FR-012**: System MUST output JSON-formatted results conforming to defined schema when json format selected.
- **FR-013**: System MUST handle BOTH direction by preventing simultaneous opposing positions in same currency pair.
- **FR-014**: System MUST apply conflict resolution when BOTH mode generates overlapping long and short signals: if timestamps differ, timestamp-first wins; if timestamps are identical, reject both signals (indicates choppy market conditions unsuitable for trade entry).
- **FR-015**: System MUST create backtest run metadata including run_id, parameters_hash, manifest_ref, start_time, end_time, total_candles_processed, reproducibility_hash.
- **FR-016**: System MUST calculate metrics summary including trade_count, win_count, loss_count, win_rate, avg_win_r, avg_loss_r, avg_r, expectancy, sharpe_estimate, profit_factor, max_drawdown_r.
- **FR-017**: System MUST exit with error code 1 and clear error message if data file not found.
- **FR-018**: System MUST log backtest progress at INFO level including signal generation count, execution progress, and final metrics.
- **FR-019**: System MUST support `--log-level` argument with values {DEBUG, INFO, WARNING, ERROR} to control logging verbosity.
- **FR-020**: System MUST save output results to `--output` directory path (default: results/) using filename format: backtest*{direction}*{YYYYMMDD}\_{HHMMSS}.{ext} where direction is lowercase (long/short/both) and ext is txt or json.
- **FR-021**: In dry-run mode, system MUST generate signals but skip simulate_execution() calls and output signal list containing essential fields: timestamp, pair, direction, entry_price, stop_price.
- **FR-022**: In BOTH mode, system MUST calculate separate metrics for long_only trades (filtering long direction trades), short_only trades (filtering short direction trades), and combined performance (aggregating all trades together for win_rate, avg_r, and other metrics).
- **FR-023**: System MUST serialize datetime objects as ISO 8601 UTC strings in JSON output.
- **FR-024**: System MUST serialize NaN/Infinity metric values as null or string representation in JSON output for compatibility.

### Key Entities

- **BacktestRun**: Metadata container with run_id, parameters_hash, manifest_ref, timestamps, candles_processed, reproducibility_hash.
- **MetricsSummary**: Performance metrics container with trade counts, win_rate, R-multiples, expectancy, Sharpe estimate, profit factor, max drawdown.
- **DirectionMode**: Enumeration or string literal controlling signal generation {LONG, SHORT, BOTH}.
- **OutputFormat**: Enumeration or string literal controlling result format {text, json}.
- **TradeSignal**: Signal object containing id, timestamp_utc, pair, direction, entry_price, stop_price, risk parameters, calculated position size.
- **TradeExecution**: Execution result containing entry/exit details, PnL in R-multiples, exit_reason, execution timestamps.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: User can execute LONG-only backtest on any valid dataset and receive complete performance metrics within 30 seconds for 100K candles.
- **SC-002**: User can execute SHORT-only backtest on any valid dataset and receive performance metrics matching LONG backtest structure.
- **SC-003**: User can execute BOTH directions backtest and receive combined metrics with direction-specific breakdowns showing separate long and short performance.
- **SC-004**: User can generate JSON output from any backtest that validates against defined JSON schema with zero parsing errors.
- **SC-005**: User can run dry-run mode and receive signal list within 10 seconds without execution overhead for parameter tuning workflows.
- **SC-006**: 95% of backtest runs complete successfully without crashes or data errors when provided valid input files.
- **SC-007**: All backtest runs produce deterministic results (same input → same output) verified by reproducibility_hash matching across reruns.
- **SC-008**: User can understand backtest results from text output without consulting documentation (clear labels, units, interpretable metrics).
- **SC-009**: JSON output size remains under 10MB for typical 100K candle backtest to enable efficient storage and transmission.
- **SC-010**: Conflict resolution in BOTH mode prevents 100% of simultaneous opposing positions per pair.
