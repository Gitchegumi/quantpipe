# Quickstart: Time Series Dataset Preparation

## Purpose

Standardize raw price data into deterministic test/validation partitions for reproducible backtests.

## Prerequisites

- Python 3.11 environment (Poetry managed)
- Raw CSV files placed under `price_data/raw/<symbol>/`

## Steps

1. Ensure raw data directory structure:
   - `price_data/raw/eurusd/` containing one or more CSV files
   - Additional symbols in analogous subdirectories
2. Run dataset build (CLI command to be implemented):
   - `poetry run python -m backtest.cli.build_dataset --all`
3. Inspect outputs:
   - `price_data/processed/<symbol>/test/` and `.../validate/` CSV partitions
   - `price_data/processed/<symbol>/metadata.json` per-symbol details
   - `price_data/processed/build_summary.json` consolidated summary
4. Execute backtest using processed data:
   - `poetry run python -m backtest.cli.run --symbol eurusd --mode split`
5. Review results separated by partition in `results/`.

## Validation Checklist

- Each processed symbol has two partitions (unless skipped for low rows)
- Validation partition row count ≈ 20% of total (remainder after floor)
- Metadata timestamps align with raw source
- No synthetic rows introduced (gaps/overlaps reported only)

## Troubleshooting

| Symptom                            | Possible Cause                       | Resolution                                              |
| ---------------------------------- | ------------------------------------ | ------------------------------------------------------- |
| Symbol missing in processed output | Schema mismatch or insufficient rows | Check summary JSON reason; adjust raw data or threshold |
| Validation metrics absent          | Backtest not run in split mode       | Re-run with `--mode split`                              |
| Excessive gaps reported            | Raw data cadence inconsistent        | Accept as-is; consider future enhancement (resampling)  |

## Next Steps

- Add rolling evaluation modes
- Consider Parquet for performance if large-scale datasets emerge
