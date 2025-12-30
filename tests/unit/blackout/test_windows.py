"""
Unit tests for blackout window management.

Tests validate window expansion, merging, overlap detection,
and vectorized signal filtering.
"""

from datetime import datetime, timezone, timedelta

import numpy as np
import pytest

from src.risk.blackout.windows import (
    BlackoutWindow,
    expand_news_windows,
    expand_session_windows,
    merge_overlapping_windows,
    is_in_blackout,
)
from src.risk.blackout.calendar import NewsEvent
from src.risk.blackout.config import NewsBlackoutConfig, SessionBlackoutConfig


pytestmark = pytest.mark.unit


# Helper to create UTC datetime
def utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


class TestBlackoutWindow:
    """Test BlackoutWindow dataclass validation."""

    def test_valid_window(self):
        """Valid window should be created."""
        window = BlackoutWindow(
            start_utc=utc(2023, 1, 6, 13, 20),
            end_utc=utc(2023, 1, 6, 14, 0),
            source="news",
        )
        assert window.source == "news"

    def test_end_must_be_after_start(self):
        """Window end must be after start."""
        with pytest.raises(ValueError, match="end_utc must be after start_utc"):
            BlackoutWindow(
                start_utc=utc(2023, 1, 6, 14, 0),
                end_utc=utc(2023, 1, 6, 13, 0),
                source="news",
            )

    def test_must_be_timezone_aware(self):
        """Timestamps must be timezone-aware."""
        with pytest.raises(ValueError, match="timezone-aware"):
            BlackoutWindow(
                start_utc=datetime(2023, 1, 6, 13, 0),  # naive
                end_utc=datetime(2023, 1, 6, 14, 0),  # naive
                source="news",
            )


class TestExpandNewsWindows:
    """Test expansion of news events into blackout windows."""

    def test_expands_single_event(self):
        """Single event should produce single window."""
        events = [
            NewsEvent(
                event_name="NFP",
                currency="USD",
                event_time_utc=utc(2023, 1, 6, 13, 30),
            )
        ]
        config = NewsBlackoutConfig(
            enabled=True,
            pre_close_minutes=10,
            post_pause_minutes=30,
        )

        windows = expand_news_windows(events, config)

        assert len(windows) == 1
        assert windows[0].start_utc == utc(2023, 1, 6, 13, 20)  # 10 min before
        assert windows[0].end_utc == utc(2023, 1, 6, 14, 0)  # 30 min after
        assert windows[0].source == "news"

    def test_expands_multiple_events(self):
        """Multiple events should produce multiple windows."""
        events = [
            NewsEvent("NFP", "USD", utc(2023, 1, 6, 13, 30)),
            NewsEvent("IJC", "USD", utc(2023, 1, 5, 13, 30)),
        ]
        config = NewsBlackoutConfig(enabled=True)

        windows = expand_news_windows(events, config)

        assert len(windows) == 2


class TestExpandSessionWindows:
    """Test expansion of session gaps into blackout windows."""

    def test_creates_windows_for_weekdays(self):
        """Should create windows for each weekday."""
        from datetime import date

        config = SessionBlackoutConfig(enabled=True)

        # One week of data
        windows = expand_session_windows(date(2023, 1, 2), date(2023, 1, 6), config)

        # Mon-Fri = 5 weekdays (but Sat/Sun excluded)
        assert len(windows) == 5

    def test_window_source_is_session(self):
        """Windows should have source='session'."""
        from datetime import date

        config = SessionBlackoutConfig(enabled=True)

        windows = expand_session_windows(date(2023, 1, 2), date(2023, 1, 2), config)

        assert len(windows) == 1
        assert windows[0].source == "session"

    def test_skips_weekends(self):
        """Should not create windows for weekends."""
        from datetime import date

        config = SessionBlackoutConfig(enabled=True)

        # Saturday Jan 7, Sunday Jan 8
        windows = expand_session_windows(date(2023, 1, 7), date(2023, 1, 8), config)

        assert len(windows) == 0


class TestMergeOverlappingWindows:
    """Test window merging logic."""

    def test_merge_overlapping(self):
        """Overlapping windows should merge into one."""
        windows = [
            BlackoutWindow(utc(2023, 1, 6, 13, 0), utc(2023, 1, 6, 14, 0), "news"),
            BlackoutWindow(utc(2023, 1, 6, 13, 30), utc(2023, 1, 6, 15, 0), "news"),
        ]

        merged = merge_overlapping_windows(windows)

        assert len(merged) == 1
        assert merged[0].start_utc == utc(2023, 1, 6, 13, 0)
        assert merged[0].end_utc == utc(2023, 1, 6, 15, 0)

    def test_merge_adjacent(self):
        """Adjacent windows should merge into one."""
        windows = [
            BlackoutWindow(utc(2023, 1, 6, 13, 0), utc(2023, 1, 6, 14, 0), "news"),
            BlackoutWindow(utc(2023, 1, 6, 14, 0), utc(2023, 1, 6, 15, 0), "news"),
        ]

        merged = merge_overlapping_windows(windows)

        assert len(merged) == 1

    def test_disjoint_stay_separate(self):
        """Non-overlapping windows should stay separate."""
        windows = [
            BlackoutWindow(utc(2023, 1, 6, 13, 0), utc(2023, 1, 6, 14, 0), "news"),
            BlackoutWindow(utc(2023, 1, 6, 16, 0), utc(2023, 1, 6, 17, 0), "news"),
        ]

        merged = merge_overlapping_windows(windows)

        assert len(merged) == 2

    def test_empty_list(self):
        """Empty list should return empty list."""
        merged = merge_overlapping_windows([])
        assert merged == []


class TestIsInBlackout:
    """Test timestamp blackout checking."""

    def test_inside_window(self):
        """Timestamp inside window should return True."""
        windows = [
            BlackoutWindow(utc(2023, 1, 6, 13, 0), utc(2023, 1, 6, 14, 0), "news"),
        ]

        assert is_in_blackout(utc(2023, 1, 6, 13, 30), windows) is True

    def test_outside_window(self):
        """Timestamp outside window should return False."""
        windows = [
            BlackoutWindow(utc(2023, 1, 6, 13, 0), utc(2023, 1, 6, 14, 0), "news"),
        ]

        assert is_in_blackout(utc(2023, 1, 6, 15, 0), windows) is False

    def test_at_window_start(self):
        """Timestamp at window start should return True."""
        windows = [
            BlackoutWindow(utc(2023, 1, 6, 13, 0), utc(2023, 1, 6, 14, 0), "news"),
        ]

        assert is_in_blackout(utc(2023, 1, 6, 13, 0), windows) is True

    def test_at_window_end(self):
        """Timestamp at window end should return True (inclusive)."""
        windows = [
            BlackoutWindow(utc(2023, 1, 6, 13, 0), utc(2023, 1, 6, 14, 0), "news"),
        ]

        assert is_in_blackout(utc(2023, 1, 6, 14, 0), windows) is True

    def test_empty_windows(self):
        """Empty window list should return False."""
        assert is_in_blackout(utc(2023, 1, 6, 13, 0), []) is False
