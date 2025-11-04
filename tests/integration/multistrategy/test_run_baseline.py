"""Integration test: Multi-strategy baseline run.

Tests end-to-end multi-strategy execution with 2+ strategies producing
individual and aggregated outputs per US1 acceptance criteria.

Validates:
- Multiple strategies execute successfully
- Per-strategy results captured
- Portfolio aggregation computed
- Structured metrics generated
- RunManifest created with deterministic run ID
"""

# pylint: disable=unused-argument, unused-import

from datetime import datetime, UTC
import pytest
from src.backtest.orchestrator import BacktestOrchestrator
from src.models.enums import DirectionMode
from src.models.core import Candle


def dummy_strategy_alpha(candles):
    """Simple strategy returning fixed PnL and exposure."""
    return {
        "name": "alpha",
        "pnl": 100.0,
        "max_drawdown": 0.05,
        "exposure": {"EURUSD": 0.02},
    }


def dummy_strategy_beta(candles):
    """Simple strategy returning different PnL and exposure."""
    return {
        "name": "beta",
        "pnl": 50.0,
        "max_drawdown": 0.03,
        "exposure": {"EURUSD": -0.01, "USDJPY": 0.015},
    }


def test_multi_strategy_baseline_execution():
    """
    Test baseline multi-strategy run with 2 strategies.

    Validates:
    - Both strategies execute
    - Weighted PnL calculated correctly (0.6 * 100 + 0.4 * 50 = 80)
    - Net exposure aggregated
    - Structured metrics populated
    - Deterministic run ID generated
    """
    orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

    strategies = [
        ("alpha", dummy_strategy_alpha),
        ("beta", dummy_strategy_beta),
    ]

    # Empty candles for dummy strategies
    candles_by_strategy = {
        "alpha": [],
        "beta": [],
    }

    weights = [0.6, 0.4]

    result = orchestrator.run_multi_strategy_full(
        strategies=strategies,
        candles_by_strategy=candles_by_strategy,
        weights=weights,
        run_id="test_baseline_001",
        data_manifest_refs=["data/test_manifest.json"],
    )

    # Validate result structure
    assert "run_manifest" in result
    assert "structured_metrics" in result
    assert "per_strategy_results" in result
    assert "portfolio_summary" in result
    assert "deterministic_run_id" in result
    assert "manifest_hash" in result

    # Validate per-strategy results
    per_strategy = result["per_strategy_results"]
    assert len(per_strategy) == 2
    assert per_strategy[0]["name"] == "alpha"
    assert per_strategy[0]["pnl"] == 100.0
    assert per_strategy[1]["name"] == "beta"
    assert per_strategy[1]["pnl"] == 50.0

    # Validate portfolio aggregation
    portfolio = result["portfolio_summary"]
    expected_weighted_pnl = 0.6 * 100.0 + 0.4 * 50.0  # 80.0
    assert portfolio["weighted_pnl"] == pytest.approx(expected_weighted_pnl)
    assert portfolio["strategies_count"] == 2
    assert portfolio["instruments_count"] == 2  # EURUSD, USDJPY
    assert portfolio["weights_applied"] == [0.6, 0.4]

    # Validate net exposure aggregation
    net_exposure = portfolio["net_exposure_by_instrument"]
    # Alpha: 0.02 * 0.6 = 0.012, Beta: -0.01 * 0.4 = -0.004
    # Net EURUSD = 0.012 - 0.004 = 0.008
    assert net_exposure["EURUSD"] == pytest.approx(0.008)
    # USDJPY: 0.015 * 0.4 = 0.006
    assert net_exposure["USDJPY"] == pytest.approx(0.006)

    # Validate structured metrics
    metrics = result["structured_metrics"]
    assert metrics.strategies_count == 2
    assert metrics.instruments_count == 2
    assert metrics.aggregate_pnl == pytest.approx(80.0)
    assert metrics.weights_applied == [0.6, 0.4]
    assert metrics.global_abort_triggered is False
    assert len(metrics.risk_breaches) == 0
    assert len(metrics.deterministic_run_id) == 16  # Truncated hash

    # Validate RunManifest
    manifest = result["run_manifest"]
    assert manifest.run_id == "test_baseline_001"
    assert manifest.strategies == ["alpha", "beta"]
    assert manifest.weights == [0.6, 0.4]
    assert manifest.correlation_status == "deferred"
    assert manifest.global_abort_triggered is False
    assert len(manifest.deterministic_run_id) == 16


def test_multi_strategy_with_single_strategy():
    """Test multi-strategy framework with single strategy (edge case)."""
    orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

    strategies = [("alpha", dummy_strategy_alpha)]
    candles_by_strategy = {"alpha": []}
    weights = [1.0]

    result = orchestrator.run_multi_strategy_full(
        strategies=strategies,
        candles_by_strategy=candles_by_strategy,
        weights=weights,
        run_id="test_single_001",
    )

    # With single strategy and weight 1.0, weighted PnL = raw PnL
    portfolio = result["portfolio_summary"]
    assert portfolio["weighted_pnl"] == pytest.approx(100.0)
    assert portfolio["strategies_count"] == 1


def test_multi_strategy_with_equal_weights_fallback():
    """Test equal-weight fallback when invalid weights provided."""
    orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

    strategies = [
        ("alpha", dummy_strategy_alpha),
        ("beta", dummy_strategy_beta),
    ]
    candles_by_strategy = {"alpha": [], "beta": []}

    # Provide invalid weights (sum != 1.0)
    invalid_weights = [0.5, 0.6]  # sum = 1.1

    result = orchestrator.run_multi_strategy_full(
        strategies=strategies,
        candles_by_strategy=candles_by_strategy,
        weights=invalid_weights,
        run_id="test_fallback_001",
    )

    # Should fallback to equal weights [0.5, 0.5]
    portfolio = result["portfolio_summary"]
    assert portfolio["weights_applied"] == [0.5, 0.5]
    expected_pnl = 0.5 * 100.0 + 0.5 * 50.0  # 75.0
    assert portfolio["weighted_pnl"] == pytest.approx(expected_pnl)


def test_multi_strategy_determinism():
    """Test that identical inputs produce identical deterministic run IDs."""
    orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

    strategies = [("alpha", dummy_strategy_alpha)]
    candles_by_strategy = {"alpha": []}
    weights = [1.0]

    # Run 1
    result1 = orchestrator.run_multi_strategy_full(
        strategies=strategies,
        candles_by_strategy=candles_by_strategy,
        weights=weights,
        run_id="test_det_001",
        data_manifest_refs=["data/test.json"],
        config_params={"param1": 10},
        seed=42,
    )

    # Run 2 with identical inputs
    result2 = orchestrator.run_multi_strategy_full(
        strategies=strategies,
        candles_by_strategy=candles_by_strategy,
        weights=weights,
        run_id="test_det_002",  # Different user run_id
        data_manifest_refs=["data/test.json"],
        config_params={"param1": 10},
        seed=42,
    )

    # Deterministic run IDs should be identical despite different run_id
    assert result1["deterministic_run_id"] == result2["deterministic_run_id"]
    assert (
        result1["run_manifest"].deterministic_run_id
        == result2["run_manifest"].deterministic_run_id
    )
