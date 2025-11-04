# Feature Specification: Documentation Restructure & Separation

**Feature Branch**: `005-docs-restructure`
**Created**: 2025-11-03
**Status**: Draft
**Input**: User description: "Restructure documentation so README only contains what the project is and how to use it. Move environment & development setup into a dedicated contributor guide. Optionally create a docs/ directory with detailed strategy explanations and backtest results."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - First-Time User Quick Start (Priority: P1)

A first-time visitor lands on the repository, scans the README, and runs a backtest successfully in under 5 minutes using only the commands and links provided there (no need to scroll through long development details).

**Why this priority**: Core adoption funnel; frictionless first success drives interest and contributions.

**Independent Test**: Fresh clone; follow only README sections; measure elapsed time and number of commands needed.

**Acceptance Scenarios**:

1. **Given** a clean environment with Poetry installed, **When** the user follows the Quick Start in the README, **Then** they install deps and run a sample backtest producing output without errors.
2. **Given** the README links to deeper docs, **When** the user wants strategy rationale, **Then** they can follow a link to `docs/strategies.md` without broken links.

---

### User Story 2 - New Contributor Environment Setup (Priority: P2)

A prospective contributor wants to run tests and follow quality gates; they open `CONTRIBUTING.md` and complete environment setup, linting, and tests successfully without consulting README.

**Why this priority**: Separating user vs contributor concerns reduces README noise and speeds onboarding for maintainers.

**Independent Test**: Delete virtual environment; follow only CONTRIBUTING.md to recreate environment, run quality commands, and open a feature branch.

**Acceptance Scenarios**:

1. **Given** a machine with Python 3.11 but no dependencies, **When** contributor follows the steps, **Then** Poetry environment is created and tests pass.
2. **Given** quality gate commands listed, **When** executed sequentially, **Then** each completes with expected pass criteria documented (formatting no changes, lint score threshold, tests green).

---

### User Story 3 - Strategy / Research Deep Dive (Priority: P3)

An analyst wants to understand strategy design and backtest methodology; they navigate from README to `docs/` pages summarising strategies and pointing to spec directories for full detail.

**Why this priority**: Consolidates knowledge location and reduces duplication between specs and README.

**Independent Test**: Starting only from README links, analyst reaches both strategy overview and backtesting methodology pages without searching.

**Acceptance Scenarios**:

1. **Given** README strategy link, **When** clicked, **Then** user sees a high-level summary of current strategy (trend pullback) plus placeholders for future ones.
2. **Given** README backtesting link, **When** clicked, **Then** user sees dataset build & split-mode explanation consistent with existing CLI behavior.

---

### Edge Cases

- User without Poetry installed: CONTRIBUTING.md must direct how to install Poetry (link + brief command) without bloating README.
- Windows vs Unix shell differences: At least one note clarifies PowerShell vs bash quoting for multi-line examples.
- Future strategies added: docs structure supports adding new markdown without needing large README edits.
- Link rot: All internal links validated—no 404 or missing file references post-restructure.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: README MUST contain only: project name/tagline, concise overview (≤150 words), Quick Start (install + one backtest example), minimal CLI usage table, and links to CONTRIBUTING.md & docs/ pages.
- **FR-002**: All environment setup, development workflow, test tiers, quality gate commands, and contribution workflow MUST be moved from README into `CONTRIBUTING.md` (conventional filename adopted).
- **FR-003**: `CONTRIBUTING.md` MUST include sections: Purpose, Prerequisites (Python 3.11, Poetry), Environment Setup, Quality Gates (Black/Ruff/Pylint/pytest markers), Test Strategy (unit/integration/performance), Branch & Feature Flow (create-new-feature script), Logging Standards (no f-string in logger calls), Commit Hygiene, License & Compliance note.
- **FR-004**: Create `docs/` directory containing at minimum: `strategies.md` (overview + links to `specs/00*-*/spec.md`), `backtesting.md` (dataset building, split-mode rationale, metrics glossary), and `structure.md` (brief repo layout explanation referencing but not duplicating specs).
- **FR-005**: README MUST link to each new docs page and the contributions guide using relative paths.
- **FR-006**: Duplicated content removed—no section present verbatim in both README and CONTRIBUTING.md (manual diff shows reductions).
- **FR-007**: Add a CHANGELOG entry noting documentation restructure (date + summary) without inflating README.
- **FR-008**: All internal markdown links introduced MUST resolve (link check passes with 0 errors).
- **FR-009**: Provide clear guidance for running first backtest using existing CLI (no new code) with exactly ≤3 commands (install, run, optional view results path).
- **FR-010**: docs pages MUST avoid implementation details beyond referencing existing filenames & CLI flags; no duplication of full parameter tables already in specs unless summarized.

### Key Entities

- **README**: User-facing entry; purpose: orientation + first success path.
- **CONTRIBUTING.md**: Contributor onboarding & governance guide for environment, quality gates, branching.
- **Strategy Docs (`docs/strategies.md`)**: High-level narrative of strategies implemented/planned.
- **Backtesting Docs (`docs/backtesting.md`)**: Describes methodology (dataset build, partitioning, metrics definitions).
- **Repository Structure Doc (`docs/structure.md`)**: Lightweight map of directories with roles.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user executes a successful sample backtest using only README in ≤5 minutes (time-boxed test run).
- **SC-002**: README non-blank line count reduced by ≥40% compared to pre-change version (baseline captured before commit).
- **SC-003**: 100% (≥95% threshold) of internal links added/retained pass a markdown link check (0 failures).
- **SC-004**: Environment setup + quality gate commands present ONLY in CONTRIBUTING.md (manual grep of README returns none of: `pylint`, `ruff`, `pytest -m`).
- **SC-005**: docs/ contains ≥3 markdown files with distinct scopes (strategies, backtesting, structure) and each linked from README.
- **SC-006**: Contributor following only CONTRIBUTING.md can reach green tests & lint in ≤10 minutes (observed walkthrough).
- **SC-007**: CHANGELOG updated with a Documentation section entry referencing issue/feature number 005.

### Assumptions

- Using conventional `CONTRIBUTING.md` for contributor guidance.
- No automated link checker currently in pipeline; manual or ad-hoc script acceptable.
- No need to version docs separately; changes ship with repo commits.
- Backtest result examples reused from existing README—moved, not rewritten.

### Out of Scope

- Generating new strategy content beyond summarizing existing specs.
- Adding automated documentation site tooling (MkDocs/Sphinx) at this stage.
- Changing CLI behavior or backtest engine.

No clarifications required; all design decisions inferred from user intent and existing repository standards.
