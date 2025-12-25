# Research: Decouple Risk Management from Strategy

**Feature**: 021-decouple-risk-management
**Date**: 2024-12-24

## Overview

Research findings to inform the implementation of decoupled risk management, addressing unknowns and establishing best practices for the pluggable policy architecture.

---

## Decision 1: Signal Model Refactoring Approach

**Decision**: Introduce a new lightweight `Signal` dataclass that strategies emit; `TradeSignal` becomes internal to the RiskManager output (OrderPlan).

**Rationale**:

- Existing `TradeSignal` contains risk fields (`initial_stop_price`, `target_price`, `calc_position_size`) that violate the separation principle.
- Creating a new `Signal` type with minimal fields (direction, symbol, timestamp, optional entry_hint) provides clean decoupling.
- `TradeSignal` can be deprecated gradually or repurposed as `OrderPlan` output.

**Alternatives Considered**:

- _Make existing TradeSignal fields optional_: Rejected—would create ambiguous state where signals may or may not have risk data.
- _Use dict instead of dataclass_: Rejected—loses type safety and validation.

---

## Decision 2: Policy Registration Pattern

**Decision**: Use class registry with string-based lookup for policies, instantiated from config dicts.

**Rationale**:

- CLI uses string identifiers (`--stop-policy ATR_Trailing`) that map to class names.
- Factory pattern with registry enables runtime selection without code changes.
- Matches existing `indicator_registry.py` pattern in codebase.

**Alternatives Considered**:

- _Plugin discovery via entry points_: Rejected—overkill for initial implementation; can add later.
- _Hardcoded if/else_: Rejected—violates open/closed principle.

---

## Decision 3: Trailing Stop Implementation

**Decision**: StopPolicy interface has two methods: `initial_stop(entry, context) -> float` and `update_stop(position, market) -> float`. RiskManager calls update on each bar.

**Rationale**:

- Separates initial placement from update logic.
- `update_stop` receives current position state (entry, direction, current stop) and market data (high, low, ATR).
- Ratchet logic (never widen risk) enforced in base class or RiskManager.

**Alternatives Considered**:

- _Single method with all logic_: Rejected—harder to implement fixed policies that never update.
- _Event-driven updates_: Rejected—unnecessary complexity for backtesting context.

---

## Decision 4: Configuration Schema Format

**Decision**: JSON config with pydantic validation, mirroring CLI args structure.

**Rationale**:

- Existing project uses pydantic (v2.4.0+) for data validation.
- JSON is explicitly assumed in spec.
- Schema can validate policy parameters before instantiation.

**Config Structure**:

```json
{
  "risk_pct": 0.25,
  "stop_policy": { "type": "ATR", "multiplier": 2.0, "period": 14 },
  "take_profit_policy": { "type": "RiskMultiple", "rr_ratio": 3.0 },
  "position_sizer": { "type": "RiskPercent" },
  "max_position_size": 10.0
}
```

**Alternatives Considered**:

- _YAML_: Rejected for initial implementation—spec assumes JSON; YAML support can be added later.
- _TOML_: Rejected—less common for runtime config.

---

## Decision 5: Backward Compatibility Strategy

**Decision**: Existing strategies continue working via a "legacy adapter" that extracts signal data and provides default risk config matching current behavior.

**Rationale**:

- FR-010 mandates backward compatibility.
- Current strategies return `TradeSignal` with stops/targets already set.
- Adapter interprets existing signals and optionally overrides with RiskManager output.

**Default Risk Config** (matches current system):

- `risk_pct`: 0.25%
- `stop_policy`: ATR with 2× multiplier
- `take_profit_policy`: RiskMultiple with 2:1 ratio

**Alternatives Considered**:

- _Force migration_: Rejected—would break existing workflows.
- _Dual code paths indefinitely_: Rejected—legacy adapter provides clean migration path.

---

## Decision 6: Integration Point in Backtest Flow

**Decision**: RiskManager intercepts signals after strategy `scan_vectorized()` and before `BatchSimulation.simulate()`.

**Rationale**:

- Current flow: Strategy → (signals with stops) → Simulation
- New flow: Strategy → (pure signals) → RiskManager → (OrderPlan with stops) → Simulation
- Minimal changes to orchestrator; RiskManager transforms signals to orders.

**Integration Code Location**: `src/backtest/orchestrator.py` in `_run_vectorized_backtest()` method.

**Alternatives Considered**:

- _Modify BatchSimulation_: Rejected—simulation should remain generic.
- _New orchestrator method_: Rejected—unnecessary code duplication.

---

## Best Practices Gathered

### Python Design Patterns for Pluggable Policies

1. **Protocol classes** (PEP 544) for policy interfaces—allows duck typing with static analysis support.
2. **Dataclasses with frozen=True** for immutable config objects.
3. **Factory functions** returning policy instances from config dicts.
4. **Lazy % formatting in logging** (Constitution X requirement).

### Position Sizing Patterns

1. **Risk-percent sizing**: `position_size = risk_amount / (stop_pips × pip_value)` - already implemented.
2. **Kelly criterion**: For future—optimal growth sizing.
3. **Volatility-adjusted**: ATR-based position scaling—can layer on risk-percent.

### Trailing Stop Patterns

1. **ATR trailing**: `new_stop = price - (ATR × mult)` for longs.
2. **Percentage trailing**: Fixed percent from highest point.
3. **Chandelier exit**: ATR-based from highest high.

---

## Open Questions Resolved

| Question                   | Resolution                                                                       |
| -------------------------- | -------------------------------------------------------------------------------- |
| Where does ATR come from?  | Indicator cache in candle data, key `atr` or `atr14`.                            |
| How to handle missing ATR? | Raise `RiskConfigurationError` if ATR-based policy selected but ATR unavailable. |
| Position min/max limits?   | Existing `lot_step=0.01`, `max_position_size=10.0` defaults in `manager.py`.     |
| Signal timestamp source?   | Candle timestamp propagated through signal.                                      |
