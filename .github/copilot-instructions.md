# trading-strategies Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-30

## Active Technologies
- Python 3.13 + HoloViews 1.19+, hvplot 0.10+, Datashader 0.16+, Panel 1.4+, Bokeh 3.4+ (017-dynamic-viz-indicators)
- N/A (in-memory visualization) (017-dynamic-viz-indicators)
- Python 3.11+ + NumPy (vectorized operations), pytest (testing) (018-strategy-trade-rules)
- N/A (in-memory arrays) (018-strategy-trade-rules)
- Python 3.11+ + Polars (vectorized data), HoloViews/Datashader (visualization), Pytest (testing) (019-fix-portfolio-viz)
- N/A (stateless execution, outputs to files) (019-fix-portfolio-viz)
- Python 3.11 (per pyproject.toml) + numpy, pandas, polars, pydantic (v2.4.0+), pytest (021-decouple-risk-management)
- N/A (file-based config, memory-resident processing) (021-decouple-risk-management)
- Python 3.13 + Click (CLI), pytest (testing), Jinja2 (template rendering) (022-strategy-templating)
- N/A (file system for scaffold output) (022-strategy-templating)

- Python 3.13 + numpy, pandas, pydantic, rich (existing); no new dependencies required (002-directional-backtesting)
- CSV files for price data input; text/JSON files for backtest results output (002-directional-backtesting)
- Python 3.13 + pytest (for tests), numpy, pandas (used in indicator calculations), pydantic (configs), rich/logging (structured output), Black/Ruff/Pylint (quality gates) (003-update-001-tests)
- File-based fixtures (CSV / in-repo small synthetic datasets); no database (003-update-001-tests)
- Python 3.13 (per project guidelines) + numpy, pandas, pydantic, rich (logging/output), pytest (tests) – no new deps planned (004-timeseries-dataset)
- File system (CSV inputs; processed outputs as CSV + JSON metadata) (004-timeseries-dataset)
- Python 3.13 (per project standards) + Poetry-managed; numpy, pandas (data & metrics), pydantic (config validation), rich/logging (structured logs), pytest (tests). No new external runtime services. (006-multi-strategy)
- File-based artifacts (CSV/JSON) for outputs; in-memory state during runs. (006-multi-strategy)
- Python 3.13 (confirmed by constitution) + numpy, pandas, pydantic, rich (existing). Optional: numba (JIT) [NEEDS CLARIFICATION: adopt as hard dependency or optional fallback?]. (007-performance-optimization)
- File-based time series (CSV current). Parquet/Arrow considered Phase 2 optimization [NEEDS CLARIFICATION: introduce pyarrow now or defer?]. (007-performance-optimization)
- Python 3.13 (confirmed by constitution) + numpy, pandas, pydantic, rich (progress/logging), pytest; optional numba (TBD NEEDS CLARIFICATION: adopt now or defer) → default: defer numba until baseline vectorization measured. (010-scan-sim-perf)
- File-based time series (CSV inputs) and in-memory arrays; potential future Parquet/Arrow (out of current scope). (010-scan-sim-perf)
- Python 3.13 (confirmed by constitution) + numpy, pandas, pydantic, rich (progress/logging), pytest; optional numba (defer until baseline measured); optional Polars (pilot ingestion & columnar transformation path, adoption gated by ROI criteria). (010-scan-sim-perf)
- File-based time series (CSV inputs) and in-memory arrays; optional Polars DataFrame / LazyFrame for ingestion & preprocessing; potential future Parquet/Arrow (still deferred until Polars evaluation complete). (010-scan-sim-perf)
- Python 3.13 + pytest, polars, pandas, numpy (012-cleanup-tests)
- N/A (test cleanup, no data storage changes) (012-cleanup-tests)
- Python 3.13 + Polars, Pandas, Rich (progress bars) (013-multi-symbol-backtest)
- Parquet files (`price*data/processed/<pair>/<dataset>/<pair>*<dataset>.parquet`) (013-multi-symbol-backtest)
- Python 3.13 + Polars, Pandas, Rich (progress bars) (013-multi-symbol-backtest)
- Python 3.13 + `lightweight-charts`, `polars` (data), `pandas` (view compatibility) (014-interactive-viz)
- N/A (Transient visualization) (014-interactive-viz)
- Python 3.13 + `lightweight-charts`, `polars` (data), `pandas` (view compatibility) (014-interactive-viz)
- Python 3.13 + `lightweight-charts`, `polars` (data), `pandas` (view compatibility) (014-interactive-viz)
- Python 3.13 + Polars (for vectorized resampling), existing pandas/numpy (015-multi-timeframe-backtest)
- `.time_cache/` directory for resampled Parquet files (015-multi-timeframe-backtest)
- Python 3.13 + HoloViews, hvplot, Panel, Bokeh (existing visualization stack) (016-multi-symbol-viz)
- N/A (HTML output to `results/dashboards/`) (016-multi-symbol-viz)

- Python 3.13 (chosen for ecosystem breadth, numerical libs, readability) + numpy (vector math), pandas (time series handling), ta-lib or custom EMA/ATR/RSI fallback implementation, pydantic (config validation), rich/logging (structured logs), pytest (tests) (001-trend-pullback)
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
- Markdownlint: Validate all Markdown files (\*.md)

**Logging Standards:**

- MUST use lazy % formatting: `logger.info("Processing %d items", count)`
- PROHIBITED: F-strings in logging: `logger.info(f"Processing {count} items")`
- All W1203 warnings MUST be fixed

**Documentation (Principle VIII):**

- MUST follow PEP 8 style guidelines
- All modules, classes, methods, and functions MUST include complete docstrings (PEP 257)
- Use type hints for all signatures
- Line length ≤88 characters (Black standard)

**Commit Messages (Principle XI):**

- Format: `<semantic-tag>(<spec-number>): <Descriptive Title> (<Task-number>)`
- Semantic tags: docs, test, feat, fix, break, chore
- Example: `test(008): Add unknown symbol validation tests (T046)`
- Include detailed summary with bullet points for multi-part changes
- See Constitution Principle XI for full requirements

## Recent Changes
- 022-strategy-templating: Added Python 3.13 + Click (CLI), pytest (testing), Jinja2 (template rendering)
- 021-decouple-risk-management: Added Python 3.11 (per pyproject.toml) + numpy, pandas, polars, pydantic (v2.4.0+), pytest
- 019-fix-portfolio-viz: Added Python 3.11+ + Polars (vectorized data), HoloViews/Datashader (visualization), Pytest (testing)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
