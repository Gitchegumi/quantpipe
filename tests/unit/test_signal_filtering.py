"""Unit tests for signal filtering module.

Tests for filter_overlapping_signals() function from
src/backtest/signal_filter.py.
"""

import numpy as np

from src.backtest.signal_filter import filter_overlapping_signals


class TestFilterOverlappingSignals:
    """Tests for filter_overlapping_signals function."""

    def test_filter_empty_array(self):
        """Empty input returns empty output."""
        signals = np.array([], dtype=np.int64)
        result = filter_overlapping_signals(signals)
        assert len(result) == 0
        assert result.dtype == np.int64

    def test_filter_single_signal(self):
        """Single signal passes through unchanged."""
        signals = np.array([42], dtype=np.int64)
        result = filter_overlapping_signals(signals)
        assert len(result) == 1
        assert result[0] == 42

    def test_filter_non_overlapping_with_exits(self):
        """Widely-spaced signals all pass when exits don't overlap."""
        signals = np.array([10, 100, 200], dtype=np.int64)
        exits = np.array([50, 150, 250], dtype=np.int64)
        result = filter_overlapping_signals(signals, exits, max_concurrent=1)
        # 10 exits at 50, well before 100 enters
        # 100 exits at 150, well before 200 enters
        assert len(result) == 3
        np.testing.assert_array_equal(result, [10, 100, 200])

    def test_filter_overlapping_removes_second(self):
        """Two overlapping signals - first kept, second filtered."""
        signals = np.array([10, 15], dtype=np.int64)
        exits = np.array([50, 60], dtype=np.int64)
        result = filter_overlapping_signals(signals, exits, max_concurrent=1)
        # Signal at 10 exits at 50
        # Signal at 15 enters before 50 exit, so blocked
        assert len(result) == 1
        assert result[0] == 10

    def test_filter_multiple_overlapping(self):
        """Cluster of 5 signals - only first kept when all overlap."""
        signals = np.array([10, 11, 12, 13, 14], dtype=np.int64)
        exits = np.array([100, 101, 102, 103, 104], dtype=np.int64)
        result = filter_overlapping_signals(signals, exits, max_concurrent=1)
        # First signal at 10 exits at 100
        # All others enter before 100, so blocked
        assert len(result) == 1
        assert result[0] == 10

    def test_filter_preserves_sorted_order(self):
        """Output remains sorted ascending."""
        # Signals and exits correspond positionally: signal[i] -> exit[i]
        # Input: signal 100 exits at 150, signal 10 exits at 50, signal 200 exits at 250
        signals = np.array([100, 10, 200], dtype=np.int64)  # Unsorted input
        exits = np.array([150, 50, 250], dtype=np.int64)
        result = filter_overlapping_signals(signals, exits, max_concurrent=1)
        # After sorting by signal: [10, 100, 200] with sorted exits [50, 150, 250]
        # But exit_indices is NOT re-sorted, so correspondence is maintained by argsort
        # signal 10 exits at 50 (before 100 enters at 100) -> 10 kept
        # signal 100 exits at 150 (before 200 enters at 200) -> 100 kept
        # signal 200 exits at 250 -> 200 kept
        # Output should be sorted
        assert list(result) == sorted(result)

    def test_filter_unlimited_concurrent(self):
        """max_concurrent=None allows all signals."""
        signals = np.array([10, 15, 20, 25], dtype=np.int64)
        exits = np.array([100, 100, 100, 100], dtype=np.int64)
        result = filter_overlapping_signals(signals, exits, max_concurrent=None)
        assert len(result) == 4
        np.testing.assert_array_equal(result, [10, 15, 20, 25])

    def test_filter_max_concurrent_zero(self):
        """max_concurrent=0 treated as unlimited."""
        signals = np.array([10, 15, 20], dtype=np.int64)
        exits = np.array([100, 100, 100], dtype=np.int64)
        result = filter_overlapping_signals(signals, exits, max_concurrent=0)
        assert len(result) == 3

    def test_filter_same_candle_exit_entry(self):
        """Allow new entry on same candle as previous exit."""
        signals = np.array([10, 50], dtype=np.int64)
        exits = np.array([50, 100], dtype=np.int64)
        result = filter_overlapping_signals(signals, exits, max_concurrent=1)
        # Signal at 10 exits at 50, signal at 50 can enter at exit candle
        assert len(result) == 2
        np.testing.assert_array_equal(result, [10, 50])

    def test_filter_without_exits_simple(self):
        """Simple window filtering when no exits provided."""
        signals = np.array([10, 15, 20], dtype=np.int64)
        result = filter_overlapping_signals(signals, max_concurrent=1)
        # Without exit info, should return at least the first signal
        assert len(result) >= 1
        assert result[0] == 10
