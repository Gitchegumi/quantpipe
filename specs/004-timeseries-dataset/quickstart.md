# Quickstart: Time Series Dataset Preparation

## Purpose

Standardize raw price data into deterministic test/validation partitions for reproducible backtests.

## Prerequisites

- Python 3.11+ environment (Poetry managed)
- Raw CSV files placed under `price_data/raw/<symbol>/`
- Required columns: timestamp, open, high, low, close, volume

## Installation

```bash
# Ensure dependencies installed
poetry install
```

## Steps

### 1. Prepare Raw Data Structure

Organize raw CSV files by symbol:

```text
price_data/
└── raw/
    ├── eurusd/
    │   ├── eurusd_2020.csv
    │   └── eurusd_2021.csv
    └── usdjpy/
        └── usdjpy_2020.csv
```

### 2. Build Dataset for Single Symbol

```bash
# Build dataset for specific symbol
poetry run python -m src.cli.build_dataset --symbol eurusd

# With custom paths
poetry run python -m src.cli.build_dataset --symbol eurusd \
  --raw-path custom/raw \
  --output-path custom/processed
```

**Output:**

```text
Building dataset for symbol: eurusd

                              Dataset: eurusd
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric           ┃ Value                                                 ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Total Rows       │ 1,440,000                                             │
│ Test Rows        │ 1,152,000 (80.0%)                                     │
│ Validation Rows  │ 288,000 (20.0%)                                       │
│ Time Span        │ 2020-01-01 00:00:00+00:00 → 2021-12-31 23:59:00+00:00 │
│ Validation Start │ 2021-10-04 19:12:00+00:00                             │
│ Gap Count        │ 142                                                   │
│ Overlap Count    │ 5                                                     │
│ Source Files     │ 2                                                     │
└──────────────────┴───────────────────────────────────────────────────────┘

✓ Dataset build successful
```

### 3. Build Datasets for All Symbols

```bash
# Process all discovered symbols
poetry run python -m src.cli.build_dataset --all

# Force rebuild (future enhancement)
poetry run python -m src.cli.build_dataset --all --force
```

**Output:**

```text
Building datasets for all symbols
Raw path: price_data/raw
Output path: price_data/processed

                Build Summary
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Metric            ┃ Value        ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Duration          │ 12.45 seconds│
│ Symbols Processed │ 2            │
│ Symbols Skipped   │ 0            │
│ Total Rows        │ 2,880,000    │
│ Test Rows         │ 2,304,000    │
│ Validation Rows   │ 576,000      │
└───────────────────┴──────────────┘

Processed Symbols:
  ✓ eurusd
  ✓ usdjpy

✓ All symbols processed successfully
```

### 4. Inspect Outputs

After building, inspect the generated structure:

```text
price_data/
└── processed/
    ├── build_summary.json          # Consolidated summary
    ├── eurusd/
    │   ├── metadata.json            # Per-symbol metadata
    │   ├── test/
    │   │   └── eurusd_test.csv      # 80% partition
    │   └── validate/
    │       └── eurusd_validate.csv  # 20% partition (most recent)
    └── usdjpy/
        ├── metadata.json
        ├── test/
        │   └── usdjpy_test.csv
        └── validate/
            └── usdjpy_validate.csv
```

**Sample metadata.json:**

```json
{
  "symbol": "eurusd",
  "total_rows": 1440000,
  "test_rows": 1152000,
  "validation_rows": 288000,
  "start_timestamp": "2020-01-01T00:00:00Z",
  "end_timestamp": "2021-12-31T23:59:00Z",
  "validation_start_timestamp": "2021-10-04T19:12:00Z",
  "gap_count": 142,
  "overlap_count": 5,
  "canonical_timezone": "UTC",
  "build_timestamp": "2025-10-30T18:30:00.123456Z",
  "schema_version": "v1",
  "source_files": [
    "price_data/raw/eurusd/eurusd_2020.csv",
    "price_data/raw/eurusd/eurusd_2021.csv"
  ]
}
```

### 5. Execute Backtest Using Processed Data

```bash
# Run backtest with partition-based evaluation (future: T032)
poetry run python -m src.cli.run_backtest --symbol eurusd --mode split
```

### 6. Review Results

Results will be separated by partition in `results/` directory (future implementation).

## Validation Checklist

- [x] Each processed symbol has two partitions (unless skipped for low rows)
- [x] Validation partition row count ≈ 20% of total (remainder after floor)
- [x] Metadata timestamps align with raw source
- [x] No synthetic rows introduced (gaps/overlaps reported only)
- [x] Gaps counted silently, overlaps logged as warnings
- [x] All timestamps normalized to UTC

## Troubleshooting

| Symptom                            | Possible Cause                       | Resolution                                                                             |
| ---------------------------------- | ------------------------------------ | -------------------------------------------------------------------------------------- |
| Symbol missing in processed output | Schema mismatch or insufficient rows | Check `build_summary.json` for skip reason; ensure CSV has timestamp + OHLCV columns   |
| Insufficient rows error            | Dataset has < 500 rows               | Combine multiple files or use longer time period                                       |
| Schema mismatch error              | Column names inconsistent            | Standardize column names: timestamp, open, high, low, close, volume (case-insensitive) |
| Validation metrics absent          | Backtest not run in split mode       | Re-run with `--mode split` (future feature)                                            |
| Excessive gaps reported            | Raw data cadence inconsistent        | Expected for historical data; gaps counted silently                                    |
| Overlap warnings                   | Duplicate timestamps in raw data     | Review source data; duplicates automatically deduplicated (first occurrence kept)      |

## Advanced Usage

### Debug Mode

```bash
# Enable detailed logging
poetry run python -m src.cli.build_dataset --symbol eurusd --log-level DEBUG
```

### Custom Split Ratio

Currently fixed at 80/20. Future enhancement: configurable via CLI flag.

### Performance Expectations

- Build time: ~2 minutes for 1M combined rows (per spec SC-005)
- Memory usage: < 1GB for typical datasets
- Processing: Sequential per symbol (parallel future enhancement)

## Next Steps

- Add rolling evaluation modes (future)
- Consider Parquet for performance if large-scale datasets emerge (future)
- Implement backtest split mode integration (T028-T034)
