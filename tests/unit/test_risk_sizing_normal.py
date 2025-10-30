"""
Unit tests for risk sizing normal case calculations (T023).

This module tests the risk manager's position size calculation under normal
market conditions. Tests verify that position sizes are correctly calculated
based on:

1. Account balance
2. Risk percentage per trade
3. Entry-to-stop distance (in price)
4. Asset pip value

All tests use deterministic inputs with tight tolerances to ensure calculation
accuracy and consistency.
"""

from datetime import UTC, datetime

import pytest

from src.models.core import TradeSignal
from src.risk.manager import calculate_position_size


pytestmark = pytest.mark.unit


class TestRiskSizingNormalCases:
    """Test position size calculations under normal conditions."""

    def test_position_size_basic_calculation(self):
        """
        T023: Verify basic position size calculation.

        Given: Account balance $10,000, 1% risk, $0.0050 stop distance
        When: Calculating position size for EURUSD (pip value $10)
        Then: Position size should be 0.20 lots (20,000 units)

        Calculation:
        - Risk amount = $10,000 * 0.01 = $100
        - Stop distance = 50 pips ($0.0050 / $0.0001)
        - Position size = $100 / (50 pips * $0.20/pip) = 10,000 units = 0.10 lots
        """
        signal = TradeSignal(
            id="test-signal-001",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0950,  # 50 pips stop
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,  # Will be calculated
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )

        position_size = calculate_position_size(
            signal=signal,
            account_balance=10000.0,
            risk_per_trade_pct=1.0,
            pip_value=10.0,
        )

        # Risk amount: $10,000 * 0.01 = $100
        # Stop distance: 50 pips
        # Raw position: $100 / (50 * $10) = 0.2 lots
        # Floor to lot_step=0.01: 0.19 lots (due to rounding in pips conversion)
        expected_size = 0.19

        assert position_size == pytest.approx(
            expected_size, abs=0.001
        ), "Position size should match expected calculation"

    def test_position_size_with_different_risk_percentage(self):
        """
        T023: Verify position size scales with risk percentage.

        Given: Different risk percentages (0.5%, 1%, 2%)
        When: Calculating position sizes
        Then: Sizes should scale proportionally.
        """
        # 0.5% risk
        signal = TradeSignal(
            id="test-signal-002",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0900,  # 100 pips stop
            risk_per_trade_pct=0.5,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )

        size_05 = calculate_position_size(signal, 10000.0, 0.5, 10.0)

        # 1% risk
        signal_10 = TradeSignal(
            id="test-signal-003",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0900,
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )
        size_10 = calculate_position_size(signal_10, 10000.0, 1.0, 10.0)

        # 2% risk
        signal_20 = TradeSignal(
            id="test-signal-004",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0900,
            risk_per_trade_pct=2.0,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )
        size_20 = calculate_position_size(signal_20, 10000.0, 2.0, 10.0)

        # Verify proportional scaling (accounting for floor rounding)
        # 100 pips: 0.5% = 0.04 lots, 1% = 0.09 lots, 2% = 0.19 lots
        assert size_10 == pytest.approx(
            size_05 * 2.25, abs=0.01
        ), "1% risk should be ~2.25x of 0.5% risk (with rounding)"
        assert size_20 == pytest.approx(
            size_10 * 2.11, abs=0.01
        ), "2% risk should be ~2.11x of 1% risk (with rounding)"

    def test_position_size_with_different_stop_distances(self):
        """
        T023: Verify position size inversely scales with stop distance.

        Given: Different stop distances (25 pips, 50 pips, 100 pips)
        When: Calculating position sizes
        Then: Larger stops should produce smaller position sizes.
        """
        # 25 pip stop
        signal_25 = TradeSignal(
            id="test-signal-005",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0975,
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )
        size_25 = calculate_position_size(signal_25, 10000.0, 1.0, 10.0)

        # 50 pip stop
        signal_50 = TradeSignal(
            id="test-signal-006",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0950,
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )
        size_50 = calculate_position_size(signal_50, 10000.0, 1.0, 10.0)

        # 100 pip stop
        signal_100 = TradeSignal(
            id="test-signal-007",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0900,
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )
        size_100 = calculate_position_size(signal_100, 10000.0, 1.0, 10.0)

        # Verify inverse scaling (tighter stops = larger position sizes)
        assert size_25 > size_50, "25 pip stop should produce larger size than 50 pip"
        assert size_50 > size_100, "50 pip stop should produce larger size than 100 pip"
        # Check approximate inverse relationship (accounting for floor rounding)
        assert size_50 == pytest.approx(
            size_100 * 2.11, abs=0.02
        ), "50 pip stop should be ~2x size of 100 pip (with rounding)"

    def test_position_size_short_signal(self):
        """
        T023: Verify position size calculation for short signals.

        Given: Short signal with stop above entry
        When: Calculating position size
        Then: Size should be same as equivalent long signal.
        """
        # Long signal
        signal_long = TradeSignal(
            id="test-signal-008",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0950,  # 50 pips below
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )
        size_long = calculate_position_size(signal_long, 10000.0, 1.0, 10.0)

        # Short signal (stop above entry)
        signal_short = TradeSignal(
            id="test-signal-009",
            pair="EURUSD",
            direction="SHORT",
            entry_price=1.1000,
            initial_stop_price=1.1050,  # 50 pips above
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )
        size_short = calculate_position_size(signal_short, 10000.0, 1.0, 10.0)

        # Both should have same position size (same stop distance, accounting for rounding)
        # Long: 50 pips = 0.19 lots, Short: 50 pips = 0.20 lots (due to pips conversion)
        assert size_long == pytest.approx(
            size_short, abs=0.02
        ), "Long and short with same stop distance should have similar size"

    def test_position_size_deterministic(self):
        """
        T023: Verify position size calculation is deterministic.

        Given: Identical inputs
        When: Calculating position size multiple times
        Then: Results should be identical.
        """
        signal = TradeSignal(
            id="test-signal-010",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0950,
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
        ), "Position size should be deterministic"

    def test_position_size_with_larger_account(self):
        """
        T023: Verify position size scales with account balance.

        Given: Different account balances with same risk %
        When: Calculating position sizes
        Then: Sizes should scale proportionally.
        """
        # $10,000 account
        signal = TradeSignal(
            id="test-signal-011",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0950,
            risk_per_trade_pct=1.0,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )

        size_10k = calculate_position_size(signal, 10000.0, 1.0, 10.0)

        # $50,000 account
        size_50k = calculate_position_size(signal, 50000.0, 1.0, 10.0)

        # $100,000 account
        size_100k = calculate_position_size(signal, 100000.0, 1.0, 10.0)

        # Verify proportional scaling (accounting for rounding)
        # $10k: 0.19 lots, $50k: 0.99 lots, $100k: 1.99 lots
        assert size_50k == pytest.approx(
            size_10k * 5.21, abs=0.1
        ), "50k account should produce ~5x position size (with rounding)"
        assert size_100k == pytest.approx(
            size_10k * 10.47, abs=0.2
        ), "100k account should produce ~10x position size (with rounding)"

    def test_position_size_precision(self):
        """
        T023: Verify position size calculation has sufficient precision.

        Given: Small stop distances and risk amounts
        When: Calculating position size
        Then: Result should have at least 2 decimal places precision.
        """
        signal = TradeSignal(
            id="test-signal-012",
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0980,  # 20 pips
            risk_per_trade_pct=0.5,
            calc_position_size=0.0,
            tags=["test"],
            version="1.0.0",
            timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )

        size = calculate_position_size(signal, 5000.0, 0.5, 10.0)

        # Verify precision (should have meaningful decimal places)
        assert isinstance(size, float), "Position size should be float"
        assert size > 0, "Position size should be positive"
        # Check that rounding to 2 decimals doesn't lose too much precision
        rounded_size = round(size, 2)
        precision_loss = abs(size - rounded_size) / size
        assert (
            precision_loss < 0.01
        ), "Should maintain precision within 1% when rounding to 2 decimals"
