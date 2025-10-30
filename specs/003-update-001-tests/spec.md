# Feature Specification: Update 001 Test Suite Alignment

**Feature Branch**: `003-update-001-tests`
**Created**: 2025-10-30
**Status**: Draft (post-analysis adjustments applied)
**Input**: User description: "Update all 001 tests so that they work for the current code base. Either update the existing tests, or remove tests that are no longer relevant."

## Clarifications

### Session 2025-10-30

- Q: Define performance test tiering approach → A: Three tiers: Unit (<5s), Integration (<30s), Performance (<120s)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Validate Core Strategy Behavior (Priority: P1)

Ensures the foundational strategy (001) remains trustworthy after refactors.

**Independent Test**: Running unit + integration tiers yields deterministic pass/fail outcomes covering entry, exit, indicator calculation, and risk sizing.

**Acceptance Scenarios**:

1. Given current code base, when unit tests run, then all valid tests pass.
2. Given intentional rule violation, when affected tests run, then at least one fails clearly indicating the broken rule.

---

### User Story 2 - Remove Obsolete / Redundant Tests (Priority: P2)

Reduces noise by deleting tests for deprecated interfaces or redundant coverage.

**Independent Test**: Suite shows reduced count only where redundancy existed; no obsolete references.

**Acceptance Scenarios**:

1. Given a test referencing removed interface, when audit completes, then test is removed with justification note.
2. Given two tests asserting identical behavior, when consolidated, then one comprehensive test remains.

---

### User Story 3 - Introduce Deterministic Fixtures (Priority: P3)

Replaces large historical datasets with deterministic synthetic fixtures for speed and stability.

**Independent Test**: Fixture-based unit tests complete <5s and yield consistent results across runs.

**Acceptance Scenarios**:

1. Given new fixtures, when indicator tests run, then results match expected numeric values exactly.
2. Given multiple consecutive runs, when tests execute, then no variance in outcomes.

---

### Edge Cases

- Data window shorter than required lookback (e.g., EMA period > dataset length) → indicators return None/NaN for first (lookback-1) bars; tests assert NaN count equals lookback-1.
- Missing optional columns (e.g., volume) must not break price-based indicator tests.
- Zero volatility (flat prices) should produce no false momentum signals.
- Extreme outlier candle must not produce division-by-zero or numeric overflow in risk sizing.
- Test removal must not delete shared utilities needed by remaining tests.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The 001 test suite MUST execute successfully against the current code base with zero unexpected failures.
- **FR-002**: Tests MUST be updated to reflect current public strategy and risk model interfaces (no references to removed methods or classes).
- **FR-003**: Obsolete or redundant tests MUST be removed; each removal MUST have an explanatory commit message note.
- **FR-004**: Remaining tests MUST be deterministic (no reliance on current date/time, random seeds without seeding, or external network/data fetch).
- **FR-005**: Indicator tests MUST validate exact expected values for EMA(20), EMA(50), and ATR(14) using deterministic synthetic fixtures.
- **FR-006**: Signal generation tests MUST assert both long and short entry/exit criteria aligned with documented 001 rules; expected counts defined in mapping.
- **FR-007**: Risk sizing tests MUST confirm position size calculations under normal and edge conditions (minimal account balance = 1000, high volatility spike, large spread scenario) without producing negative or overflow sizes.
- **FR-008**: Provide a unit-tier timing assertion mechanism (e.g., perf counter) enforcing SC-003 (<5s threshold).
- **FR-009**: A test is flaky if ≥1 failure across 5 identical consecutive runs; any flaky test MUST be stabilized before feature completion.
- **FR-010**: Test names and docstrings MUST clearly state purpose; docstrings follow template: first line 1-sentence summary; blank line; optional "Parameters:" and "Returns:".
- **FR-011**: Categorize tests into Unit (<5s), Integration (<30s), Performance (<120s). Each test file declares exactly ONE tier marker; mixed-tier files prohibited. Performance tier present but optional in default fast CI run.
- **FR-012**: All new test logging (if used) MUST use lazy percent-style formatting (no f-strings) per Constitution Principle X.

### Key Entities

- **Strategy Configuration**: parameter name, value.
- **Fixture Price Series**: timestamp, open, high, low, close (optional volume).
- **Risk Parameters**: account_balance, risk_fraction, volatility_value.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of retained 001 tests pass on first CI run.
- **SC-002**: Net test reduction ≤30% unless justified (duplicate, deprecated API, parameterized consolidation).
- **SC-003**: Unit tier completes <5s (±20% tolerance; hard fail if >6s) on baseline CI runner.
- **SC-004**: Zero flaky failures across iteration sets (unit 3x, integration 3x, performance 5x subset).
- **SC-005**: Each functional requirement FR-001..FR-012 has ≥1 direct test assertion.
- **SC-006**: Integration tier completes <30s (±20% tolerance; hard fail if >36s).
- **SC-007**: Performance tier completes <120s (±20% tolerance; hard fail if >144s) and is isolatable from default fast run.
- **SC-008**: Tier enforcement validated: every test file has exactly one tier marker; no mixed-tier files.
- **SC-009**: Flakiness definition satisfied: 0 flaky tests after stabilization loop.

## Assumptions

- Existing 001 strategy contract reflects intended rules.
- Public interfaces stable during update window.
- CI baseline hardware: GitHub Actions ubuntu-latest ~2 vCPU, 7 GB RAM.
- Scope limited to alignment, no new indicators.

## Out of Scope

- Adding new strategy logic or parameters.
- Refactoring production code unrelated to enabling tests.
- Performance benchmarking beyond simple execution time thresholds.
- Drawdown limit tests (covered by broader risk management suite).

## Dependencies

- Access to existing test files and fixtures under `tests/`.
- Strategy and indicator modules in `src/strategy` and `src/indicators`.
- Risk model modules in `src/risk`.
- `analysis-report.md` (final metrics and counts).
- `removal-notes.md` (justification of deletions).

## Risks

- Hidden coupling to deprecated internals may require minor refactors (limit changes to interface alignment).
- Large deletions risk removing shared utilities (mitigate via diff review + full suite run).

## Acceptance Summary

Feature accepted when all measurable outcomes (SC-001..SC-009) are met and functional requirements FR-001..FR-012 have corresponding passing tests.
