# Feature Specification: Strategy Templating Framework

**Feature Branch**: `022-strategy-templating`
**Created**: 2025-12-26
**Status**: Draft
**Input**: Issue #46 - Make strategies templatable (scaffold + docs + reference implementation)

## Clarifications

### Session 2025-12-26

- Q: Should scaffolded strategies be auto-registered in the strategy registry, or should users manually register them? → A: Auto-register - scaffold adds entry to registry automatically
- Q: Where should the scaffold command create the new strategy directory? → A: `src/strategy/<name>/` - alongside existing strategies
- Q: When strategy validation fails, should the system halt immediately or continue with a warning? → A: Hard fail - exit with error code, do not proceed

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Create New Strategy from Template (Priority: P1)

A new user wants to implement a custom trading strategy. They run a scaffold command that generates a working strategy template with clearly marked TODO sections. The generated strategy compiles and can be executed immediately in a basic backtest, even before customization.

**Why this priority**: This is the core deliverable—enabling users to start quickly without reverse-engineering engine internals. It directly addresses the main pain point from Issue #46.

**Independent Test**: Can be fully tested by running the scaffold command, then executing a backtest with the generated template, and verifying it runs without errors.

**Acceptance Scenarios**:

1. **Given** a user with CLI access, **When** they run the scaffold command with a strategy name, **Then** a new strategy directory is created with all required files.
2. **Given** the scaffolded strategy template, **When** the user runs a backtest without modifications, **Then** the backtest executes successfully (no runtime errors).
3. **Given** the scaffolded template, **When** the user reads the generated code, **Then** they find clearly marked TODO comments explaining what to customize.

---

### User Story 2 - Validate Strategy Contract at Load Time (Priority: P1)

A developer implements a custom strategy but accidentally omits a required method. When they attempt to run a backtest, the system validates the strategy contract at startup and fails fast with a clear error message explaining exactly which method is missing and what signature is expected.

**Why this priority**: Fail-fast validation prevents frustrating debugging sessions and is essential for a good developer experience. This is equally important as the scaffold for adoption.

**Independent Test**: Can be tested by creating an incomplete strategy (missing a required method), then running a backtest and verifying the error message is clear and actionable.

**Acceptance Scenarios**:

1. **Given** a strategy missing the `generate_signals` method, **When** the engine loads the strategy, **Then** validation fails with message: "Strategy missing required method: generate_signals(candles, parameters) -> list"
2. **Given** a strategy with incorrect method signature, **When** the engine loads the strategy, **Then** validation fails explaining the expected vs. actual signature.
3. **Given** a strategy missing required metadata fields, **When** the engine loads the strategy, **Then** validation fails listing the missing fields.

---

### User Story 3 - Reference Strategy Implementation (Priority: P2)

A user wants to understand how to structure a real strategy by studying a working example. They find a reference strategy that uses the template pattern, demonstrates best practices, and passes all validation checks. This strategy runs in a basic backtest and produces meaningful results.

**Why this priority**: Examples are critical for learning, but the scaffold and validation are prerequisites for the reference to be useful.

**Independent Test**: Can be tested by running the reference strategy in a backtest and verifying it produces trades with proper entry/exit signals.

**Acceptance Scenarios**:

1. **Given** the reference strategy, **When** executed in a backtest, **Then** it generates at least one trade signal.
2. **Given** the reference strategy source code, **When** reviewed for documentation, **Then** each section includes comments explaining its purpose.

---

### User Story 4 - Strategy Authoring Documentation (Priority: P2)

A user reads the strategy authoring guide to understand the lifecycle, constraints, and integration points. The documentation explains when each method is called, what data is available, and how the strategy interacts with the backtesting engine.

**Why this priority**: Documentation supports adoption and reduces support burden, but is secondary to having working functionality.

**Independent Test**: Can be validated by having a new user read the documentation and successfully implement a strategy without additional assistance.

**Acceptance Scenarios**:

1. **Given** the documentation, **When** a user reads the "Strategy Lifecycle" section, **Then** they understand the sequence: load → validate → inject indicators → call generate_signals.
2. **Given** the documentation, **When** a user reads the "Required Methods" section, **Then** they find complete signatures with parameter and return type descriptions.

---

### Edge Cases

- What happens when a strategy declares indicators that don't exist in the registry?
- What happens when `generate_signals` returns malformed `TradeSignal` objects?
- How does validation behave when the strategy class exists but isn't properly instantiable?
- What happens if `scan_vectorized` is implemented but returns wrong tuple size?

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST provide a CLI scaffold command that generates a new strategy directory at `src/strategy/<name>/` with template files
- **FR-002**: System MUST generate a strategy class file that implements the `Strategy` Protocol with all required methods stubbed
- **FR-003**: Generated template MUST include TODO markers in each method body indicating what the user should implement
- **FR-004**: Generated template MUST be syntactically valid Python and immediately executable
- **FR-005**: System MUST validate strategy compliance before execution and exit with non-zero error code if validation fails, checking for:
  - Presence of required `metadata` property
  - Presence of required `generate_signals` method with correct signature
  - Valid `StrategyMetadata` with non-empty `name`, `version`, and `required_indicators`
- **FR-006**: System MUST provide clear, actionable error messages when validation fails, including:
  - Name of missing method/property
  - Expected signature with parameter names and types
  - Example of correct implementation
- **FR-007**: System MUST include a reference strategy that demonstrates the template pattern and passes all validations
- **FR-008**: System MUST automatically register scaffolded strategies in the strategy registry upon scaffold command completion
- **FR-009**: Documentation MUST include a complete strategy authoring guide explaining:
  - Strategy lifecycle (when methods are called)
  - Available data in each method
  - Return type requirements
  - Integration with indicator system
  - Integration with risk management system

### Key Entities

- **StrategyTemplate**: The scaffolded structure including strategy class, configuration, and module initialization
- **StrategyValidator**: Component that validates strategies implement the required contract before execution
- **StrategyMetadata**: Existing dataclass describing name, version, required indicators, and tags
- **Strategy Protocol**: Existing protocol defining required methods (metadata, generate_signals, optional scan_vectorized)

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: New users can create a working strategy scaffold in under 30 seconds using the CLI
- **SC-002**: Scaffolded strategies execute in a basic backtest without modification
- **SC-003**: 100% of contract violations are caught at load time (before backtest execution begins)
- **SC-004**: Error messages for contract violations include the specific fix needed (method name, signature, example)
- **SC-005**: Reference strategy passes all validation checks and produces trades in backtest
- **SC-006**: Strategy authoring documentation covers all required methods and lifecycle phases
