"""
Blackout window dataclass and window management functions.

This module provides the core BlackoutWindow dataclass and functions for
expanding, merging, and checking blackout windows.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from src.risk.blackout.calendar import NewsEvent
from src.risk.blackout.config import NewsBlackoutConfig


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BlackoutWindow:
    """
    Represents a time period during which new trade entries are blocked.

    Attributes:
        start_utc: Window start time in UTC (timezone-aware).
        end_utc: Window end time in UTC (timezone-aware).
        source: Origin of the window ('news' or 'session').

    Example:
        >>> from datetime import datetime, timezone
        >>> window = BlackoutWindow(
        ...     start_utc=datetime(2023, 1, 6, 13, 20, tzinfo=timezone.utc),
        ...     end_utc=datetime(2023, 1, 6, 14, 0, tzinfo=timezone.utc),
        ...     source="news"
        ... )
        >>> window.source
        'news'
    """

    start_utc: datetime
    end_utc: datetime
    source: Literal["news", "session"]

    def __post_init__(self) -> None:
        """Validate window constraints."""
        if self.end_utc <= self.start_utc:
            msg = "end_utc must be after start_utc"
            raise ValueError(msg)
        if self.start_utc.tzinfo is None or self.end_utc.tzinfo is None:
            msg = "Both timestamps must be timezone-aware"
            raise ValueError(msg)


def expand_news_windows(
    events: Sequence[NewsEvent],
    config: NewsBlackoutConfig,
) -> list[BlackoutWindow]:
    """
    Expand news events into blackout windows.

    Args:
        events: List of news events.
        config: News blackout configuration with timing offsets.

    Returns:
        List of BlackoutWindow objects (one per event).

    Example:
        >>> from src.risk.blackout.calendar import NewsEvent
        >>> from datetime import datetime, timezone
        >>> events = [NewsEvent("NFP", "USD", datetime(2023, 1, 6, 13, 30, tzinfo=timezone.utc))]
        >>> config = NewsBlackoutConfig(enabled=True, pre_close_minutes=10, post_pause_minutes=30)
        >>> windows = expand_news_windows(events, config)
        >>> len(windows)
        1
    """
    windows: list[BlackoutWindow] = []

    for event in events:
        start_utc = event.event_time_utc - timedelta(minutes=config.pre_close_minutes)
        end_utc = event.event_time_utc + timedelta(minutes=config.post_pause_minutes)

        windows.append(
            BlackoutWindow(
                start_utc=start_utc,
                end_utc=end_utc,
                source="news",
            )
        )

    logger.debug(
        "Expanded %d news events into blackout windows",
        len(windows),
        extra={"windows_built": len(windows)},
    )
    return windows


def merge_overlapping_windows(
    windows: Sequence[BlackoutWindow],
) -> list[BlackoutWindow]:
    """
    Merge overlapping or adjacent blackout windows.

    Uses interval union algorithm with O(n log n) complexity.

    Args:
        windows: List of possibly overlapping windows.

    Returns:
        List of merged, non-overlapping windows.

    Example:
        >>> from datetime import datetime, timezone
        >>> w1 = BlackoutWindow(datetime(2023, 1, 6, 13, 0, tzinfo=timezone.utc),
        ...                     datetime(2023, 1, 6, 14, 0, tzinfo=timezone.utc), "news")
        >>> w2 = BlackoutWindow(datetime(2023, 1, 6, 13, 30, tzinfo=timezone.utc),
        ...                     datetime(2023, 1, 6, 15, 0, tzinfo=timezone.utc), "news")
        >>> merged = merge_overlapping_windows([w1, w2])
        >>> len(merged)
        1
    """
    if not windows:
        return []

    # Sort by start time
    sorted_windows = sorted(windows, key=lambda w: w.start_utc)

    merged: list[BlackoutWindow] = []
    current_start = sorted_windows[0].start_utc
    current_end = sorted_windows[0].end_utc
    current_source = sorted_windows[0].source

    for window in sorted_windows[1:]:
        if window.start_utc <= current_end:
            # Overlapping or adjacent - extend current window
            current_end = max(current_end, window.end_utc)
            # Keep source as "news" if either is news, else "session"
            if window.source == "news" or current_source == "news":
                current_source = "news"
        else:
            # Non-overlapping - save current and start new
            merged.append(
                BlackoutWindow(
                    start_utc=current_start,
                    end_utc=current_end,
                    source=current_source,
                )
            )
            current_start = window.start_utc
            current_end = window.end_utc
            current_source = window.source

    # Don't forget the last window
    merged.append(
        BlackoutWindow(
            start_utc=current_start,
            end_utc=current_end,
            source=current_source,
        )
    )

    windows_merged = len(windows) - len(merged)
    if windows_merged > 0:
        logger.debug(
            "Merged %d overlapping windows into %d",
            len(windows),
            len(merged),
            extra={"windows_merged": windows_merged},
        )

    return merged


def is_in_blackout(
    timestamp: datetime,
    windows: Sequence[BlackoutWindow],
) -> bool:
    """
    Check if a timestamp falls within any blackout window.

    Args:
        timestamp: UTC timestamp to check (must be timezone-aware).
        windows: List of blackout windows.

    Returns:
        True if timestamp is within any window (inclusive bounds).

    Example:
        >>> from datetime import datetime, timezone
        >>> window = BlackoutWindow(
        ...     datetime(2023, 1, 6, 13, 0, tzinfo=timezone.utc),
        ...     datetime(2023, 1, 6, 14, 0, tzinfo=timezone.utc),
        ...     "news"
        ... )
        >>> is_in_blackout(datetime(2023, 1, 6, 13, 30, tzinfo=timezone.utc), [window])
        True
    """
    return any(window.start_utc <= timestamp <= window.end_utc for window in windows)


def expand_session_windows(
    start_date,
    end_date,
    config,
) -> list[BlackoutWindow]:
    """
    Expand session gaps into blackout windows.

    Creates windows from NY close (17:00 ET) to Asian open (09:00 Tokyo)
    for each trading day in the date range.

    Args:
        start_date: Start of date range (inclusive).
        end_date: End of date range (inclusive).
        config: SessionBlackoutConfig with timing parameters.

    Returns:
        List of BlackoutWindow objects for session gaps.

    Example:
        >>> from datetime import date
        >>> from src.risk.blackout.config import SessionBlackoutConfig
        >>> config = SessionBlackoutConfig(enabled=True)
        >>> windows = expand_session_windows(date(2023, 1, 1), date(2023, 1, 7), config)
        >>> len(windows) > 0  # Should have windows for each weekday
        True
    """
    from datetime import time, timedelta
    from zoneinfo import ZoneInfo

    windows: list[BlackoutWindow] = []

    ny_tz = ZoneInfo(config.ny_timezone)
    asian_tz = ZoneInfo(config.asian_timezone)
    utc_tz = ZoneInfo("UTC")

    # Parse time strings
    ny_close_parts = config.ny_close_time.split(":")
    asian_open_parts = config.asian_open_time.split(":")
    ny_close_time = time(int(ny_close_parts[0]), int(ny_close_parts[1]))
    asian_open_time = time(int(asian_open_parts[0]), int(asian_open_parts[1]))

    current = start_date
    while current <= end_date:
        # Skip weekends (Saturday=5, Sunday=6)
        if current.weekday() < 5:
            from datetime import datetime

            # NY close on current day
            ny_close_local = datetime.combine(current, ny_close_time, tzinfo=ny_tz)
            window_start = ny_close_local - timedelta(minutes=config.pre_close_minutes)

            # Asian open on next day
            next_day = current + timedelta(days=1)
            asian_open_local = datetime.combine(
                next_day, asian_open_time, tzinfo=asian_tz
            )
            window_end = asian_open_local + timedelta(minutes=config.post_pause_minutes)

            # Convert to UTC
            window_start_utc = window_start.astimezone(utc_tz)
            window_end_utc = window_end.astimezone(utc_tz)

            windows.append(
                BlackoutWindow(
                    start_utc=window_start_utc,
                    end_utc=window_end_utc,
                    source="session",
                )
            )

        current += timedelta(days=1)

    logger.debug(
        "Created %d session blackout windows",
        len(windows),
        extra={"session_windows": len(windows)},
    )

    return windows
