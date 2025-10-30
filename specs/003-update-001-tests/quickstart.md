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
7. Confirm runtime targets: unit <5s, integration <30s, performance <120s (suite cumulative). Allow ±20% tolerance for transient CI variance; consistent excess requires optimization or classification as flaky.
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

Use minimal OHLC CSVs in `tests/fixtures/` (10–300 rows). Provide edge case sets (flat, spike, trend). Columns MUST be ordered: timestamp, open, high, low, close, (optional volume). See `fixture-manifest.md` for required metadata fields.

## Stability Check

Loop test subset locally:

```powershell
1..3 | ForEach-Object { poetry run pytest -m unit }
```

Interpretation: Any failure in these 3 runs OR runtime > tier budget + 20% flags the relevant test(s) for flakiness triage.

## Next

Proceed to implementation tasks once redundant tests identified and glossary definitions accepted.
