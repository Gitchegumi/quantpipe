# Strategy Overview

This document summarizes the trading strategies represented (or planned) in the repository and points to their canonical specifications.

## Current Implemented Strategy

### Trend Pullback Continuation

* **Goal**: Participate in sustained directional moves while avoiding momentum exhaustion.
* **Core Idea**: Identify prevailing trend (EMA relationship + ranging filter) → wait for price pullback against trend → require reversal + momentum confirmation → risk-managed entry with ATR-based stop and R-multiple target.
* **Specification**: See `specs/001-trend-pullback/spec.md`
* **Quickstart**: `specs/001-trend-pullback/quickstart.md`
* **Data Model**: `specs/001-trend-pullback/data-model.md`

### Key Components Referenced

| Component | Role |
|-----------|------|
| Indicators (`src/indicators/`) | EMA, momentum, volatility context |
| Strategy Logic (`src/strategy/trend_pullback/`) | Signal evaluation & state handling |
| Risk (`src/risk/`) | Position sizing & ATR-based stops |
| Backtest (`src/backtest/`) | Deterministic event loop & metrics collection |

## Planned / Extensible Areas

| Potential Direction | Rationale | Status |
|---------------------|-----------|--------|
| Additional mean-reversion module | Diversification beyond trend dependency | Concept only |
| Multi-timeframe confirmation refinements | Improve signal quality in choppy regimes | Under evaluation |
| Volatility regime adaptation | Dynamic parameter tuning | Optional flags exist |

## Adding a New Strategy (High-Level)

1. Draft a feature spec in `specs/` using the feature creation script.
2. Add minimal indicator or state primitives if missing (avoid duplication).
3. Provide unit tests for core decision logic and integration tests for end-to-end entry/exit lifecycle.
4. Update this page with summary + pointer to new spec.

## Backtest Result Summaries (Placeholder)

Future iterations may include aggregated performance snapshots (win rate, expectancy, drawdown) per strategy version. For now, consult CLI output or JSON exports.

## Design Principles

* Parsimony first—prefer fewer, interpretable inputs.
* Determinism—identical inputs yield identical metrics.
* Explicit risk—no implicit leverage or hidden exposure.

---
For deep methodological details, see `docs/backtesting.md`.
