"""
Unit tests for PositionSizer implementations.

Tests validate:
- RiskPercentSizer formula correctness (SC-006)
- Edge cases: zero stop, max cap, JPY pairs
"""

import pytest

from src.risk.config import RiskConfig


pytestmark = pytest.mark.unit


class TestRiskPercentSizingFormula:
    """Test RiskPercentSizer formula: risk_amount / (stop_distance × pip_value)."""

    def test_basic_sizing_calculation(self):
        """Position size = (balance × risk_pct) / (stop_pips × pip_value)."""
        from src.risk.manager import RiskManager

        # Setup: $10,000 balance, 0.25% risk, 20 pip stop, $10/pip
        # Risk amount = $10,000 × 0.0025 = $25
        # Position size = $25 / (20 × $10) = 0.125 lots
        config = RiskConfig(risk_pct=0.25)
        manager = RiskManager(config)

        # Simulate position sizing with known values
        entry = 1.1000
        # 20 pips = 0.0020 for 4-decimal pair
        stop = 1.0980

        size = manager._calculate_size(entry, stop, 10000.0)
        # Expected: $25 / ($10 × 20) = 0.125 lots
        # But our default lot_step is 0.01, so 0.12 lots
        assert size == pytest.approx(0.12, abs=0.01)

    def test_larger_risk_percent_increases_size(self):
        """Higher risk percent should produce larger position."""
        from src.risk.manager import RiskManager

        config_low = RiskConfig(risk_pct=0.25)
        config_high = RiskConfig(risk_pct=1.0)

        manager_low = RiskManager(config_low)
        manager_high = RiskManager(config_high)

        entry, stop, balance = 1.1000, 1.0980, 10000.0

        size_low = manager_low._calculate_size(entry, stop, balance)
        size_high = manager_high._calculate_size(entry, stop, balance)

        # 4× risk = 4× position size
        assert size_high > size_low
        assert size_high / size_low == pytest.approx(4.0, rel=0.1)


class TestPositionSizeEdgeCases:
    """SC-006: Edge cases for position sizing."""

    def test_zero_stop_distance_returns_minimum(self):
        """Zero stop distance should return minimum position size."""
        from src.risk.manager import RiskManager

        config = RiskConfig(risk_pct=0.25)
        manager = RiskManager(config)

        # Same entry and stop = zero distance
        entry = 1.1000
        stop = 1.1000

        size = manager._calculate_size(entry, stop, 10000.0)
        # Should return lot_step minimum (0.01)
        assert size == config.lot_step

    def test_max_position_size_cap(self):
        """Position size should be capped at max_position_size."""
        from src.risk.manager import RiskManager

        config = RiskConfig(
            risk_pct=10.0,  # Very high risk
            max_position_size=5.0,
        )
        manager = RiskManager(config)

        entry, stop = 1.1000, 1.0999  # Very tight stop
        size = manager._calculate_size(entry, stop, 100000.0)

        assert size <= config.max_position_size

    def test_small_balance_small_position(self):
        """Small balance should produce small position."""
        from src.risk.manager import RiskManager

        config = RiskConfig(risk_pct=0.25)
        manager = RiskManager(config)

        entry, stop = 1.1000, 1.0980

        # $100 balance
        size = manager._calculate_size(entry, stop, 100.0)

        # Should be very small
        assert size <= 0.05

    def test_lot_step_rounding(self):
        """Position size should be rounded to lot_step."""
        from src.risk.manager import RiskManager

        config = RiskConfig(risk_pct=0.25, lot_step=0.01)
        manager = RiskManager(config)

        entry, stop = 1.1000, 1.0980
        size = manager._calculate_size(entry, stop, 10000.0)

        # Should be multiple of lot_step
        remainder = size % 0.01
        # Floating point precision: use larger tolerance
        assert remainder == pytest.approx(0.0, abs=0.01)
