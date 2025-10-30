"""
Unit tests for signal cooldown enforcement.

Validates that can_generate_signal() prevents signals from being
generated within the minimum cooldown period (5 candles by default).
"""

from datetime import UTC, datetime, timedelta

import pytest

pytestmark = pytest.mark.unit

from src.models.core import Candle
from src.strategy.trend_pullback.signal_generator import can_generate_signal


class TestSignalCooldown:
    """Tests for signal generation cooldown logic."""

    @pytest.fixture()
    def sample_candles(self):
        """Create sample candle sequence for cooldown testing."""
        candles = []
        base_time = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)

        for i in range(10):
            candle = Candle(
                timestamp_utc=base_time + timedelta(hours=i),
                open=1.10000,
                high=1.10010,
                low=1.09990,
                close=1.10005,
                volume=1000,
                ema20=1.10000,
                ema50=1.09900,
                atr=0.00100,
                rsi=50.0,
                stoch_rsi=0.5,
            )
            candles.append(candle)

        return candles

    def test_no_previous_signal_allows_generation(self, sample_candles):
        """
        GIVEN: No previous signal generated
        WHEN: Checking if signal can be generated
        THEN: Should return True (no cooldown)
        """
        # Act
        can_generate = can_generate_signal(sample_candles, last_signal_timestamp=None)

        # Assert
        assert (
            can_generate is True
        ), "Should allow signal when no previous signal exists"

    def test_cooldown_blocks_immediate_signal(self, sample_candles):
        """
        GIVEN: Signal generated on last candle
        WHEN: Checking if new signal can be generated immediately
        THEN: Should return False (in cooldown)
        """
        # Arrange: Last signal was the most recent candle
        last_signal_time = sample_candles[-1].timestamp_utc

        # Act
        can_generate = can_generate_signal(
            sample_candles, last_signal_timestamp=last_signal_time, cooldown_candles=5
        )

        # Assert
        assert (
            can_generate is False
        ), "Should block signal immediately after previous signal"

    def test_cooldown_blocks_within_5_candles(self, sample_candles):
        """
        GIVEN: Signal generated 4 candles ago
        WHEN: Checking if new signal can be generated
        THEN: Should return False (still in 5-candle cooldown)
        """
        # Arrange: Last signal was 4 candles ago (index 5, current is 9)
        last_signal_time = sample_candles[5].timestamp_utc

        # Act
        can_generate = can_generate_signal(
            sample_candles, last_signal_timestamp=last_signal_time, cooldown_candles=5
        )

        # Assert: Only 4 candles have passed (6, 7, 8, 9)
        assert can_generate is False, "Should block signal within 5-candle cooldown"

    def test_cooldown_allows_after_5_candles(self, sample_candles):
        """
        GIVEN: Signal generated 5+ candles ago
        WHEN: Checking if new signal can be generated
        THEN: Should return True (cooldown expired)
        """
        # Arrange: Last signal was 6 candles ago (index 3, current is 9)
        last_signal_time = sample_candles[3].timestamp_utc

        # Act
        can_generate = can_generate_signal(
            sample_candles, last_signal_timestamp=last_signal_time, cooldown_candles=5
        )

        # Assert: 6 candles have passed (4, 5, 6, 7, 8, 9) >= 5
        assert (
            can_generate is True
        ), "Should allow signal after 5-candle cooldown expires"

    def test_cooldown_exact_boundary_5_candles(self, sample_candles):
        """
        GIVEN: Signal generated exactly 5 candles ago
        WHEN: Checking if new signal can be generated
        THEN: Should return True (at boundary, cooldown complete)
        """
        # Arrange: Last signal was exactly 5 candles ago (index 4, current is 9)
        last_signal_time = sample_candles[4].timestamp_utc

        # Act
        can_generate = can_generate_signal(
            sample_candles, last_signal_timestamp=last_signal_time, cooldown_candles=5
        )

        # Assert: Exactly 5 candles have passed (5, 6, 7, 8, 9)
        assert (
            can_generate is True
        ), "Should allow signal when exactly 5 candles have passed"

    def test_custom_cooldown_period(self, sample_candles):
        """
        GIVEN: Custom cooldown period of 3 candles
        WHEN: Signal was 3 candles ago
        THEN: Should allow new signal
        """
        # Arrange: Last signal was 3 candles ago
        last_signal_time = sample_candles[6].timestamp_utc

        # Act: Use custom cooldown of 3 candles
        can_generate = can_generate_signal(
            sample_candles, last_signal_timestamp=last_signal_time, cooldown_candles=3
        )

        # Assert: 3 candles have passed (7, 8, 9)
        assert can_generate is True, "Should respect custom cooldown period"

    def test_empty_candles_blocks_signal(self):
        """
        GIVEN: Empty candle sequence
        WHEN: Checking if signal can be generated
        THEN: Should return False
        """
        # Act
        can_generate = can_generate_signal(
            [],
            last_signal_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            cooldown_candles=5,
        )

        # Assert
        assert can_generate is False, "Should block signal with empty candle sequence"

    def test_signal_before_candle_sequence(self, sample_candles):
        """
        GIVEN: Last signal timestamp is before all candles in sequence
        WHEN: Checking if new signal can be generated
        THEN: Should return True (old signal, no recent activity)
        """
        # Arrange: Signal was before the first candle
        old_signal_time = sample_candles[0].timestamp_utc - timedelta(days=1)

        # Act
        can_generate = can_generate_signal(
            sample_candles, last_signal_timestamp=old_signal_time, cooldown_candles=5
        )

        # Assert
        assert can_generate is True, "Should allow signal when previous is very old"
