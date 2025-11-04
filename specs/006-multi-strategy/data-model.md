# Data Model: Multi-Strategy Support

**Date**: 2025-11-03  
**Branch**: 006-multi-strategy  
**Spec Reference**: ./spec.md

## Entities Overview

### Strategy

- id: string (unique)
- name: string
- tags: list[string]
- default_parameters: map[string, any]
- default_risk_limits: RiskLimits
- description: string (optional)
- active: bool
- validation_version: string (strategy implementation version hash)
  **Constraints**: `id` unique; `name` non-empty.

### StrategyConfig

- strategy_id: string
- parameters: map[string, any]
- risk_limits: RiskLimits
- weight: float (0..1) optional
- overrides_source: string ("cli" | "file" | "default")
  **Validation**: if `weight` provided then 0 <= weight <= 1.

### RiskLimits

- max_position_size: float
- daily_loss_limit: float
- global_drawdown_limit: float (optional; portfolio-level parameter mirrored in manifest)
- max_trade_notional: float (optional)
  **Constraints**: Positive values; drawdown limit < 1.0 (fraction of starting equity).

### StrategyState

- open_positions: list[Position]
- indicators_cache: map[string, any]
- trade_history: list[Trade]
- realized_pnl: float
- unrealized_pnl: float
- drawdown: float
- halted: bool
- halt_reason: string (optional)

### Position

- instrument: string
- quantity: float
- entry_price: float
- direction: string ("long"|"short")
- timestamp_open: datetime
- timestamp_close: datetime (optional)

### Trade

- trade_id: string
- instrument: string
- direction: string ("buy"|"sell")
- quantity: float
- price: float
- timestamp: datetime
- strategy_id: string
- order_type: string (optional)

### StrategyResult

- strategy_id: string
- metrics: StrategyMetrics
- positions: list[Position]
- trades: list[Trade]
- risk_events: list[RiskEvent]
- halted: bool
- halt_reason: string (optional)

### StrategyMetrics

- total_trades: int
- gross_pnl: float
- net_pnl: float
- max_drawdown: float
- volatility: float
- win_rate: float
- average_trade_pnl: float

### RiskEvent

- event_type: string ("limit_breach"|"halt"|"error")
- timestamp: datetime
- detail: string

### PortfolioAggregate

- strategies_count: int
- weights_applied: map[string, float]
- aggregate_pnl: float
- aggregate_drawdown: float
- aggregate_volatility: float
- net_exposure_by_instrument: map[string, float]
- total_trades: int
- global_abort_triggered: bool
- risk_breaches: list[RiskEvent]
- deterministic_run_id: string

### RunManifest

- run_id: string
- timestamp_start: datetime
- timestamp_end: datetime (optional)
- strategies: list[StrategyConfig]
- weights_mode: string ("user"|"equal-weight")
- global_drawdown_limit: float (optional)
- data_manifest_ref: string
- correlation_status: string ("deferred")
- deterministic_run_id: string
- version_hash: string (hash of spec + plan snapshot)

## Relationships

- Strategy 1..\* StrategyConfig (a strategy may have multiple configs across runs)
- StrategyConfig 1..1 StrategyState (per run)
- StrategyResult aggregates Trade and Position
- PortfolioAggregate summarizes StrategyResult list
- RunManifest links all StrategyConfig entries used in the run

## State Transitions

StrategyState:

1. INIT → ACTIVE (on run start)
2. ACTIVE → HALTED (risk breach or global abort)
3. ACTIVE → COMPLETED (end of data stream)
4. HALTED → COMPLETED (post processing of partial results)

## Validation Rules

- All strategy ids must be unique in registry
- Weights sum (if provided) must be ~1.0 within tolerance 1e-6 else fallback equal-weight
- global_drawdown_limit when set must be 0 < limit < 1.0
- Deterministic run id must equal sha256(manifest + ordered strategy ids + weights)

## Aggregation Logic (Summary)

- Net exposure by instrument = Σ (signed quantity \* contract_size if applicable) across strategies at each time slice → last value stored per instrument.
- Aggregate volatility computed from concatenated per-strategy PnL time series normalized by weights.

## Edge Case Handling

- Zero-trade strategy → metrics defaults; included in counts.
- Risk breach → StrategyState.halted set; portfolio continues unless global abort.
- Unrecoverable error → global_abort_triggered set; partial results retained.

## Open Future Extensions

- Correlation matrix (strategy_id pairwise correlations) added to PortfolioAggregate.
- Dynamic reweighting events appended to RunManifest.
