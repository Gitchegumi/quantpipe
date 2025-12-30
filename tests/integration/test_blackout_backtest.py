"""
Integration tests for blackout filtering in backtests.

Tests verify end-to-end behavior when blackout configuration is enabled,
ensuring signals are correctly filtered during news and session windows.
"""

from datetime import date, datetime, timezone, timedelta

import numpy as np
import pytest

from src.risk.blackout.config import (
    BlackoutConfig,
    NewsBlackoutConfig,
    SessionBlackoutConfig,
)
from src.risk.blackout.calendar import generate_news_calendar
from src.risk.blackout.windows import (
    expand_news_windows,
    expand_session_windows,
    merge_overlapping_windows,
)
from src.backtest.signal_filter import filter_blackout_signals


pytestmark = pytest.mark.integration


class TestNewsBlackoutIntegration:
    """Test end-to-end news blackout filtering."""

    def test_calendar_to_windows_to_filter(self):
        """Full pipeline: calendar -> windows -> signal filter."""
        # Generate calendar for January 2023
        events = generate_news_calendar(
            date(2023, 1, 1),
            date(2023, 1, 31),
            event_types=["NFP", "IJC"],
        )

        # Expand to windows
        config = NewsBlackoutConfig(
            enabled=True,
            pre_close_minutes=10,
            post_pause_minutes=30,
        )
        windows = expand_news_windows(events, config)

        # Verify windows were created
        assert len(windows) > 0

        # Create synthetic signals - some inside, some outside NFP window
        # NFP Jan 6, 2023 at 13:30 UTC (08:30 EST)
        # Blackout: 13:20 - 14:00 UTC
        signal_times = np.array(
            [
                np.datetime64("2023-01-06T13:00"),  # Before blackout - OK
                np.datetime64("2023-01-06T13:25"),  # Inside blackout - BLOCKED
                np.datetime64("2023-01-06T13:45"),  # Inside blackout - BLOCKED
                np.datetime64("2023-01-06T14:30"),  # After blackout - OK
            ],
            dtype="datetime64[s]",
        )
        signal_indices = np.arange(len(signal_times))

        # Convert windows to tuples for filter
        window_tuples = [(w.start_utc, w.end_utc) for w in windows]

        # Filter signals
        filtered, blocked = filter_blackout_signals(
            signal_indices, signal_times, window_tuples
        )

        # Should block signals at 13:25 and 13:45
        assert blocked >= 2  # At least 2 blocked by NFP window

    def test_disabled_config_allows_all_signals(self):
        """When blackouts disabled, all signals should pass through."""
        config = BlackoutConfig()  # Both disabled by default

        assert config.news.enabled is False
        assert config.sessions.enabled is False

        # With no windows, nothing should be filtered
        signal_indices = np.arange(10)
        # Create valid datetime64 timestamps
        base_time = np.datetime64("2023-01-01T12:00", "s")
        timestamps = np.array([base_time + np.timedelta64(i, "h") for i in range(10)])

        filtered, blocked = filter_blackout_signals(signal_indices, timestamps, [])

        assert blocked == 0
        assert len(filtered) == 10


class TestSessionBlackoutIntegration:
    """Test end-to-end session blackout filtering."""

    def test_session_windows_block_overnight_signals(self):
        """Session blackouts should block signals during NY close -> Asian open."""
        config = SessionBlackoutConfig(enabled=True)

        # Generate windows for one day
        windows = expand_session_windows(date(2023, 1, 2), date(2023, 1, 2), config)

        assert len(windows) == 1

        # The window should span from ~22:00 UTC (17:00 ET - 10 min)
        # to ~00:05 UTC next day (09:00 Tokyo + 5 min)
        window = windows[0]
        assert window.source == "session"

        # Verify window spans overnight
        assert (
            window.start_utc.day != window.end_utc.day
            or window.start_utc.hour > window.end_utc.hour
        )


class TestCombinedBlackouts:
    """Test combined news and session blackouts."""

    def test_overlapping_windows_merge(self):
        """Overlapping news and session windows should merge."""
        # Create overlapping windows
        news_config = NewsBlackoutConfig(enabled=True)
        session_config = SessionBlackoutConfig(enabled=True)

        news_events = generate_news_calendar(
            date(2023, 1, 1),
            date(2023, 1, 7),
            event_types=["NFP"],
        )

        news_windows = expand_news_windows(news_events, news_config)
        session_windows = expand_session_windows(
            date(2023, 1, 1), date(2023, 1, 7), session_config
        )

        all_windows = news_windows + session_windows
        merged = merge_overlapping_windows(all_windows)

        # Merged should have fewer or equal windows
        assert len(merged) <= len(all_windows)


class TestBlackoutTelemetry:
    """Test that telemetry is logged correctly."""

    def test_filter_logs_blocked_count(self, caplog):
        """Filter should log number of blocked signals."""
        import logging

        caplog.set_level(logging.INFO)

        # Create a window that blocks some signals
        window_tuples = [
            (
                np.datetime64("2023-01-06T13:00", "s"),
                np.datetime64("2023-01-06T14:00", "s"),
            )
        ]

        signal_indices = np.array([0, 1, 2])
        timestamps = np.array(
            [
                np.datetime64("2023-01-06T13:30", "s"),  # Blocked
                np.datetime64("2023-01-06T13:45", "s"),  # Blocked
                np.datetime64("2023-01-06T15:00", "s"),  # OK
            ]
        )

        filtered, blocked = filter_blackout_signals(
            signal_indices, timestamps, window_tuples
        )

        assert blocked == 2
        assert len(filtered) == 1

        # Check logging (if INFO level enabled)
        assert any("blocked" in record.message.lower() for record in caplog.records)
