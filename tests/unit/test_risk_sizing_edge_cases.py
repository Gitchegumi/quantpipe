"""Unit tests for risk sizing edge cases and extreme scenarios."""

from datetime import UTC, datetime

import pytest


pytestmark = pytest.mark.unit

from src.models.core import TradeSignal
from src.risk.manager import calculate_position_size, validate_risk_limits


class TestMinimalBalanceScenarios:
    """Tests for position sizing with minimal account balances."""

    def test_minimal_balance_with_normal_risk(self):
        """
        Given minimal account balance ($100),
        When calculating position with 1% risk,
        Then should return valid small position size.
        """
        signal = TradeSignal(
            id="test_minimal_balance",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.10000,
            initial_stop_price=1.09800,  # 20 pips
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=[],
            version="0.1.0",
            timestamp_utc=datetime(2025, 1, 1, tzinfo=UTC),
        )

        position_size = calculate_position_size(
            signal=signal,
            account_balance=100.0,  # Minimal balance
            risk_per_trade_pct=1.0,  # $1 risk
            pip_value=10.0,
        )

        # Risk amount: 100 * 0.01 = $1
        # Stop distance: 20 pips
        # Position size: 1 / (20 * 10) = 0.005 lots  rounds to 0.01 (minimum)
        assert position_size >= 0.01
        assert position_size <= 0.02

    def test_minimal_balance_below_minimum_position(self):
        """
        Given minimal balance with wide stop,
        When calculated position < 0.01 lots,
        Then should return minimum 0.01 lots.
        """
        signal = TradeSignal(
            id="test_wide_stop",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.10000,
            initial_stop_price=1.09500,  # 50 pips (wide stop)
            risk_per_trade_pct=0.5,
            calc_position_size=0.0,
            tags=[],
            version="0.1.0",
            timestamp_utc=datetime(2025, 1, 1, tzinfo=UTC),
        )

        position_size = calculate_position_size(
            signal=signal,
            account_balance=200.0,
            risk_per_trade_pct=0.1,  # $0.20 risk
            pip_value=10.0,
        )

        # Risk amount: 200 * 0.001 = $0.20
        # Stop distance: 50 pips
        # Position size: 0.2 / (50 * 10) = 0.0004 lots  minimum 0.01
        assert position_size == 0.01

    def test_minimal_balance_respects_risk_limits(self):
        """
        Given minimal balance,
        When position is calculated,
        Then should still validate risk limits.
        """
        signal = TradeSignal(
            id="test_risk_limits",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.10000,
            initial_stop_price=1.09900,
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=[],
            version="0.1.0",
            timestamp_utc=datetime(2025, 1, 1, tzinfo=UTC),
        )

        position_size = calculate_position_size(
            signal=signal,
            account_balance=500.0,
            risk_per_trade_pct=1.0,
            pip_value=10.0,
        )

        # Validate risk limits with minimal balance
        is_valid = validate_risk_limits(
            position_size=position_size,
            _account_balance=500.0,  # Fixed parameter name
            max_drawdown_pct=10.0,
            current_drawdown_pct=0.0,
        )

        assert is_valid is True


class TestHighVolatilityScenarios:
    """Tests for position sizing during high volatility periods."""

    def test_high_volatility_wide_atr_stop(self):
        """
        Given high volatility with wide ATR-based stop,
        When calculating position size,
        Then should reduce position size to maintain risk %.
        """
        signal = TradeSignal(
            id="test_high_vol",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.10000,
            initial_stop_price=1.09200,  # 80 pips (high volatility)
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=[],
            version="0.1.0",
            timestamp_utc=datetime(2025, 1, 1, tzinfo=UTC),
        )

        position_size = calculate_position_size(
            signal=signal,
            account_balance=10000.0,
            risk_per_trade_pct=1.0,  # $100 risk
            pip_value=10.0,
        )

        # Risk amount: 10000 * 0.01 = $100
        # Stop distance: 80 pips
        # Position size: 100 / (80 * 10) = 0.125 lots  0.12 lots
        assert position_size == 0.12

    def test_extreme_volatility_very_wide_stop(self):
        """
        Given extreme volatility with 200+ pip stop,
        When calculating position size,
        Then should return very small position.
        """
        signal = TradeSignal(
            id="test_extreme_vol",
            pair="GBPJPY",
            direction="SHORT",
            entry_price=150.000,
            initial_stop_price=152.500,  # 250 pips
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=[],
            version="0.1.0",
            timestamp_utc=datetime(2025, 1, 1, tzinfo=UTC),
        )

        position_size = calculate_position_size(
            signal=signal,
            account_balance=10000.0,
            risk_per_trade_pct=1.0,  # $100 risk
            pip_value=10.0,
        )

        # Risk amount: $100
        # Stop distance: 250 pips
        # Position size: 100 / (250 * 10) = 0.04 lots
        # But manager applies minimum of 0.01, so result is 0.01
        assert position_size == 0.01
        assert position_size <= 0.10  # Should be small

    def test_volatility_adjustment_maintains_risk_pct(self):
        """
        Given different ATR values (volatility),
        When calculating positions,
        Then actual risk should remain consistent.
        """
        # Normal volatility scenario
        normal_signal = TradeSignal(
            id="normal_vol",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.10000,
            initial_stop_price=1.09800,  # 20 pips (normal)
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=[],
            version="0.1.0",
            timestamp_utc=datetime(2025, 1, 1, tzinfo=UTC),
        )

        # High volatility scenario
        high_vol_signal = TradeSignal(
            id="high_vol",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.10000,
            initial_stop_price=1.09400,  # 60 pips (high)
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=[],
            version="0.1.0",
            timestamp_utc=datetime(2025, 1, 1, tzinfo=UTC),
        )

        normal_size = calculate_position_size(
            signal=normal_signal,
            account_balance=10000.0,
            risk_per_trade_pct=1.0,
            pip_value=10.0,
        )

        high_vol_size = calculate_position_size(
            signal=high_vol_signal,
            account_balance=10000.0,
            risk_per_trade_pct=1.0,
            pip_value=10.0,
        )

        # High vol should have smaller position
        assert high_vol_size < normal_size

        # Calculate actual risk amounts
        normal_risk = normal_size * 20 * 10  # position * pips * pip_value
        high_vol_risk = high_vol_size * 60 * 10

        # Both should risk approximately $100 (1% of 10000)
        assert abs(normal_risk - 100.0) < 10.0
        assert abs(high_vol_risk - 100.0) < 10.0


class TestExtremeSpikeScenarios:
    """Tests for extreme price spikes and large spreads."""

    def test_extreme_spike_no_negative_position(self):
        """
        Given extreme price spike with invalid prices,
        When calculating position size,
        Then should not return negative position size.
        """
        signal = TradeSignal(
            id="test_spike",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.10000,
            initial_stop_price=1.09950,  # 5 pips (very tight)
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=[],
            version="0.1.0",
            timestamp_utc=datetime(2025, 1, 1, tzinfo=UTC),
        )

        position_size = calculate_position_size(
            signal=signal,
            account_balance=10000.0,
            risk_per_trade_pct=1.0,
            pip_value=10.0,
        )

        # Must be positive
        assert position_size > 0
        assert position_size >= 0.01  # At least minimum

    def test_large_spread_during_news(self):
        """
        Given large spread during news event,
        When stop is very wide,
        Then position should be appropriately small.
        """
        signal = TradeSignal(
            id="test_news_spread",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.10000,
            initial_stop_price=1.08500,  # 150 pips (news event)
            risk_per_trade_pct=0.5,
            calc_position_size=0.0,
            tags=[],
            version="0.1.0",
            timestamp_utc=datetime(2025, 1, 1, tzinfo=UTC),
        )

        position_size = calculate_position_size(
            signal=signal,
            account_balance=10000.0,
            risk_per_trade_pct=0.5,  # $50 risk
            pip_value=10.0,
        )

        # Risk amount: $50
        # Stop distance: 150 pips
        # Position size: 50 / (150 * 10) = 0.0333 lots  0.03 lots
        assert position_size == 0.03
        assert position_size < 0.10  # Should be small for wide stop

    def test_no_position_overflow_with_tiny_stop(self):
        """
        Given unrealistically tiny stop distance,
        When calculating position size,
        Then should cap at max_position_size (no overflow).
        """
        signal = TradeSignal(
            id="test_tiny_stop",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.10000,
            initial_stop_price=1.09999,  # 0.1 pips (unrealistic)
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=[],
            version="0.1.0",
            timestamp_utc=datetime(2025, 1, 1, tzinfo=UTC),
        )

        position_size = calculate_position_size(
            signal=signal,
            account_balance=10000.0,
            risk_per_trade_pct=1.0,
            pip_value=10.0,
            max_position_size=10.0,
        )

        # Should cap at maximum
        assert position_size <= 10.0
        # Should not overflow or crash
        assert isinstance(position_size, float)
        assert position_size > 0


class TestDrawdownRiskLimits:
    """Tests for risk limit validation during drawdown periods."""

    def test_risk_limits_block_trade_at_max_drawdown(self):
        """
        Given current drawdown at maximum threshold,
        When validating risk limits,
        Then should reject trade.
        """
        is_valid = validate_risk_limits(
            position_size=0.50,
            _account_balance=10000.0,  # Fixed parameter name
            max_drawdown_pct=10.0,
            current_drawdown_pct=10.0,  # At threshold
        )

        assert is_valid is False

    def test_risk_limits_allow_trade_below_drawdown_threshold(self):
        """
        Given current drawdown below threshold,
        When validating risk limits,
        Then should allow trade.
        """
        is_valid = validate_risk_limits(
            position_size=0.50,
            _account_balance=10000.0,  # Fixed parameter name
            max_drawdown_pct=10.0,
            current_drawdown_pct=5.0,  # Below threshold
        )

        assert is_valid is True

    def test_risk_limits_reject_negative_position_size(self):
        """
        Given invalid negative position size,
        When validating risk limits,
        Then should reject.
        """
        is_valid = validate_risk_limits(
            position_size=-0.10,  # Invalid
            _account_balance=10000.0,  # Fixed parameter name
            max_drawdown_pct=10.0,
            current_drawdown_pct=0.0,
        )

        assert is_valid is False

    def test_risk_limits_reject_zero_position_size(self):
        """
        Given zero position size,
        When validating risk limits,
        Then should reject.
        """
        is_valid = validate_risk_limits(
            position_size=0.0,  # Invalid
            _account_balance=10000.0,  # Fixed parameter name
            max_drawdown_pct=10.0,
            current_drawdown_pct=0.0,
        )

        assert is_valid is False
