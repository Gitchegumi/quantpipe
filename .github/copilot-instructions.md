# trading-strategies Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-30

## Active Technologies
- Python 3.11 + numpy, pandas, pydantic, rich (existing); no new dependencies required (002-directional-backtesting)
- CSV files for price data input; text/JSON files for backtest results output (002-directional-backtesting)
- Python 3.11 + pytest (for tests), numpy, pandas (used in indicator calculations), pydantic (configs), rich/logging (structured output), Black/Ruff/Pylint (quality gates) (003-update-001-tests)
- File-based fixtures (CSV / in-repo small synthetic datasets); no database (003-update-001-tests)
- Python 3.11 (per project guidelines) + numpy, pandas, pydantic, rich (logging/output), pytest (tests) – no new deps planned (004-timeseries-dataset)
- File system (CSV inputs; processed outputs as CSV + JSON metadata) (004-timeseries-dataset)
- Python 3.11 (per project standards) + Poetry-managed; numpy, pandas (data & metrics), pydantic (config validation), rich/logging (structured logs), pytest (tests). No new external runtime services. (006-multi-strategy)
- File-based artifacts (CSV/JSON) for outputs; in-memory state during runs. (006-multi-strategy)

- Python 3.11 (chosen for ecosystem breadth, numerical libs, readability) + numpy (vector math), pandas (time series handling), ta-lib or custom EMA/ATR/RSI fallback implementation, pydantic (config validation), rich/logging (structured logs), pytest (tests) (001-trend-pullback)
- Poetry (mandatory package manager for dependency management and virtual environments)
- Black (≥23.10.0) - code formatter
- Ruff (≥0.1.0) - fast Python linter
- Pylint (≥3.3.0) - comprehensive linter
- Markdownlint (markdownlint-cli2) - Markdown linter

## Project Structure

```text
src/
tests/
pyproject.toml  # Poetry configuration
poetry.lock     # Locked dependencies (MUST be committed)
```

## Commands

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Code quality checks
poetry run black src/ tests/
poetry run ruff check src/ tests/
poetry run pylint src/ --score=yes
markdownlint-cli2 "**/*.md" "!poetry.lock"
```

## Dependency Management

Python projects MUST use Poetry. Prohibit requirements.txt. All dependencies in pyproject.toml. See Constitution Principle IX.

## Code Quality

**Formatting & Linting (Principle X):**
- Black: Format all code (88 char lines)
- Ruff: Zero errors required
- Pylint: Minimum 8.0/10 score
- Markdownlint: Validate all Markdown files (*.md)

**Logging Standards:**
- MUST use lazy % formatting: `logger.info("Processing %d items", count)`
- PROHIBITED: F-strings in logging: `logger.info(f"Processing {count} items")`
- All W1203 warnings MUST be fixed

**Documentation (Principle VIII):**
- MUST follow PEP 8 style guidelines
- All modules, classes, methods, and functions MUST include complete docstrings (PEP 257)
- Use type hints for all signatures
- Line length ≤88 characters (Black standard)

## Recent Changes
- 006-multi-strategy: Added Python 3.11 (per project standards) + Poetry-managed; numpy, pandas (data & metrics), pydantic (config validation), rich/logging (structured logs), pytest (tests). No new external runtime services.
- 004-timeseries-dataset: Added Python 3.11 (per project guidelines) + numpy, pandas, pydantic, rich (logging/output), pytest (tests) – no new deps planned
- 003-update-001-tests: Added Python 3.11 + pytest (for tests), numpy, pandas (used in indicator calculations), pydantic (configs), rich/logging (structured output), Black/Ruff/Pylint (quality gates)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
