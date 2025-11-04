"""Integration test: Net exposure aggregation.

Tests portfolio-level net exposure calculation across multiple strategies
with different instruments and directions per FR-013.

Validates:
- Long + short exposures net correctly
- Multiple instruments aggregated
- Weighted exposure calculation
- Zero net exposure scenarios
"""

# pylint: disable=unused-argument

import pytest
from src.backtest.orchestrator import BacktestOrchestrator
from src.models.enums import DirectionMode


def strategy_long_eurusd(candles):
    """Strategy with long EURUSD exposure."""
    return {
        "pnl": 50.0,
        "max_drawdown": 0.02,
        "exposure": {"EURUSD": 0.05},  # Long 5%
    }


def strategy_short_eurusd(candles):
    """Strategy with short EURUSD exposure."""
    return {
        "pnl": 30.0,
        "max_drawdown": 0.03,
        "exposure": {"EURUSD": -0.03},  # Short 3%
    }


def strategy_multi_instrument(candles):
    """Strategy with multiple instrument exposures."""
    return {
        "pnl": 75.0,
        "max_drawdown": 0.04,
        "exposure": {
            "EURUSD": 0.02,
            "USDJPY": 0.04,
            "GBPUSD": -0.01,
        },
    }


def test_net_exposure_long_short_offset():
    """
    Test net exposure with offsetting long/short positions.

    Setup:
    - Strategy A: Long EURUSD 0.05, weight 0.6 → 0.03
    - Strategy B: Short EURUSD -0.03, weight 0.4 → -0.012
    - Net EURUSD = 0.03 - 0.012 = 0.018
    """
    orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

    strategies = [
        ("long_eur", strategy_long_eurusd),
        ("short_eur", strategy_short_eurusd),
    ]
    candles_by_strategy = {"long_eur": [], "short_eur": []}
    weights = [0.6, 0.4]

    result = orchestrator.run_multi_strategy_full(
        strategies=strategies,
        candles_by_strategy=candles_by_strategy,
        weights=weights,
        run_id="test_net_exposure_001",
    )

    net_exposure = result["portfolio_summary"]["net_exposure_by_instrument"]

    # Long: 0.05 * 0.6 = 0.03
    # Short: -0.03 * 0.4 = -0.012
    # Net: 0.03 - 0.012 = 0.018
    expected_net = 0.05 * 0.6 + (-0.03) * 0.4
    assert net_exposure["EURUSD"] == pytest.approx(expected_net)


def test_net_exposure_multiple_instruments():
    """
    Test net exposure aggregation across multiple instruments.

    Setup:
    - Strategy A: Long EUR 0.05, weight 0.5 → 0.025
    - Strategy B: Multi (EUR 0.02, JPY 0.04, GBP -0.01), weight 0.5
      → EUR 0.01, JPY 0.02, GBP -0.005
    - Net: EUR 0.035, JPY 0.02, GBP -0.005
    """
    orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

    strategies = [
        ("long_eur", strategy_long_eurusd),
        ("multi", strategy_multi_instrument),
    ]
    candles_by_strategy = {"long_eur": [], "multi": []}
    weights = [0.5, 0.5]

    result = orchestrator.run_multi_strategy_full(
        strategies=strategies,
        candles_by_strategy=candles_by_strategy,
        weights=weights,
        run_id="test_multi_instrument_001",
    )

    net_exposure = result["portfolio_summary"]["net_exposure_by_instrument"]
    instruments_count = result["portfolio_summary"]["instruments_count"]

    # EURUSD: 0.05 * 0.5 + 0.02 * 0.5 = 0.025 + 0.01 = 0.035
    assert net_exposure["EURUSD"] == pytest.approx(0.035)
    # USDJPY: 0.04 * 0.5 = 0.02
    assert net_exposure["USDJPY"] == pytest.approx(0.02)
    # GBPUSD: -0.01 * 0.5 = -0.005
    assert net_exposure["GBPUSD"] == pytest.approx(-0.005)

    # Total 3 distinct instruments
    assert instruments_count == 3


def test_net_exposure_zero_net():
    """
    Test scenario where long and short positions fully offset.

    Setup:
    - Strategy A: Long EURUSD 0.04, weight 0.5 → 0.02
    - Strategy B: Short EURUSD -0.04, weight 0.5 → -0.02
    - Net EURUSD = 0.0 (perfect hedge)
    """

    def strat_long(candles):
        return {"pnl": 10, "exposure": {"EURUSD": 0.04}}

    def strat_short(candles):
        return {"pnl": 10, "exposure": {"EURUSD": -0.04}}

    orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

    strategies = [("long", strat_long), ("short", strat_short)]
    candles_by_strategy = {"long": [], "short": []}
    weights = [0.5, 0.5]

    result = orchestrator.run_multi_strategy_full(
        strategies=strategies,
        candles_by_strategy=candles_by_strategy,
        weights=weights,
        run_id="test_zero_net_001",
    )

    net_exposure = result["portfolio_summary"]["net_exposure_by_instrument"]

    # 0.04 * 0.5 + (-0.04) * 0.5 = 0.02 - 0.02 = 0.0
    assert net_exposure["EURUSD"] == pytest.approx(0.0, abs=1e-9)


def test_net_exposure_single_sided():
    """
    Test all strategies on same side (all long or all short).

    Setup:
    - Both strategies long EURUSD
    - Net exposure = sum of weighted exposures
    """

    def strat_a(candles):
        return {"pnl": 20, "exposure": {"EURUSD": 0.03}}

    def strat_b(candles):
        return {"pnl": 15, "exposure": {"EURUSD": 0.02}}

    orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

    strategies = [("a", strat_a), ("b", strat_b)]
    candles_by_strategy = {"a": [], "b": []}
    weights = [0.6, 0.4]

    result = orchestrator.run_multi_strategy_full(
        strategies=strategies,
        candles_by_strategy=candles_by_strategy,
        weights=weights,
        run_id="test_single_sided_001",
    )

    net_exposure = result["portfolio_summary"]["net_exposure_by_instrument"]

    # 0.03 * 0.6 + 0.02 * 0.4 = 0.018 + 0.008 = 0.026
    expected = 0.03 * 0.6 + 0.02 * 0.4
    assert net_exposure["EURUSD"] == pytest.approx(expected)


def test_net_exposure_structured_metrics():
    """
    Validate net exposure appears in structured metrics output.
    """
    orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

    strategies = [("multi", strategy_multi_instrument)]
    candles_by_strategy = {"multi": []}
    weights = [1.0]

    result = orchestrator.run_multi_strategy_full(
        strategies=strategies,
        candles_by_strategy=candles_by_strategy,
        weights=weights,
        run_id="test_metrics_001",
    )

    metrics = result["structured_metrics"]

    # With weight 1.0, net exposure = raw exposure
    assert metrics.net_exposure_by_instrument["EURUSD"] == pytest.approx(0.02)
    assert metrics.net_exposure_by_instrument["USDJPY"] == pytest.approx(0.04)
    assert metrics.net_exposure_by_instrument["GBPUSD"] == pytest.approx(-0.01)
