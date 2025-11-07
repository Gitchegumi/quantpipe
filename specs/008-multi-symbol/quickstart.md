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

## 5. Portfolio Mode (Phase 5: Components Ready, CLI Integration Pending)

Portfolio mode enables coordinated multi-symbol execution with shared capital,
correlation tracking, and portfolio-level metrics. The core components are
implemented and tested:

### Portfolio Mode Features

**Shared Capital Pool:**

- Capital allocated dynamically across symbols based on volatility and correlation
- Allocation sum enforced to 100% with <0.01% precision (largest remainder rounding)
- Failed symbols excluded from allocation (isolation per Decision 5)

**Correlation Tracking:**

- Rolling 100-period window with provisional 20-period minimum (FR-010)
- Pair-wise correlation matrix updated each candle
- Customizable thresholds per symbol pair (default 0.8)
- Failed symbols frozen in matrix (no further updates)

**Diversification Metrics:**

- Diversification ratio: portfolio_vol / avg_symbol_vol
- Effective number of assets (independence measure)
- Portfolio variance reduction estimation

**Periodic Snapshots:**

- JSONL format (Decision 7)
- Configurable interval (default 50 candles)
- Includes: timestamp, positions, unrealized PnL, correlation matrix, diversification ratio

### Portfolio Configuration Example

```python
from src.models.portfolio import PortfolioConfig, CurrencyPair
from src.backtest.portfolio.orchestrator import PortfolioOrchestrator

symbols = [
    CurrencyPair(code="EURUSD"),
    CurrencyPair(code="GBPUSD"),
    CurrencyPair(code="USDJPY"),
]

config = PortfolioConfig(
    correlation_threshold_default=0.8,
    snapshot_interval_candles=50,
    allocation_rounding_dp=2,
)

orchestrator = PortfolioOrchestrator(
    symbols=symbols,
    portfolio_config=config,
    initial_capital=10000.0,
)
```

### Allocation Strategies

**Equal Weight:**

- Each symbol receives equal capital allocation
- Simplest approach, no volatility adjustment

**Volatility-Based:**

- Higher volatility symbols receive smaller allocations
- Balances risk contribution across symbols

**Custom Weights:**

- Explicit per-symbol weights via SymbolConfig
- Allows manual portfolio construction

### Correlation Threshold Overrides

Set different correlation thresholds for specific symbol pairs:

```python
from src.backtest.portfolio.correlation_service import CorrelationService

service = CorrelationService(correlation_threshold=0.8)

# Override for specific pair
service.set_threshold_override(
    pair_a=CurrencyPair(code="EURUSD"),
    pair_b=CurrencyPair(code="GBPUSD"),
    threshold=0.7  # More strict for this pair
)
```

### Failure Isolation

Per Decision 5, failed symbols are automatically isolated:

```python
# Mark symbol as failed (e.g., data loading error)
orchestrator.mark_symbol_failed(
    symbol=CurrencyPair(code="GBPUSD"),
    error="Dataset file not found"
)

# Failed symbol is:
# - Removed from active symbols set
# - Excluded from correlation updates (matrix frozen)
# - Excluded from capital allocation
# - Recorded in failures dictionary
```

### Manifest Generation

Portfolio manifests document execution configuration per FR-019:

```python
from src.io.manifest import create_portfolio_manifest
from pathlib import Path

manifest = create_portfolio_manifest(
    symbols=["EURUSD", "GBPUSD", "USDJPY"],
    execution_mode="portfolio",
    dataset_paths={
        "EURUSD": "price_data/processed/eurusd/processed.csv",
        "GBPUSD": "price_data/processed/gbpusd/processed.csv",
        "USDJPY": "price_data/processed/usdjpy/processed.csv",
    },
    correlation_threshold=0.8,
    snapshot_interval=50,
    allocation_strategy="equal_weight",
    initial_capital=10000.0,
    output_path=Path("results/manifest_portfolio_20251106.json"),
)
```

**Manifest contents:**

- Symbols executed
- Execution mode
- Dataset paths
- Correlation settings
- Allocation strategy
- Initial capital

### Future CLI Integration

Planned command-line interface (not yet wired):

```powershell
poetry run python -m src.cli.run_backtest \
--direction BOTH \
--pair EURUSD GBPUSD USDJPY \
--portfolio-mode portfolio \
--correlation-threshold 0.8 \
--snapshot-interval 50 \
--allocation-strategy equal_weight
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

## 8. CLI Flags & Filtering (Phase 6: Implemented)

The CLI now supports runtime filtering and configuration via command-line flags.

### Portfolio Mode Selection

Switch between independent and portfolio execution modes:

```powershell
# Independent mode (default): each symbol isolated
poetry run python -m src.cli.run_backtest \
--direction BOTH \
--pair EURUSD GBPUSD USDJPY \
--portfolio-mode independent

# Portfolio mode: shared capital, correlation tracking
poetry run python -m src.cli.run_backtest \
--direction BOTH \
--pair EURUSD GBPUSD USDJPY \
--portfolio-mode portfolio
```

**Independent mode:**

- Each symbol has separate capital ($10,000 default)
- Risk limits applied per symbol
- No correlation tracking
- Failures don't affect other symbols

**Portfolio mode:**

- Shared capital pool ($10,000 total)
- Dynamic allocation based on volatility/correlation
- Correlation matrix updated each candle
- Failed symbols excluded from allocation

### Symbol Filtering

Exclude specific symbols at runtime without modifying configuration:

```powershell
# Run all specified symbols
poetry run python -m src.cli.run_backtest \
--direction LONG \
--pair EURUSD GBPUSD USDJPY

# Exclude GBPUSD (useful for A/B testing or isolating failures)
poetry run python -m src.cli.run_backtest \
--direction LONG \
--pair EURUSD GBPUSD USDJPY \
--disable-symbol GBPUSD
```

Result: Only EURUSD and USDJPY execute. GBPUSD is filtered before validation.

**Multiple exclusions:**

```powershell
poetry run python -m src.cli.run_backtest \
--direction SHORT \
--pair EURUSD GBPUSD USDJPY NZDUSD \
--disable-symbol GBPUSD NZDUSD
```

### Correlation Threshold Override

Customize correlation threshold for portfolio mode:

```powershell
# Default threshold: 0.8
poetry run python -m src.cli.run_backtest \
--direction BOTH \
--pair EURUSD GBPUSD USDJPY \
--portfolio-mode portfolio

# Stricter threshold: 0.7 (trigger warnings earlier)
poetry run python -m src.cli.run_backtest \
--direction BOTH \
--pair EURUSD GBPUSD USDJPY \
--portfolio-mode portfolio \
--correlation-threshold 0.7

# Relaxed threshold: 0.9 (allow higher correlation)
poetry run python -m src.cli.run_backtest \
--direction BOTH \
--pair EURUSD GBPUSD USDJPY \
--portfolio-mode portfolio \
--correlation-threshold 0.9
```

**Validation:**

- Must be between 0.0 and 1.0
- Values outside range trigger error and abort
- Threshold applies to all symbol pairs globally

**Warning behavior:**

When correlation exceeds threshold:

```text
WARNING: Correlation between EURUSD and GBPUSD (0.85) exceeds threshold (0.70)
```

### Snapshot Interval Override

Control portfolio snapshot frequency:

```powershell
# Default interval: 50 candles
poetry run python -m src.cli.run_backtest \
--direction BOTH \
--pair EURUSD GBPUSD USDJPY \
--portfolio-mode portfolio

# More frequent snapshots: every 20 candles
poetry run python -m src.cli.run_backtest \
--direction BOTH \
--pair EURUSD GBPUSD USDJPY \
--portfolio-mode portfolio \
--snapshot-interval 20

# Less frequent snapshots: every 100 candles
poetry run python -m src.cli.run_backtest \
--direction BOTH \
--pair EURUSD GBPUSD USDJPY \
--portfolio-mode portfolio \
--snapshot-interval 100
```

**Validation:**

- Must be positive integer
- Zero or negative values trigger error
- Snapshot file grows proportionally with frequency

**Output location:**

```text
results/snapshots/<run_id>.jsonl
```

**Snapshot contents:**

```json
{
  "timestamp": "2025-11-06T14:30:00Z",
  "candle_index": 50,
  "positions": {
    "EURUSD": {"size": 100000, "unrealized_pnl": 123.45},
    "GBPUSD": {"size": 50000, "unrealized_pnl": -45.67}
  },
  "correlation_matrix": {
    "EURUSD_GBPUSD": 0.75,
    "EURUSD_USDJPY": 0.12,
    "GBPUSD_USDJPY": 0.08
  },
  "diversification_ratio": 1.42
}
```

### Combined Filtering Example

All flags work together:

```powershell
poetry run python -m src.cli.run_backtest \
--direction BOTH \
--pair EURUSD GBPUSD USDJPY NZDUSD \
--portfolio-mode portfolio \
--disable-symbol NZDUSD \
--correlation-threshold 0.75 \
--snapshot-interval 30
```

**Result:**

- Portfolio mode with shared capital
- Only EURUSD, GBPUSD, USDJPY execute (NZDUSD excluded)
- Correlation warnings at 0.75 threshold
- Snapshots every 30 candles

### Flag Summary

| Flag                              | Type   | Default      | Purpose                                          |
| --------------------------------- | ------ | ------------ | ------------------------------------------------ |
| `--portfolio-mode`                | str    | independent  | Execution mode: `independent` or `portfolio`     |
| `--disable-symbol`                | str(s) | (none)       | Exclude symbols from execution                   |
| `--correlation-threshold`         | float  | 0.8          | Portfolio correlation warning threshold (0.0-1.0)|
| `--snapshot-interval`             | int    | 50           | Portfolio snapshot frequency (candles)           |

## 9. Planned New Flags (Design Only)

(Not yet wired into CLI — reserved for future implementation.)

| Flag                              | Purpose                                                  |
| --------------------------------- | -------------------------------------------------------- |
| `--allocation-log`                | Emit allocation decisions at INFO level                  |

## 10. Troubleshooting

| Issue                       | Cause                             | Resolution                                                      |
| --------------------------- | --------------------------------- | --------------------------------------------------------------- |
| Data file error             | Path missing or format wrong      | Verify CSV header or run conversion automatically (done by CLI) |
| Win rate shows `None`       | Division by zero due to no trades | Use BOTH direction or larger dataset                            |
| Memory spike                | Large candle ingestion            | Profile with `--profile` and compare against baseline formula   |
| Symbol validation failure   | Missing dataset files             | Check `price_data/processed/{symbol}/processed.csv` exists      |
| Correlation threshold error | Value outside 0.0-1.0 range       | Use valid threshold between 0.0 and 1.0                         |
| Snapshot interval error     | Zero or negative value            | Use positive integer (e.g., 20, 50, 100)                        |

## 11. Next Steps

1. ✅ Implement multi-pair loop & ingestion bundle.
2. ✅ Wire correlation & allocation engine (`AllocationRequest`/`AllocationResponse`).
3. ✅ Add snapshot emission with JSONL writer.
4. ✅ Introduce `--portfolio-mode` flag and CLI filtering options.
5. Future: Add `--allocation-log` for debug-level allocation decisions.

## 12. References

- `data-model.md`: Entity definitions.
- `contracts/portfolio-allocation.yaml`: Request/response schema.
- `research.md`: Decision log (numba optional, memory formula, correlation config).
