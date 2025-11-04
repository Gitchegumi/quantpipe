# Contributions Guide

This guide contains everything needed to set up a development environment, pass quality gates, and propose changes. The README intentionally stays lean; all contributor details live here.

> Note: Conventional filename is `CONTRIBUTING.md`; this project intentionally uses `CONTRIBUTIONS.md` per maintainer preference.

## 1. Prerequisites

| Requirement | Version / Notes |
|-------------|-----------------|
| Python      | 3.11.x (deterministic fixtures depend on this) |
| Poetry      | Latest stable (dependency + virtualenv management) |
| OS          | Windows, macOS, Linux supported (examples show PowerShell + bash) |

Install Poetry (see: [Poetry Installation Guide](https://python-poetry.org/docs/#installation)).

## 2. Environment Setup

```powershell
# From repository root
poetry install

# (Optional) create shell
poetry shell

# Verify
poetry run python -c "import sys; print(sys.version)"
```

Regenerate lockfile only when adding/upgrading dependencies:

```powershell
poetry add <package>
poetry lock --no-update   # lock refresh without version bumps
```

## 3. Quality Gates

All changes must satisfy:

| Gate | Command | Pass Criteria |
|------|---------|---------------|
| Formatting | `poetry run black src/ tests/` | No diffs after run |
| Fast Lint | `poetry run ruff check src/ tests/` | 0 errors |
| Deep Lint | `poetry run pylint src/ --score=yes` | Score ≥ 8.0/10 |
| Unit Tests | `poetry run pytest -m unit` | 100% pass <5s |
| Full Suite (pre-PR) | `poetry run pytest` | Green |

Optional coverage:

```powershell
poetry run pytest --cov=src --cov-report=term-missing
```

## 4. Test Tiers

| Tier | Path | Target Runtime | Data Size | Purpose |
|------|------|----------------|-----------|---------|
| Unit | `tests/unit/` | <5s | <100 rows | Core logic & indicators |
| Integration | `tests/integration/` | <30s | 100–10k rows | Multi-module behavior |
| Performance | `tests/performance/` | <120s | >10k rows | Throughput & scaling |

Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.performance`.

## 5. Branch & Feature Workflow

This repository uses a structured feature specification workflow.

1. Create a feature branch via script:

```powershell
\.specify\scripts\powershell\create-new-feature.ps1 -Json "Add concise description here"
```

* Complete `specs/<NNN-short-name>/spec.md` (if template not already filled)
* Plan & implement
* Open PR referencing feature number (e.g. `005`)

Branch naming pattern: `NNN-short-slug` (e.g. `005-docs-restructure`).

## 6. Logging Standards

| Rule | Example |
|------|---------|
| Use lazy `%` formatting | `logger.info("Processed %d rows", count)` |
| Avoid f-strings in logs | `# BAD logger.info(f"Processed {count} rows")` |
| Structured context | Prefer key=value in message or enrich via adapter |

## 7. Code Style

* PEP 8 + enforced by Black (88 char lines)
* Type hints required on all public functions/classes
* Docstrings (PEP 257) required for modules, classes, functions
* Prefer pure functions for indicator math

## 8. Adding Tests

1. Place new fixture CSVs in `tests/fixtures/` and register in manifest if required
2. Keep unit fixtures tiny (<100 rows) and deterministic
3. Avoid randomness; if needed, seed explicitly
4. For performance tests, gate by marker so they don't run by default in fast loops

## 9. Backtesting & Datasets (Contributor View)

End-user details sit in `docs/backtesting.md`; here only contributor notes:

* Dataset builder lives in `src/cli/build_dataset.py`
* Split-mode command: `src.cli.run_split_backtest`
* Keep partition logic chronological (no random shuffle)

## 10. Strategy Docs & Specs

* High-level strategy summaries: `docs/strategies.md`
* Full specification history: `specs/` directory (one folder per feature)
* Avoid duplicating detailed logic here—link instead

## 11. Commit Hygiene

| Aspect | Guideline |
|--------|-----------|
| Scope | One logical change per commit |
| Message Subject | Imperative, ≤72 chars (e.g. `Refactor risk sizing calc`) |
| Body | Explain why (if non-trivial) |
| Referencing Spec | Include feature number: `Refs 005` |

## 12. Opening a Pull Request

Checklist before pushing:

* [ ] Black & Ruff clean
* [ ] Pylint ≥ 8.0
* [ ] Unit tests green
* [ ] Added/updated tests for new logic
* [ ] Updated spec / docs if behavior or usage changed

## 13. Security & Data Integrity

* No external network calls in tests
* Deterministic seeds for reproducibility
* Validate OHLC columns on ingestion (exceptions on missing columns)

## 14. License & Compliance

Code is proprietary. Do not copy external code without license review.

## 15. FAQ

| Question | Answer |
|----------|--------|
| Why Poetry? | Reproducibility + lockfile discipline |
| Can I add dependencies? | Only if justified in spec / PR description |
| Add a docs site generator? | Future consideration; not in current scope |

## 16. Future Improvements (Non-blocking)

* Automated link checker in CI
* Pre-commit hook running Black + Ruff
* MkDocs or Sphinx site if docs volume grows

---
Happy building—open a draft PR early for feedback.
