# Quickstart: Scan & Simulation Performance Optimization (Spec 010)

## 1. Baseline Setup

1. Ensure Python 3.11 + Poetry environment installed.
2. Install dependencies:

   ```bash
   poetry install
   ```

3. Identify dataset manifest (e.g., `price_data/processed/eurusd/manifest.json`). Record SHA256 checksum.
4. (Optional) Install Polars for pilot ingestion:

```bash
poetry add polars --group dev
```

Adoption gated by ≥20% preprocessing speedup & ≥15% memory reduction; keep pandas path as default.

1. Run existing backtest once to capture baseline timings & output signals/trades.

## 2. Capture Baseline Metrics

Use timing wrapper (to be added) or manual measurement:

```bash
poetry run python -m src.cli.run_backtest --data <path-to-csv> --direction BOTH
```

Store:

- Scan duration (sec)
- Simulation duration (sec)
- Signal count
- Trade count
- Peak memory estimate (optional initial)

## 3. Run Optimized Scan

After implementing batch modules:

````bash
poetry run python -m src.cli.run_backtest --data <path-to-csv> --direction BOTH --benchmark --report ./results/performance_report.json
```text
Optional Polars path (only after pilot benchmark acceptance):
```bash
poetry run python -m src.cli.run_backtest --data <path-to-csv> --direction BOTH --benchmark --use-polars --report ./results/performance_report.json
````

Expected:

- Reduced scan time (≤12 min target on 6.9M candles)
- Progress updates every ≤2% or ≤120s

## 4. Run Optimized Simulation

Same invocation produces simulation metrics. Confirm:

- Simulation duration ≤8 min target
- Trade results equivalent (PnL variance ≤0.5%)

## 5. Review Performance Report

Inspect generated JSON:

```json
{
  "scan_duration_sec": 721.4,
  "simulation_duration_sec": 467.2,
  "peak_memory_mb": 1530.2,
  "manifest_path": "price_data/processed/eurusd/manifest.json",
  "manifest_sha256": "<sha256>",
  "candle_count": 6900000,
  "signal_count": 12345,
  "trade_count": 84938,
  "equivalence_verified": true,
  "progress_emission_count": 420
}
```

## 6. Deterministic Re-run

Execute the same command 3× and verify durations within ±1% and identical counts.

## 7. Indicator Ownership Audit

Run contract test suite:

```bash
poetry run pytest tests/contract/test_indicator_ownership.py -q
```

Expect all indicators used present in strategy declarations and no extras.

## 8. Memory Profiling (Optional)

Enable memory sampling flag (to be added) for deeper analysis:

```bash
poetry run python -m src.cli.run_backtest --data <path-to-csv> --direction BOTH --benchmark --memory-profile
```

## 9. Optional numba Experiment

After baseline optimization passes targets, enable prototype:

```bash
poetry run python -m src.cli.run_backtest --data <path-to-csv> --direction BOTH --experimental-numba
```

Adopt only if ≥25% further simulation improvement.

## 10. Polars Pilot Verification

Run both paths (pandas vs Polars) and capture preprocessing metrics:

```bash
poetry run python -m src.cli.run_backtest --data <path-to-csv> --direction BOTH --benchmark --report ./results/pandas_report.json
poetry run python -m src.cli.run_backtest --data <path-to-csv> --direction BOTH --benchmark --use-polars --report ./results/polars_report.json
```

Compare `scan_duration_sec` and `peak_memory_mb` fields:

- Speed improvement ≥20%
- Memory reduction ≥15%
  If criteria met, proceed with Polars flag for future runs; otherwise remain on pandas path.

## 11. Troubleshooting

| Symptom             | Cause                              | Action                                             |
| ------------------- | ---------------------------------- | -------------------------------------------------- |
| No progress updates | Progress dispatcher not integrated | Check FR-011 implementation                        |
| Signal mismatch     | Dedupe or batch logic error        | Compare baseline signals; run unit tests           |
| Memory spike        | Copies of arrays retained          | Use profiling to find duplicates; convert to views |
| Slow simulation     | Vectorization incomplete           | Inspect batch_simulation hotspots                  |

## 12. Next Steps

- Integrate multi-symbol batching (future spec)
- Introduce Parquet ingestion for faster IO
- Evaluate numba adoption conditions
