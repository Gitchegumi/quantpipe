# Feature Specification: Decouple Indicator Registration

**Feature Branch**: `026-decouple-indicators`
**Created**: 2026-01-14
**Status**: Draft
**Input**: User description: "Decouple indicator registration to enable strategy-specific indicators without modifying core registry."

## User Scenarios & Testing

### User Story 1 - Strategy-Specific Indicator Definition (Priority: P1)

A strategy developer wants to define and use custom technical indicators (e.g., "ema_55_close", "custom_volatility_band") directly within their strategy class or module, without modifying the global indicator registry or core engine code.

**Why this priority**: This is the core value proposition. It enables creating portable, self-contained strategies and rapid prototyping without "polluting" the global codebase or requiring core PRs for strategy-specific logic.

**Independent Test**: Create a new strategy file (e.g., `TestCustomIndicatorStrategy`), define a simple custom indicator function within it (e.g., returns `close * 1.01`), and run a backtest using this strategy. The backtest should succeed, and the indicator data should be present in the simulation.

**Acceptance Scenarios**:

1. **Given** a strategy that defines a mapping for a custom indicator string (e.g., "my_custom_indicator"), **When** the backtest engine initializes and parses indicators, **Then** it uses the strategy-provided logic to calculate "my_custom_indicator".
2. **Given** a strategy that uses a custom indicator, **When** the backtest runs, **Then** the indicator values are correctly calculated and available to the strategy logic (signals/rules).
3. **Given** a strategy file containing a custom indicator, **When** valid parameters are passed, **Then** the backtest completes without "Indicator not found" errors.

---

### User Story 2 - Backward Compatibility (Priority: P1)

Existing strategies that rely on the global indicator registry MUST continue to function exactly as before.

**Why this priority**: Ensuring no regressions for the existing strategy library is critical.

**Independent Test**: Run the full suite of existing integration tests and sample strategy backtests.

**Acceptance Scenarios**:

1. **Given** a standard strategy using global indicators (e.g., "rsi_14", "sma_200"), **When** a backtest is run, **Then** the system resolves these indicators using the global registry.
2. **Given** a strategy uses _both_ global and custom indicators, **When** a backtest is run, **Then** both are resolved correctly.

### Edge Cases

- **Naming Conflict**: What happens if a strategy defines an indicator with the same name as a global one?

  - _Expected Behavior_: The backtest engine prioritizes the strategy's definition, allowing strategies to override default behavior if desired.

- **Invalid Custom Implementation**: What happens if the strategy's custom indicator function raises an exception during execution?

  - _Expected Behavior_: The system catches the error, logs it with context (Strategy Name, Indicator Name, Error Message), and halts the backtest with a clear failure message.

- **Missing Indicator**: What happens if a strategy requests an indicator that is neither in the global registry nor defined by the strategy?

  - _Expected Behavior_: The system fails fast with a "Indicator not found: [Name]" error, listing available strategy-specific indicators in the error message if possible.

- **Missing Dependency**: What happens if a custom indicator requires data columns that are not present?
  - _Expected Behavior_: Standard pandas/numpy errors usually occur. The system should ideally catch `KeyError` during enrichment and provide a helpful message suggesting the data might be missing.

## Requirements

### Functional Requirements

- **FR-001**: The `Strategy` class MUST provide a `get_custom_indicators(self)` method returning a `dict[str, Callable]` of indicator definitions.
- **FR-002**: The backtest orchestration/data ingestion pipeline MUST query the Strategy for indicator definitions when (or before/after) looking up the global registry.
- **FR-003**: Strategy-defined indicators MUST take precedence over or fallback to the global registry (Need to define precedence: typically local > global allows overriding).
  - _Assumption_: Strategy-specific definitions take precedence to allow overriding global behavior if desired.
- **FR-004**: Custom indicators MUST support the same interface as global indicators (accepting `ohlcv` data, returning enriched DataFrame/Series).
- **FR-005**: The solution MUST allow defining indicators that require parameters (parsed from the string, e.g., "my_indicator_10_2.5").

### Assumptions

- **Standard Parsing**: Custom indicators MUST follow the standard naming conventions (e.g., `name(args)` or `name123`) to be correctly parsed by the core engine's `parse_indicator_string` utility. Custom filtering/parsing logic is out of scope.

### Key Entities

- **Strategy**: The base class or interface will be extended to support indicator lookup/registration.,
- **IndicatorRegistry**: The existing component that currently holds all mappings.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A new strategy with a unique, non-global indicator can be implemented and backtested adding files ONLY in the `src/strategy/` directory (and its subdirectories).
- **SC-002**: 100% of existing strategies and integration tests pass without modification.
- **SC-003**: Verify that a strategy can define at least 1 custom indicator and use it in a signal generation rule.

## Clarifications

### Session 2026-01-14

- Q: How should strategies define custom indicators? -> A: Use an instance method `get_custom_indicators(self)` returning `dict[str, Callable]`.
