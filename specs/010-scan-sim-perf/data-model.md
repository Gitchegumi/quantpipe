# Data Model: Scan & Simulation Performance Optimization (Spec 010)

**Date**: 2025-11-11  
**Scope**: Entities and validation rules required for optimized scan & simulation phases.

## Candle

| Field         | Type                         | Constraints                     | Notes                                      |
| ------------- | ---------------------------- | ------------------------------- | ------------------------------------------ |
| timestamp_utc | datetime                     | Strictly increasing post-dedupe | Source ordering preserved                  |
| open          | float64                      | >=0                             | Raw market data                            |
| high          | float64                      | >= open                         | Standard OHLC assumption                   |
| low           | float64                      | <= open                         | Standard OHLC assumption                   |
| close         | float64                      | >=0                             | Raw market data                            |
| indicators    | dict[str, float64 or NaN]    | Keys from strategy; NaN allowed in warm-up | No external mutation |

Warm-up Region: Indicators may be NaN for initial N candles required by their lookback window; signals must not trigger where required indicators contain NaN.

## IndicatorSet

| Field       | Type      | Constraints         | Notes                          |
| ----------- | --------- | ------------------- | ------------------------------ |
| strategy_id | str       | Non-empty           | Identity for ownership audit   |
| names       | list[str] | Unique; length <=64 | Declared by strategy only      |
| version     | str       | SemVer pattern      | Optional, aids reproducibility |

## TradeSignal

| Field           | Type              | Constraints                 | Notes                       |
| --------------- | ----------------- | --------------------------- | --------------------------- |
| id              | str               | UUID or incremental         | Unique per run              |
| timestamp_utc   | datetime          | Must match Candle timestamp | Entry reference             |
| direction       | enum(long, short) | Required                    | Defines simulation path     |
| stop_loss_pct   | float64           | 0 < value <= 1              | Fractional risk threshold   |
| take_profit_pct | float64           | 0 < value <= 1              | Fractional reward threshold |
| strategy_id     | str               | Non-empty                   | Traceability & ownership    |

Derived Fields (not stored in base signal object; computed during simulation): entry_index, exit_index.

## SimulationResult

| Field           | Type                                         | Constraints                               | Notes                       |
| --------------- | -------------------------------------------- | ----------------------------------------- | --------------------------- |
| trade_id        | str                                          | Exists in TradeSignal.id                  | Foreign key                 |
| entry_timestamp | datetime                                     | == TradeSignal.timestamp_utc or +1 candle | Aligns with execution model |
| exit_timestamp  | datetime                                     | > entry_timestamp                         | Closure condition           |
| pnl             | float64                                      | Any real                                  | Net profit/loss             |
| exit_reason     | enum(stop_loss, take_profit, timeout, other) | Required                                  | Classification              |

## PerformanceReport

| Field                   | Type     | Constraints              | Notes                  |
| ----------------------- | -------- | ------------------------ | ---------------------- |
| scan_duration_sec       | float    | >=0                      | Wall-clock measurement |
| simulation_duration_sec | float    | >=0                      | Wall-clock measurement |
| peak_memory_mb          | float    | >=0                      | Sampled peak           |
| manifest_path           | str      | Relative path            | Provenance             |
| manifest_sha256         | str      | 64 hex chars             | Integrity              |
| candle_count            | int      | >0                       | Dataset size           |
| signal_count            | int      | >=0                      | Post-scan count        |
| trade_count             | int      | >=0                      | Executed trades        |
| equivalence_verified    | bool     | True if baseline matched | Signal & trade parity  |
| progress_emission_count | int      | >=0                      | UX instrumentation     |
| created_at              | datetime | UTC                      | Report creation time   |

## Relationships

- Candle → TradeSignal: Many signals reference unique candle timestamps.
- TradeSignal → SimulationResult: 1→1.
- Strategy (external) → IndicatorSet: 1→1 binding for ownership.

## Validation Rules Summary

- Duplicate timestamps removed before entity creation (first occurrence retained).
- IndicatorSet names must match exactly runtime used indicator keys.
- Memory metrics sampled after major phases; absence handled gracefully.
- Deterministic mode: given identical input & strategy, signal_count and trade_count must match baseline.

## State Transitions

Trade lifecycle: `generated (signal) → simulated (result) → aggregated (report)`.

## Open Considerations

- Future multi-symbol extension will introduce PortfolioResult entity (out of current scope).
- Potential addition of volatility-adjusted fields (e.g., ATR) retained only in Candle.indicators.
- Optional Polars representation: `CandleFrame` (LazyFrame/DataFrame) mirroring columns `timestamp_utc, open, high, low, close` plus indicator columns; conversion to NumPy arrays MUST preserve ordering and dtype; equivalence tests ensure identical signals/trades vs pandas path.
