# Feature Specification: Parallel Indicator Parameter Sweep Testing

**Feature Branch**: `024-parallel-param-sweep`
**Created**: 2025-12-30
**Status**: Draft
**Input**: Combine GitHub issues #9 (Adjustable Indicator Parameters) and #10 (Parallelized Execution)
**Constraint**: Must use existing vectorized scanning methods; per-candle loops are prohibited

## Clarifications

### Session 2025-12-30

- Q: How should invalid constraint combinations (e.g., fast_ema ≥ slow_ema) be handled? → A: Skip silently and log warning at end (show count of skipped)
- Q: How should large sweeps (1000+ combinations) be managed for memory? → A: Warn at threshold (>500) and require confirmation, but no hard limit

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Interactive Indicator Parameter Entry (Priority: P1)

A quant developer runs the backtest CLI with `--test_range` flag. The system loads the selected strategy, reads its `required_indicators` from metadata, retrieves each indicator's configurable parameters from the registry, and prompts the user for each. The user can accept defaults, specify a single value, or define a range.

**Why this priority**: Core interaction model - must work before parallel execution matters.

**Independent Test**: Can be fully tested by running `--test_range` and verifying all indicator parameters are prompted with correct defaults.

**Acceptance Scenarios**:

1. **Given** `--test_range` flag and TrendPullbackStrategy with required indicators [fast_ema, slow_ema, atr, stoch_rsi], **When** CLI starts, **Then** user is prompted for each indicator's configurable parameters.
2. **Given** prompts for `fast_ema`, **When** user sees prompt `Enter fast_ema period (20):` and presses Enter, **Then** the default value 20 is used.
3. **Given** prompt for `fast_ema period`, **When** user enters `10-30 step 5`, **Then** system interprets as range [10, 15, 20, 25, 30].
4. **Given** prompt for `stoch_rsi`, **When** CLI displays, **Then** all configurable params are shown: rsi_period (14), stoch_period (14), k_smooth (3), d_smooth (3).

---

### User Story 2 - Semantic Indicator Names (Priority: P1)

Strategy declares indicators with semantic names (e.g., `fast_ema`, `slow_ema`) rather than hardcoded periods (`ema20`, `ema50`). This allows the sweep to dynamically assign periods to each semantic role.

**Why this priority**: Enables meaningful parameter ranges while maintaining strategy semantics.

**Independent Test**: Can be tested by verifying strategy metadata uses semantic names and prompts reflect those names.

**Acceptance Scenarios**:

1. **Given** TrendPullbackStrategy declares `required_indicators=["fast_ema", "slow_ema", "atr", "stoch_rsi"]`, **When** `--test_range` runs, **Then** prompts show `fast_ema period`, `slow_ema period`, etc.
2. **Given** user sets fast_ema period=15 and slow_ema period=60, **When** backtest runs, **Then** system computes ema15 and ema60 for the respective roles.
3. **Given** sweep generates combinations where fast_ema period >= slow_ema period, **When** combinations are filtered, **Then** those invalid combinations are skipped with a warning.

---

### User Story 3 - Multi-Parameter Cartesian Sweep (Priority: P2)

After collecting all indicator parameter inputs, the system generates the cartesian product of all ranges and runs backtests for each combination in parallel.

**Why this priority**: Builds on P1 - requires parameter collection to work first.

**Independent Test**: Can be tested by specifying 2 parameter ranges and verifying all combinations are tested.

**Acceptance Scenarios**:

1. **Given** fast_ema period=[10, 20] and slow_ema period=[50, 100], **When** sweep runs, **Then** 4 combinations are tested.
2. **Given** a large sweep with 100+ combinations, **When** executed, **Then** progress is displayed showing combinations completed/total.
3. **Given** all combinations complete, **When** results display, **Then** they are sorted by performance metric with indicator parameter labels.

---

### User Story 4 - Parallel Execution with Worker Control (Priority: P3)

The system runs backtests in parallel using available CPU cores. Users can optionally limit concurrency with `--max-workers`.

**Why this priority**: Performance optimization builds on functional features.

**Independent Test**: Can be tested by running a sweep with different `--max-workers` settings and measuring speedup.

**Acceptance Scenarios**:

1. **Given** 4 available CPU cores and no max-workers specified, **When** sweep runs, **Then** system uses 3 workers (leaving 1 free).
2. **Given** `--max-workers 2` flag, **When** sweep runs, **Then** only 2 backtests run concurrently.
3. **Given** `--sequential` flag, **When** sweep runs, **Then** backtests run one at a time for debugging.

---

### User Story 5 - Results Export (Priority: P3)

Users can export sweep results to CSV for further analysis. Results include all indicator parameter combinations and metrics.

**Why this priority**: Enables downstream analysis; dependent on P1-P3.

**Independent Test**: Can be tested by running a sweep and verifying CSV output.

**Acceptance Scenarios**:

1. **Given** a completed sweep, **When** export runs, **Then** CSV contains columns for each indicator parameter plus metrics (Sharpe, win rate, PnL).
2. **Given** CSV export, **When** opened in spreadsheet software, **Then** data parses correctly.

---

### Edge Cases

- What happens when an indicator has no configurable parameters?
- How does system handle user entering invalid range syntax?
- What happens when one combination fails while others succeed?
- What happens if strategy doesn't implement `scan_vectorized()`?
- How are semantic constraints handled (e.g., fast_ema period must be < slow_ema period)? **Clarified:** Skip invalid combinations silently and log count at end.
- What happens if two indicator parameters have the same name (e.g., both EMAs have "period")?

## Requirements _(mandatory)_

### Functional Requirements

**CLI Interface**:

- **FR-001**: System MUST support `--test_range` flag to enable interactive indicator parameter sweep mode.
- **FR-002**: System MUST prompt user for each configurable parameter of each required indicator.
- **FR-003**: System MUST display default value in parentheses for each prompt (e.g., `Enter fast_ema period (20):`).
- **FR-004**: System MUST accept empty input as "use default".
- **FR-005**: System MUST accept single values (e.g., `15`) as fixed parameters.
- **FR-006**: System MUST accept range syntax `start-end step increment` (e.g., `10-30 step 5`).
- **FR-007**: System MUST validate range inputs and display clear error messages for malformed syntax.

**Indicator Discovery**:

- **FR-008**: System MUST read `required_indicators` from strategy metadata.
- **FR-009**: System MUST look up each indicator in the registry to retrieve its `params` dict.
- **FR-010**: System MUST prompt for each key in the indicator's `params` dict.
- **FR-011**: System MUST NOT hardcode indicator-specific parameter names or constraints.
- **FR-012**: System MUST work with any strategy implementing the `Strategy` protocol.

**Semantic Indicator Names**:

- **FR-013**: Strategies SHOULD declare indicators with semantic names (e.g., `fast_ema`, `slow_ema`) rather than hardcoded period names.
- **FR-014**: Registry MUST support registering indicators with semantic names that map to parameterized computations.
- **FR-015**: System MUST use the semantic name as a prefix in prompts (e.g., `fast_ema period`).

**Sweep Generation**:

- **FR-016**: System MUST generate cartesian product of all indicator parameter ranges.
- **FR-017**: System MUST calculate total combinations before execution and display to user.
- **FR-018**: System MUST warn and require confirmation before starting large sweeps (>500 combinations).
- **FR-019**: System SHOULD support semantic constraints (e.g., fast_ema period < slow_ema period) declared by strategies.

**Execution**:

- **FR-020**: System MUST use existing vectorized `scan_vectorized()` method for all backtests.
- **FR-021**: System MUST NOT use per-candle loops for scanning or simulation.
- **FR-022**: System MUST recompute indicators for each parameter combination before running the backtest.
- **FR-023**: System MUST execute parameter combinations in parallel using `ProcessPoolExecutor`.
- **FR-023a**: System MUST auto-detect CPU cores and use N-1 workers by default.
- **FR-023b**: System MUST support `--max-workers` flag to limit concurrency.
- **FR-024**: System MUST support `--sequential` flag for debugging mode.

**Results**:

- **FR-025**: System MUST label each result with the exact indicator parameter set used.
- **FR-026**: System MUST rank results by configurable metric (default: Sharpe ratio).
- **FR-027**: System MUST support CSV export of all sweep results.
- **FR-028**: System MUST display progress during sweep execution.

**Integration**:

- **FR-029**: System MUST leverage existing `src/backtest/parallel.py` module.
- **FR-030**: System MUST integrate with existing `BatchScan` and `BatchSimulation` classes.
- **FR-031**: System MUST integrate with existing indicator registry in `src/indicators/registry/`.

### Key Entities

- **IndicatorSpec** (existing): Registry entry with `name`, `params` (defaults), and `compute` function.
- **SemanticIndicator**: Named indicator role (e.g., "fast_ema") with underlying computation type.
- **IndicatorParameterInput**: User's input for an indicator parameter (single value or range).
- **IndicatorParameterSet**: A specific combination of all indicator parameter values for one backtest.
- **SweepResult**: Aggregated results from all parameter combinations.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Users can configure an indicator parameter sweep for any strategy in under 90 seconds of interactive prompting.
- **SC-002**: Indicator discovery works with 100% of strategies implementing the `Strategy` protocol.
- **SC-003**: Parallel execution achieves at least 70% efficiency vs theoretical linear speedup.
- **SC-004**: System processes 100 indicator parameter combinations on 1-year hourly data in under 15 minutes on 4-core hardware (includes indicator recomputation).
- **SC-005**: 100% of sweep results are correctly labeled with their indicator parameter sets.
- **SC-006**: Progress updates display at least every 5 seconds during execution.

## Assumptions

- Strategies implement `scan_vectorized()` for high-performance scanning.
- Strategies declare `required_indicators` in their metadata.
- Indicators are registered in the registry with their `params` dict containing defaults.
- OHLCV data is already loaded before sweep execution.
- Users have multi-core CPUs (2+ logical cores) for parallel benefits.
- The existing `run_parallel()` function in `src/backtest/parallel.py` is the foundation for parallel execution.
- Semantic indicator names (e.g., `fast_ema`, `slow_ema`) will require strategy metadata updates.
