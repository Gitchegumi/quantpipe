# Data Model: Portfolio Visualization Mapping (Feature 019)

This document defines the transformation required to adapt `PortfolioResult` (execution model) into `BacktestResult` (visualization model) to enable multi-symbol charting.

## Core Transformation

The goal is to convert the monolithic `PortfolioResult` into a hierarchical `BacktestResult` that the visualization engine recognizes as a multi-symbol result.

### Source Entity: `PortfolioResult`

Currently produced by `PortfolioSimulator.simulate()`:

```python
@dataclass
class PortfolioResult:
    # ... metadata ...
    closed_trades: list[ClosedTrade]  # Flat list of all trades mixed
    equity_curve: list[tuple[datetime, float]] # Shared equity
    # ...
```

### Target Entity: `BacktestResult` (Visualization-Ready)

Required structure for `_create_multi_symbol_layout`:

```python
@dataclass
class BacktestResult:
    # ... metadata ...
    is_multi_symbol: bool = True
    results: dict[str, BacktestResult] # Per-symbol sub-results
    metrics: dict                      # Portfolio-wide metrics
```

### Mapping Logic

1. **Portfolio-Level Container**:

   - Create a root `BacktestResult`.
   - `is_multi_symbol = True`
   - `metrics` = Global portfolio metrics (Total Return, Sharpe, etc.)
   - `executions` = `[]` (Root level has no trades of its own in this view)

2. **Per-Symbol Children (`results` dict - NEW)**:

   - For each symbol `S` in the portfolio:
     - Filter `PortfolioResult.closed_trades` where `trade.symbol == S`.
     - Create a child `BacktestResult`:
       - `executions` = The filtered trades for `S`.
       - `metrics` = Symbol-specific metrics (Win Rate, PnL for `S` only).
       - `is_multi_symbol = False`
     - Add to `results[S]`.

3. **Trade Conversion**:
   - Input `ClosedTrade` objects need mapping to `TradeExecution` objects expected by the visualization (field name compatibility).

## Validation Rules

- **Completeness**: Sum of trades in child results MUST equal total trades in `PortfolioResult`.
- **Symbol Consistency**: Keys in `results` dict must supply accurate OHLC data matching that key in the Polars `all_symbol_data`.
