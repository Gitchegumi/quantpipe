"""
Trading session definitions for session-only trading.

Defines the major forex trading sessions with their local hours and timezones.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class TradingSession:
    """Definition of a trading session with local hours."""

    name: str
    start_time: time
    end_time: time
    timezone: str

    def get_utc_window(self, trading_date: date) -> tuple[datetime, datetime]:
        """
        Get UTC start/end times for this session on a given date.

        Args:
            trading_date: The date to calculate session times for.

        Returns:
            Tuple of (start_utc, end_utc) datetimes.
        """
        tz = ZoneInfo(self.timezone)
        utc = ZoneInfo("UTC")

        local_start = datetime.combine(trading_date, self.start_time, tzinfo=tz)
        local_end = datetime.combine(trading_date, self.end_time, tzinfo=tz)

        return (local_start.astimezone(utc), local_end.astimezone(utc))


# Standard trading session definitions
TRADING_SESSIONS: dict[str, TradingSession] = {
    "NY": TradingSession(
        name="New York",
        start_time=time(8, 0),
        end_time=time(17, 0),
        timezone="America/New_York",
    ),
    "LONDON": TradingSession(
        name="London",
        start_time=time(8, 0),
        end_time=time(16, 0),
        timezone="Europe/London",
    ),
    "ASIA": TradingSession(
        name="Asian",
        start_time=time(9, 0),
        end_time=time(18, 0),
        timezone="Asia/Tokyo",
    ),
    "SYDNEY": TradingSession(
        name="Sydney",
        start_time=time(7, 0),
        end_time=time(16, 0),
        timezone="Australia/Sydney",
    ),
}


def get_session(name: str) -> TradingSession:
    """
    Get a trading session by name.

    Args:
        name: Session name (case-insensitive): NY, LONDON, ASIA, SYDNEY.

    Returns:
        TradingSession definition.

    Raises:
        ValueError: If session name is not recognized.
    """
    key = name.upper()
    if key not in TRADING_SESSIONS:
        valid = ", ".join(TRADING_SESSIONS.keys())
        msg = f"Unknown session '{name}'. Valid sessions: {valid}"
        raise ValueError(msg)
    return TRADING_SESSIONS[key]


def get_allowed_session_windows(
    start_date: date,
    end_date: date,
    allowed_sessions: list[str],
) -> list[tuple[datetime, datetime]]:
    """
    Generate windows of ALLOWED trading times for specified sessions.

    Args:
        start_date: Start of date range.
        end_date: End of date range.
        allowed_sessions: List of session names (e.g., ["NY", "LONDON"]).

    Returns:
        List of (start_utc, end_utc) tuples for allowed trading periods.
        Overlapping sessions are merged.
    """
    from src.risk.blackout.windows import merge_overlapping_windows, BlackoutWindow

    if not allowed_sessions:
        return []

    # Get session definitions
    sessions = [get_session(name) for name in allowed_sessions]

    # Generate allowed windows for each day
    all_windows = []
    current = start_date

    while current <= end_date:
        # Skip weekends
        if current.weekday() < 5:
            for session in sessions:
                start_utc, end_utc = session.get_utc_window(current)
                # Use BlackoutWindow for merging, then extract tuples
                all_windows.append(BlackoutWindow(start_utc, end_utc, "session"))
        current += timedelta(days=1)

    # Merge overlapping windows (e.g., NY/London overlap)
    if all_windows:
        merged = merge_overlapping_windows(all_windows)
        return [(w.start_utc, w.end_utc) for w in merged]

    return []


def build_session_only_blackouts(
    start_date: date,
    end_date: date,
    allowed_sessions: list[str],
) -> list[tuple[datetime, datetime]]:
    """
    Build blackout windows for times OUTSIDE allowed sessions.

    This inverts the allowed session windows to create blackout periods.

    Args:
        start_date: Start of date range.
        end_date: End of date range.
        allowed_sessions: List of session names (e.g., ["NY", "LONDON"]).

    Returns:
        List of (start_utc, end_utc) tuples for blackout periods.

    Example:
        >>> from datetime import date
        >>> blackouts = build_session_only_blackouts(
        ...     date(2023, 1, 2), date(2023, 1, 2), ["NY"]
        ... )
        >>> len(blackouts) >= 1  # Will have blackout before and after NY session
        True
    """
    if not allowed_sessions:
        return []

    # Get allowed windows (already merged)
    allowed = get_allowed_session_windows(start_date, end_date, allowed_sessions)

    if not allowed:
        return []

    # Invert allowed windows to get blackout windows
    # Blackouts are the gaps between allowed windows
    blackouts = []

    # Sort by start time
    sorted_allowed = sorted(allowed, key=lambda w: w[0])

    # Blackout before first allowed window (from start of day)
    utc = ZoneInfo("UTC")
    day_start = datetime.combine(start_date, time(0, 0), tzinfo=utc)

    if sorted_allowed[0][0] > day_start:
        blackouts.append((day_start, sorted_allowed[0][0]))

    # Blackouts between allowed windows
    for i in range(len(sorted_allowed) - 1):
        current_end = sorted_allowed[i][1]
        next_start = sorted_allowed[i + 1][0]

        if next_start > current_end:
            blackouts.append((current_end, next_start))

    # Blackout after last allowed window (to end of date range)
    day_end = datetime.combine(end_date + timedelta(days=1), time(0, 0), tzinfo=utc)

    if sorted_allowed[-1][1] < day_end:
        blackouts.append((sorted_allowed[-1][1], day_end))

    return blackouts
