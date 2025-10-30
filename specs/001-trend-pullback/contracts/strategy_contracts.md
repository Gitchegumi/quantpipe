# Strategy Contracts: Trend Pullback Continuation

Version: 0.1.0
Feature Branch: 001-trend-pullback
Source Artifacts: `spec.md`, `research.md`, `data-model.md`

## Purpose

Formalize stable interfaces between components before implementation. These contracts enable:

- Deterministic reproducibility (hashable inputs/outputs)
- Clear separation of concerns (ingestion, classification, detection, signal, risk, execution, metrics)
- Test harness generation (each contract can be mocked)
- Future multi-strategy orchestration

## Component Boundaries

1. Ingestion Service
2. Trend Classifier
3. Pullback Detector
4. Signal Generator
5. Risk Manager
6. Execution Simulator (backtest phase)
7. Metrics Aggregator
8. Reproducibility Service
9. Observability Reporter

## High-Level Flow

```python
for candle in ingestion.stream(pair, timeframe):
    trend_state = trend_classifier.update(candle)
    pullback_state = pullback_detector.update(candle, trend_state)
    signal = signal_generator.generate(candle, trend_state, pullback_state)
    if signal:
        sized_signal = risk_manager.size(signal, account_equity)
        execution = execution_simulator.execute(sized_signal, candle)
        metrics_aggregator.ingest(execution)
metrics = metrics_aggregator.finalize()
repro_hash = reproducibility.hash_run(parameters, manifest, metrics)
observability_reporter.emit(metrics, latency_stats, repro_hash)
```

## Contract Details

### 1. Ingestion Service

- Input: `pair: str`, `timeframe: str`
- Output: `Iterator[Candle]`
- Guarantees: Monotonic timestamps; computed fields (EMA20, EMA50, ATR14, RSI14) available or lazily filled.
- Errors: Raises `DataIntegrityError` if gap > GAP_THRESHOLD.

### 2. Trend Classifier

- Input: `Candle`
- Output: `TrendState`
- Logic: EMA20 vs EMA50 plus cross density; returns RANGE if choppy.
- Performance: O(1) per update.

### 3. Pullback Detector

- Input: `Candle`, `TrendState`
- Output: Optional[`PullbackState`]
- Activation Criteria: Counter-trend move within max ATR multiple & oscillator extreme flagged.
- Expiration: Age > PULLBACK_MAX_AGE or trend invalidated.

### 4. Signal Generator

- Input: `Candle`, `TrendState`, Optional[`PullbackState`]
- Output: Optional[`TradeSignal`]
- Deterministic ID: `id = sha256(timestamp|pair|direction|entry_price|strategy_version)[:16]`
- Conditions: Reversal confirmation; liquidity check; volatility regime filter.

### 5. Risk Manager

- Input: `TradeSignal`, `account_equity: float`
- Output: `TradeSignal` (augmented with `calc_position_size`, `risk_per_trade_pct`, `initial_stop_price` confirmed)
- Constraints: Position size > 0; risk % within configured band (e.g., 0.25%–0.75%).

### 6. Execution Simulator

- Input: Sized `TradeSignal`, fill context (slippage model, spread)
- Output: `TradeExecution`
- Exit Conditions: Target, trailing stop, hard stop, time expiry.
- Latency Simulation: p95 < 5ms target (SC-010).

### 7. Metrics Aggregator

- Input: Stream of `TradeExecution`
- Output: `MetricsSummary` (expectancy, win_rate, avg_R, sharpe_estimate, drawdown_curve, latency_stats)
- Finalization: `finalize()` produces immutable summary dataclass.

### 8. Reproducibility Service

- Input: Parameters JSON, DataManifest, MetricsSummary
- Output: `reproducibility_hash: str`
- Algorithm: sha256(parameters_hash + manifest.checksum + strategy_version + metrics_digest)
- Validation: `verify(hash, inputs) -> bool`.

### 9. Observability Reporter

- Input: MetricsSummary, latency stats, reproducibility hash
- Output: Side-effect (log/event emission)
- Channels: Structured log (JSON), optional metrics sink.

## Python Protocol Sketch (See `interfaces.py`)

Defines `Protocol` types for each component to allow dependency injection and testing.

## Error Types (to define later)

- `DataIntegrityError`
- `ValidationError`
- `RiskLimitError`
- `ExecutionSimulationError`

## Non-Functional Guarantees

| Aspect | Guarantee | Source |
|--------|-----------|--------|
| Determinism | Same input stream -> identical signal IDs | FR-025, Clarification Q1 |
| Latency | p95 update < 5ms | SC-010 |
| Memory | <= 150MB for 1y 1m data | SC-007 |
| Throughput | >= 50k candles/sec synthetic | SC-009 |
| Hash Integrity | Run hash reproducible | SC-012 |

## Test Harness Plan

| Component | Primary Test | Edge Case |
|-----------|--------------|-----------|
| Ingestion | Gap detection | Duplicate timestamp |
| Trend Classifier | Trend flip correctness | Choppy EMA whipsaw |
| Pullback Detector | Activation counts | Expiration timing |
| Signal Generator | ID determinism | Volatility filter blocks trade |
| Risk Manager | Size calc rounding | Risk % upper bound breach |
| Execution Simulator | Stop/target precedence | Simultaneous exit signals |
| Metrics Aggregator | Expectancy math | Zero trades scenario |
| Reproducibility | Hash stability | Manifest change diff |
| Observability | Log schema | Missing metrics field |

## Open Items (Deferred)

- Multi-pair portfolio risk aggregation (later phase).
- Advanced volatility regime adaptive sizing.
- Stoch RSI integration post baseline.

## Change Control

Contract modifications require spec update + version bump to strategy `version` string; breaking changes trigger minor version increment.

---
Generated on: 2025-10-25
