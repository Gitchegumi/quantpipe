"""Integration test: Multi-strategy selection subset.

Tests US3 acceptance criteria:
- Select subset of registered strategies
- Run only selected strategies
- Verify only selected strategies produce outputs

Validates FR-004 (CLI selection by name/tag).
"""

# pylint: disable=unused-argument, unused-variable

import pytest
from src.strategy.registry import StrategyRegistry
from src.backtest.orchestrator import BacktestOrchestrator
from src.backtest.validation import validate_pre_run, ValidationError
from src.models.enums import DirectionMode


def test_registry_filter_subset_by_names():
    """
    Test registry filtering selects correct subset by names.

    Given 5 registered strategies, when operator selects 2 via filter,
    then only those 2 are returned.
    """
    registry = StrategyRegistry()

    def dummy_strategy(candles):
        return {"pnl": 100.0, "max_drawdown": 0.05, "exposure": {}}

    # Register 5 strategies
    for name in ["alpha", "beta", "gamma", "delta", "epsilon"]:
        registry.register(name, dummy_strategy, tags=["test"])

    # Select subset
    selected = registry.filter(names=["alpha", "gamma"])

    assert len(selected) == 2
    names = [s.name for s in selected]
    assert "alpha" in names
    assert "gamma" in names
    assert "beta" not in names


def test_registry_filter_by_tags():
    """
    Test filtering strategies by tag.

    Validates FR-004: CLI selection by tag filters.
    """
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("trend_a", dummy, tags=["trend", "pullback"])
    registry.register("trend_b", dummy, tags=["trend", "breakout"])
    registry.register("momentum_a", dummy, tags=["momentum"])
    registry.register("mean_revert", dummy, tags=["mean-reversion"])

    # Filter by tag "trend"
    trend_strategies = registry.filter(tags=["trend"])

    assert len(trend_strategies) == 2
    names = [s.name for s in trend_strategies]
    assert "trend_a" in names
    assert "trend_b" in names


def test_multi_strategy_run_with_subset():
    """
    Test multi-strategy execution with selected subset.

    Validates that only selected strategies execute and produce results.
    """

    def strategy_alpha(candles):
        return {
            "pnl": 100.0,
            "max_drawdown": 0.05,
            "exposure": {"EURUSD": 0.02},
        }

    def strategy_beta(candles):
        return {
            "pnl": 50.0,
            "max_drawdown": 0.03,
            "exposure": {"EURUSD": -0.01},
        }

    def strategy_gamma(candles):
        # This strategy should NOT execute
        return {
            "pnl": 200.0,
            "max_drawdown": 0.10,
            "exposure": {"EURUSD": 0.05},
        }

    orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

    # Execute only alpha and beta (not gamma)
    strategies = [
        ("alpha", strategy_alpha),
        ("beta", strategy_beta),
    ]

    candles_by_strategy = {"alpha": [], "beta": []}
    weights = [0.6, 0.4]

    result = orchestrator.run_multi_strategy_full(
        strategies=strategies,
        candles_by_strategy=candles_by_strategy,
        weights=weights,
        run_id="subset_test_001",
    )

    # Verify only 2 strategies executed
    assert result["portfolio_summary"]["strategies_count"] == 2
    assert len(result["per_strategy_results"]) == 2

    # Verify weighted PnL excludes gamma
    expected_pnl = 100.0 * 0.6 + 50.0 * 0.4  # 80.0
    assert result["portfolio_summary"]["weighted_pnl"] == pytest.approx(expected_pnl)


def test_validation_catches_unknown_strategies():
    """
    Test that validation catches selection of unregistered strategies.

    Validates FR-011: Fail fast on unknown strategies.
    """
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy)
    registry.register("beta", dummy)

    # Try to select unknown strategy
    with pytest.raises(ValidationError, match="Unknown strategies"):
        validate_pre_run(
            selected_strategies=["alpha", "gamma"],  # gamma not registered
            registry=registry,
        )


def test_validation_passes_for_valid_selection():
    """
    Test that validation passes for valid strategy selection.
    """
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy)
    registry.register("beta", dummy)
    registry.register("gamma", dummy)

    # Validate subset selection
    validate_pre_run(
        selected_strategies=["alpha", "beta"],
        registry=registry,
        weights=[0.5, 0.5],
    )  # Should not raise


def test_empty_strategy_selection_raises_error():
    """
    Test that selecting no strategies raises validation error.
    """
    registry = StrategyRegistry()

    with pytest.raises(ValidationError, match="No strategies selected"):
        validate_pre_run(
            selected_strategies=[],
            registry=registry,
        )


def test_filter_combined_names_and_tags():
    """
    Test filtering with both name and tag criteria.

    Validates combined filtering logic.
    """
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy, tags=["trend"])
    registry.register("beta", dummy, tags=["trend"])
    registry.register("gamma", dummy, tags=["momentum"])
    registry.register("delta", dummy, tags=["trend"])

    # Select strategies with name in [alpha, beta, delta] AND tag "trend"
    filtered = registry.filter(names=["alpha", "beta", "delta"], tags=["trend"])

    assert len(filtered) == 3
    names = [s.name for s in filtered]
    assert "alpha" in names
    assert "beta" in names
    assert "delta" in names


def test_multi_strategy_subset_maintains_isolation():
    """
    Test that running subset maintains state isolation.

    Validates FR-003: Per-strategy state isolation.
    """

    def profitable_strategy(candles):
        return {"pnl": 100.0, "max_drawdown": 0.02, "exposure": {}}

    def losing_strategy(candles):
        return {"pnl": -50.0, "max_drawdown": 0.08, "exposure": {}}

    orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

    strategies = [
        ("profitable", profitable_strategy),
        ("losing", losing_strategy),
    ]

    candles_by_strategy = {"profitable": [], "losing": []}
    weights = [0.7, 0.3]

    result = orchestrator.run_multi_strategy_full(
        strategies=strategies,
        candles_by_strategy=candles_by_strategy,
        weights=weights,
        run_id="isolation_test_001",
    )

    # Verify individual results maintained
    assert len(result["per_strategy_results"]) == 2

    # Profitable strategy PnL
    profitable_result = next(
        r for r in result["per_strategy_results"] if r["name"] == "profitable"
    )
    assert profitable_result["pnl"] == 100.0

    # Losing strategy PnL
    losing_result = next(
        r for r in result["per_strategy_results"] if r["name"] == "losing"
    )
    assert losing_result["pnl"] == -50.0

    # Aggregated PnL combines both
    expected_portfolio = 100.0 * 0.7 + (-50.0) * 0.3  # 55.0
    assert result["portfolio_summary"]["weighted_pnl"] == pytest.approx(
        expected_portfolio
    )
