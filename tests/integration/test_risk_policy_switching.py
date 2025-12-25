"""
Integration tests for risk policy switching via CLI.

Tests validate:
- SC-002: Policy switching via config/CLI without code changes
- Different policies produce distinct trade lifecycles
"""

from datetime import UTC, datetime

import pytest

from src.models.signal import Signal
from src.risk.config import RiskConfig, StopPolicyConfig, TakeProfitPolicyConfig
from src.risk.manager import RiskManager


pytestmark = pytest.mark.integration


@pytest.fixture
def sample_signal():
    """Create a sample LONG signal for testing."""
    return Signal(
        symbol="EURUSD",
        direction="LONG",
        timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        entry_hint=1.1000,
    )


@pytest.fixture
def market_context():
    """Create sample market context with ATR."""
    return {
        "close": 1.1000,
        "high": 1.1050,
        "low": 1.0950,
        "atr": 0.0020,  # 20 pips
        "symbol": "EURUSD",
    }


class TestPolicySwitchingViaCLI:
    """
    SC-002: Users can switch between policies via config/CLI without code changes.
    """

    def test_switch_from_fixed_to_trailing_stop(self, sample_signal, market_context):
        """
        Switching from fixed ATR stop to trailing stop should be config-only change.
        """
        # Fixed ATR stop config
        config_fixed = RiskConfig(
            stop_policy=StopPolicyConfig(type="ATR", multiplier=2.0)
        )

        # Trailing ATR stop config
        config_trailing = RiskConfig(
            stop_policy=StopPolicyConfig(type="ATR_Trailing", multiplier=2.0)
        )

        manager_fixed = RiskManager(config_fixed)
        manager_trailing = RiskManager(config_trailing)

        order_fixed = manager_fixed.build_orders(sample_signal, 10000.0, market_context)
        order_trailing = manager_trailing.build_orders(
            sample_signal, 10000.0, market_context
        )

        # Both should have same stop price initially
        assert order_fixed.stop_price == order_trailing.stop_price

        # But trailing should be marked as trailing
        assert order_fixed.is_trailing is False
        assert order_trailing.is_trailing is True

    def test_switch_rr_ratio_via_config(self, sample_signal, market_context):
        """
        Switching R:R ratio should be config-only change.
        """
        config_2r = RiskConfig(
            take_profit_policy=TakeProfitPolicyConfig(type="RiskMultiple", rr_ratio=2.0)
        )
        config_3r = RiskConfig(
            take_profit_policy=TakeProfitPolicyConfig(type="RiskMultiple", rr_ratio=3.0)
        )

        manager_2r = RiskManager(config_2r)
        manager_3r = RiskManager(config_3r)

        order_2r = manager_2r.build_orders(sample_signal, 10000.0, market_context)
        order_3r = manager_3r.build_orders(sample_signal, 10000.0, market_context)

        # 3R target should be 1.5x further than 2R target
        dist_2r = abs(order_2r.target_price - order_2r.entry_price)
        dist_3r = abs(order_3r.target_price - order_3r.entry_price)
        assert dist_3r == pytest.approx(dist_2r * 1.5, rel=0.01)

    def test_switch_to_no_take_profit(self, sample_signal, market_context):
        """
        Switching to no take-profit (trail-only) should be config-only change.
        """
        config_with_tp = RiskConfig(
            take_profit_policy=TakeProfitPolicyConfig(type="RiskMultiple", rr_ratio=2.0)
        )
        config_no_tp = RiskConfig(
            take_profit_policy=TakeProfitPolicyConfig(type="None")
        )

        manager_with_tp = RiskManager(config_with_tp)
        manager_no_tp = RiskManager(config_no_tp)

        order_with_tp = manager_with_tp.build_orders(
            sample_signal, 10000.0, market_context
        )
        order_no_tp = manager_no_tp.build_orders(sample_signal, 10000.0, market_context)

        assert order_with_tp.target_price is not None
        assert order_no_tp.target_price is None

    def test_config_from_json_dict(self, sample_signal, market_context):
        """
        Config should be loadable from JSON-like dict (simulating CLI).
        """
        # Simulate JSON config that would come from --risk-config file
        json_config = {
            "risk_pct": 0.5,
            "stop_policy": {"type": "ATR", "multiplier": 1.5},
            "take_profit_policy": {"type": "RiskMultiple", "rr_ratio": 4.0},
        }

        config = RiskConfig.from_dict(json_config)
        manager = RiskManager(config)

        order = manager.build_orders(sample_signal, 10000.0, market_context)

        # Verify custom config was applied
        assert order.stop_policy_type == "ATR"
        # Stop should use 1.5x ATR (0.0020 * 1.5 = 0.003)
        expected_stop = 1.1000 - (0.0020 * 1.5)
        assert order.stop_price == pytest.approx(expected_stop, abs=0.00001)


class TestPolicyLifecycles:
    """Test that different policies produce distinct trade lifecycles."""

    def test_fixed_ratio_lifecycle(self, sample_signal, market_context):
        """Fixed ratio policy: exit at fixed TP or fixed SL."""
        config = RiskConfig(
            stop_policy=StopPolicyConfig(type="ATR", multiplier=2.0),
            take_profit_policy=TakeProfitPolicyConfig(
                type="RiskMultiple", rr_ratio=2.0
            ),
        )
        manager = RiskManager(config)

        order = manager.build_orders(sample_signal, 10000.0, market_context)

        # Should have fixed stop and target
        assert order.is_trailing is False
        assert order.target_price is not None
        # R:R should be 2:1
        assert order.risk_reward_ratio == pytest.approx(2.0, rel=0.01)

    def test_trailing_only_lifecycle(self, sample_signal, market_context):
        """Trailing-only policy: exit only at trailing stop."""
        config = RiskConfig(
            stop_policy=StopPolicyConfig(type="ATR_Trailing", multiplier=2.0),
            take_profit_policy=TakeProfitPolicyConfig(type="None"),
        )
        manager = RiskManager(config)

        order = manager.build_orders(sample_signal, 10000.0, market_context)

        # Should have trailing stop and no target
        assert order.is_trailing is True
        assert order.target_price is None
        assert len(order.trailing_params) > 0
