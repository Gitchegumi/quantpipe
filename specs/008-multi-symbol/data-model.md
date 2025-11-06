# Data Model: Multi-Symbol & Portfolio Backtesting (Phase 1)

Date: 2025-11-06  
Branch: 008-multi-symbol  
Spec Reference: `specs/008-multi-symbol/spec.md` (FR-001..FR-023, SC-001..SC-014)  
Research Decisions: `research.md` (1–9)

## Overview

This document defines the core entities required to implement independent and portfolio multi-symbol backtesting. It translates functional requirements (FR) and decisions into concrete data structures. All models will be implemented with `pydantic` (validation + type hints) unless noted otherwise. Line length ≤88 chars (Black) and complete docstrings required in code.

## Entity Catalogue

| Entity                    | Purpose                                     | Persistence   | Source FR/Decision |
| ------------------------- | ------------------------------------------- | ------------- | ------------------ |
| `CurrencyPair`            | Represents a tradable symbol (e.g., EURUSD) | In-memory     | FR-001, FR-023     |
| `SymbolConfig`            | Per-symbol overrides (thresholds, weights)  | In-memory     | Decision 8         |
| `PortfolioConfig`         | Portfolio-level parameters & thresholds     | In-memory     | FR-010, Decision 8 |
| `CorrelationWindowState`  | Rolling correlation calculation state       | In-memory     | FR-010             |
| `CorrelationMatrix`       | Current pairwise correlations               | In-memory     | FR-010, Decision 8 |
| `VolatilitySnapshot`      | Per-symbol volatility metrics               | In-memory     | Decision 6         |
| `AllocationRequest`       | Input to AllocationEngine                   | Transient     | Decision 6         |
| `AllocationResponse`      | Output allocations + metadata               | Transient     | Decision 6         |
| `PortfolioSnapshotRecord` | Periodic JSONL snapshot row                 | File JSONL    | FR-022, Decision 7 |
| `RuntimeFailureEvent`     | Symbol isolation logging struct             | Transient/log | Decision 5         |

## Definitions

### `CurrencyPair`

Represents a normalized 6-letter FX pair code.

Fields:

- `code: str` (pattern: `^[A-Z]{6}$`; validation on init)
- `base: str` (first 3 chars)
- `quote: str` (last 3 chars)

### `SymbolConfig`

Optional overrides per symbol.

Fields:

- `pair: CurrencyPair`
- `correlation_threshold_override: float | None` (0.0–1.0 inclusive)
- `base_weight: float | None` (non-negative, used when base weights provided)
- `enabled: bool` (default True)
- `spread_pips: float | None` (symbol-specific spread in pips; overrides global default if provided; FR-008)
- `commission_rate: float | None` (symbol-specific commission as fraction of trade value; overrides global default if provided; FR-008)

### `PortfolioConfig`

Global portfolio tuning.

Fields:

- `correlation_threshold_default: float` (default 0.8)
- `snapshot_interval_candles: int` (default 50; FR-022)
- `max_memory_growth_factor: float` (formula reference Decision 2)
- `abort_on_symbol_failure: bool` (False → isolate per Decision 5)
- `allocation_rounding_dp: int` (default 2)

### `CorrelationWindowState`

Rolling correlation computation for a pair of symbols.

Fields:

- `pair_a: CurrencyPair`
- `pair_b: CurrencyPair`
- `window: int` (target length: 100; FR-010)
- `values_a: deque[float]`
- `values_b: deque[float]`
- `provisional_min: int` (minimum length for provisional evaluation, default 20)

Methods:

- `update(price_a: float, price_b: float) -> float | None` (returns current correlation if provisional_min met; else None)
- `is_ready() -> bool` (len == window)

### `CorrelationMatrix`

Holds current correlation values keyed by lexicographically ordered pair token: `"EURUSD:GBPUSD"`.

Fields:

- `values: dict[str, float]` (each value in [-1.0, 1.0])
- `timestamp: datetime` (last update time)

### `VolatilitySnapshot`

Per-symbol volatility metrics (ATR, stdev, etc.).

Fields:

- `pair: CurrencyPair`
- `atr: float | None`
- `std_dev: float | None`
- `lookback_used: int` (candles)

### `AllocationRequest`

Input into allocation engine.

Fields:

- `symbols: list[CurrencyPair]` (≥1)
- `volatility: dict[str, float]` (key: pair code, value >0)
- `correlation_matrix: dict[str, float]` (pair key → correlation)
- `base_weights: dict[str, float] | None` (optional; all symbols present if not None; sum ≈1.0 ± tolerance)
- `capital: float` (>0)

### `AllocationResponse`

Output allocations with invariants.

Fields:

- `allocations: dict[str, float]` (sum == request.capital, rounded to dp)
- `diversification_ratio: float` (0.0–1.0)
- `correlation_penalty: float` (aggregate penalty factor; optional initial version)
- `timestamp: datetime`

Validation:

- Sum of `allocations` equals `capital` after rounding (largest remainder correction)

### `PortfolioSnapshotRecord`

Periodic state persistence (JSONL, FR-022, Decision 7).

Fields:

- `t: datetime` (ISO8601 serialization)
- `positions: dict[str, float]` (current position sizes)
- `unrealized: dict[str, float]` (per-symbol unrealized P&L in R or currency)
- `portfolio_pnl: float` (aggregate realized + unrealized)
- `exposure: float` (notional exposure fraction of capital)
- `diversification_ratio: float`
- `corr_window: int` (active correlation window length for current evaluation)

### `RuntimeFailureEvent`

Logs isolation of a failed symbol.

Fields:

- `pair: CurrencyPair`
- `reason: str` (exception message or classification)
- `timestamp: datetime`

## Key Relationships

- `PortfolioConfig` consumed by allocation & orchestrator logic.
- `CorrelationMatrix` + `VolatilitySnapshot` feed `AllocationRequest`.
- `AllocationResponse` informs trade sizing / capital partitioning.
- `PortfolioSnapshotRecord` produced at interval defined by `PortfolioConfig`.

## Edge Cases & Handling

| Scenario                                | Handling                                             |
| --------------------------------------- | ---------------------------------------------------- |
| Provisional correlation not ready (<20) | Skip allocation adjustments; use base weights        |
| Symbol disabled mid-run                 | Exclude from future requests; recompute base weights |
| Missing volatility metric               | Fallback: equal weighting among available symbols    |
| Correlation key missing                 | Treat as 0.0 (uncorrelated)                          |
| Allocations rounding drift              | Adjust largest allocation to fix sum                 |

## Performance Considerations

- Correlation windows stored in deques for O(1) append/pop.
- Volatility snapshots updated incrementally (no full recomputation each candle).
- Memory growth tracked vs baseline per Decision 2; periodic logging of peak and ratio.

## Serialization Strategy

- JSONL for snapshots (append-only writes).
- Allocation requests/responses not persisted (transient, may be logged at DEBUG).
- Failure events logged via structured logging only.

## Next Steps

1. Implement `models/portfolio.py` with pydantic classes for these entities.
2. Integrate correlation update loop into orchestrator (portfolio mode prototype).
3. Implement AllocationEngine per contract YAML.
