# Feature Specification: Update 001 Test Suite Alignment

**Feature Branch**: `003-update-001-tests`
**Created**: 2025-10-30
**Status**: Draft
**Input**: User description: "Update all 001 tests so that they work for the current code base. Either update the existing tests, or remove tests that are no longer relevant."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Validate Core Strategy Behavior (Priority: P1)

A maintainer updates or runs the 001 Trend Pullback strategy tests to confirm the strategy produces expected signals and risk adjustments after recent refactors without manual inspection.

**Why this priority**: Ensures the foundational strategy (001) remains trustworthy; broken tests erode confidence and slow future changes.

**Independent Test**: Running the updated 001 test suite in isolation yields deterministic pass/fail outcomes covering entry, exit, indicator calculation, and risk sizing.

**Acceptance Scenarios**:

1. **Given** the current code base, **When** the 001 unit tests are executed, **Then** all valid tests pass with no unexpected failures.
2. **Given** an intentional change that violates a documented strategy rule, **When** affected tests run, **Then** at least one test fails clearly indicating the broken rule.

---

### User Story 2 - Remove Obsolete / Redundant Tests (Priority: P2)

A maintainer audits the 001 test files, removing tests that target deprecated interfaces or redundant coverage to reduce noise.

**Why this priority**: Eliminates false failures and maintenance overhead, improving signal quality of the suite.

**Independent Test**: After removal, running the suite shows zero skipped-for-obsolescence tests and reduced count only where redundancy existed.

**Acceptance Scenarios**:

1. **Given** a test referencing an interface no longer present, **When** the audit is completed, **Then** that test file or case is removed with justification noted in commit message.
2. **Given** two tests asserting identical behavior, **When** consolidation occurs, **Then** one remains with comprehensive assertions; the other is deleted.

---

### User Story 3 - Introduce Deterministic Fixtures (Priority: P3)

Add or adjust fixtures so indicator and signal tests rely on controlled sample data rather than large historical datasets, enabling fast local and CI runs.

**Why this priority**: Improves execution speed and reduces flakiness from evolving external sample data.

**Independent Test**: Running only the deterministic fixture-based tests completes quickly (<5s) and yields consistent results across runs.

**Acceptance Scenarios**:

1. **Given** new small fixture datasets, **When** indicator tests run, **Then** results match documented expected values exactly.
2. **Given** multiple consecutive runs, **When** tests execute, **Then** no variance in pass/fail outcomes or numeric assertions.

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

- Data window shorter than required lookback (e.g., EMA period > dataset length) should cause test to assert graceful handling (e.g., partial warm-up rather than failure).
- Missing optional columns in fixture (e.g., volume) must not break tests targeting price-based indicators.
- Zero volatility period (flat prices) should produce no false signals for momentum-based entries.
- Extreme outlier candle in fixture should not produce division-by-zero or overflow in risk calculations.
- Test removal must not accidentally delete shared utilities used by remaining tests.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: The 001 test suite MUST execute successfully against the current code base with zero unexpected failures.
- **FR-002**: Tests MUST be updated to reflect current public strategy and risk model interfaces (no references to removed methods or classes).
- **FR-003**: Obsolete or redundant tests MUST be removed; each removal MUST have an explanatory commit message note.
- **FR-004**: Remaining tests MUST be deterministic (no reliance on current date/time, random seeds without seeding, or external network/data fetch).
- **FR-005**: Indicator computation tests MUST validate expected values for core indicators used by 001 (e.g., EMA, ATR) using fixed fixture data.
- **FR-006**: Signal generation tests MUST assert both long and short (if applicable) entry/exit criteria aligned with documented 001 rules.
- **FR-007**: Risk sizing tests MUST confirm position size calculations under normal and edge conditions (e.g., minimal account size, high volatility).
- **FR-008**: Performance or timing-sensitive tests MUST complete within an acceptable threshold (<5 seconds for fixture-based unit subset).
- **FR-009**: Any flaky test identified MUST be stabilized via fixture adjustment or logic correction before feature completion.
- **FR-010**: Test names and docstrings MUST clearly state purpose and covered behavior for maintainability.

No clarification markers required; defaults chosen based on existing strategy conventions.

### Key Entities *(include if feature involves data)*

- **Strategy Configuration**: Represents parameter set (period lengths, thresholds) used by tests to validate signals; attributes: parameter name, value.
- **Fixture Price Series**: Simplified dataset of OHLC (and optional volume) used for deterministic indicator and signal validation; attributes: timestamp, open, high, low, close.
- **Risk Parameters**: Position sizing inputs (account size, risk per trade, volatility measure) used in risk tests; attributes: account_balance, risk_fraction, volatility_value.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: 100% of retained 001 tests pass on first run of CI after update.
- **SC-002**: Total count of 001 tests decreases only where redundancy/obsolescence is documented (net reduction <=30% unless justified).
- **SC-003**: Deterministic subset (unit-level tests excluding integration) completes in <5 seconds on standard CI hardware.
- **SC-004**: Zero flaky reruns required across three consecutive CI runs post-change.
- **SC-005**: Each functional requirement FR-001 through FR-010 has at least one direct test case asserting its behavior.

## Assumptions

- Existing 001 strategy contract in `specs/001-trend-pullback/contracts` reflects intended current strategy rules.
- Current code base public interfaces are stable during the test update window.
- CI environment performance roughly matches local execution for timing targets.
- No new indicators need to be introduced—scope limited to alignment, not feature expansion.

## Out of Scope

- Adding new strategy logic or parameters.
- Refactoring production code unrelated to enabling tests.
- Introducing performance benchmarking beyond simple execution time threshold.

## Dependencies

- Access to existing test files and fixtures under `tests/`.
- Strategy and indicator modules in `src/strategy` and `src/indicators`.
- Risk model modules in `src/risk`.

## Risks

- Hidden coupling between tests and deprecated internals may require minor refactors (mitigation: limit to interface-level updates only).
- Large deletions could accidentally remove still-needed shared utilities (mitigation: review diff and run full suite).

## Acceptance Summary

Feature accepted when all measurable outcomes (SC-001..SC-005) are met and functional requirements have corresponding passing tests.
