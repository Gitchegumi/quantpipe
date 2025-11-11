# Quickstart: Scan & Simulation Performance Optimization (Spec 010)

## 1. Baseline Setup

1. Ensure Python 3.11 + Poetry environment installed.
2. Install dependencies (includes Polars 1.17.0):

   ```bash
   poetry install
   ```

3. **Polars is now mandatory** for ingestion and preprocessing. It provides:
   - ≥20% preprocessing speedup via columnar operations
   - ≥15% memory reduction through efficient data structures
   - LazyFrame evaluation for deferred computation
4. Identify dataset manifest (e.g., `price_data/processed/eurusd/manifest.json`). Record SHA256 checksum.
5. Run existing backtest once to capture baseline timings & output signals/trades.

## 2. Capture Baseline Metrics

Use the CLI with BOTH direction mode:

```bash
poetry run python -m src.cli.run_backtest --data <path-to-csv> --direction BOTH
```

Store:

- Scan duration (target: ≤720 sec for 6.9M candles)
- Simulation duration (target: ≤480 sec for ~85k trades)
- Signal count
- Trade count
- Peak memory (target: ≤2GB)

## 3. Run Optimized Scan & Simulation

After implementing batch modules (Phase 3-5 complete):

```bash
poetry run python -m src.cli.run_backtest --data <path-to-csv> --direction BOTH
```

Expected outcomes:

- Scan duration ≤720 sec (≥50% speedup target)
- Simulation duration ≤480 sec (≥55% speedup target)
- Progress updates every 16,384 items or 120 sec intervals
- Trade results equivalent (PnL variance ≤0.5%)
- Progress tracking overhead ≤1%

Performance reports are automatically generated (future: once orchestrator integration complete).

## 4. Parquet Ingestion Workflow

**Recommended for production**: Use Parquet format for faster IO and better compression.

Convert CSV to Parquet (one-time):

```python
import polars as pl

# Read CSV with Polars
df = pl.read_csv("price_data/raw/eurusd/eurusd_2020.csv")

# Write as Parquet with zstd compression
df.write_parquet(
    "price_data/processed/eurusd/eurusd_2020.parquet",
    compression="zstd"
)
```

Ingest Parquet with LazyFrame:

```python
from src.io.ingestion.arrow import ingest_ohlcv_data

# LazyFrame provides deferred evaluation
lf = ingest_ohlcv_data("price_data/processed/eurusd/eurusd_2020.parquet")

# Collect when needed
df = lf.collect()
```

Benefits:

- **Faster IO**: Parquet read ~3-5× faster than CSV
- **Smaller files**: zstd compression ~40-60% reduction
- **Columnar format**: Direct mapping to Polars DataFrame
- **Schema enforcement**: Type validation at read time

## 5. Review Performance Report

Performance reports will be generated automatically once orchestrator integration is complete (T045).

Expected JSON structure:

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
  "progress_emission_count": 420,
  "progress_overhead_pct": 0.8,
  "schema_version": "1.0.0"
}
```

## 6. Deterministic Re-run

Execute the same command 3× and verify:

- Durations within ±1% variance
- Identical signal/trade counts
- PnL within ±0.5% variance

```bash
poetry run pytest tests/integration/test_deterministic_runs.py -v
```

## 7. Indicator Ownership Audit

Run contract test suite to verify strategy indicator declarations:

```bash
poetry run pytest tests/contract/test_indicator_ownership.py -q
```

Expect all indicators used present in strategy declarations and no extras.

## 8. Performance Benchmarks

Run comprehensive performance test suite:

```bash
# Scan performance tests (≤720 sec target)
poetry run pytest tests/performance/test_scan_perf.py -v

# Simulation performance tests (≤480 sec target)
poetry run pytest tests/performance/test_sim_perf.py -v

# Memory efficiency tests
poetry run pytest tests/performance/test_sim_memory.py -v

# Progress overhead tests (≤1% overhead)
poetry run pytest tests/performance/test_progress_overhead.py -v
```

## 9. Optional Experiments

### numba JIT Compilation (Deferred)

numba adoption is deferred until baseline vectorization is measured. To experiment:

1. Install numba: `poetry add numba --group dev`
2. Create prototype script: `scripts/experiment_numba_sim.py`
3. Measure speedup vs vectorized NumPy baseline
4. Adopt only if ≥25% further simulation improvement

### Polars Streaming Mode (Experimental)

For datasets that don't fit in memory, experiment with streaming evaluation:

```python
from src.backtest.streaming_scan import StreamingScan

# Experimental: Process LazyFrame in chunks
scanner = StreamingScan(chunk_size=100_000)
results = scanner.scan_streaming(lf)
```

Mark as experimental; production adoption requires validation.

## 10. Troubleshooting

| Symptom                  | Cause                                    | Action                                                        |
| ------------------------ | ---------------------------------------- | ------------------------------------------------------------- |
| No progress updates      | Progress dispatcher not integrated       | Verify ProgressDispatcher passed to BatchScan/BatchSimulation |
| Signal mismatch          | Dedupe or batch logic error              | Compare baseline signals; run equivalence tests               |
| Memory spike             | Copies of arrays retained                | Use memory profiling to find duplicates; convert to views     |
| Slow simulation          | Vectorization incomplete                 | Run hotspot profiling on batch_simulation                     |
| Polars import error      | Poetry dependency not installed          | Run `poetry install` to ensure Polars 1.17.0+ installed      |
| LazyFrame evaluation OOM | Dataset too large for memory             | Use streaming mode (experimental) or reduce batch size        |

## 11. Performance Targets Summary

| Metric                    | Baseline | Target    | Achieved  |
| ------------------------- | -------- | --------- | --------- |
| Scan duration (6.9M)      | ~1440s   | ≤720s     | Phase 3   |
| Simulation duration (85k) | ~1067s   | ≤480s     | Phase 5   |
| Memory peak               | ~2.2GB   | ≤2GB      | Phase 5   |
| Progress overhead         | N/A      | ≤1%       | Phase 6   |
| PnL equivalence           | N/A      | ±0.5%     | Phase 5   |
| Timing determinism        | N/A      | ±1%       | Phase 5   |

## 12. Next Steps

- **Orchestrator refactoring**: Expose ScanResult/SimulationResult for full report integration (T045)
- **Multi-symbol batching**: Extend batch processing to multiple symbols (future spec)
- **Parquet migration**: Convert all datasets to Parquet format for optimal IO
- **Streaming evaluation**: Prototype Polars streaming for large-scale datasets
- **numba evaluation**: Measure JIT compilation impact on hot simulation loops
