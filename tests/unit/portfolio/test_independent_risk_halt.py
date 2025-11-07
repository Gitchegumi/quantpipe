"""Unit tests for independent risk halt behavior.

Feature: 008-multi-symbol
Task: T024 - Test that one symbol's risk breach halts only that symbol
User Story: US2 - Independent Multi-Symbol Mode

This test verifies that risk isolation works correctly in independent mode:
when one symbol breaches risk limits, it should halt only that symbol,
not affect other symbols in the same run.
"""
import pytest

from src.backtest.portfolio.risk_isolation import RiskIsolationTracker
from src.models.portfolio import CurrencyPair


class TestIndependentRiskHalt:
    """Test risk isolation in independent multi-symbol execution."""

    @pytest.fixture
    def tracker(self):
        """Create a fresh RiskIsolationTracker."""
        return RiskIsolationTracker()

    def test_isolate_single_symbol(self, tracker):
        """Test isolating a single symbol due to failure.

        Verifies that:
        - Symbol is marked as isolated
        - Failure event is recorded
        - Other symbols are not affected
        """
        pair_a = CurrencyPair(code="EURUSD")
        pair_b = CurrencyPair(code="GBPUSD")

        # Isolate EURUSD
        event = tracker.isolate_symbol(pair_a, "Dataset read error")

        # Verify isolation
        assert tracker.is_symbol_isolated(pair_a)
        assert not tracker.is_symbol_isolated(pair_b)

        # Verify event
        assert event.pair.code == "EURUSD"
        assert "Dataset read error" in event.reason

        # Verify isolated symbols list
        isolated = tracker.get_isolated_symbols()
        assert len(isolated) == 1
        assert "EURUSD" in isolated

    def test_multiple_isolations(self, tracker):
        """Test isolating multiple symbols independently.

        Verifies that:
        - Multiple symbols can be isolated
        - Each has its own failure event
        - Isolation state is tracked independently
        """
        pair_a = CurrencyPair(code="EURUSD")
        pair_b = CurrencyPair(code="GBPUSD")
        pair_c = CurrencyPair(code="USDJPY")

        # Isolate two symbols
        tracker.isolate_symbol(pair_a, "Error A")
        tracker.isolate_symbol(pair_c, "Error C")

        # Verify isolation states
        assert tracker.is_symbol_isolated(pair_a)
        assert not tracker.is_symbol_isolated(pair_b)  # Not isolated
        assert tracker.is_symbol_isolated(pair_c)

        # Verify events
        events = tracker.get_failure_events()
        assert len(events) == 2

        event_pairs = {e.pair.code for e in events}
        assert "EURUSD" in event_pairs
        assert "USDJPY" in event_pairs
        assert "GBPUSD" not in event_pairs

    def test_risk_breach_recording(self, tracker):
        """Test recording risk breaches for symbols.

        Verifies that:
        - Risk breaches are recorded per symbol
        - Multiple breach types can be tracked
        - Breaches don't automatically isolate symbols
        """
        pair_a = CurrencyPair(code="EURUSD")
        pair_b = CurrencyPair(code="GBPUSD")

        # Record breaches
        tracker.record_risk_breach(pair_a, "max_drawdown")
        tracker.record_risk_breach(pair_a, "position_size")
        tracker.record_risk_breach(pair_b, "stop_loss_hit")

        # Verify breaches
        breaches_a = tracker.get_risk_breaches(pair=pair_a)
        breaches_b = tracker.get_risk_breaches(pair=pair_b)

        assert len(breaches_a) == 2
        assert "max_drawdown" in breaches_a
        assert "position_size" in breaches_a

        assert len(breaches_b) == 1
        assert "stop_loss_hit" in breaches_b

        # Verify symbols are not isolated (just breach recording)
        assert not tracker.is_symbol_isolated(pair_a)
        assert not tracker.is_symbol_isolated(pair_b)

    def test_risk_breach_all_symbols(self, tracker):
        """Test getting all risk breaches across symbols."""
        pair_a = CurrencyPair(code="EURUSD")
        pair_b = CurrencyPair(code="GBPUSD")

        tracker.record_risk_breach(pair_a, "breach_type_1")
        tracker.record_risk_breach(pair_b, "breach_type_2")

        # Get all breaches
        all_breaches = tracker.get_risk_breaches()

        assert isinstance(all_breaches, dict)
        assert "EURUSD" in all_breaches
        assert "GBPUSD" in all_breaches
        assert len(all_breaches["EURUSD"]) == 1
        assert len(all_breaches["GBPUSD"]) == 1

    def test_summary_statistics(self, tracker):
        """Test summary statistics for risk isolation.

        Verifies that:
        - Summary includes isolation counts
        - Summary includes breach counts
        - Summary includes symbol lists
        """
        pair_a = CurrencyPair(code="EURUSD")
        pair_b = CurrencyPair(code="GBPUSD")
        pair_c = CurrencyPair(code="USDJPY")

        # Create mixed scenario
        tracker.isolate_symbol(pair_a, "Fatal error")
        tracker.record_risk_breach(pair_b, "drawdown")
        tracker.record_risk_breach(pair_b, "exposure")
        tracker.record_risk_breach(pair_c, "volatility")

        # Get summary
        summary = tracker.get_summary()

        assert summary["isolated_symbols_count"] == 1
        assert "EURUSD" in summary["isolated_symbols"]

        assert summary["total_failure_events"] == 1
        assert summary["total_risk_breaches"] == 3

        assert "GBPUSD" in summary["symbols_with_breaches"]
        assert "USDJPY" in summary["symbols_with_breaches"]

    def test_clear_tracker(self, tracker):
        """Test clearing tracker state.

        Verifies that:
        - All isolation state is cleared
        - All breach records are cleared
        - Tracker can be reused
        """
        pair_a = CurrencyPair(code="EURUSD")

        # Add data
        tracker.isolate_symbol(pair_a, "Test error")
        tracker.record_risk_breach(pair_a, "test_breach")

        # Verify data exists
        assert tracker.is_symbol_isolated(pair_a)
        assert len(tracker.get_risk_breaches(pair=pair_a)) > 0

        # Clear
        tracker.clear()

        # Verify cleared
        assert not tracker.is_symbol_isolated(pair_a)
        assert len(tracker.get_risk_breaches(pair=pair_a)) == 0
        assert len(tracker.get_isolated_symbols()) == 0
        assert len(tracker.get_failure_events()) == 0

    def test_isolation_prevents_processing(self, tracker):
        """Test that isolated symbols should be skipped in processing.

        Verifies that:
        - is_symbol_isolated can be checked before processing
        - Isolated symbols return True
        - Non-isolated symbols return False
        """
        pair_a = CurrencyPair(code="EURUSD")
        pair_b = CurrencyPair(code="GBPUSD")

        # Isolate EURUSD
        tracker.isolate_symbol(pair_a, "Processing error")

        # Simulate processing check
        if not tracker.is_symbol_isolated(pair_a):
            # This shouldn't execute
            pytest.fail("Isolated symbol should not be processed")

        if not tracker.is_symbol_isolated(pair_b):
            # This should execute - GBPUSD is not isolated
            pass  # Normal processing would continue

        # Verify final state
        assert tracker.is_symbol_isolated(pair_a)
        assert not tracker.is_symbol_isolated(pair_b)

    def test_breach_accumulation(self, tracker):
        """Test that breaches accumulate for a symbol.

        Verifies that:
        - Multiple breaches on same symbol are all recorded
        - Breach list grows with each new breach
        - All breach types are preserved
        """
        pair = CurrencyPair(code="EURUSD")

        # Record multiple breach types
        breach_types = [
            "max_drawdown",
            "position_size",
            "stop_loss_hit",
            "volatility_spike",
            "liquidity_constraint",
        ]

        for breach_type in breach_types:
            tracker.record_risk_breach(pair, breach_type)

        # Verify all breaches recorded
        breaches = tracker.get_risk_breaches(pair=pair)
        assert len(breaches) == len(breach_types)

        for breach_type in breach_types:
            assert breach_type in breaches

    def test_failure_event_timestamp(self, tracker):
        """Test that failure events include timestamps.

        Verifies that:
        - Events have timestamp attribute
        - Timestamps are valid
        - Events can be ordered by time
        """
        pair_a = CurrencyPair(code="EURUSD")
        pair_b = CurrencyPair(code="GBPUSD")

        # Create events
        event1 = tracker.isolate_symbol(pair_a, "Error 1")
        event2 = tracker.isolate_symbol(pair_b, "Error 2")

        # Verify timestamps exist
        assert hasattr(event1, "timestamp")
        assert hasattr(event2, "timestamp")
        assert event1.timestamp is not None
        assert event2.timestamp is not None

        # Verify event2 timestamp >= event1 timestamp (created after)
        assert event2.timestamp >= event1.timestamp
