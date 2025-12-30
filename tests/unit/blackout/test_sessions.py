"""
Unit tests for session-only trading feature.

Tests validate session definitions, allowed window generation,
and blackout period calculation for non-allowed times.
"""

from datetime import date, datetime, timezone

import pytest

from src.risk.blackout.sessions import (
    TRADING_SESSIONS,
    TradingSession,
    get_session,
    get_allowed_session_windows,
    build_session_only_blackouts,
)
from src.risk.blackout.config import SessionOnlyConfig


pytestmark = pytest.mark.unit


class TestTradingSessions:
    """Test trading session definitions."""

    def test_ny_session_defined(self):
        """NY session should be defined."""
        assert "NY" in TRADING_SESSIONS
        assert TRADING_SESSIONS["NY"].timezone == "America/New_York"

    def test_london_session_defined(self):
        """London session should be defined."""
        assert "LONDON" in TRADING_SESSIONS
        assert TRADING_SESSIONS["LONDON"].timezone == "Europe/London"

    def test_asia_session_defined(self):
        """Asia session should be defined."""
        assert "ASIA" in TRADING_SESSIONS
        assert TRADING_SESSIONS["ASIA"].timezone == "Asia/Tokyo"

    def test_sydney_session_defined(self):
        """Sydney session should be defined."""
        assert "SYDNEY" in TRADING_SESSIONS
        assert TRADING_SESSIONS["SYDNEY"].timezone == "Australia/Sydney"


class TestGetSession:
    """Test session lookup by name."""

    def test_get_ny_case_insensitive(self):
        """Session lookup should be case-insensitive."""
        session = get_session("ny")
        assert session.name == "New York"

    def test_get_london(self):
        """Should return London session."""
        session = get_session("LONDON")
        assert session.name == "London"

    def test_invalid_session_raises(self):
        """Unknown session should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown session"):
            get_session("INVALID")


class TestSessionUtcWindow:
    """Test UTC window calculation for sessions."""

    def test_ny_session_utc_window(self):
        """NY session should convert to UTC correctly."""
        session = get_session("NY")
        start_utc, end_utc = session.get_utc_window(date(2023, 1, 3))

        # January is EST (UTC-5), so 08:00 EST = 13:00 UTC
        assert start_utc.hour == 13
        # 17:00 EST = 22:00 UTC
        assert end_utc.hour == 22

    def test_london_session_utc_window(self):
        """London session should convert to UTC correctly."""
        session = get_session("LONDON")
        start_utc, end_utc = session.get_utc_window(date(2023, 1, 3))

        # January is GMT (no offset), so 08:00 GMT = 08:00 UTC
        assert start_utc.hour == 8
        # 16:00 GMT = 16:00 UTC
        assert end_utc.hour == 16


class TestGetAllowedSessionWindows:
    """Test allowed session window generation."""

    def test_single_session(self):
        """Single session should produce windows for each trading day."""
        windows = get_allowed_session_windows(
            date(2023, 1, 2), date(2023, 1, 6), ["NY"]
        )

        # Mon-Fri = 5 trading days
        assert len(windows) == 5

    def test_overlapping_sessions_merge(self):
        """Overlapping sessions (NY/London) should merge."""
        # NY and London overlap for several hours
        windows = get_allowed_session_windows(
            date(2023, 1, 2), date(2023, 1, 2), ["NY", "LONDON"]
        )

        # Should merge into fewer windows than 2
        assert len(windows) == 1  # Merged into single extended window

    def test_empty_sessions_returns_empty(self):
        """Empty session list should return empty windows."""
        windows = get_allowed_session_windows(date(2023, 1, 2), date(2023, 1, 6), [])
        assert windows == []


class TestBuildSessionOnlyBlackouts:
    """Test blackout generation for non-allowed times."""

    def test_generates_blackouts(self):
        """Should generate blackout periods for non-allowed times."""
        blackouts = build_session_only_blackouts(
            date(2023, 1, 2), date(2023, 1, 2), ["NY"]
        )

        # Should have at least one blackout (before NY opens, after NY closes)
        assert len(blackouts) >= 1

    def test_empty_sessions_returns_empty(self):
        """Empty session list should return empty blackouts."""
        blackouts = build_session_only_blackouts(date(2023, 1, 2), date(2023, 1, 2), [])
        assert blackouts == []


class TestSessionOnlyConfig:
    """Test SessionOnlyConfig model."""

    def test_default_disabled(self):
        """Should be disabled by default."""
        config = SessionOnlyConfig()
        assert config.enabled is False
        assert config.allowed_sessions == []

    def test_with_sessions(self):
        """Should accept session list."""
        config = SessionOnlyConfig(enabled=True, allowed_sessions=["NY", "LONDON"])
        assert config.enabled is True
        assert config.allowed_sessions == ["NY", "LONDON"]
