# Quickstart: Performance Optimization Features

**Branch**: 007-performance-optimization  
**Spec**: ./spec.md  

## 1. Install / Environment

Ensure existing dependencies installed:

```powershell
poetry install
```

(Optional) Install acceleration dependencies if approved:

```powershell
poetry add numba pyarrow
```

(If dependencies deferred, skip.)

## 2. Basic Full Backtest

```powershell
poetry run python -m src.cli.run_backtest --data price_data/processed/eurusd/test/eurusd_test.csv --direction BOTH
```

Outputs standard results; no profiling, full dataset.

## 3. Fractional Dataset Run

Process 25% of leading rows for faster iteration:

```powershell
poetry run python -m src.cli.run_backtest \
  --data price_data/processed/eurusd/test/eurusd_test.csv \
  --direction BOTH \
  --data-frac 0.25
```

Verify slice in benchmark JSON (`fraction` field).

## 4. Profiling & Benchmark Artifact

```powershell
poetry run python -m src.cli.run_backtest \
  --data price_data/processed/eurusd/test/eurusd_test.csv \
  --direction BOTH \
  --profile \
  --benchmark-out results/benchmarks
```

Artifacts:

- `benchmark_<timestamp>.json`
- Optional `profiling_<timestamp>.json` (or `.txt`) hotspot breakdown

## 5. Deterministic Mode

```powershell
poetry run python -m src.cli.run_backtest --data price_data/processed/eurusd/test/eurusd_test.csv --direction BOTH --deterministic
```

Run twice; aggregate metrics should match within tolerance.

## 6. Parallel Parameter Execution

```powershell
poetry run python -m src.cli.run_backtest \
  --data price_data/processed/eurusd/test/eurusd_test.csv \
  --direction BOTH \
  --max-workers 4
```

Efficiency reported in benchmark JSON (`parallel_efficiency`). Adjust workers ≤ logical cores.

## 7. Optional Parquet Ingestion (Deferred Phase)

```powershell
poetry run python -m src.cli.run_backtest --data price_data/processed/eurusd/test/eurusd_test.parquet --direction BOTH --use-parquet
```

If `pyarrow` missing, fallback logged.

## 8. Interpreting Benchmark JSON

Essential fields:

- `total_time_s`: End-to-end seconds
- `simulation_s`: Trade simulation phase
- `speedup_vs_baseline`: Ratio vs stored baseline
- `memory_peak_mb`: Peak memory
- `fidelity_pass`: True if tolerance satisfied

## 9. Performance Test Execution

Run performance tests (after implementation):

```powershell
poetry run pytest tests/performance -k trade_sim_speed -q
```

## 10. Troubleshooting

| Symptom | Resolution |
|---------|------------|
| Slow simulation persists | Confirm batch path invoked; check numba availability |
| Memory over threshold | Reduce data fraction; ensure shared memory path used |
| Fidelity failure | Re-run deterministic; compare floating tolerance settings |
| Parquet ignored | Install pyarrow; verify file extension |

## 11. Next Steps

After verifying benchmarks meet success criteria, proceed to integration tests, then task generation phase.
