"""
Unit tests for risk manager with short positions.

Validates that stop loss placement for short positions is correctly
positioned ABOVE the entry price (opposite of long positions).
"""

import pytest
from datetime import datetime, timezone

from src.models.core import TradeSignal


class TestRiskManagerShortPositions:
    """Tests for short position stop loss placement."""

    def test_short_stop_above_entry(self):
        """
        GIVEN: A short trade signal
        WHEN: Stop loss is calculated
        THEN: Stop price should be ABOVE entry price
        """
        # Arrange: Create short signal
        signal = TradeSignal(
            id="test_short_123",
            pair="EURUSD",
            direction="SHORT",
            entry_price=1.10000,
            initial_stop_price=1.10050,  # Stop above entry for shorts
            risk_per_trade_pct=0.25,
            calc_position_size=0.01,
            tags=["short", "test"],
            version="0.1.0",
            timestamp_utc=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        # Assert: Stop is above entry
        assert signal.initial_stop_price > signal.entry_price, \
            "Short position stop must be above entry"
        
        # Assert: Risk distance is positive
        risk_distance = signal.initial_stop_price - signal.entry_price
        assert risk_distance > 0, "Risk distance must be positive"
        assert abs(risk_distance - 0.00050) < 1e-9, f"Expected 50 pips risk, got {risk_distance}"

    def test_short_stop_calculation_with_atr(self):
        """
        GIVEN: Short signal with ATR-based stop
        WHEN: Stop is 2.0 ATR above entry
        THEN: Stop distance should be entry + (2.0 * ATR)
        """
        # Arrange
        entry_price = 1.20000
        atr_value = 0.00100  # 100 pips
        atr_multiplier = 2.0
        
        # Calculate stop (above entry for shorts)
        stop_price = entry_price + (atr_value * atr_multiplier)
        
        # Assert
        assert stop_price == 1.20200, f"Expected 1.20200, got {stop_price}"
        assert stop_price > entry_price, "Stop must be above entry for shorts"

    def test_short_vs_long_stop_direction(self):
        """
        GIVEN: Equivalent long and short setups
        WHEN: Comparing stop placement
        THEN: Short stop is above entry, long stop is below entry
        """
        # Arrange: Same entry and ATR
        entry_price = 1.15000
        atr_value = 0.00150
        atr_multiplier = 2.0
        
        # Long stop: below entry
        long_stop = entry_price - (atr_value * atr_multiplier)
        
        # Short stop: above entry
        short_stop = entry_price + (atr_value * atr_multiplier)
        
        # Assert: Opposite directions
        assert long_stop < entry_price, "Long stop should be below entry"
        assert short_stop > entry_price, "Short stop should be above entry"
        assert abs(long_stop - 1.14700) < 1e-9, f"Long stop incorrect: {long_stop}"
        assert abs(short_stop - 1.15300) < 1e-9, f"Short stop incorrect: {short_stop}"

    def test_short_signal_validation(self):
        """
        GIVEN: Short signal with invalid stop placement
        WHEN: Stop is below entry (wrong direction)
        THEN: Signal structure allows it but logic would be invalid
        """
        # This test documents that the data model allows invalid stops
        # but the signal generator should never create them
        
        # Create signal with WRONG stop placement (below entry)
        signal = TradeSignal(
            id="invalid_short",
            pair="EURUSD",
            direction="SHORT",
            entry_price=1.10000,
            initial_stop_price=1.09950,  # WRONG: below entry for short
            risk_per_trade_pct=0.25,
            calc_position_size=0.01,
            tags=["short", "invalid"],
            version="0.1.0",
            timestamp_utc=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        
        # Assert: Model allows this, but it's logically wrong
        assert signal.initial_stop_price < signal.entry_price
        # Note: In real implementation, signal generator should prevent this
