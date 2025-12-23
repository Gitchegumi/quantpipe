# Implementation Plan: Fix Portfolio Mode Visualization

**Branch**: `019-fix-portfolio-viz` | **Date**: 2025-12-23 | **Spec**: [specs/019-fix-portfolio-viz/spec.md](../spec.md)
**Input**: Feature specification from `/specs/019-fix-portfolio-viz/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This plan addresses critical defects in Portfolio Mode backtesting: double execution of simulations (CLI bug) and incorrect "merged" visualization of multi-symbol portfolios. The implementation will ensure portfolio simulations run exactly once and produce a visualization with separate, synchronized charts for each symbol, preserving the shared equity curve.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Polars (vectorized data), HoloViews/Datashader (visualization), Pytest (testing)
**Storage**: N/A (stateless execution, outputs to files)
**Testing**: Pytest integration tests
**Target Platform**: Windows/Linux (CLI tool)
**Project Type**: Single project (CLI/Library)
**Performance Goals**: < 5s viz generation for typical portfolio backtset
**Constraints**: Must use Polars for all data op; NO per-candle loops in python
**Scale/Scope**: Support for 2-10 symbols per portfolio

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Principle               | Check                          | Status | Notes                                    |
| :---------------------- | :----------------------------- | :----- | :--------------------------------------- |
| **I. Strategy-First**   | 1. Modular strategy Interface? | PASS   | No changes to strategy interface         |
| **II. Risk Management** | 1. Mandatory risk controls?    | PASS   | Portfolio mode maintains position sizing |
| **III. Backtesting**    | 1. Comprehensive backtesting?  | PASS   | Enhances backtest verification tools     |
| **IV. Monitoring**      | 1. UX feedback?                | PASS   | Improves visualization UX                |
| **VIII. Code Quality**  | 1. Python 3.13 standards?      | PASS   | Will follow PEP8/Type hints              |
| **X. Quality Auto**     | 1. Linting/Formatting?         | PASS   | CI checks in place                       |
| **XI. Commit Msgs**     | 1. Semantic format?            | PASS   | Will follow `fix(019): ...`              |
| **XII. Task Tracking**  | 1. Sequential execution?       | PASS   | Tasks will be tracked in tasks.md        |

## Project Structure

### Documentation (this feature)

```text
specs/019-fix-portfolio-viz/
├── plan.md              # This file
├── research.md          # N/A - No new research needed (clarified in spec)
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # N/A - No API contracts
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
src/
├── cli/
│   └── run_backtest.py       # [MODIFY] Fix execution flow and viz mapping
└── visualization/
    └── datashader_viz.py     # [See Note] Review/adjust for consistent tagging

tests/
└── integration/
    └── test_portfolio_flow.py # [NEW] Test execution flow and output structure
```

**Structure Decision**: Standard single project layout. Focus is on modifying existing CLI orchestrator to correct data mapping passed to visualization module.

## Complexity Tracking

N/A - No violations.
