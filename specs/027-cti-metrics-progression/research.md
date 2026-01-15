# Research Findings: Feature 027 - CTI Metrics

## Decisions

### 1. Independent "Lives" for PnL

- **Context**: When an account fails a challenge (reset), we need to decide how to track PnL.
- **Decision**: Use "Independent Lives" model. A reset closes the current "Life" (Attempt) and starts a fresh PnL tracking sequence.
- **Rationale**: Keeps the math clean for each attempt. Summing PnL across failed 10k accounts implies a "net portfolio" view which obscures the specific performance of the strategy in passing the challenge.
- **Implementation**: `ScalingReport` will contain a list of `LifeResult` objects.

### 2. Closed Balance Drawdown

- **Context**: Prop firms vary on "Intraday Equity" vs "Closed Balance" drawdown.
- **Decision**: Enforce drawdown rules on **Closed Balance Only**.
- **Rationale**: Our backtest engine is signal-based/vectorized and does not natively simulate tick-level intraday equity excursions without significant complexity/estimation error. "Closed Balance" is a standard interpretation for "Day Trading" challenge variants and is computationally efficient.

### 3. Periodic Scaling

- **Context**: When to check for scale-up eligibility.
- **Decision**: Fixed 4-month windows (Periodic).
- **Rationale**: Matches CTI terms ("Review Period"). Continuous rolling window is more aggressive but less standard for this specific prop firm.

## Impact Analysis

### `src/models/core.py`

- **MetricsSummary**: Needs expansion.
  - Add `sortino_ratio`, `avg_trade_duration`, `max_consecutive_wins`, `max_consecutive_losses`, `profit_factor` (already exists, verify calc), `annualized_volatility`.
  - **Note**: `MetricsSummary` is frozen. We must update the definition.

### `src/backtest/metrics.py`

- **compute_metrics**:
  - Needs `sortino` logic (requires downside deviation calc).
  - Needs `duration` logic (requires start/end timestamps).
  - Needs `streak` logic (requires iterating PnL array).

## Alternatives Considered

- **Intraday Drawdown Estimation**: Rejected. Using High/Low of candles to estimate "max excursion" during a trade is possible but prone to false positives if the High happened _after_ the exit. Requires tick data for accuracy.
- **Cumulative PnL**: Rejected. Merging PnL of failed accounts into one number hides the "Survival Rate" of the strategy.
