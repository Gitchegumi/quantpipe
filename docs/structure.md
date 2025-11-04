# Repository Structure (Concise)

High-level map; for deeper strategy / process detail see `docs/strategies.md` and `docs/backtesting.md`.

```text
src/
  indicators/        Technical indicator calculations
  strategy/          Strategy orchestration + state (trend_pullback)
  risk/              Risk sizing + protective logic
  backtest/          Engine, metrics, reproducibility helpers
  io/                Ingestion, formatting, dataset building utilities
  cli/               Command-line entry points
  config/            Parameter models (Pydantic)

specs/               Feature specifications & plans (one folder per feature)
price_data/          Raw + processed (test/validation) symbol datasets
tests/               Unit / integration / performance suites + fixtures
docs/                Human-facing conceptual documentation (you are here)
```

## File Naming Conventions

* Snake case for Python modules
* Lowercase directories
* Feature folders prefixed with zero-padded number (e.g. `005-docs-restructure`)

## Adding New Modules

1. Add module under the most specific existing domain directory.
2. Provide unit tests close to affected behavior.
3. Update `docs/structure.md` only if a new top-level concept is introduced.

## Where Things Live

| Concern | Location |
|---------|----------|
| CLI parameters | `src/cli/*.py` |
| Strategy logic | `src/strategy/trend_pullback/` |
| Indicator math | `src/indicators/` |
| Risk sizing | `src/risk/` |
| Metrics & aggregation | `src/backtest/metrics*.py` |
| Dataset build | `src/cli/build_dataset.py` |
| Config models | `src/config/parameters.py` |
| Specs & research | `specs/<NNN-name>/` |

---
For contribution workflow see `CONTRIBUTIONS.md`.
