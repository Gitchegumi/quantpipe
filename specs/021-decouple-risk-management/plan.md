# Implementation Plan: Decouple Risk Management from Strategy

**Branch**: `021-decouple-risk-management` | **Date**: 2024-12-24 | **Spec**: [spec.md](file:///e:/GitHub/trading-strategies/specs/021-decouple-risk-management/spec.md)
**Input**: Feature specification from `/specs/021-decouple-risk-management/spec.md`

## Summary

Separate trade signal generation (strategy) from risk management/execution so risk rules can be changed without touching strategy code. Strategies will emit lightweight `Signal` objects containing only direction and symbol; a configurable `RiskManager` component will transform signals into complete `OrderPlan` objects with stops, targets, and position sizes based on pluggable policies.

Key changes:

1. New `Signal` dataclass in `src/models/` - pure direction signals
2. New `RiskManager` class in `src/risk/` with pluggable policies
3. Protocol classes for `StopPolicy`, `TakeProfitPolicy`, `PositionSizer`
4. ATR and ATR_Trailing stop implementations
5. CLI integration for runtime policy selection
6. Orchestrator modification to inject RiskManager into backtest flow

## Technical Context

**Language/Version**: Python 3.11 (per pyproject.toml)
**Primary Dependencies**: numpy, pandas, polars, pydantic (v2.4.0+), pytest
**Storage**: N/A (file-based config, memory-resident processing)
**Testing**: pytest with existing fixtures in `tests/fixtures/`
**Target Platform**: Windows/Linux (cross-platform)
**Project Type**: Single Python package (`src/`)
**Performance Goals**: No degradation from current backtest throughput
**Constraints**: Backward compatibility with existing strategies (FR-010)
**Scale/Scope**: Single-symbol and multi-symbol backtests

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Principle                       | Status  | Notes                                 |
| ------------------------------- | ------- | ------------------------------------- |
| I. Strategy-First Architecture  | ✅ Pass | Decoupling enhances modularity        |
| II. Risk Management Integration | ✅ Pass | Core focus of this feature            |
| III. Backtesting & Validation   | ✅ Pass | Regression tests planned              |
| IV. Real-Time Monitoring        | ✅ Pass | Backtest logging includes risk params |
| V. Data Integrity & Security    | ✅ Pass | No credential handling                |
| VI. Data Version Control        | ✅ Pass | Config versioning                     |
| VIII. Code Quality & Docs       | ✅ Pass | Docstrings, type hints required       |
| IX. Poetry Dependency Mgmt      | ✅ Pass | No new dependencies needed            |
| X. Code Quality Automation      | ✅ Pass | Black, ruff, pylint checks            |
| XI. Commit Message Standards    | ✅ Pass | Semantic tags will be used            |
| XII. Task Tracking              | ✅ Pass | tasks.md will track progress          |
| XIII. GitHub Workflow Templates | ✅ Pass | PR template will be used              |

## Project Structure

### Documentation (this feature)

```text
specs/021-decouple-risk-management/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: architectural decisions
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: usage guide
├── contracts/
│   └── risk-config.schema.json  # JSON Schema for config validation
└── tasks.md             # Phase 2: implementation tasks (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── models/
│   ├── signal.py                # [NEW] Lightweight Signal dataclass
│   └── order_plan.py            # [NEW] OrderPlan dataclass
├── risk/
│   ├── __init__.py              # [MODIFY] Export new components
│   ├── manager.py               # [MODIFY] Add RiskManager class
│   ├── policies/                # [NEW] Directory
│   │   ├── __init__.py
│   │   ├── stop_policies.py     # ATR, ATR_Trailing, FixedPips
│   │   ├── tp_policies.py       # RiskMultiple, NoTakeProfit
│   │   └── position_sizers.py   # RiskPercentSizer
│   ├── config.py                # [NEW] RiskConfig pydantic model
│   └── registry.py              # [NEW] Policy registry
├── cli/
│   └── run_backtest.py          # [MODIFY] Add --risk-* CLI args
└── backtest/
    └── orchestrator.py          # [MODIFY] Inject RiskManager

tests/
├── unit/
│   ├── test_signal_model.py           # [NEW]
│   ├── test_order_plan.py             # [NEW]
│   ├── test_risk_manager.py           # [NEW]
│   ├── test_stop_policies.py          # [NEW]
│   ├── test_tp_policies.py            # [NEW]
│   └── test_risk_config.py            # [NEW]
└── integration/
    └── test_risk_policy_switching.py  # [NEW] FR-001 verification
```

**Structure Decision**: Existing single-project layout with `src/` and `tests/` directories. New `src/risk/policies/` subdirectory for pluggable components.

## Proposed Changes

### Component: Models

#### [NEW] [signal.py](file:///e:/GitHub/trading-strategies/src/models/signal.py)

Lightweight `Signal` dataclass with:

- `symbol: str`
- `direction: Literal["LONG", "SHORT"]`
- `timestamp: datetime`
- `entry_hint: float | None`
- `metadata: dict`

#### [NEW] [order_plan.py](file:///e:/GitHub/trading-strategies/src/models/order_plan.py)

`OrderPlan` dataclass output by RiskManager with complete order specification.

---

### Component: Risk Management

#### [MODIFY] [manager.py](file:///e:/GitHub/trading-strategies/src/risk/manager.py)

Add `RiskManager` class that:

- Accepts `RiskConfig` and instantiates policies
- Implements `build_orders(signal, portfolio_state) -> OrderPlan`
- Implements `update_trailing(position, market) -> float`

#### [NEW] [policies/stop_policies.py](file:///e:/GitHub/trading-strategies/src/risk/policies/stop_policies.py)

Implement `StopPolicy` protocol with:

- `ATRStop`: Fixed ATR-based stop
- `ATRTrailingStop`: Trailing ATR stop with ratchet logic
- `FixedPipsStop`: Fixed pip distance

#### [NEW] [policies/tp_policies.py](file:///e:/GitHub/trading-strategies/src/risk/policies/tp_policies.py)

Implement `TakeProfitPolicy` protocol with:

- `RiskMultipleTP`: TP at N× risk distance
- `NoTakeProfit`: Returns None

#### [NEW] [policies/position_sizers.py](file:///e:/GitHub/trading-strategies/src/risk/policies/position_sizers.py)

Implement `PositionSizer` protocol with:

- `RiskPercentSizer`: Size = risk_amount / (stop_distance × pip_value)

#### [NEW] [config.py](file:///e:/GitHub/trading-strategies/src/risk/config.py)

Pydantic model for `RiskConfig` with validation.

#### [NEW] [registry.py](file:///e:/GitHub/trading-strategies/src/risk/registry.py)

Policy registry with string-based lookup for CLI integration.

---

### Component: CLI

#### [MODIFY] [run_backtest.py](file:///e:/GitHub/trading-strategies/src/cli/run_backtest.py)

Add arguments:

- `--risk-config`: Path to JSON config file
- `--risk-pct`: Risk percentage per trade
- `--stop-policy`: Stop policy type (ATR, ATR_Trailing, FixedPips)
- `--atr-mult`: ATR multiplier
- `--atr-period`: ATR period
- `--tp-policy`: TP policy type (RiskMultiple, None)
- `--rr-ratio`: Reward-to-risk ratio

---

### Component: Backtest Engine

#### [MODIFY] [orchestrator.py](file:///e:/GitHub/trading-strategies/src/backtest/orchestrator.py)

Modify `_run_vectorized_backtest()` to:

1. Accept optional `RiskManager` instance
2. Transform pure signals to OrderPlans via RiskManager
3. Pass OrderPlans to simulation
4. Handle trailing stop updates per bar

---

## Verification Plan

### Automated Tests

Existing risk tests to validate during development:

```bash
# Run existing risk sizing tests (should pass unchanged)
pytest tests/unit/test_risk_sizing_normal.py -v
pytest tests/unit/test_risk_sizing_edge_cases.py -v
pytest tests/unit/test_risk_manager_rounding.py -v
pytest tests/unit/test_risk_manager_short.py -v
pytest tests/unit/test_risk_sizing_volatility.py -v
```

New tests to implement:

```bash
# Run all new unit tests
pytest tests/unit/test_signal_model.py -v
pytest tests/unit/test_order_plan.py -v
pytest tests/unit/test_risk_manager.py -v
pytest tests/unit/test_stop_policies.py -v
pytest tests/unit/test_tp_policies.py -v
pytest tests/unit/test_risk_config.py -v

# Run integration test for SC-001: Same signal, different configs
pytest tests/integration/test_risk_policy_switching.py -v

# Run full test suite to verify no regressions
pytest tests/ -v --ignore=tests/performance/
```

### Linting & Code Quality

```bash
# Run linters (Constitution X requirements)
poetry run black src/ tests/ --check
poetry run ruff check src/ tests/
poetry run pylint src/ --score=yes
```

### Manual Verification

1. **SC-002: Switch policies via CLI**

   - Run backtest with fixed ratio: `python -m src.cli.run_backtest --strategy trend_pullback --pair EURUSD --direction LONG --risk-pct 0.25 --stop-policy ATR --atr-mult 2.0 --tp-policy RiskMultiple --rr-ratio 3.0`
   - Run backtest with trailing stop: `python -m src.cli.run_backtest --strategy trend_pullback --pair EURUSD --direction LONG --risk-pct 0.25 --stop-policy ATR_Trailing --atr-mult 2.0 --tp-policy None`
   - Verify different trade outcomes in output

2. **SC-003: No strategy-to-risk imports**

   ```bash
   # Verify no imports from risk in strategy modules
   grep -r "from src.risk" src/strategy/
   grep -r "from ..risk" src/strategy/
   # Should return no results
   ```

3. **SC-005: Backtest metadata includes risk params**
   - Run any backtest and verify output includes `Risk Manager: <type> (params...)`

### Regression Protection

```bash
# Run full test suite after implementation to verify SC-004
pytest tests/ -v --ignore=tests/performance/

# Expected: All existing tests pass (no behavioral changes with default config)
```

## Complexity Tracking

No constitution violations—implementation uses straightforward Python patterns.
