import pytest


pytestmark = pytest.mark.unit
"""
Unit tests for risk manager position sizing and lot rounding logic.

Tests position size calculation, lot rounding to 0.01 step, maximum position
size capping, and edge cases for ATR-based stop calculations.
"""

import pytest

from src.models.exceptions import RiskLimitError
from src.risk.manager import (
    calculate_atr_stop,
    calculate_position_size,
    calculate_take_profit,
    validate_risk_limits,
)


class TestPositionSizeCalculation:
    """Tests for calculate_position_size with lot rounding."""

    def test_position_size_rounds_down_to_01_step(self):
        """
        Given calculated position size with decimals beyond 0.01,
        When rounding,
        Then should floor to 0.01 lot step.
        """
        position_size = calculate_position_size(
            account_balance=10000.0,
            risk_per_trade_pct=0.25,  # $25 risk
            stop_distance_pips=20.0,
            pip_value=10.0,
        )

        # Risk amount: 10000 * 0.0025 = $25
        # Position size: 25 / (20 * 10) = 0.125 lots
        # Rounded down: 0.12 lots
        assert position_size == 0.12

    def test_position_size_rounds_down_example_2(self):
        """
        Given position size 0.347,
        When rounding,
        Then should floor to 0.34 lots.
        """
        position_size = calculate_position_size(
            account_balance=10000.0,
            risk_per_trade_pct=0.7,  # $70 risk
            stop_distance_pips=20.0,
            pip_value=10.0,
        )

        # Risk amount: 10000 * 0.007 = $70
        # Position size: 70 / (20 * 10) = 0.35 lots
        # Rounded down: 0.35 lots
        assert position_size == 0.35

    def test_position_size_minimum_001_lots(self):
        """
        Given very small risk resulting in < 0.01 lots,
        When rounding,
        Then should return 0.01 minimum (or 0.0 if truly tiny).
        """
        position_size = calculate_position_size(
            account_balance=1000.0,
            risk_per_trade_pct=0.1,  # $1 risk
            stop_distance_pips=50.0,
            pip_value=10.0,
        )

        # Risk amount: 1000 * 0.001 = $1
        # Position size: 1 / (50 * 10) = 0.002 lots
        # Rounded down: 0.0 lots (below minimum)
        assert position_size == 0.0

    def test_position_size_zero_stop_distance_raises_error(self):
        """
        Given stop distance of zero,
        When calculating position size,
        Then should raise RiskLimitError.
        """
        with pytest.raises(RiskLimitError, match="Stop distance must be positive"):
            calculate_position_size(
                account_balance=10000.0,
                risk_per_trade_pct=1.0,
                stop_distance_pips=0.0,  # Invalid
                pip_value=10.0,
            )

    def test_position_size_negative_risk_raises_error(self):
        """
        Given negative risk percentage,
        When calculating position size,
        Then should raise RiskLimitError.
        """
        with pytest.raises(RiskLimitError, match="Risk percentage must be positive"):
            calculate_position_size(
                account_balance=10000.0,
                risk_per_trade_pct=-1.0,  # Invalid
                stop_distance_pips=20.0,
                pip_value=10.0,
            )

    def test_position_size_various_rounding_cases(self):
        """
        Test multiple rounding scenarios to verify 0.01 step floor behavior.
        """
        test_cases = [
            # (account, risk_pct, stop_pips, expected_lots)
            (10000.0, 1.0, 20.0, 0.5),  # 0.5 exact
            (10000.0, 0.33, 20.0, 0.16),  # 0.165 → 0.16
            (10000.0, 0.77, 20.0, 0.38),  # 0.385 → 0.38
            (10000.0, 1.23, 20.0, 0.61),  # 0.615 → 0.61
            (5000.0, 2.0, 15.0, 0.66),  # 0.666... → 0.66
        ]

        for balance, risk_pct, stop_pips, expected in test_cases:
            result = calculate_position_size(
                account_balance=balance,
                risk_per_trade_pct=risk_pct,
                stop_distance_pips=stop_pips,
                pip_value=10.0,
            )
            assert (
                result == expected
            ), f"Failed for {balance}, {risk_pct}%, {stop_pips} pips"


class TestATRStopCalculation:
    """Tests for ATR-based stop-loss price calculation."""

    def test_atr_stop_long_position(self):
        """
        Given long entry and ATR value,
        When calculating stop,
        Then should return entry - (ATR * multiplier).
        """
        stop_price = calculate_atr_stop(
            entry_price=1.10000,
            atr=0.00050,
            atr_multiplier=2.0,
            direction="LONG",
        )

        # Stop = 1.10000 - (0.00050 * 2.0) = 1.09900
        assert stop_price == pytest.approx(1.09900, abs=1e-6)

    def test_atr_stop_short_position(self):
        """
        Given short entry and ATR value,
        When calculating stop,
        Then should return entry + (ATR * multiplier).
        """
        stop_price = calculate_atr_stop(
            entry_price=1.10000,
            atr=0.00050,
            atr_multiplier=2.0,
            direction="SHORT",
        )

        # Stop = 1.10000 + (0.00050 * 2.0) = 1.10100
        assert stop_price == pytest.approx(1.10100, abs=1e-6)

    def test_atr_stop_different_multipliers(self):
        """
        Test ATR stop calculation with various multipliers.
        """
        test_cases = [
            # (multiplier, direction, expected_stop)
            (1.5, "LONG", 1.10000 - 0.00075),
            (2.5, "LONG", 1.10000 - 0.00125),
            (3.0, "LONG", 1.10000 - 0.00150),
            (1.5, "SHORT", 1.10000 + 0.00075),
            (2.5, "SHORT", 1.10000 + 0.00125),
        ]

        for multiplier, direction, expected in test_cases:
            result = calculate_atr_stop(
                entry_price=1.10000,
                atr=0.00050,
                atr_multiplier=multiplier,
                direction=direction,
            )
            assert result == pytest.approx(expected, abs=1e-6)


class TestTakeProfitCalculation:
    """Tests for R-multiple based take-profit calculation."""

    def test_take_profit_long_position_2r(self):
        """
        Given long position with 2R target,
        When calculating take-profit,
        Then should return entry + (stop_distance * 2).
        """
        target_price = calculate_take_profit(
            entry_price=1.10000,
            stop_loss_price=1.09900,  # 100 pips risk
            r_multiple=2.0,
            direction="LONG",
        )

        # Risk distance: 1.10000 - 1.09900 = 0.00100
        # Target: 1.10000 + (0.00100 * 2.0) = 1.10200
        assert target_price == pytest.approx(1.10200, abs=1e-6)

    def test_take_profit_short_position_2r(self):
        """
        Given short position with 2R target,
        When calculating take-profit,
        Then should return entry - (stop_distance * 2).
        """
        target_price = calculate_take_profit(
            entry_price=1.10000,
            stop_loss_price=1.10100,  # 100 pips risk
            r_multiple=2.0,
            direction="SHORT",
        )

        # Risk distance: 1.10100 - 1.10000 = 0.00100
        # Target: 1.10000 - (0.00100 * 2.0) = 1.09800
        assert target_price == pytest.approx(1.09800, abs=1e-6)

    def test_take_profit_various_r_multiples(self):
        """
        Test take-profit calculation with different R-multiples.
        """
        test_cases = [
            # (r_multiple, direction, expected_target)
            (1.0, "LONG", 1.10100),  # 1R
            (1.5, "LONG", 1.10150),  # 1.5R
            (3.0, "LONG", 1.10300),  # 3R
            (1.0, "SHORT", 1.09900),  # 1R
            (2.5, "SHORT", 1.09750),  # 2.5R
        ]

        for r_mult, direction, expected in test_cases:
            result = calculate_take_profit(
                entry_price=1.10000,
                stop_loss_price=1.09900 if direction == "LONG" else 1.10100,
                r_multiple=r_mult,
                direction=direction,
            )
            assert result == pytest.approx(expected, abs=1e-6)


class TestRiskLimitValidation:
    """Tests for drawdown and risk limit validation."""

    def test_validate_risk_limits_within_limits(self):
        """
        Given current drawdown below maximum,
        When validating risk limits,
        Then should not raise error.
        """
        # Should not raise
        validate_risk_limits(
            current_drawdown_r=5.0,
            max_drawdown_r=10.0,
        )

    def test_validate_risk_limits_exceeds_maximum(self):
        """
        Given current drawdown exceeds maximum,
        When validating risk limits,
        Then should raise RiskLimitError.
        """
        with pytest.raises(RiskLimitError, match="Maximum drawdown exceeded"):
            validate_risk_limits(
                current_drawdown_r=12.0,
                max_drawdown_r=10.0,
            )

    def test_validate_risk_limits_at_boundary(self):
        """
        Given current drawdown exactly at maximum,
        When validating risk limits,
        Then should raise RiskLimitError (not <=, just <).
        """
        with pytest.raises(RiskLimitError, match="Maximum drawdown exceeded"):
            validate_risk_limits(
                current_drawdown_r=10.0,
                max_drawdown_r=10.0,
            )

    def test_validate_risk_limits_negative_drawdown(self):
        """
        Given negative drawdown (account in profit),
        When validating risk limits,
        Then should not raise error.
        """
        # Negative drawdown means account above peak (shouldn't happen but valid)
        validate_risk_limits(
            current_drawdown_r=-2.0,
            max_drawdown_r=10.0,
        )


class TestEdgeCases:
    """Edge case tests for risk management."""

    def test_position_size_very_small_risk(self):
        """
        Given very small risk percentage,
        When calculating position size,
        Then should return appropriately small size.
        """
        position_size = calculate_position_size(
            account_balance=10000.0,
            risk_per_trade_pct=0.05,  # $5 risk
            stop_distance_pips=20.0,
            pip_value=10.0,
        )

        # Risk amount: $5
        # Position size: 5 / (20 * 10) = 0.025 lots
        # Rounded down: 0.02 lots
        assert position_size == 0.02

    def test_atr_stop_zero_atr_raises_error(self):
        """
        Given ATR of zero,
        When calculating stop,
        Then should raise RiskLimitError.
        """
        with pytest.raises(RiskLimitError, match="ATR must be positive"):
            calculate_atr_stop(
                entry_price=1.10000,
                atr=0.0,  # Invalid
                atr_multiplier=2.0,
                direction="LONG",
            )
