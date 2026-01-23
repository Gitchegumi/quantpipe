# Implementation Plan - Package 'quantpipe' CLI Tool

Feature: **package-quantpipe-cli**
Branch: `028-package-quantpipe-cli`
Spec: [spec.md](spec.md)

## Goal Description

Package the application as a standard Python package with a `quantpipe` CLI entry point. This enables system-wide installation and consistent execution via `quantpipe backtest` subcommand, replacing the direct module invocation `python -m src.cli.run_backtest`.

## User Review Required

> [!NOTE]
> This change introduces a subcommand structure. The legacy method (`python -m src.cli.run_backtest`) will continue to work, but the new preferred method is `quantpipe backtest [args]`.

## Proposed Changes

### Infrastructure

#### [MODIFY] [pyproject.toml](file:///e:/GitHub/trading-strategies/pyproject.toml)

- Add `[tool.poetry.scripts]` section.
- Define `quantpipe = "src.cli.main:main"`.

### CLI Logic

#### [MODIFY] [src/cli/run_backtest.py](file:///e:/GitHub/trading-strategies/src/cli/run_backtest.py)

- **Refactor**: Extract argument definition logic from `main()` into `configure_backtest_parser(parser)`.
- **Refactor**: Extract execution logic from `main()` into `run_backtest_command(args)`.
- **Maintain**: `main()` should call these new functions to preserve backward compatibility.

#### [NEW] [src/cli/main.py](file:///e:/GitHub/trading-strategies/src/cli/main.py)

- Implement `main()` entry point.
- Set up `argparse.ArgumentParser` with `add_subparsers`.
- Create `backtest` subcommand using `configure_backtest_parser` and `run_backtest_command` imported from `run_backtest.py`.

## Verification Plan

### Automated Tests

- Run existing unit tests to ensure refactoring didn't break `run_backtest.py`.
- `pytest tests/unit/cli` (if exists) or create basic test for arg parsing.

### Manual Verification

1. **Install Package**:

   ```bash
   poetry install
   ```

2. **Verify Command**:

   ```bash
   poetry run quantpipe --help
   poetry run quantpipe backtest --help
   ```

3. **Execute Backtest**:

   ```bash
   poetry run quantpipe backtest --direction LONG --pair EURUSD --dataset test --dry-run
   ```

4. **Legacy Check**:

   ```bash
   python -m src.cli.run_backtest --direction LONG --pair EURUSD --dataset test --dry-run
   ```
