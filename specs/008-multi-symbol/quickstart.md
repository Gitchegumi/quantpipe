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

## 4. Independent Multi-Symbol Mode (Phase 4: Implemented)

The CLI now supports independent multi-symbol execution. When multiple pairs are
specified, each symbol runs its own isolated backtest with separate capital,
risk limits, and execution context.

### Running Independent Multi-Symbol Backtest

```powershell
poetry run python -m src.cli.run_backtest \
--direction BOTH \
--pair EURUSD GBPUSD USDJPY
```

**What happens:**

- Each symbol is validated (missing datasets are skipped with warnings)
- Valid symbols run independent backtests in isolation
- Results are aggregated for summary reporting
- Failures in one symbol don't affect others

### Symbol Validation

Symbols without datasets are automatically skipped:

```powershell
poetry run python -m src.cli.run_backtest \
--direction LONG \
--pair EURUSD INVALID GBPUSD
```

Output:

```text
WARNING: Symbol validation found 1 error(s), skipping invalid symbols:
  - Dataset not found for INVALID at price_data/processed/invalid/...
INFO: Proceeding with 2 valid symbol(s): EURUSD, GBPUSD
```

### Text Output Format

```text
=============================================================
INDEPENDENT MULTI-SYMBOL BACKTEST RESULTS
=============================================================

RUN METADATA
-------------------------------------------------------------
Run ID:           multi_both_20251106_143022
Direction Mode:   BOTH
Symbols:          EURUSD, GBPUSD, USDJPY
Start Time:       2025-11-06T14:30:22+00:00

AGGREGATE SUMMARY
-------------------------------------------------------------
Total Symbols:    3
Total Trades:     142
Avg Win Rate:     54.23%
Total P&L:        $1,245.67

PER-SYMBOL BREAKDOWN
-------------------------------------------------------------

EURUSD:
  Trades:         48
  Win Rate:       52.08%
  Final Balance:  $10,412.34

GBPUSD:
  Trades:         51
  Win Rate:       56.86%
  Final Balance:  $10,521.12

USDJPY:
  Trades:         43
  Win Rate:       53.49%
  Final Balance:  $10,312.21

=============================================================
```

### JSON Output Format

```powershell
poetry run python -m src.cli.run_backtest \
--direction SHORT \
--pair EURUSD GBPUSD \
--output-format json
```

Output:

```json
{
  "run_id": "multi_short_20251106_143045",
  "direction_mode": "SHORT",
  "start_time": "2025-11-06T14:30:45+00:00",
  "symbols": ["EURUSD", "GBPUSD"],
  "mode": "independent",
  "summary": {
    "total_symbols": 2,
    "total_trades": 95,
    "average_win_rate": 0.5315,
    "total_pnl": 823.45
  },
  "per_symbol": {
    "EURUSD": {
      "symbol": "EURUSD",
      "total_trades": 48,
      "win_rate": 0.5208,
      "final_balance": 10412.34
    },
    "GBPUSD": {
      "symbol": "GBPUSD",
      "total_trades": 47,
      "win_rate": 0.5426,
      "final_balance": 10411.11
    }
  },
  "failures": {}
}
```

## 5. Portfolio Mode (Phase 5: Planned)

Future portfolio mode will:

- Ingest each pair's candles.
- Maintain `CorrelationWindowState` objects.
- Generate `AllocationRequest` per snapshot interval.
- Persist snapshots to JSONL.

Example (future behavior):

```powershell
poetry run python -m src.cli.run_backtest \
--direction BOTH \
--pair EURUSD GBPUSD USDJPY \
--portfolio-mode
```

## 6. Profiling & Benchmark Output

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
