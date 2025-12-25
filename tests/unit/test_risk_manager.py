"""
Unit tests for RiskManager class.

Tests validate:
- build_orders creates valid OrderPlans
- Different configs produce different outputs (SC-001)
- Policy selection works correctly
"""

from datetime import UTC, datetime

import pytest

from src.models.signal import Signal
from src.risk.config import RiskConfig, StopPolicyConfig, TakeProfitPolicyConfig
from src.risk.manager import RiskManager


pytestmark = pytest.mark.unit


@pytest.fixture
def sample_signal():
    """Create a sample LONG signal for testing."""
    return Signal(
        symbol="EURUSD",
        direction="LONG",
        timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        entry_hint=1.1000,
        metadata={"strategy": "test"},
    )


@pytest.fixture
def sample_short_signal():
    """Create a sample SHORT signal for testing."""
    return Signal(
        symbol="EURUSD",
        direction="SHORT",
        timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        entry_hint=1.1000,
        metadata={"strategy": "test"},
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


class TestRiskManagerBuildOrders:
    """Test RiskManager.build_orders() method."""

    def test_build_orders_long_basic(self, sample_signal, market_context):
        """Build orders for LONG signal with default config."""
        config = RiskConfig()
        manager = RiskManager(config)

        order = manager.build_orders(
            sample_signal,
            portfolio_balance=10000.0,
            market_context=market_context,
        )

        assert order.signal == sample_signal
        assert order.entry_price == 1.1000
        # Stop should be below entry for LONG
        assert order.stop_price < order.entry_price
        # Target should be above entry for LONG with RiskMultiple
        assert order.target_price > order.entry_price
        assert order.position_size > 0

    def test_build_orders_short_basic(self, sample_short_signal, market_context):
        """Build orders for SHORT signal with default config."""
        config = RiskConfig()
        manager = RiskManager(config)

        order = manager.build_orders(
            sample_short_signal,
            portfolio_balance=10000.0,
            market_context=market_context,
        )

        # Stop should be above entry for SHORT
        assert order.stop_price > order.entry_price
        # Target should be below entry for SHORT with RiskMultiple
        assert order.target_price < order.entry_price


class TestDifferentConfigsProduceDifferentOutputs:
    """
    SC-001: Same signal produces different OrderPlans under different risk configs.
    """

    def test_different_risk_pct_different_position_size(
        self, sample_signal, market_context
    ):
        """Different risk_pct should produce different position sizes."""
        config_low = RiskConfig(risk_pct=0.25)
        config_high = RiskConfig(risk_pct=1.0)

        manager_low = RiskManager(config_low)
        manager_high = RiskManager(config_high)

        order_low = manager_low.build_orders(sample_signal, 10000.0, market_context)
        order_high = manager_high.build_orders(sample_signal, 10000.0, market_context)

        # Higher risk should produce larger position
        assert order_high.position_size > order_low.position_size

    def test_different_atr_mult_different_stops(self, sample_signal, market_context):
        """Different ATR multipliers should produce different stop distances."""
        config_tight = RiskConfig(stop_policy=StopPolicyConfig(multiplier=1.0))
        config_wide = RiskConfig(stop_policy=StopPolicyConfig(multiplier=3.0))

        manager_tight = RiskManager(config_tight)
        manager_wide = RiskManager(config_wide)

        order_tight = manager_tight.build_orders(sample_signal, 10000.0, market_context)
        order_wide = manager_wide.build_orders(sample_signal, 10000.0, market_context)

        # Tight stop should be closer to entry
        assert abs(order_tight.entry_price - order_tight.stop_price) < abs(
            order_wide.entry_price - order_wide.stop_price
        )

    def test_different_rr_ratio_different_targets(self, sample_signal, market_context):
        """Different RR ratios should produce different take-profit distances."""
        config_2r = RiskConfig(take_profit_policy=TakeProfitPolicyConfig(rr_ratio=2.0))
        config_5r = RiskConfig(take_profit_policy=TakeProfitPolicyConfig(rr_ratio=5.0))

        manager_2r = RiskManager(config_2r)
        manager_5r = RiskManager(config_5r)

        order_2r = manager_2r.build_orders(sample_signal, 10000.0, market_context)
        order_5r = manager_5r.build_orders(sample_signal, 10000.0, market_context)

        # 5R target should be further from entry
        assert abs(order_5r.target_price - order_5r.entry_price) > abs(
            order_2r.target_price - order_2r.entry_price
        )

    def test_no_tp_policy_returns_none_target(self, sample_signal, market_context):
        """TP policy 'None' should produce None target_price."""
        config = RiskConfig(take_profit_policy=TakeProfitPolicyConfig(type="None"))
        manager = RiskManager(config)

        order = manager.build_orders(sample_signal, 10000.0, market_context)

        assert order.target_price is None


class TestRiskManagerLabel:
    """Test RiskManager.get_label() method."""

    def test_get_label_default(self):
        """get_label should return descriptive string."""
        config = RiskConfig()
        manager = RiskManager(config)

        label = manager.get_label()

        assert "ATR" in label
        assert "0.25" in label


class TestRiskManagerErrors:
    """Test RiskManager error handling."""

    def test_missing_atr_raises_error(self, sample_signal):
        """ATR policy without ATR in context should raise error."""
        from src.risk.policies.stop_policies import RiskConfigurationError

        config = RiskConfig()
        manager = RiskManager(config)

        # Context without ATR
        context = {"close": 1.1000}

        with pytest.raises(RiskConfigurationError, match="requires ATR"):
            manager.build_orders(sample_signal, 10000.0, context)
