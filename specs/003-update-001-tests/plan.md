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

### Initial Gate Assessment (Pre-Phase 0)

| Principle | Compliance | Notes |
|-----------|------------|-------|
| I Strategy-First | ✅ | Tests align with existing strategy modules, no new coupling. |
| II Risk Management | ✅ | Risk sizing tests retained/improved (FR-007). |
| III Backtesting & Validation | ✅ (scope-limited) | Strategy validated indirectly; backtest performance not altered. |
| IV Real-Time Monitoring | N/A | Feature targets test suite only. |
| V Data Integrity & Security | ✅ | Fixtures deterministic; no credentials involved. |
| VI Data Version Control | ✅ | Using small synthetic fixture datasets, can add manifest if new files added. |
| VII Parsimony | ✅ | Removing redundant tests reduces complexity. |
| VIII Code Quality & Docs | ✅ | Will add docstrings to test helpers; enforce line length. |
| IX Dependency Mgmt | ✅ | No new deps; Poetry unchanged. |
| X Code Quality Automation | ✅ | Plan includes running Black, Ruff, Pylint post-refactor. |
| Risk Management Standards | ✅ | Risk tests maintained. |
| Milestone Commit Messages | ✅ | Will use conventional commit with summary bullets. |

Gate Result: PASS — proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
specs/003-update-001-tests/
├── spec.md
├── plan.md
├── research.md              # (Phase 0 to be generated)
├── data-model.md            # (Phase 1)
├── quickstart.md            # (Phase 1)
├── contracts/               # (Phase 1)
└── checklists/requirements.md

src/
├── strategy/                # 001 strategy implementation
├── indicators/              # Indicator calculations used by tests
├── risk/                    # Risk sizing logic
└── cli/                     # CLI entry points (unchanged)

tests/
├── unit/                    # Will house unit tier tests (fast deterministic)
├── integration/             # Will house integration tier tests (strategy flows)
├── performance/             # Will house performance tier tests (optional long-running)
└── fixtures/                # Shared deterministic fixtures
```

**Structure Decision**: Retain single-package layout; reorganize tests into explicit tier directories (unit/integration/performance) while preserving existing fixture sharing.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Additional test tier directory (performance) | Isolates long-running tests from default runs | Mixing all tests increases CI time and obscures failures |
| Introduction of pytest markers | Enables selective execution per tier | Reliance on directory alone limits granularity for mixed cases |

## Constitution Re-Check (Post-Design)

No changes introduce new strategies, data sources, or dependencies. Added artifacts (research.md, data-model.md, contracts/test-tiering.md, quickstart.md) reinforce Principles II, VIII, X. Performance tier isolation supports Principle III by keeping validation focused. All gates remain PASS.

| Principle | Post-Design Status | Delta |
|-----------|--------------------|-------|
| I Strategy-First | ✅ | Unchanged |
| II Risk Management | ✅ | Risk edge cases documented in fixtures scope |
| III Backtesting & Validation | ✅ | Performance tier optionally used for longer scenario runs |
| V Data Integrity | ✅ | Deterministic fixture approach affirmed |
| VIII Code Quality | ✅ | Naming/documentation conventions established |
| X Automation | ✅ | Plan integrates lint/test flows in quickstart |
| Risk Management Standards | ✅ | Retained and covered by FR-007 |

Result: Ready for Phase 2 task breakdown.
