# Quickstart: Update 001 Test Suite Alignment

## Goals

Realign and stabilize 001 strategy tests with deterministic fixtures and tiered execution.

## Steps

1. Ensure environment: `poetry install`.
2. Run fast tests only: `poetry run pytest -m unit`.
3. Run integration tests: `poetry run pytest -m integration`.
4. Run performance tests (optional): `poetry run pytest -m performance`.
5. Regenerate fixtures if modified: keep under version control if small; add manifest if new.
6. Validate lint & format:
   - `poetry run black src/ tests/`
   - `poetry run ruff check src/ tests/`
   - `poetry run pylint src/ --score=yes`
7. Confirm runtime targets: unit <5s, integration <30s, performance <120s.
8. Document removed tests in commit body.

## Markers

Add markers at top of files or per test:

```python
import pytest

@pytest.mark.unit
def test_indicator_ema_warmup_behavior(...):
    ...
```

## Fixture Design

Use minimal OHLC CSVs in `tests/fixtures/` (10–300 rows). Provide edge case sets (flat, spike, trend).

## Stability Check

Loop test subset locally:

```powershell
1..3 | ForEach-Object { poetry run pytest -m unit }
```

## Next

Proceed to implementation tasks once redundant tests identified.
