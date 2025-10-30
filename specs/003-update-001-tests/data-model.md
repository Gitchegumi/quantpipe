# Data Model: Update 001 Test Suite Alignment

## Entities

### Strategy Configuration

Fields:

- name (string)
- parameters (mapping: str -> numeric/string)
- version (string)
  Constraints:
- Parameters documented in spec; test uses stable subset only.

### Fixture Price Series

Fields:

- timestamp (datetime or string ISO)
- open (float)
- high (float)
- low (float)
- close (float)
- volume (optional float)
  Constraints:
- Must be strictly ordered by timestamp ascending (fixture dependency for indicators).
- Columns MUST appear in order: timestamp, open, high, low, close, (optional volume) to simplify parsing.
- Length must meet minimum lookback for indicators under test OR warm-up logic applied; deterministic fixture scope is 10–300 rows (see `glossary.md`).

### Risk Parameters

Fields:

- account_balance (float)
- risk_fraction (float 0<r<=1)
- volatility_value (float)
  Constraints:
- risk_fraction <= 0.05 default assumption for tests.

### Test Tier

Fields:

- name (enum: unit | integration | performance)
- time_budget_seconds (int)
- deterministic (bool)
  Constraints:
- Unit deterministic = true; performance deterministic may be false only if justified with seeded randomness.

## Relationships

- Strategy Configuration referenced by unit and integration tests.
- Fixture Price Series consumed by indicator and signal tests across tiers.
- Risk Parameters combined with Strategy Configuration for sizing calculations.
- Test Tier assigned to each test file via marker or directory location.

## Validation Rules

- All fixtures must avoid missing OHLC values; tests assert non-null rows.
- Risk sizing tests assert resulting position size > 0 and <= account_balance \* risk_fraction.
- Indicator tests assert EMA warm-up produces expected first stable value after lookback period.
  - Fixture validation tests assert column ordering and row count within supported range.

## State Transitions

Not applicable; entities are static inputs to tests.

## Notes

Data model focused on test input artifacts rather than production persistence; no identity/uniqueness beyond filename and parameter mapping keys.
