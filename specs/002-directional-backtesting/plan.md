# Implementation Plan: Directional Backtesting System

**Branch**: `002-directional-backtesting` | **Date**: 2025-10-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-directional-backtesting/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a unified backtesting CLI (`run_backtest.py`) that manages all directional testing with three modes: LONG (long-only signals), SHORT (short-only signals), and BOTH (combined long/short with conflict resolution). The system integrates existing signal generation functions (`generate_long_signals`, `generate_short_signals`), execution simulation (`simulate_execution`), and metrics calculation to provide comprehensive performance analysis with support for both text and JSON output formats. Key features include dry-run mode for signal validation, deterministic file naming for result tracking, and conflict resolution logic for BOTH mode that rejects simultaneous opposing signals as market indecision indicators.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: numpy, pandas, pydantic, rich (existing); no new dependencies required
**Storage**: CSV files for price data input; text/JSON files for backtest results output
**Testing**: pytest with hypothesis for property-based testing
**Target Platform**: Cross-platform CLI (Windows/Linux/macOS)
**Project Type**: Single project (CLI-based backtesting tool)
**Performance Goals**: Process 100K candles in ≤30 seconds (LONG/SHORT), ≤10 seconds for dry-run mode
**Constraints**: Deterministic results (reproducibility_hash verification), JSON output ≤10MB for 100K candles
**Scale/Scope**: Extends existing backtest infrastructure; adds ~500-800 LOC across CLI, orchestration, and metrics aggregation modules

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Principle                                | Status  | Notes                                                                                                                                                     |
| ---------------------------------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **I. Strategy-First Architecture**       | ✅ PASS | Extends existing backtest infrastructure without modifying strategy modules; maintains clear separation between signal generation, execution, and metrics |
| **II. Risk Management Integration**      | ✅ PASS | Backtesting tool does not execute real trades; risk parameters already integrated in signal generation functions                                          |
| **III. Backtesting & Validation**        | ✅ PASS | Core feature purpose; implements comprehensive backtesting with realistic execution simulation, slippage, and metrics                                     |
| **IV. Real-Time Performance Monitoring** | N/A     | Offline backtesting tool; monitoring not applicable                                                                                                       |
| **V. Data Integrity & Security**         | ✅ PASS | Validates data file existence (FR-017); uses existing data ingestion module with integrity checks                                                         |
| **VI. Data Version Control**             | ✅ PASS | Uses manifest-based data referencing (FR-015: manifest_ref); maintains reproducibility via reproducibility_hash                                           |
| **VII. Model Parsimony**                 | ✅ PASS | Leverages existing signal generation logic; no new indicators or model complexity added                                                                   |
| **VIII. Code Quality & Documentation**   | ✅ PASS | Will follow PEP 8, PEP 257 docstrings, type hints, 88-char lines per Black standard                                                                       |
| **IX. Dependency Management**            | ✅ PASS | Uses Poetry (pyproject.toml); no new dependencies required                                                                                                |
| **X. Code Quality Automation**           | ✅ PASS | Will format with Black, lint with Ruff (zero errors), Pylint (≥8.0/10); use lazy % logging                                                                |

**Overall Assessment**: ✅ ALL GATES PASS - Feature aligns with all applicable constitution principles. No violations or justifications required.

## Project Structure

### Documentation (this feature)

```text
specs/002-directional-backtesting/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (architecture decisions, patterns)
├── data-model.md        # Phase 1 output (data flows, entities)
├── quickstart.md        # Phase 1 output (developer guide)
├── contracts/           # Phase 1 output (CLI interface spec, JSON schema)
├── checklists/          # Quality validation checklists
│   └── requirements.md  # Specification quality checklist (completed)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created yet)
```

### Source Code (repository root)

```text
src/
├── cli/
│   ├── __init__.py
│   ├── run_backtest.py          # [ENHANCED] Unified CLI entry point (LONG/SHORT/BOTH)
│   ├── run_long_backtest.py     # [EXISTING] Current LONG implementation
│   └── logging_setup.py         # [EXISTING] Logging configuration
├── backtest/
│   ├── __init__.py
│   ├── execution.py             # [EXISTING] simulate_execution function
│   ├── orchestrator.py          # [NEW] Backtest orchestration logic
│   └── metrics.py               # [NEW/ENHANCED] Metrics aggregation for BOTH mode
├── strategy/
│   └── trend_pullback/
│       ├── signal_generator.py  # [EXISTING] generate_long/short_signals
│       └── ...                  # [EXISTING] Other strategy modules
├── io/
│   ├── __init__.py
│   ├── ingestion.py             # [EXISTING] Data loading
│   └── formatters.py            # [NEW] Text/JSON output formatters
└── models/
    ├── __init__.py
    └── core.py                  # [EXISTING] BacktestRun, MetricsSummary, etc.

tests/
├── unit/
│   ├── test_backtest_orchestrator.py   # [NEW] Unit tests for orchestrator
│   ├── test_metrics_aggregation.py     # [NEW] BOTH mode metrics tests
│   └── test_output_formatters.py       # [NEW] JSON/text formatter tests
├── integration/
│   └── test_directional_backtesting.py # [NEW] End-to-end CLI tests
└── fixtures/
    └── sample_data.csv                  # [EXISTING] Test datasets
```

**Structure Decision**: Single project structure maintained. New modules added to existing `src/backtest/` and `src/io/` packages. CLI enhanced in-place at `src/cli/run_backtest.py`. All new code follows existing architectural patterns with clear module responsibilities.

## Complexity Tracking

> **No violations** - All constitution gates pass. This section intentionally left empty.

---

## Phase 0: Research (COMPLETE)

**Status**: ✅ Complete
**Output**: [research.md](./research.md)

**Key Decisions Documented**:

1. CLI orchestration pattern (Factory/Strategy with dedicated orchestrator)
2. BOTH mode conflict resolution architecture (timestamp-based merge with early detection)
3. Metrics aggregation for BOTH mode (three-tier: long/short/combined)
4. Output file naming convention (`backtest_{direction}_{YYYYMMDD}_{HHMMSS}.{ext}`)
5. JSON output schema design (nested structure with metadata/metrics/details)
6. Dry-run mode implementation (signal generation only, skip execution)

**Technologies Confirmed**:

- No new dependencies required
- Python 3.11 standard library + existing dependencies (numpy, pandas, pydantic, rich)

---

## Phase 1: Design & Contracts (COMPLETE)

**Status**: ✅ Complete
**Outputs**:

- [data-model.md](./data-model.md) - Complete data model specification
- [contracts/cli-interface.md](./contracts/cli-interface.md) - CLI contract with examples
- [contracts/json-output-schema.json](./contracts/json-output-schema.json) - JSON Schema v7
- [quickstart.md](./quickstart.md) - Developer implementation guide

**Data Models Defined**:

- Existing: `Candle`, `TradeSignal`, `TradeExecution`, `BacktestRun`, `MetricsSummary` (reused)
- New: `DirectionMode`, `OutputFormat`, `ConflictEvent`, `DirectionalMetrics`, `BacktestResult`

**Data Flows Documented**:

1. LONG-only backtest flow
2. SHORT-only backtest flow
3. BOTH directions backtest flow (with conflict resolution)
4. Dry-run mode flow

**Contracts Finalized**:

- CLI interface with all arguments, examples, error messages
- JSON output schema with type definitions and validation rules
- Performance guarantees (30s for 100K candles, 10s dry-run)

**Agent Context Updated**:

- GitHub Copilot context file updated with Python 3.11, dependencies, project structure

---

## Phase 2: Implementation (PENDING)

**Status**: ⏸️ Awaiting developer
**Reference**: See [quickstart.md](./quickstart.md) for detailed implementation guide

**Implementation Phases** (from quickstart):

1. **Phase 1**: Core Data Models (2 hours) - Add Pydantic models to `src/models/core.py`
2. **Phase 2**: Backtest Orchestrator (4 hours) - Create `src/backtest/orchestrator.py`
3. **Phase 3**: Metrics Aggregation (3 hours) - Create `src/backtest/metrics.py`
4. **Phase 4**: Output Formatters (3 hours) - Create `src/io/formatters.py`
5. **Phase 5**: CLI Enhancement (2 hours) - Update `src/cli/run_backtest.py`
6. **Phase 6**: Integration Tests (3 hours) - Create end-to-end tests
7. **Phase 7**: Code Quality (2 hours) - Black, Ruff, Pylint, docstrings
8. **Phase 8**: Performance Validation (1 hour) - Benchmark against targets

**Total Estimated Time**: 20 hours (2.5 days)

**Files to Create/Modify**:

- CREATE: `src/backtest/orchestrator.py` (core orchestration logic)
- CREATE: `src/backtest/metrics.py` (metrics aggregation)
- CREATE: `src/io/formatters.py` (text/JSON formatters)
- EDIT: `src/models/core.py` (add 5 new models)
- EDIT: `src/cli/run_backtest.py` (enhance with unified interface)
- CREATE: 4 test files (orchestrator, metrics, formatters, integration)

**Next Command**: `/speckit.tasks` command completed successfully → tasks.md generated with 101 tasks

---

## Constitution Re-Check (Post-Design)

**Status**: ✅ PASS (re-validated)

All design decisions conform to constitution principles:

- Code quality tools integrated (Black, Ruff, Pylint) - Principle X
- Poetry dependency management maintained - Principle IX
- Lazy % logging enforced - Principle X
- Data manifest referencing via `manifest_ref` - Principle VI
- Backtest validation standards met - Principle III
- Model parsimony maintained (no new dependencies) - Principle VII

No new risks or violations identified in design phase.

---

## Completion Summary

**Planning Complete**: ✅ All Phase 0 and Phase 1 tasks complete

**Artifacts Generated**:

1. ✅ research.md - All technical decisions documented (6 major decisions)
2. ✅ data-model.md - Complete data specification (5 new models, 4 flows)
3. ✅ contracts/cli-interface.md - CLI contract with examples and error handling
4. ✅ contracts/json-output-schema.json - JSON Schema v7 with validation
5. ✅ quickstart.md - 8-phase implementation guide (20 hours estimated)
6. ✅ Agent context updated - GitHub Copilot instructions enhanced

**Ready for Implementation**: Developer can proceed with coding following quickstart.md

**Next Steps**:

1. Run `/speckit.tasks` to generate detailed task breakdown
2. Begin implementation starting with Phase 1 (Core Data Models)
3. Follow quickstart guide phases sequentially
4. Validate against constitution at each checkpoint

---

## Branch Information

**Branch**: `002-directional-backtesting`
**Spec File**: `E:\GitHub\trading-strategies\specs\002-directional-backtesting\spec.md`
**Plan File**: `E:\GitHub\trading-strategies\specs\002-directional-backtesting\plan.md`
**Specs Directory**: `E:\GitHub\trading-strategies\specs\002-directional-backtesting`

All planning documents are committed to the feature branch and ready for implementation.
