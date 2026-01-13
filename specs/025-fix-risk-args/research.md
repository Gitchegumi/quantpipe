# Research: Fix Risk Argument Mapping

**Objective**: Verify implementation details for mapping `run_backtest.py` CLI args to `StrategyParameters` and `StrategyParameters` schema updates.

## Decision 1: Mapping `max_position_size`

**Context**: The `max-position-size` CLI arg (default 10.0 lots) currently has no home in `StrategyParameters`.
**Findings**:

- `StrategyParameters` has `max_pair_exposure` (int) which is a count limit.
- `RiskConfig` has `max_position_size` (float), but `RiskConfig` is not consistently used across the pipeline for this purpose (primary param carrier is `StrategyParameters` for the strategy logic).
- `run_backtest.py` creates `RiskConfig` but `run_portfolio_backtest` relies primarily on `StrategyParameters`.

**Decision**: Add `max_position_size` (float) to `StrategyParameters` in `src/config/parameters.py`.
**Rationale**: `StrategyParameters` is the central configuration object passed to the strategy. Adding it there ensures the strategy has access to this limit during signal generation/execution.
**Alternatives Considered**:

- Use `RiskConfig`: Would require refactoring `run_portfolio_backtest` and `BatchSimulation` to accept and prioritize `RiskConfig` over `StrategyParameters` or merge them. This is a larger scope refactor. Adding one field to `StrategyParameters` is cleaner for this specific fix.

## Decision 2: CLI Argument Precedence

**Context**: Need to ensure CLI args override `config.yaml` values.
**Findings**: `run_backtest.py` already logic for `timeframe` and `direction`.
**Decision**: Extend the override logic in `run_backtest.py` to check if args are non-default (or explicitly passed) and overwrite the `StrategyParameters` (or `config` dict) values.
**Rationale**: Standard CLI behavior.

## Decision 3: Logging

**Context**: FR-006 requires logging active params.
**Decision**: Add info logs in `run_backtest.py` just before calling `run_portfolio_backtest` dumping the final risk parameters.
