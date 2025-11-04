import pytest
from src.backtest.aggregation import PortfolioAggregator


def test_equal_weight_fallback_on_invalid_weights():
    aggregator = PortfolioAggregator()
    results = [
        {"name": "alpha", "pnl": 10.0},
        {"name": "beta", "pnl": -4.0},
        {"name": "gamma", "pnl": 6.0},
    ]
    # Provide mismatched weights to trigger fallback
    summary = aggregator.aggregate(results, [0.7, 0.3])
    assert summary["strategies_count"] == 3
    # Equal weights 1/3 each => weighted pnl = (10 -4 +6)/3 = 4.0
    assert abs(summary["weighted_pnl"] - 4.0) < 1e-9
    assert summary["weights_applied"] == [pytest.approx(1/3)] * 3  # type: ignore


def test_valid_weights_normalization():
    aggregator = PortfolioAggregator()
    results = [
        {"name": "alpha", "pnl": 10.0},
        {"name": "beta", "pnl": -4.0},
    ]
    weights = [0.6, 0.4]
    summary = aggregator.aggregate(results, weights)
    # Weighted pnl = 10*0.6 + (-4)*0.4 = 6 - 1.6 = 4.4
    assert abs(summary["weighted_pnl"] - 4.4) < 1e-9
    assert summary["weights_applied"] == weights
