# Data Model: Trend Pullback Continuation Strategy

**Branch**: 001-trend-pullback  
**Date**: 2025-10-25  
**Source**: ./spec.md, research.md

## Entities

### Candle

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| timestamp_utc | datetime | UTC timestamp | Required; monotonic ascending |
| open | float | Open price | >0 |
| high | float | High price | ≥ open; ≥ low |
| low | float | Low price | ≤ high; ≤ open |
| close | float | Close price | >0 |
| volume | float | Raw volume or tick count | ≥0 (may be absent FX) |
| ema20 | float | Fast EMA value | Computed; non-negative |
| ema50 | float | Slow EMA value | Computed; non-negative |
| atr | float | ATR(14) | ≥0 |
| rsi | float | RSI(14) | 0–100 |
| stoch_rsi | float? | Optional Stoch RSI | 0–100 or null |

**State Rules**:

- Candle sequence must not skip more than GAP_THRESHOLD minutes; gaps flagged.
- Derived fields computed lazily in ingestion pipeline.


### TrendState

| Field | Type | Description |
|-------|------|-------------|
| state | enum(UP, DOWN, RANGE) | Current directional classification |
| cross_count | int | EMA crosses in lookback window |
| last_change_timestamp | datetime | When state last changed |

**Transition Logic**:

- UP ↔ DOWN transitions only if fast EMA crosses slow EMA and stays > 1 candle.
- RANGE entered if cross_count ≥ RANGE_CROSS_THRESHOLD.



### PullbackState

| Field | Type | Description |
|-------|------|-------------|
| active | bool | Whether pullback context exists |
| direction | enum(LONG, SHORT) | Direction of potential trade |
| start_timestamp | datetime | First qualifying candle |
| qualifying_candle_ids | list[str] | IDs referencing candidate candles |
| oscillator_extreme_flag | bool | RSI extreme satisfied |

**Expiration**: Expires after PULLBACK_MAX_AGE candles or if trend invalidated.

### TradeSignal

| Field | Type | Description |
|-------|------|-------------|
| id | string | 16 hex deterministic hash; SHA256(timestamp,pair,direction,entry_price,strategy_version) truncated |
| pair | string | Instrument (e.g., EURUSD) |
| direction | enum(LONG, SHORT) | Trade direction |
| entry_price | float | Candidate entry price |
| initial_stop_price | float | Stop level |
| risk_per_trade_pct | float | Fraction of equity risked |
| calc_position_size | float | Computed units/lot size |
| tags | list[string] | Rationale labels |
| version | string | Strategy version string |
| timestamp_utc | datetime | Signal generation time |

### TradeExecution

| Field | Type | Description |
|-------|------|-------------|
| signal_id | string | Foreign key to TradeSignal id |
| open_timestamp | datetime | Filled timestamp |
| entry_fill_price | float | Actual filled price (slippage applied) |
| close_timestamp | datetime | Exit time |
| exit_fill_price | float | Exit price |
| exit_reason | enum(TARGET, TRAILING_STOP, STOP_LOSS, EXPIRY) | Why closed |
| pnl_R | float | Profit/loss in R multiples |
| slippage_entry_pips | float | Entry slippage |
| slippage_exit_pips | float | Exit slippage |
| costs_total | float | Spread + commission |

### BacktestRun

| Field | Type | Description |
|-------|------|-------------|
| run_id | string | UUID or deterministic label |
| parameters_hash | string | Hash of params & manifest |
| manifest_ref | string | Path/reference to data manifest |
| metrics_summary | object | Aggregated performance metrics |
| reproducibility_hash | string | Combined hash for rerun validation |
| observability | object | Latency, slippage, drawdown curve |

### DataManifest

| Field | Type | Description |
|-------|------|-------------|
| pair | string | Instrument |
| timeframe | string | Candle timeframe (e.g., 1m, 15m) |
| date_range_start | date | Inclusive start |
| date_range_end | date | Inclusive end |
| source_provider | string | Data vendor/endpoint |
| download_date | date | Acquisition date |
| checksum | string | SHA256 of raw source file |
| preprocessing_notes | string | Transformations applied |

## Relationships

- TradeExecution.signal_id → TradeSignal.id (1:1 once executed)
- BacktestRun contains many TradeSignals and TradeExecutions (1:N)
- TradeSignal references derived Candle data indirectly (not persisted inside signal to reduce duplication)
- DataManifest linked to BacktestRun.manifest_ref (1:N across runs)

## Validation Rules

- Position sizing MUST produce calc_position_size > 0 and integer micro-lots rounding rule documented.
- initial_stop_price MUST be >0 and in correct direction (long: stop < entry, short: stop > entry).
- pnl_R computed as (exit_fill_price - entry_fill_price)/(entry_fill_price - initial_stop_price) with sign adjustment for direction.
- drawdown curve points: cumulative equity vs peak; max drawdown derived.

## State Transitions Summary

1. TrendState update each candle.
2. PullbackState activated when conditions met; accumulates qualifying candles.
3. Reversal triggers TradeSignal emission.
4. TradeSignal becomes TradeExecution upon simulated fill (same timestamp for backtest or next candle open).
5. TradeExecution closed on exit condition; metrics update BacktestRun.


## Derived Computations

- Expectancy: avg_R * win_rate - (1 - win_rate)
- Sharpe (approx): (mean_trade_R / std_trade_R) * sqrt(trade_count)
- Volatility regime classification affects risk sizing adjustments (future extension).


## Data Provenance & Reproducibility

- Each BacktestRun stores manifest_ref + parameters_hash; reproducibility_hash = SHA256(parameters_hash + manifest checksum + strategy version).


## Notes

- Stoch RSI omitted until baseline viability confirmed.
- Multi-pair correlation and portfolio risk aggregation deferred.
