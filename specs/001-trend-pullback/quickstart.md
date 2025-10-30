# Quickstart: Trend Pullback Continuation Strategy

Branch: `001-trend-pullback`
Artifacts: `spec.md`, `research.md`, `data-model.md`, `contracts/`, `plan.md`

## 1. Prerequisites

- Python 3.11
- Recommended: Virtual environment
- OS: Windows (PowerShell examples below)

## 2. Setup Environment (PowerShell)

```powershell
python -m venv .venv
./.venv/Scripts/Activate.ps1
pip install numpy pandas pydantic rich pytest hypothesis
```

(Add TA-Lib later if needed; initial version uses pure Python indicators.)

## 3. Core Concepts

- Trend classification: EMA20 vs EMA50 + cross density
- Pullback detection: Counter-trend move + RSI extreme inside ATR bounds
- Signal: Reversal confirmation; deterministic ID (SHA256 truncated 16 hex)
- Risk: ATR-based stop; fixed % of equity sized to micro-lots; validated bounds
- Execution (backtest): Simulated fills, slippage, exit precedence (target > trailing > stop > expiry)
- Metrics: Expectancy, win rate, avg R, drawdown curve, latency stats, reproducibility hash

## 4. Interfaces Overview

See `contracts/interfaces.py` for Protocol definitions.

```python
from specs001_trend_pullback.contracts.interfaces import (
    CandleIngestion, TrendClassifier, PullbackDetector,
    SignalGenerator, RiskManager, ExecutionSimulator,
    MetricsAggregator, ReproducibilityService, ObservabilityReporter
)
```

(Actual import path will be adjusted once code is organized into packages.)

## 5. Minimal Wiring Example (Pseudo-Code)

```python
params = {"risk_per_trade_pct": 0.005, "volatility_filter": True}
manifest = {"pair": "EURUSD", "timeframe": "1m"}

for candle in ingestion.stream(manifest["pair"], manifest["timeframe"]):
    trend = trend_classifier.update(candle)
    pullback = pullback_detector.update(candle, trend)
    signal = signal_generator.generate(candle, trend, pullback)
    if signal:
        sized = risk_manager.size(signal, account_equity=10_000)
        execution = execution_simulator.execute(sized, candle)
        metrics_agg.ingest(execution)

summary = metrics_agg.finalize()
run_hash = reproducibility.hash_run(params, manifest, summary)
observability.emit(summary, {"run_hash": run_hash})
```

## 6. Reproducibility

**Reproducibility Hash:**

The backtest engine generates a deterministic `reproducibility_hash` to ensure results are verifiable and reproducible. This hash combines:

- Strategy parameters (via parameters_hash from Pydantic model serialization)
- Data manifest reference (source file path, checksum, date range)
- Execution outcomes (all trade signals and executions in chronological order)

**Hash Computation:**

```python
from src.backtest.reproducibility import ReproducibilityTracker

tracker = ReproducibilityTracker()
tracker.track_manifest("/data/EURUSD_15m.csv", "sha256:abc123...")
tracker.track_parameters(params.model_dump())

# During backtest execution
for signal in signals:
    tracker.track_signal(signal)
for execution in executions:
    tracker.track_execution(execution)

# Finalize after backtest complete
repro_hash = tracker.finalize_hash()
print(f"Reproducibility hash: {repro_hash}")
```

**Verification:**

- Same parameters + same data + same code -> identical hash
- If hash differs, inspect:
  - Data source changes (file modified, checksum mismatch)
  - Parameter drift (config changed between runs)
  - Code version differences (algorithm modifications)
  - Non-deterministic behavior (random seeds, timestamp dependencies)

**Storage:**

The reproducibility hash is stored in:

- `BacktestRun.reproducibility_hash` field
- JSON output from CLI (when using --output-format json)
- Observability logs emitted at backtest completion

**Best Practices:**

1. Always commit `poetry.lock` to ensure dependency reproducibility
2. Store data manifest checksums in version control
3. Tag code releases with corresponding backtest hashes
4. Compare hashes when validating optimization results
5. Use hash as audit trail for regulatory compliance

## 7. Testing (Initial Targets)

```powershell
pytest -q
```

Planned early tests:

- Signal ID determinism (same inputs -> same ID)
- Risk sizing rounding edge (near micro-lot boundary)
- Gap detection for ingestion
- Zero-trade metrics (expectancy == 0, win_rate == 0) handling

## 8. Next Steps (Implementation Roadmap)

1. Implement ingestion stub (CSV loader or synthetic generator)
2. Add indicator calculations module
3. Implement trend classifier & pullback detector
4. Add signal generator with deterministic hashing
5. Implement risk manager & position sizing
6. Build execution simulator & basic slippage model
7. Wire metrics aggregator + reproducibility service
8. Add pytest suite for contracts
9. Integrate observability (structured logging via Rich or std logging JSON)

## 9. Performance Targets

| Metric | Target |
|--------|--------|
| Candle throughput | >= 50k/sec synthetic |
| Memory footprint | <= 150MB (1y 1m data) |
| Update latency p95 | < 5ms |
| Hash verification | 100% deterministic |

## 10. Troubleshooting

| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| Duplicate signal IDs | Non-deterministic field used | Restrict hash inputs to spec-defined set |
| Excess memory usage | Data retention beyond window | Implement pruning / streaming stats |
| Latency spikes | Excessive indicator recalculation | Cache EMA/ATR computations |
| Hash mismatch | Parameter drift / manifest change | Recompute parameters hash; check checksum |

## 11. Deferred Items

- Portfolio-level risk aggregation
- Adaptive volatility regime sizing
- Stoch RSI integration post baseline viability

---
Generated: 2025-10-25
