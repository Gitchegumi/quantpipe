# Quickstart: Multi-Symbol Backtesting (Phase 1)

Date: 2025-11-06  
Branch: 008-multi-symbol  
Spec: FR-001..FR-023, SC-001..SC-014  
Related: `data-model.md`, `contracts/portfolio-allocation.yaml`

## Purpose

This guide shows how to run the existing single-pair CLI and outlines the upcoming
multi-symbol portfolio workflow. Phase 1 focuses on design artifacts; execution
still uses the first provided pair only (loop not yet implemented).

## 1. Environment Setup (Windows PowerShell)

```powershell
poetry install
```

## 2. Basic Backtest (Single Pair)

```powershell
poetry run python -m src.cli.run_backtest --direction LONG --data price_data/raw/eurusd/eurusd_20250101.csv
```

## 3. Explicit Pair & JSON Output

```powershell
poetry run python -m src.cli.run_backtest \
--direction SHORT \
--data price_data/raw/usdjpy/usdjpy_20250101.csv \
--pair USDJPY \
--output-format json
```

## 4. Multiple Pairs (Design Preview)

Current CLI accepts multiple values via `--pair` but processes only the first. Future
portfolio mode will:

- Ingest each pair's candles.
- Maintain `CorrelationWindowState` objects.
- Generate `AllocationRequest` per snapshot interval.
- Persist snapshots to JSONL.

Example (future behavior):

```powershell
poetry run python -m src.cli.run_backtest \
--direction BOTH \
--data price_data/raw/eurusd/eurusd_20250101.csv \
--pair EURUSD GBPUSD USDJPY
```

(Expected Phase 2: independent or portfolio aggregation selection flag.)

## 5. Profiling & Benchmark Output

```powershell
poetry run python -m src.cli.run_backtest --direction LONG --data price_data/raw/eurusd/eurusd_20250101.csv --profile
```

Generates benchmark JSON under `results/benchmarks/` with phase timings and (if enabled) memory metrics.

## 6. Output Artifacts

| Artifact                 | Location                                        | Description                       |
| ------------------------ | ----------------------------------------------- | --------------------------------- | ----- | ----------------------------------- |
| Result text/json         | `results/backtest*<mode>*<symbol                | multi>\_<timestamp>.txt           | json` | Per-run metrics & metadata (FR-023) |
| Benchmark JSON           | `results/benchmarks/benchmark_<timestamp>.json` | Profiling & performance metrics   |
| Snapshots JSONL (future) | `results/snapshots/<run_id>.jsonl`              | Periodic portfolio state (FR-022) |

## 7. Filename Convention (FR-023)

Pattern:

```text
backtest_<direction>_<symbol|multi>_<YYYYMMDD>_<HHMMSS>.<ext>
```

Examples:

- `backtest_long_eurusd_20251106_123045.txt`
- `backtest_both_multi_20251106_123045.json` (future multi-symbol)

## 8. Planned New Flags (Design Only)

(Not yet wired into CLI — reserved for Phase 2/3 implementation.)

| Flag                              | Purpose                                                  |
| --------------------------------- | -------------------------------------------------------- |
| `--portfolio-mode`                | Switch between `independent` and `portfolio` aggregation |
| `--snapshot-interval <int>`       | Override default 50-candle snapshot interval             |
| `--correlation-threshold <float>` | Global correlation cutoff (default 0.8)                  |
| `--allocation-log`                | Emit allocation decisions at INFO level                  |
| `--disable-symbol <code>`         | Exclude specific symbol at runtime (isolation test)      |

## 9. Troubleshooting

| Issue                 | Cause                             | Resolution                                                      |
| --------------------- | --------------------------------- | --------------------------------------------------------------- |
| Data file error       | Path missing or format wrong      | Verify CSV header or run conversion automatically (done by CLI) |
| Win rate shows `None` | Division by zero due to no trades | Use BOTH direction or larger dataset                            |
| Memory spike          | Large candle ingestion            | Profile with `--profile` and compare against baseline formula   |

## 10. Next Steps

1. Implement multi-pair loop & ingestion bundle.
2. Wire correlation & allocation engine (`AllocationRequest`/`AllocationResponse`).
3. Add snapshot emission with JSONL writer.
4. Introduce `--portfolio-mode` flag and allocation logging.

## 11. References

- `data-model.md`: Entity definitions.
- `contracts/portfolio-allocation.yaml`: Request/response schema.
- `research.md`: Decision log (numba optional, memory formula, correlation config).
