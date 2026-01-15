# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `pandas`, `numpy`, `structlog` (Project Standard)
**Storage**: JSON configuration files (read-only CTI presets)
**Testing**: `pytest` (Unit & Integration)
**Target Platform**: Windows/Linux (CLI Backtester)
**Project Type**: Python CLI Tool
**Performance Goals**: N/A (Offline analysis of backtest results)
**Constraints**: Must match CTI specific rules exactly; No changes to core backtest engine loop (Post-hoc analysis).
**Scale/Scope**: < 20 new files, localized to `src/risk/prop_firm` and `src/backtest/metrics.py`.

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Principle               | Status | Justification / Notes                                                     |
| :---------------------- | :----- | :------------------------------------------------------------------------ |
| **I. Strategy-First**   | PASS   | Feature enhances backtest analysis, does not alter strategy interfaces.   |
| **II. Risk Management** | PASS   | Core feature purpose: Validating strategies against Prop Firm risk rules. |
| **III. Backtesting**    | PASS   | Adds new metrics (Sharpe, Sortino) requested by standard.                 |
| **IV. Monitoring**      | PASS   | N/A (Backtest feature).                                                   |
| **XII. Task Tracking**  | PASS   | Tasks will be generated sequentially in Phase 2.                          |
| **VIII. Code Quality**  | PASS   | New modules will follow PEP 8, types, docs.                               |

## Project Structure

### Documentation (this feature)

```text
specs/027-cti-metrics-progression/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # N/A (No API)
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
src/
├── backtest/
│   ├── metrics.py               # [MODIFY] Add Sharpe, Sortino, etc.
│   └── report.py                # [MODIFY] Add CTI & Scaling sections
├── config/
│   └── presets/
│       └── cti/                 # [NEW] JSON Configs
├── risk/
│   └── prop_firm/               # [NEW] Domain Logic
│       ├── evaluator.py         # Rule checking
│       ├── loader.py            # Config loading
│       ├── models.py            # Pydantic definitions
│       └── scaling.py           # Progression logic
└── cli/
    └── run_backtest.py          # [MODIFY] New CLI args
```

**Structure Decision**: Standard "Single project" CLI layout. New domain logic isolated in `src/risk/prop_firm`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
| :-------- | :--------- | :----------------------------------- |
| None      | N/A        | N/A                                  |
