# Fixture Manifest Specification

Defines required fields for `tests/fixtures/manifest.yaml` prior to implementing T006a/T036.

## YAML Structure

```yaml
fixtures:
  - id: trend_v1
    filename: fixture_trend_example.csv
    scenario_type: trend
    row_count: 120
    checksum: "<sha256>"
    seed: 42
    indicators_covered: [EMA20, EMA50, ATR14]
    created: 2025-10-30T00:00:00Z
    notes: "Upward drift with minor pullbacks"
  - id: flat_v1
    filename: fixture_flat_prices.csv
    scenario_type: flat
    row_count: 60
    checksum: "<sha256>"
    seed: 42
    indicators_covered: [EMA20, EMA50]
    created: 2025-10-30T00:00:00Z
    notes: "Near-zero volatility for false-signal prevention"
  - id: spike_v1
    filename: fixture_spike_outlier.csv
    scenario_type: spike
    row_count: 75
    checksum: "<sha256>"
    seed: 99
    indicators_covered: [ATR14]
    created: 2025-10-30T00:00:00Z
    notes: "Single large candle to test outlier handling"
```

## Field Definitions

| Field | Description | Constraints |
|-------|-------------|-------------|
| id | Unique identifier for fixture scenario | kebab or snake case |
| filename | CSV file name stored under `tests/fixtures/` | MUST exist in repo |
| scenario_type | Logical category (trend, flat, spike) | Enum fixed |
| row_count | Number of rows (including header) | 10–300 range |
| checksum | SHA256 of file contents | Regenerate on change |
| seed | Random seed used (if generation logic applied) | Integer or null |
| indicators_covered | Indicator set validated using this fixture | Non-empty list |
| created | ISO8601 timestamp | UTC preferred |
| notes | Freeform description | ≤120 chars recommended |

## Generation Guidance

1. Build fixture DataFrame in code (not yet implemented) with seeded randomness where needed.
2. Export to CSV ensuring columns ordered: timestamp, open, high, low, close, (optional volume).
3. Compute SHA256: `Get-FileHash -Algorithm SHA256 fixture_trend_example.csv` (PowerShell).
4. Update manifest entry with row_count & checksum.

## Validation Checks (Future Test `test_fixture_validation.py`)

- Each manifest entry filename exists.
- `row_count` matches actual file rows.
- `checksum` matches current file contents.
- Required columns present and ordered.

## Rationale

Ensures reproducibility, auditability, and quick verification of fixture integrity (supports FR-004, SC-001).
