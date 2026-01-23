# Research: Package 'quantpipe' CLI Tool

**Feature**: `package-quantpipe-cli`
**Status**: Completed

## Unknowns & Resolutions

### 1. Structure of `src/cli/run_backtest.py`

**Question**: How is the current CLI implemented? Can it be easily adapted to a subcommand structure?
**Resolution**:

- The current implementation has a monolithic `main()` function (800+ lines) that handles argument parsing and business logic.
- It includes logic for backtesting, listing strategies, registering strategies, and running parameter sweeps.
- **Decision**: Refactor `src/cli/run_backtest.py` to separate argument definition (`configure_backtest_parser`) and execution logic (`run_backtest_command`). This allows both the legacy script and the new `quantpipe` CLI to share the same code.

### 2. Dependency Management

**Question**: How to expose the CLI script?
**Resolution**:

- Project uses Poetry.
- **Decision**: Use `[tool.poetry.scripts]` in `pyproject.toml` to map `quantpipe` to `src.cli.main:main`.

## Implementation Strategy

1. **Refactor**: Extract logic from `src/cli/run_backtest.py` into reusable functions.
2. **New Entry Point**: Create `src/cli/main.py` with `argparse` subparsers.
3. **Registration**: Update `pyproject.toml`.
