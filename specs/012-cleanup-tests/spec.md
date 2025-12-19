# Feature Specification: Clean Up Tests and Fix Integration Tests

**Feature Branch**: `012-cleanup-tests`
**Created**: 2025-12-18
**Status**: Draft
**Input**: User description: "Clean up old tests and fix current integration tests - Remove or refactor outdated/legacy tests that are no longer relevant or maintained. Fix currently failing or broken integration tests to restore CI reliability."

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Fix Failing Integration Tests (Priority: P1)

As a developer, I want all integration tests to pass in CI so that the test suite provides reliable feedback on code quality and I can trust that merges don't break existing functionality.

**Why this priority**: Failing tests block CI pipelines and undermine confidence in the test suite. This is the highest priority as it directly impacts development velocity and code quality assurance.

**Independent Test**: Can be fully tested by running `poetry run pytest tests/integration -x --tb=short` and verifying all tests pass with exit code 0.

**Acceptance Scenarios**:

1. **Given** I have the latest code from main, **When** I run integration tests, **Then** all tests pass with exit code 0
2. **Given** a failing integration test, **When** I investigate the root cause, **Then** I can identify whether it's a test bug or production code bug and fix accordingly

---

### User Story 2 - Remove Obsolete/Redundant Tests (Priority: P2)

As a developer, I want the test suite to contain only relevant, non-redundant tests so that test execution is efficient and test maintenance burden is reduced.

**Why this priority**: Redundant tests increase CI time and maintenance burden. This should be done after fixing failing tests to ensure baseline coverage is preserved.

**Independent Test**: Can be verified by reviewing the test inventory, confirming removed tests overlap with existing coverage, and running full test suite to ensure no regression.

**Acceptance Scenarios**:

1. **Given** a test marked as redundant in the inventory, **When** I compare it with Phase 3 tests, **Then** I can confirm the coverage is duplicated and the test can be safely removed
2. **Given** I remove redundant tests, **When** I run the full test suite, **Then** all remaining tests pass and coverage is maintained

---

### User Story 3 - Audit and Document Test Suite (Priority: P3)

As a developer, I want a documented audit trail of test changes so that future developers understand why tests were removed or modified.

**Why this priority**: Documentation ensures knowledge transfer and justifies cleanup decisions for future maintainers.

**Independent Test**: Can be verified by reviewing the removal notes and confirming each removed test has a documented justification.

**Acceptance Scenarios**:

1. **Given** I complete the test cleanup, **When** I review the documentation, **Then** each removed test has a clear justification referencing the overlapping test or reason for obsolescence

---

### Edge Cases

- What happens if removing a "redundant" test actually removes unique edge case coverage?
- How do we handle tests that reference deprecated interfaces that no longer exist?
- What is the threshold for acceptable test reduction (current inventory suggests ≤30%)?

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST pass all integration tests in CI environment
- **FR-002**: System MUST identify and remove tests that duplicate coverage from Phase 3 tests
- **FR-003**: System MUST preserve unique edge case coverage (e.g., empty arrays, single values, boundary conditions)
- **FR-004**: System MUST consolidate similar tests into parameterized test cases where appropriate
- **FR-005**: System MUST document all test removals with justifications in a removal notes file
- **FR-006**: System MUST maintain or improve overall test coverage percentage after cleanup

### Key Entities

- **Test Inventory**: Document tracking test files, their coverage, and removal status
- **Redundant Test**: A test whose assertions are fully covered by another test (typically Phase 3 tests)
- **Obsolete Test**: A test referencing removed/deprecated interfaces that no longer exists
- **Phase 3 Tests**: The newer, more comprehensive tests added in `test_indicators_core.py`, `test_risk_sizing_normal.py`, `test_risk_sizing_volatility.py`

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: All integration tests pass in CI (0 failures, exit code 0)
- **SC-002**: Test reduction is within acceptable limits (≤30% of total tests removed)
- **SC-003**: Test execution time remains stable or improves after cleanup
- **SC-004**: No regression in code coverage percentage after test removal
- **SC-005**: All test removals are documented with justifications

## Assumptions

- The existing `tests/_inventory_removed.txt` document provides accurate analysis of redundant tests
- Phase 3 tests (`test_indicators_core.py`, `test_risk_sizing_*.py`) are the authoritative source for indicator and risk sizing coverage
- Tests marked with `@pytest.mark.local_data` are expected to skip in CI and should not be counted as failures
- The project uses Poetry for dependency management (`poetry run pytest`)
