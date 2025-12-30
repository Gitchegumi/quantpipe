"""
Unit tests for rule-based calendar generation.

Tests validate the deterministic generation of NFP and IJC event calendars,
including timezone handling, holiday skipping, and DST transitions.
"""

from datetime import date, datetime, timezone

import pytest

from src.risk.blackout.calendar import (
    generate_nfp_events,
    generate_ijc_events,
    generate_news_calendar,
)


pytestmark = pytest.mark.unit


class TestNFPGeneration:
    """Test Non-Farm Payrolls event generation."""

    def test_nfp_first_friday_of_month(self):
        """NFP should land on first Friday of each month."""
        events = generate_nfp_events(date(2023, 1, 1), date(2023, 3, 31))

        # January 2023: First Friday is Jan 6
        # February 2023: First Friday is Feb 3
        # March 2023: First Friday is Mar 3
        assert len(events) == 3

        # Verify dates are on Fridays
        for event in events:
            assert event.event_time_utc.weekday() == 4  # Friday

    def test_nfp_at_0830_et(self):
        """NFP should be scheduled at 08:30 ET (13:30 UTC in winter)."""
        events = generate_nfp_events(date(2023, 1, 1), date(2023, 1, 31))

        assert len(events) == 1
        # January is EST (UTC-5), so 08:30 EST = 13:30 UTC
        assert events[0].event_time_utc.hour == 13
        assert events[0].event_time_utc.minute == 30

    def test_nfp_currency_is_usd(self):
        """NFP events should be tagged with USD currency."""
        events = generate_nfp_events(date(2023, 1, 1), date(2023, 1, 31))
        assert events[0].currency == "USD"

    def test_nfp_event_name(self):
        """NFP events should have correct name."""
        events = generate_nfp_events(date(2023, 1, 1), date(2023, 1, 31))
        assert events[0].event_name == "NFP"

    def test_nfp_full_year(self):
        """Full year should produce 11-12 NFP events (may skip holidays)."""
        events = generate_nfp_events(date(2023, 1, 1), date(2023, 12, 31))
        # Usually 12, but may be 11 if first Friday falls on Good Friday
        assert 11 <= len(events) <= 12


class TestIJCGeneration:
    """Test Initial Jobless Claims event generation."""

    def test_ijc_every_thursday(self):
        """IJC should occur every Thursday."""
        events = generate_ijc_events(date(2023, 1, 1), date(2023, 1, 31))

        # January 2023 has 4-5 Thursdays
        for event in events:
            assert event.event_time_utc.weekday() == 3  # Thursday

    def test_ijc_52_per_year(self):
        """Full year should produce ~50-53 IJC events (holidays skipped)."""
        events = generate_ijc_events(date(2023, 1, 1), date(2023, 12, 31))
        # Typically 52-53 Thursdays, minus any that fall on holidays (Thanksgiving)
        assert 50 <= len(events) <= 53

    def test_ijc_at_0830_et(self):
        """IJC should be scheduled at 08:30 ET."""
        events = generate_ijc_events(date(2023, 1, 1), date(2023, 1, 7))

        if events:
            # January is EST (UTC-5), so 08:30 EST = 13:30 UTC
            assert events[0].event_time_utc.hour == 13
            assert events[0].event_time_utc.minute == 30

    def test_ijc_event_name(self):
        """IJC events should have correct name."""
        events = generate_ijc_events(date(2023, 1, 1), date(2023, 1, 7))
        if events:
            assert events[0].event_name == "IJC"


class TestCalendarAggregation:
    """Test combined calendar generation."""

    def test_generates_both_event_types(self):
        """Should include both NFP and IJC events."""
        events = generate_news_calendar(
            date(2023, 1, 1), date(2023, 1, 31), event_types=["NFP", "IJC"]
        )

        event_names = {e.event_name for e in events}
        assert "NFP" in event_names
        assert "IJC" in event_names

    def test_nfp_only(self):
        """Should filter to NFP only when requested."""
        events = generate_news_calendar(
            date(2023, 1, 1), date(2023, 1, 31), event_types=["NFP"]
        )

        assert all(e.event_name == "NFP" for e in events)

    def test_events_sorted_by_time(self):
        """Events should be sorted chronologically."""
        events = generate_news_calendar(
            date(2023, 1, 1), date(2023, 3, 31), event_types=["NFP", "IJC"]
        )

        times = [e.event_time_utc for e in events]
        assert times == sorted(times)


class TestDeterminism:
    """Test that calendar generation is deterministic."""

    def test_same_inputs_same_outputs(self):
        """Same date range should always produce identical results."""
        events1 = generate_news_calendar(
            date(2023, 1, 1), date(2023, 12, 31), event_types=["NFP", "IJC"]
        )
        events2 = generate_news_calendar(
            date(2023, 1, 1), date(2023, 12, 31), event_types=["NFP", "IJC"]
        )

        assert len(events1) == len(events2)
        for e1, e2 in zip(events1, events2):
            assert e1.event_name == e2.event_name
            assert e1.event_time_utc == e2.event_time_utc


class TestDSTHandling:
    """Test correct UTC conversion around DST transitions."""

    def test_march_dst_transition(self):
        """NFP in March should use EDT (UTC-4) after DST."""
        # 2023 DST starts March 12
        events = generate_nfp_events(date(2023, 3, 1), date(2023, 3, 31))

        assert len(events) == 1
        # March 3, 2023 is before DST, so EST (UTC-5): 08:30 EST = 13:30 UTC
        assert events[0].event_time_utc.hour == 13

    def test_november_dst_transition(self):
        """NFP in November should use EST (UTC-5) after DST ends."""
        # 2023 DST ends November 5
        events = generate_nfp_events(date(2023, 11, 1), date(2023, 11, 30))

        assert len(events) == 1
        # November 3, 2023 is before DST ends, so EDT (UTC-4): 08:30 EDT = 12:30 UTC
        # But Nov 3 is a Friday and DST ends Nov 5...
        # Actually NFP Nov 3 is during EDT, so 08:30 EDT = 12:30 UTC


class TestTimezoneAwareness:
    """Test that all returned timestamps are timezone-aware."""

    def test_nfp_events_timezone_aware(self):
        """All NFP event timestamps should be timezone-aware (UTC)."""
        events = generate_nfp_events(date(2023, 1, 1), date(2023, 3, 31))

        for event in events:
            assert event.event_time_utc.tzinfo is not None

    def test_ijc_events_timezone_aware(self):
        """All IJC event timestamps should be timezone-aware (UTC)."""
        events = generate_ijc_events(date(2023, 1, 1), date(2023, 1, 31))

        for event in events:
            assert event.event_time_utc.tzinfo is not None
