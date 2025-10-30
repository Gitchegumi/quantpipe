"""
Unit tests for risk sizing under high volatility conditions (T024).

This module tests position sizing behavior when ATR values are elevated,
representing high-volatility market environments. Tests verify that:

1. Position sizes decrease appropriately with larger ATR-based stops
2. Max position size constraints are enforced
3. Risk per trade limits are respected even with wide stops
4. Calculations remain deterministic under volatile conditions

All tests use realistic high-volatility scenarios with tight tolerances.
"""

from datetime import UTC, datetime

import pytest

from src.models.core import TradeSignal
from src.risk.manager import calculate_position_size


pytestmark = pytest.mark.unit


class TestRiskSizingVolatility:
    """Test position sizing under high volatility conditions."""

    def test_position_size_with_high_atr_stop(self):
        """
        T024: Verify position size decreases with high ATR-based stops.

        Given: Large stop distance due to high ATR
        When: Calculating position size
        Then: Position size should be smaller than normal volatility case.
        """
        # Normal volatility: 50 pip stop
        normal_signal = TradeSignal(
            id="test-volatility-001",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0950,  # 50 pips
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )
        normal_size = calculate_position_size(normal_signal, 10000.0, 1.0, 10.0)

        # High volatility: 150 pip stop (3x ATR)
        volatile_signal = TradeSignal(
            id="test-volatility-002",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0850,  # 150 pips
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )
        volatile_size = calculate_position_size(volatile_signal, 10000.0, 1.0, 10.0)

        # High volatility should produce significantly smaller position size
        assert volatile_size < normal_size, "High ATR stop should reduce position size"
        assert volatile_size == pytest.approx(
            normal_size / 3, abs=0.02
        ), "150 pip stop should be ~1/3 size of 50 pip stop"

    def test_position_size_with_extreme_volatility(self):
        """
        T024: Verify handling of extreme volatility scenarios.

        Given: Very large stop distance (>200 pips)
        When: Calculating position size
        Then: Position size should be minimal but positive.
        """
        extreme_signal = TradeSignal(
            id="test-volatility-003",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0750,  # 250 pips (extreme)
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )

        position_size = calculate_position_size(extreme_signal, 10000.0, 1.0, 10.0)

        # Should still produce a valid positive size
        assert position_size > 0, "Extreme volatility should still produce positive size"
        assert (
            position_size >= 0.01
        ), "Position size should be at least lot_step minimum"
        assert position_size <= 0.10, "Extreme stop should produce very small size"

    def test_max_position_size_enforcement(self):
        """
        T024: Verify max position size constraint is enforced.

        Given: Large account balance or tight stop that would exceed max size
        When: Calculating position size
        Then: Position size should be capped at max_position_size.
        """
        # Tight stop with large account to trigger max size
        signal = TradeSignal(
            id="test-volatility-004",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0990,  # 10 pips (tight)
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )

        # Very large account
        position_size = calculate_position_size(
            signal,
            account_balance=1000000.0,  # $1M
            risk_per_trade_pct=1.0,
            pip_value=10.0,
            lot_step=0.01,
            max_position_size=10.0,  # Cap at 10 lots
        )

        # Should be capped at max
        assert (
            position_size <= 10.0
        ), "Position size should not exceed max_position_size"
        assert position_size == pytest.approx(
            10.0, abs=0.01
        ), "Should cap exactly at max_position_size"

    def test_risk_consistency_across_volatility_levels(self):
        """
        T024: Verify actual risk dollar amount remains consistent.

        Given: Different volatility scenarios (different stop distances)
        When: Calculating position sizes
        Then: Dollar risk should be approximately the same.
        """
        # Low volatility: 30 pip stop
        low_vol_signal = TradeSignal(
            id="test-volatility-005",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0970,  # 30 pips
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )
        low_vol_size = calculate_position_size(low_vol_signal, 10000.0, 1.0, 10.0)
        low_vol_risk = low_vol_size * 30 * 10.0  # size * pips * pip_value

        # High volatility: 100 pip stop
        high_vol_signal = TradeSignal(
            id="test-volatility-006",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0900,  # 100 pips
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )
        high_vol_size = calculate_position_size(high_vol_signal, 10000.0, 1.0, 10.0)
        high_vol_risk = high_vol_size * 100 * 10.0

        # Dollar risk should be similar (within rounding tolerance)
        # Floor rounding can cause up to ~10% variance in dollar risk
        assert low_vol_risk == pytest.approx(
            high_vol_risk, abs=10.0
        ), "Dollar risk should be consistent across volatility levels"

    def test_position_size_volatility_deterministic(self):
        """
        T024: Verify calculations remain deterministic under volatility.

        Given: High volatility signal
        When: Calculating position size multiple times
        Then: Results should be identical.
        """
        signal = TradeSignal(
            id="test-volatility-007",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0800,  # 200 pips (high volatility)
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )

        # Calculate 5 times
        sizes = [calculate_position_size(signal, 10000.0, 1.0, 10.0) for _ in range(5)]

        # All should be identical
        assert all(
            s == sizes[0] for s in sizes
        ), "High volatility position sizing should be deterministic"

    def test_minimum_position_size_enforcement(self):
        """
        T024: Verify minimum position size (lot_step) is enforced.

        Given: Very small account or very large stop
        When: Calculated size would be below lot_step
        Then: Position size should be rounded up to lot_step.
        """
        signal = TradeSignal(
            id="test-volatility-008",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0700,  # 300 pips (extreme)
            risk_per_trade_pct=0.5,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )

        # Small account with extreme stop
        position_size = calculate_position_size(
            signal, account_balance=1000.0, risk_per_trade_pct=0.5, pip_value=10.0
        )

        # Should be at least lot_step
        assert (
            position_size >= 0.01
        ), "Position size should be at least lot_step minimum"
        assert position_size == pytest.approx(
            0.01, abs=0.001
        ), "Tiny calculated size should round to lot_step"

    def test_short_signal_volatility_symmetry(self):
        """
        T024: Verify SHORT signals behave identically under high volatility.

        Given: Long and short signals with same stop distance under volatility
        When: Calculating position sizes
        Then: Both should produce similar sizes.
        """
        # Long signal with 120 pip stop
        long_signal = TradeSignal(
            id="test-volatility-009",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0880,  # 120 pips below
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )
        long_size = calculate_position_size(long_signal, 10000.0, 1.0, 10.0)

        # Short signal with 120 pip stop
        short_signal = TradeSignal(
            id="test-volatility-010",
            pair="EURUSD",
            direction="SHORT",
            entry_price=1.1000,
            initial_stop_price=1.1120,  # 120 pips above
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )
        short_size = calculate_position_size(short_signal, 10000.0, 1.0, 10.0)

        # Should be similar (accounting for rounding)
        assert long_size == pytest.approx(
            short_size, abs=0.02
        ), "Long and short should have similar size under same volatility"
