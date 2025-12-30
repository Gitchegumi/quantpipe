"""
Rule-based economic event calendar generation.

This module generates deterministic news event calendars for NFP (Non-Farm Payrolls)
and IJC (Initial Jobless Claims) without external data dependencies.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from src.risk.blackout.holidays import is_us_market_holiday


# Timezone constants
ET_ZONE = ZoneInfo("America/New_York")
UTC_ZONE = ZoneInfo("UTC")

# Event release time (08:30 ET)
RELEASE_TIME = time(8, 30)


@dataclass(frozen=True)
class NewsEvent:
    """
    Represents a scheduled economic news release.

    Attributes:
        event_name: Event identifier (e.g., "NFP", "IJC").
        currency: Currency affected (e.g., "USD").
        event_time_utc: Scheduled release time in UTC (timezone-aware).
        impact_level: Event impact level.

    Example:
        >>> from datetime import datetime, timezone
        >>> event = NewsEvent(
        ...     event_name="NFP",
        ...     currency="USD",
        ...     event_time_utc=datetime(2023, 1, 6, 13, 30, tzinfo=timezone.utc),
        ...     impact_level="high"
        ... )
        >>> event.event_name
        'NFP'
    """

    event_name: str
    currency: str
    event_time_utc: datetime
    impact_level: Literal["high", "medium"] = "high"

    def __post_init__(self) -> None:
        """Validate event constraints."""
        if not self.event_name:
            raise ValueError("event_name must not be empty")
        if len(self.currency) != 3:
            raise ValueError("currency must be a 3-character code")
        if self.event_time_utc.tzinfo is None:
            raise ValueError("event_time_utc must be timezone-aware")


def _first_friday_of_month(year: int, month: int) -> date:
    """Find the first Friday of a given month."""
    first_day = date(year, month, 1)
    days_until_friday = (4 - first_day.weekday()) % 7  # Friday = 4
    return first_day + timedelta(days=days_until_friday)


def _to_utc(event_date: date, local_time: time, tz: ZoneInfo) -> datetime:
    """
    Convert a local date/time to UTC datetime.

    Handles DST transitions correctly by creating a localized datetime first.

    Args:
        event_date: The date of the event.
        local_time: The local time of the event.
        tz: The timezone of the local time.

    Returns:
        UTC datetime with timezone info.
    """
    local_dt = datetime.combine(event_date, local_time, tzinfo=tz)
    return local_dt.astimezone(UTC_ZONE)


def generate_nfp_events(
    start_date: date,
    end_date: date,
) -> list[NewsEvent]:
    """
    Generate Non-Farm Payrolls events for a date range.

    NFP is released on the first Friday of each month at 08:30 ET.
    Events falling on U.S. market holidays are skipped.

    Args:
        start_date: Start of date range (inclusive).
        end_date: End of date range (inclusive).

    Returns:
        List of NewsEvent objects sorted chronologically.

    Example:
        >>> events = generate_nfp_events(date(2023, 1, 1), date(2023, 12, 31))
        >>> len(events)
        12
    """
    events: list[NewsEvent] = []

    # Iterate through each month in the range
    current = date(start_date.year, start_date.month, 1)
    while current <= end_date:
        nfp_date = _first_friday_of_month(current.year, current.month)

        # Check if within range and not a holiday
        if start_date <= nfp_date <= end_date:
            if not is_us_market_holiday(nfp_date):
                event_time_utc = _to_utc(nfp_date, RELEASE_TIME, ET_ZONE)
                events.append(
                    NewsEvent(
                        event_name="NFP",
                        currency="USD",
                        event_time_utc=event_time_utc,
                        impact_level="high",
                    )
                )

        # Move to next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    return events


def generate_ijc_events(
    start_date: date,
    end_date: date,
) -> list[NewsEvent]:
    """
    Generate Initial Jobless Claims events for a date range.

    IJC is released every Thursday at 08:30 ET.
    Events falling on U.S. market holidays are skipped.

    Args:
        start_date: Start of date range (inclusive).
        end_date: End of date range (inclusive).

    Returns:
        List of NewsEvent objects sorted chronologically.

    Example:
        >>> events = generate_ijc_events(date(2023, 1, 1), date(2023, 12, 31))
        >>> 52 <= len(events) <= 53
        True
    """
    events: list[NewsEvent] = []

    # Find first Thursday >= start_date
    days_until_thursday = (3 - start_date.weekday()) % 7  # Thursday = 3
    current = start_date + timedelta(days=days_until_thursday)

    while current <= end_date:
        if not is_us_market_holiday(current):
            event_time_utc = _to_utc(current, RELEASE_TIME, ET_ZONE)
            events.append(
                NewsEvent(
                    event_name="IJC",
                    currency="USD",
                    event_time_utc=event_time_utc,
                    impact_level="high",
                )
            )

        # Move to next Thursday
        current += timedelta(days=7)

    return events


def generate_news_calendar(
    start_date: date,
    end_date: date,
    event_types: list[str] | None = None,
) -> list[NewsEvent]:
    """
    Generate a combined news calendar for multiple event types.

    Args:
        start_date: Start of date range (inclusive).
        end_date: End of date range (inclusive).
        event_types: List of event types to include (default: ["NFP", "IJC"]).

    Returns:
        List of NewsEvent objects sorted chronologically.

    Example:
        >>> events = generate_news_calendar(
        ...     date(2023, 1, 1),
        ...     date(2023, 12, 31),
        ...     event_types=["NFP", "IJC"]
        ... )
        >>> len(events) > 50  # ~12 NFP + ~52 IJC
        True
    """
    if event_types is None:
        event_types = ["NFP", "IJC"]

    all_events: list[NewsEvent] = []

    if "NFP" in event_types:
        all_events.extend(generate_nfp_events(start_date, end_date))

    if "IJC" in event_types:
        all_events.extend(generate_ijc_events(start_date, end_date))

    # Sort chronologically
    return sorted(all_events, key=lambda e: e.event_time_utc)
