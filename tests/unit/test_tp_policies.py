"""
Unit tests for TakeProfitPolicy implementations.

Tests validate:
- RiskMultipleTP calculation
- NoTakeProfit returns None
"""

from datetime import UTC, datetime

import pytest

from src.models.signal import Signal


pytestmark = pytest.mark.unit


@pytest.fixture
def long_signal():
    """Create a sample LONG signal."""
    return Signal(
        symbol="EURUSD",
        direction="LONG",
        timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        entry_hint=1.1000,
    )


class TestRiskMultipleTP:
    """Test RiskMultiple take-profit calculation."""

    def test_2r_target_for_long(self, long_signal):
        """2R target should be 2× risk distance above entry for LONG."""
        from src.risk.config import RiskConfig, TakeProfitPolicyConfig
        from src.risk.manager import RiskManager

        config = RiskConfig(
            take_profit_policy=TakeProfitPolicyConfig(type="RiskMultiple", rr_ratio=2.0)
        )
        manager = RiskManager(config)

        context = {"atr": 0.0020, "close": 1.1000}

        order = manager.build_orders(long_signal, 10000.0, context)

        # Stop at entry - 2*ATR = 1.0960 (risk = 0.0040)
        # Target at entry + 2*risk = 1.1080
        risk = abs(order.entry_price - order.stop_price)
        expected_target = order.entry_price + (risk * 2.0)

        assert order.target_price == pytest.approx(expected_target, abs=0.0001)

    def test_3r_target_further_than_2r(self, long_signal):
        """3R target should be 1.5× further than 2R target."""
        from src.risk.config import RiskConfig, TakeProfitPolicyConfig
        from src.risk.manager import RiskManager

        config_2r = RiskConfig(take_profit_policy=TakeProfitPolicyConfig(rr_ratio=2.0))
        config_3r = RiskConfig(take_profit_policy=TakeProfitPolicyConfig(rr_ratio=3.0))

        manager_2r = RiskManager(config_2r)
        manager_3r = RiskManager(config_3r)

        context = {"atr": 0.0020, "close": 1.1000}

        order_2r = manager_2r.build_orders(long_signal, 10000.0, context)
        order_3r = manager_3r.build_orders(long_signal, 10000.0, context)

        dist_2r = abs(order_2r.target_price - order_2r.entry_price)
        dist_3r = abs(order_3r.target_price - order_3r.entry_price)

        assert dist_3r / dist_2r == pytest.approx(1.5, rel=0.01)


class TestNoTakeProfit:
    """Test NoTakeProfit policy."""

    def test_no_tp_returns_none(self, long_signal):
        """NoTakeProfit policy should return None target."""
        from src.risk.config import RiskConfig, TakeProfitPolicyConfig
        from src.risk.manager import RiskManager

        config = RiskConfig(take_profit_policy=TakeProfitPolicyConfig(type="None"))
        manager = RiskManager(config)

        context = {"atr": 0.0020, "close": 1.1000}
        order = manager.build_orders(long_signal, 10000.0, context)

        assert order.target_price is None
