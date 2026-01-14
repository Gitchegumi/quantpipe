# Implementation Plan: Decouple Indicator Registration

**Branch**: `026-decouple-indicators` | **Date**: 2026-01-14 | **Spec**: [spec.md](../spec.md)
**Input**: Feature specification from `/specs/026-decouple-indicators/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Enable strategies to define custom indicators via `get_custom_indicators(self)` returning `dict[str, Callable]`. The core backtest engine will resolve these strategy-specific indicators before checking the global registry, allowing for portable strategies and safe overrides without modifying the core codebase.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Polars (data processing), Strategy Base Class
**Storage**: N/A (in-memory processing)
**Testing**: Pytest (unit & integration)
**Target Platform**: Local Windows/Linux Environment
**Project Type**: Single Python Project
**Performance Goals**: Negligible overhead for indicator resolution; vectorized calculation speed maintained
**Constraints**: Must maintain backward compatibility for all existing strategies
**Scale/Scope**: Supports arbitrary number of custom indicators per strategy

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

- [x] **Principle I: Strategy-First Architecture**: Changes enforce clearer separation of strategy logic from core engine.
- [x] **Principle X: Code Quality**: New code will adhere to lint/format standards.
- [x] **Principle XII: Task Tracking**: Tasks will be generated and tracked in `tasks.md`.
- [x] **Risk Management**: No changes to risk modules; existing controls apply to strategies using custom indicators.

## Project Structure

### Documentation (this feature)

```text
specs/026-decouple-indicators/
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
├── indicators/       # dispatcher.py logic updates
├── strategy/         # base.py interface updates
└── ...

tests/
├── integration/      # Verify custom indicator resolution
└── unit/             # Test strategy method & dispatcher logic
```

**Structure Decision**: Standard "Single project" structure for this Python backend repository. Changes are focused on `src/indicators/dispatcher.py` and `src/strategy/base.py`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --------- | ---------- | ------------------------------------ |
| None      | N/A        | N/A                                  |
