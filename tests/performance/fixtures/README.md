# Performance Test Fixtures

This directory contains references and manifests for performance benchmark datasets.

## Baseline Dataset

The baseline performance benchmark uses a ~6.9M row dataset:

- **Path**: `price_data/raw/eurusd/eurusd_2024.csv`
- **Symbol**: EURUSD
- **Timeframe**: 1 minute
- **Approximate Row Count**: 6,900,000
- **Coverage**: Full year 2024

## Performance Targets

### Baseline (SC-001)

- **Runtime**: ≤ 120 seconds
- **Throughput**: ≥ 3.5M rows/minute

### Stretch Goal (SC-012)

- **Runtime**: ≤ 90 seconds

## Usage in Tests

```python
from pathlib import Path

BASELINE_DATASET_PATH = Path("price_data/raw/eurusd/eurusd_2024.csv")
BASELINE_ROW_COUNT = 6_900_000
BASELINE_TARGET_SECONDS = 120
```

## Dataset Availability

The baseline dataset is stored in `price_data/raw/` but is excluded from version
control via `.gitignore`. Tests will be skipped if the dataset is not available.

To run performance benchmarks, ensure the baseline dataset is present:

```bash
pytest tests/performance/ -m performance
```
