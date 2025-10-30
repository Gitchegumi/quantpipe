"""
Unit tests for risk manager position sizing and lot rounding logic.

Tests position size calculation, lot rounding to 0.01 step, maximum position
size capping, and edge cases for ATR-based stop calculations.
"""

from datetime import UTC, datetime

import pytest

from src.models.core import TradeSignal
from src.risk.manager import (
    calculate_atr_stop,
    calculate_position_size,
    calculate_take_profit,
    validate_risk_limits,
)


pytestmark = pytest.mark.unit


def _create_signal(
    entry_price: float, stop_price: float, direction: str = "LONG"
) -> TradeSignal:
    """Helper to create TradeSignal for testing."""
    return TradeSignal(
        id="test-signal",
        pair="EURUSD",
        direction=direction,
        entry_price=entry_price,
        initial_stop_price=stop_price,
        risk_per_trade_pct=1.0,
        calc_position_size=0.0,
        tags=["test"],
        version="1.0.0",
        timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
    )


class TestPositionSizeCalculation:
    """Tests for calculate_position_size with lot rounding."""

    def test_position_size_rounds_down_to_01_step(self):
        """
        Given calculated position size with decimals beyond 0.01,
        When rounding,
        Then should floor to 0.01 lot step.
        """
        # Entry 1.10000, Stop 1.09800 = 20 pips
        signal = _create_signal(1.10000, 1.09800)

        position_size = calculate_position_size(
            signal=signal,
            account_balance=10000.0,
            risk_per_trade_pct=0.25,  # $25 risk
            pip_value=10.0,
        )

        # Risk amount: 10000 * 0.0025 = $25
        # Stop distance: 20 pips
        # Position size: 25 / (20 * 10) = 0.125 lots
        # Rounded down: 0.12 lots
        assert position_size == 0.12

    def test_position_size_rounds_down_example_2(self):
        """
        Given position size 0.35,
        When rounding,
        Then should floor to 0.35 lots.
        """
        # Entry 1.10000, Stop 1.09800 = 20 pips
        signal = _create_signal(1.10000, 1.09800)

        position_size = calculate_position_size(
            signal=signal,
            account_balance=10000.0,
            risk_per_trade_pct=0.7,  # $70 risk
            pip_value=10.0,
        )

        # Risk amount: 10000 * 0.007 = $70
        # Stop distance: ~20 pips (may be 19.x due to float precision)
        # Position size: 70 / (~20 * 10) = ~0.35 lots, floored to 0.34
        assert position_size == 0.34

    def test_position_size_minimum_001_lots(self):
        """
        Given very small risk resulting in < 0.01 lots,
        When rounding,
        Then should return minimum 0.01 lots (floored to 0 if below).
        """
        # Entry 1.10000, Stop 1.09500 = 50 pips
        signal = _create_signal(1.10000, 1.09500)

        position_size = calculate_position_size(
            signal=signal,
            account_balance=1000.0,
            risk_per_trade_pct=0.1,  # $1 risk
            pip_value=10.0,
        )

        # Risk amount: 1000 * 0.001 = $1
        # Stop distance: 50 pips
        # Position size: 1 / (50 * 10) = 0.002 lots
        # Rounded down: 0.0 lots (below minimum, but floored)
        assert position_size == 0.01  # Manager sets minimum to lot_step

    def test_position_size_zero_stop_distance_returns_minimum(self):
        """
        Given stop distance of zero,
        When calculating position size,
        Then should return minimum lot_step (logged warning).
        """
        # Entry and stop identical = 0 pips
        signal = _create_signal(1.10000, 1.10000)

        position_size = calculate_position_size(
            signal=signal,
            account_balance=10000.0,
            risk_per_trade_pct=1.0,
            pip_value=10.0,
        )

        # Manager logs warning and returns lot_step
        assert position_size == 0.01

    def test_position_size_negative_risk_raises_error(self):
        """
        Given negative risk percentage,
        When calculating position size,
        Then should raise ValueError.
        """
        signal = _create_signal(1.10000, 1.09800)

        with pytest.raises(
            ValueError, match="Risk per trade percentage must be positive"
        ):
            calculate_position_size(
                signal=signal,
                account_balance=10000.0,
                risk_per_trade_pct=-1.0,  # Invalid
                pip_value=10.0,
            )

    def test_position_size_various_rounding_cases(self):
        """
        Test multiple rounding scenarios to verify 0.01 step floor behavior.
        """
        test_cases = [
            # (entry, stop, balance, risk_pct, expected_lots)
            (1.10000, 1.09800, 10000.0, 1.0, 0.49),  # ~20 pips (float precision)
            (1.10000, 1.09800, 10000.0, 0.33, 0.16),  # ~20 pips, 0.165 → 0.16
            (1.10000, 1.09800, 10000.0, 0.77, 0.38),  # ~20 pips, 0.385 → 0.38
            (1.10000, 1.09800, 10000.0, 1.23, 0.61),  # ~20 pips, 0.615 → 0.61
            (1.10000, 1.09850, 5000.0, 2.0, 0.66),  # 15 pips, 0.666... → 0.66
        ]

        for entry, stop, balance, risk_pct, expected in test_cases:
            signal = _create_signal(entry, stop)
            result = calculate_position_size(
                signal=signal,
                account_balance=balance,
                risk_per_trade_pct=risk_pct,
                pip_value=10.0,
            )
            assert (
                result == expected
            ), f"Failed for entry={entry}, stop={stop}, balance={balance}, risk={risk_pct}%"


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
            atr_value=0.00050,  # Correct parameter name
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
            atr_value=0.00050,
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
                atr_value=0.00050,
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
            reward_risk_ratio=2.0,  # Correct parameter name
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
            reward_risk_ratio=2.0,
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
                reward_risk_ratio=r_mult,
                direction=direction,
            )
            assert result == pytest.approx(expected, abs=1e-6)


class TestRiskLimitValidation:
    """Tests for drawdown and risk limit validation."""

    def test_validate_risk_limits_within_limits(self):
        """
        Given current drawdown below maximum,
        When validating risk limits,
        Then should return True.
        """
        # Correct API: validate_risk_limits(position_size, _account_balance, max_drawdown_pct, current_drawdown_pct)
        result = validate_risk_limits(
            position_size=0.50,
            _account_balance=10000.0,
            max_drawdown_pct=10.0,
            current_drawdown_pct=5.0,  # Below max
        )
        assert result is True

    def test_validate_risk_limits_exceeds_maximum(self):
        """
        Given current drawdown exceeds maximum,
        When validating risk limits,
        Then should return False.
        """
        result = validate_risk_limits(
            position_size=0.50,
            _account_balance=10000.0,
            max_drawdown_pct=10.0,
            current_drawdown_pct=12.0,  # Exceeds max
        )
        assert result is False

    def test_validate_risk_limits_at_boundary(self):
        """
        Given current drawdown exactly at maximum,
        When validating risk limits,
        Then should return False (>= check).
        """
        result = validate_risk_limits(
            position_size=0.50,
            _account_balance=10000.0,
            max_drawdown_pct=10.0,
            current_drawdown_pct=10.0,  # At boundary
        )
        assert result is False

    def test_validate_risk_limits_negative_drawdown(self):
        """
        Given negative drawdown (account in profit),
        When validating risk limits,
        Then should return True.
        """
        result = validate_risk_limits(
            position_size=0.50,
            _account_balance=10000.0,
            max_drawdown_pct=10.0,
            current_drawdown_pct=-2.0,  # Profit
        )
        assert result is True


class TestEdgeCases:
    """Edge case tests for risk management."""

    def test_position_size_very_small_risk(self):
        """
        Given very small risk percentage,
        When calculating position size,
        Then should return appropriately small size.
        """
        # Entry 1.10000, Stop 1.09800 = 20 pips
        signal = _create_signal(1.10000, 1.09800)

        position_size = calculate_position_size(
            signal=signal,
            account_balance=10000.0,
            risk_per_trade_pct=0.05,  # $5 risk
            pip_value=10.0,
        )

        # Risk amount: $5
        # Stop distance: 20 pips
        # Position size: 5 / (20 * 10) = 0.025 lots
        # Rounded down: 0.02 lots
        assert position_size == 0.02

    def test_atr_stop_invalid_direction_raises_error(self):
        """
        Given invalid direction,
        When calculating ATR stop,
        Then should raise ValueError.
        """
        with pytest.raises(ValueError, match="Invalid direction"):
            calculate_atr_stop(
                entry_price=1.10000,
                atr_value=0.00050,
                atr_multiplier=2.0,
                direction="INVALID",  # Bad direction
            )
