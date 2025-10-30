# Implementation Plan: Update 001 Test Suite Alignment

**Branch**: `003-update-001-tests` | **Date**: 2025-10-30 | **Spec**: `specs/003-update-001-tests/spec.md`
**Input**: Feature specification generated via `/speckit.specify` and clarified via `/speckit.clarify`.

## Summary

Goal: Realign, prune, and stabilize the 001 Trend Pullback test suite to match current code interfaces and strategy contracts while introducing a three-tier execution model (Unit <5s, Integration <30s, Performance <120s). Approach: Audit existing tests, categorize, refactor for determinism using small fixtures, remove obsolete/redundant cases, and ensure each functional requirement (FR-001..FR-011) is covered by at least one test.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: pytest (for tests), numpy, pandas (used in indicator calculations), pydantic (configs), rich/logging (structured output), Black/Ruff/Pylint (quality gates)
**Storage**: File-based fixtures (CSV / in-repo small synthetic datasets); no database
**Testing**: pytest with markers (`unit`, `integration`, `performance`) and potential `pytest.ini` configuration for tier selection
**Target Platform**: Cross-platform dev/CI (Windows dev, Linux CI expected)
**Project Type**: Single Python package (`src/` + `tests/`)
**Performance Goals**: Unit tier <5s total, Integration tier <30s total, Performance tier <120s total on CI baseline hardware
**Constraints**: Deterministic outcomes, no network calls, no reliance on real-time clock; maintain lint scores (Pylint ≥8.0) and zero Ruff errors
**Scale/Scope**: Limited to 001 strategy test suite; expected retained tests <= original count with ≤30% reduction unless justified

No outstanding NEEDS CLARIFICATION items after clarify phase.

## Constitution Check

**Branch**: `003-update-001-tests` | **Date**: 2025-10-30 | **Spec**: `specs/003-update-001-tests/spec.md`
**Input**: Feature specification clarified and expanded post-analysis.

## Constitution Summary

Realign, prune, and stabilize the 001 Trend Pullback test suite while introducing a three-tier execution model (Unit <5s, Integration <30s, Performance <120s). Audit existing tests, categorize, refactor for determinism using *deterministic synthetic fixtures*, remove obsolete/redundant cases, and ensure each functional requirement (FR-001..FR-012) is covered by at least one test.

## Constitution Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: pytest, numpy, pandas, pydantic, rich/logging, Black, Ruff, Pylint
**Storage**: File-based fixtures (CSV deterministic synthetic fixtures); no database
**Testing**: pytest with markers (`unit`, `integration`, `performance`) + `pytest.ini`
**Target Platform**: Windows dev, Linux CI (GitHub Actions ubuntu-latest ~2 vCPU, 7 GB RAM)
**Project Type**: Single Python package (`src/` + `tests/`)
**Performance Goals**: Unit <5s, Integration <30s, Performance <120s (±20% tolerance; hard fail if >1.2× threshold)
**Constraints**: Deterministic outcomes, no network calls, no reliance on real-time clock; maintain Pylint ≥8.0, zero Ruff errors, Black formatting.
**Scale/Scope**: Limited to 001 strategy tests; retained tests ≤ original count with ≤30% reduction unless justified.

## Constitution Double Check

| Principle | Compliance | Notes |
|-----------|------------|-------|
| I Strategy-First | ✅ | Tests align with existing strategy modules. |
| II Risk Management | ✅ | Risk sizing edge cases expanded (FR-007). |
| III Backtesting & Validation | ✅ (scope-limited) | Validation via deterministic tests. |
| IV Real-Time Monitoring | N/A | Not in scope. |
| V Data Integrity & Security | ✅ | Deterministic fixtures only. |
| VI Data Version Control | ✅ | Fixture manifest (T006a) added early. |
| VII Parsimony | ✅ | Redundant tests consolidated. |
| VIII Code Quality & Docs | ✅ | Docstring template defined (FR-010). |
| IX Dependency Mgmt | ✅ | No new deps. |
| X Code Quality Automation | ✅ | Early gate (T018a) before bulk additions. |
| Risk Management Standards | ✅ | Risk tests maintained, drawdown explicitly out-of-scope. |
| Milestone Commit Messages | ✅ | Commit draft task included. |

Gate Result: PASS.

## Project Structure

```text
specs/003-update-001-tests/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
├── mapping.md
├── analysis-report.md
├── removal-notes.md
└── checklists/

tests/
├── unit/
├── integration/
├── performance/
└── fixtures/
```

**Structure Decision**: Use deterministic synthetic fixtures + tier directories; one tier marker per file.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Additional performance tier dir | Isolate long scenarios | Mixing obscures failures & increases CI time |
| Pytest markers | Selective tier execution | Directory alone lacks granularity |
| Early quality gate task | Catch issues early | Delayed linting increases rework |

## Constitution Re-Check (Post-Design)

All added artifacts reinforce Principles II, VI, VIII, X; performance tier optional in default run.

| Principle | Post-Design Status | Delta |
|-----------|--------------------|-------|
| I Strategy-First | ✅ | Unchanged |
| II Risk Management | ✅ | Expanded edge cases |
| III Backtesting & Validation | ✅ | Added flakiness stabilization tasks |
| V Data Integrity | ✅ | Fixture manifest integrated |
| VIII Code Quality | ✅ | Docstring template + mapping |
| X Automation | ✅ | Early gate + final gate |
| Risk Management Standards | ✅ | Drawdown marked out-of-scope here |

Result: Ready for task execution.

## Governance Mapping

| Item | Principle(s) |
|------|--------------|
| T006a fixture manifest | VI Data Version Control |
| T018a early quality gate | X Code Quality Automation |
| T045 lazy logging enforcement | X Code Quality Automation |
| Tier markers (T011–T013) | I Strategy-First |
| Flakiness stabilization (T026, T026a, T026b) | III Backtesting & Validation |

## Determinism Summary

Deterministic synthetic fixtures + seeded randomness (conftest) ensure repeatable outcomes; no additional determinism tasks beyond T016, T035–T039 required.

## Independent Test Criteria Summary

- US1: Run unit + integration tiers to verify signals, indicators, risk sizing.
- US2: Run full suite; confirm reduced count & unchanged coverage metrics.
- US3: Time tiers; confirm thresholds and determinism via perf counter.

## Exit Criteria

MVP: FR-001..FR-009 + SC-001..SC-004 satisfied; tier markers operational.
Full Completion: FR-001..FR-012 + SC-001..SC-009 satisfied; analysis-report.md populated.
