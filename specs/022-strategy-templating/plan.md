# Implementation Plan: Strategy Templating Framework

**Branch**: `022-strategy-templating` | **Date**: 2025-12-26 | **Spec**: [spec.md](file:///e:/GitHub/trading-strategies/specs/022-strategy-templating/spec.md)
**Input**: Feature specification from `/specs/022-strategy-templating/spec.md`

## Summary

Implement a strategy templating framework that enables users to quickly scaffold new strategies using a CLI command, with automatic registry integration and fail-fast contract validation. The implementation builds on existing `Strategy` Protocol and `StrategyRegistry` patterns.

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: Click (CLI), pytest (testing), Jinja2 (template rendering)
**Storage**: N/A (file system for scaffold output)
**Testing**: pytest (unit + integration tests)
**Target Platform**: Windows/Linux CLI
**Project Type**: Single project CLI extension
**Performance Goals**: Scaffold generation < 1 second
**Constraints**: Must maintain backward compatibility with existing strategies
**Scale/Scope**: 1 new CLI command, 1 validator module, 1 reference strategy, 1 documentation file

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Principle                          | Status  | Notes                                                    |
| ---------------------------------- | ------- | -------------------------------------------------------- |
| I. Strategy-First Architecture     | ✅ Pass | Enhances strategy modularity with standardized templates |
| II. Risk Management Integration    | ✅ Pass | Template includes required risk parameter placeholders   |
| VII. Model Parsimony               | ✅ Pass | Simple validator, no over-engineering                    |
| VIII. Code Quality & Documentation | ✅ Pass | Template includes docstrings, type hints required        |
| IX. Dependency Management          | ✅ Pass | Uses Poetry, Jinja2 added as dev dependency              |
| X. Code Quality Automation         | ✅ Pass | Template passes Black/Ruff on generation                 |

## Project Structure

### Documentation (this feature)

```text
specs/022-strategy-templating/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output (this feature has no NEEDS CLARIFICATION)
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
src/
├── strategy/
│   ├── base.py              # [MODIFY] Add validation function
│   ├── validator.py         # [NEW] Strategy contract validator
│   ├── scaffold/            # [NEW] Scaffold templates directory
│   │   ├── __init__.py
│   │   ├── templates/       # [NEW] Jinja2 templates
│   │   │   ├── strategy.py.j2
│   │   │   ├── __init__.py.j2
│   │   │   └── signal_generator.py.j2
│   │   └── generator.py     # [NEW] Scaffold generator
│   └── simple_momentum/     # [NEW] Reference strategy
│       ├── __init__.py
│       └── strategy.py
├── cli/
│   └── scaffold_strategy.py # [NEW] CLI scaffold command

tests/
├── unit/
│   ├── test_strategy_validator.py     # [NEW] Validator unit tests
│   └── test_scaffold_generator.py     # [NEW] Scaffold unit tests
└── integration/
    └── test_strategy_scaffold_e2e.py  # [NEW] E2E scaffold tests

docs/
└── strategy_authoring.md              # [NEW] Strategy authoring guide
```

**Structure Decision**: Single project extension using existing `src/strategy/` and `src/cli/` structure.

---

## Proposed Changes

### Component 1: Strategy Validator

Creates a validation module that checks strategy compliance before execution.

#### [NEW] [validator.py](file:///e:/GitHub/trading-strategies/src/strategy/validator.py)

- `validate_strategy(strategy_class) -> ValidationResult` function
- Checks for required `metadata` property
- Checks for required `generate_signals(candles, parameters)` method
- Validates `StrategyMetadata` fields are non-empty
- Returns `ValidationResult` with errors list and `is_valid` bool
- Raises `StrategyValidationError` on failure (for fail-fast behavior)

---

### Component 2: CLI Scaffold Command

New CLI command to generate strategy from template.

#### [NEW] [scaffold_strategy.py](file:///e:/GitHub/trading-strategies/src/cli/scaffold_strategy.py)

- `poetry run python -m src.cli.scaffold_strategy <name>` entry point
- Generates strategy directory at `src/strategy/<name>/`
- Files generated: `__init__.py`, `strategy.py`, `signal_generator.py`
- Auto-registers strategy in `StrategyRegistry`
- Uses Jinja2 templates from `src/strategy/scaffold/templates/`

---

### Component 3: Scaffold Templates

Jinja2 templates for generating strategy files.

#### [NEW] [generator.py](file:///e:/GitHub/trading-strategies/src/strategy/scaffold/generator.py)

- `ScaffoldGenerator` class with `generate(name, output_dir)` method
- Template rendering with Jinja2
- File writing with proper Python formatting

#### [NEW] [strategy.py.j2](file:///e:/GitHub/trading-strategies/src/strategy/scaffold/templates/strategy.py.j2)

- Template for main strategy class implementing `Strategy` Protocol
- Includes TODO markers for user customization
- Pre-filled `metadata` property with placeholder values
- Stubbed `generate_signals` and optional `scan_vectorized` methods

---

### Component 4: Reference Strategy

Simple momentum strategy as working example.

#### [NEW] [simple_momentum/strategy.py](file:///e:/GitHub/trading-strategies/src/strategy/simple_momentum/strategy.py)

- Complete implementation of `Strategy` Protocol
- Uses single indicator (EMA crossover)
- Well-documented with comments explaining each section
- Passes validation and produces trades in backtest

---

### Component 5: Strategy Integration

Wire validation into backtest execution flow.

#### [MODIFY] [registry.py](file:///e:/GitHub/trading-strategies/src/strategy/registry.py)

- Add `validate_on_register` parameter to `register()` method
- Call validator before registering strategy
- Fail with clear error if validation fails

---

### Component 6: Documentation

Complete strategy authoring guide.

#### [NEW] [strategy_authoring.md](file:///e:/GitHub/trading-strategies/docs/strategy_authoring.md)

- Strategy lifecycle explanation
- Required methods with full signatures
- Integration with indicator system
- Integration with risk management
- Examples and troubleshooting

---

## Verification Plan

### Automated Tests

All tests runnable via standard pytest commands.

**Unit Tests (run with `poetry run pytest tests/unit/test_strategy_*.py -v`)**:

| Test File                    | Coverage                                                              |
| ---------------------------- | --------------------------------------------------------------------- |
| `test_strategy_validator.py` | Validator catches missing methods, invalid metadata, wrong signatures |
| `test_scaffold_generator.py` | Template rendering, file generation, Python syntax validity           |

**Integration Tests (run with `poetry run pytest tests/integration/test_strategy_scaffold*.py -v`)**:

| Test File                       | Coverage                                 |
| ------------------------------- | ---------------------------------------- |
| `test_strategy_scaffold_e2e.py` | Full scaffold → validate → backtest flow |

**Existing Tests (ensure no regressions with `poetry run pytest tests/ -v`)**:

| Test File                                    | Purpose                               |
| -------------------------------------------- | ------------------------------------- |
| `tests/unit/test_strategy_metadata.py`       | Verify StrategyMetadata still works   |
| `tests/integration/test_strategy_signals.py` | Verify existing strategies unaffected |

### Manual Verification

1. **Scaffold Command Test**:

   ```powershell
   poetry run python -m src.cli.scaffold_strategy test_strat
   # Expected: Directory created at src/strategy/test_strat/ with 3 files
   # Verify: Check files exist and contain TODO markers
   ```

2. **Validation Fail-Fast Test**:

   ```powershell
   # Delete generate_signals from scaffolded strategy, then run backtest
   # Expected: Clear error message with method signature and example
   ```

3. **Reference Strategy Backtest**:

   ```powershell
   poetry run python -m src.cli.run_backtest --strategy simple_momentum --data <test_data>
   # Expected: Backtest completes with at least one trade
   ```

### Code Quality Checks

```powershell
# Must pass before merge
poetry run black src/ tests/
poetry run ruff check src/ tests/
poetry run pylint src/ --score=yes  # Target: ≥9.0
```

## Complexity Tracking

No constitution violations requiring justification.
