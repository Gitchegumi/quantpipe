# Implementation Plan: Fix Risk Argument Mapping

**Branch**: `025-fix-risk-args` | **Date**: 2026-01-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/025-fix-risk-args/spec.md`

## Summary

This feature addresses a bug where CLI risk arguments (`--rr-ratio`, `--atr-mult`, `--risk-pct`, etc.) are ignored during backtests. The fix involves updating the `run_backtest.py` CLI orchestrator to correctly map these arguments to the `StrategyParameters` object used by the backtest engine. Additionally, support for `--max-position-size` will be added to `StrategyParameters` to fulfill the clarification requirement.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `poetry`, `pydantic`
**Storage**: N/A (CLI arguments are transient)
**Testing**: `pytest`
**Target Platform**: CLI (Windows/Linux)
**Project Type**: single project (python backend)
**Performance Goals**: N/A
**Constraints**: Must override config file values
**Scale/Scope**: Refactor of existing CLI parsing and config injection logic.

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

- **I. Strategy-First Architecture**: Compatible. We are ensuring the strategy receives the correct parameters.
- **II. Risk Management Integration**: Strengthening compliance. Risk parameters will now be correctly enforced from the CLI.
- **VII. Model Parsimony**: No model changes, just parameter plumbing.
- **VIII. Code Quality**: Will follow Python 3.11+ and Pydantic standards.
- **XI. Commit Message Standards**: Will be followed.
- **XII. Task Tracking**: Tasks will be generated and tracked.

## Project Structure

### Documentation (this feature)

```text
specs/025-fix-risk-args/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── cli/
│   └── run_backtest.py  # Primary modification target
└── config/
    └── parameters.py    # Update to support max_position_size

tests/
└── integration/         # Integration tests for CLI arg mapping
```

**Structure Decision**: This is a targeted refactor within the existing `src/` structure. No new directories or modules are required, just updates to existing files.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --------- | ---------- | ------------------------------------ |
| N/A       |            |                                      |
