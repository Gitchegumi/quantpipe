# Feature Specification: Package 'quantpipe' CLI Tool

**Feature Branch**: `028-package-quantpipe-cli`
**Created**: 2026-01-23
**Status**: Draft
**Input**: User description: "Package application as 'quantpipe' CLI tool. Package the application so it can be installed and successfully run using the `quantpipe` command, streamlining the execution of backtests equivalent to the old command."

## Clarifications

### Session 2026-01-23

- Q: CLI Command Structure? → A: **Subcommand Structure** (`quantpipe backtest [args]`) to allow for future expansion (e.g. `quantpipe optimize`).
- Q: Execution Context? → A: **Project Root Only**; command must be run from repo root to locate data/strategies.

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Install and Verify CLI (Priority: P1)

As a developer or user, I want to install the application as a Python package and access the `quantpipe` command, so that I can use the tool system-wide or in virtual environments without manually calling scripts.

**Why this priority**: Fundamental requirement for the feature. Without installation and the command availability, the feature fails.

**Independent Test**: Can be tested by running `pip install .` or `poetry install` in a clean environment.

**Acceptance Scenarios**:

1. **Given** the project source code, **When** I run `pip install .`, **Then** the package installs successfully and dependencies are resolved using the compiled logic.
2. **Given** a successful installation, **When** I run `quantpipe --help`, **Then** the help text is displayed, listing available subcommands (including `backtest`).
3. **Given** a successful installation, **When** I run `quantpipe --version` (if applicable), **Then** the current version is displayed.
4. **Given** the source code with Poetry managed dependencies, **When** I run `poetry install`, **Then** the `quantpipe` command is available inside `poetry run` or the active shell.

---

### User Story 2 - Execute Backtest via CLI (Priority: P1)

As a user, I want to execute backtests using the `quantpipe backtest` command with the same arguments as the original script, so that I don't have to learn a new interface or change my workflow significantly.

**Why this priority**: Core functionality target. The CLI is useless if it doesn't perform the primary task (backtesting).

**Independent Test**: Can be tested by running a backtest command and comparing output/artifacts with the direct script execution.

**Acceptance Scenarios**:

1. **Given** installed `quantpipe`, **When** I run `quantpipe backtest [backtest-args]`, **Then** the backtest executes and produces results.
2. **Given** installed `quantpipe`, **When** I provide invalid arguments to the subcommand, **Then** error messages are displayed clearly.
3. **Given** installed `quantpipe`, **When** I run `quantpipe backtest` with args matching the old `src/cli/run_backtest.py` invocation, **Then** the behavior is identical.

### Edge Cases

- **Environment Conflicts**: Installation fails if a conflicting package or command named `quantpipe` already exists.
- **Missing Dependencies**: Installation process MUST report missing system-level dependencies if any (though unlikely for pure Python).
- **Invalid Arguments**: CLI MUST handle undefined arguments gracefully with a help message rather than a stack trace.
- **Incorrect Execution Directory**: The command SHOULD fail fast with a clear error if run from outside the project root (e.g., missing `data/` directory).

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: The application MUST be installable via standard Python package management tools (including `pip` and `poetry`).
- **FR-002**: The installation process MUST register a system-wide or environment-specific console command named `quantpipe`.
- **FR-003**: The `quantpipe` command MUST support subcommands, with the primary backtesting functionality mapped to `quantpipe backtest`.
- **FR-004**: The CLI `backtest` subcommand MUST accept command-line arguments consistent with the existing execution method.
- **FR-005**: The package configuration (in `pyproject.toml`) MUST define the script entry point using the standard `[tool.poetry.scripts]` (or equivalent) table to ensure compatibility.

### Key Entities _(include if feature involves data)_

N/A - This feature is infrastructure/packaging.

## Assumptions

- The project source code follows a structure compatible with standard packaging (e.g., `src` layout).
- Existing dependencies are identifiable and can be included in the package definition.
- Poetry is the primary dependency management tool for this project.
- Users invoke the CLI from the project root directory where `data/` and `src/` are accessible.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Standard installation command completes with success status in a fresh environment.
- **SC-002**: `quantpipe --help` shows usage info including the `backtest` subcommand.
- **SC-003**: Identical backtest results (PnL, number of trades) are produced when running via `quantpipe backtest` vs direct python script execution for a benchmark strategy.
