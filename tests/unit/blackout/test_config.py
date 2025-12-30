"""
Unit tests for blackout configuration models.

Tests validate:
- Default values match specification
- Pydantic validation constraints
- Backward compatibility (None = disabled)
"""

import pytest

from src.risk.blackout.config import (
    BlackoutConfig,
    NewsBlackoutConfig,
    SessionBlackoutConfig,
)


pytestmark = pytest.mark.unit


class TestNewsBlackoutConfigDefaults:
    """Test NewsBlackoutConfig default values."""

    def test_default_disabled(self):
        """News blackouts should be disabled by default."""
        config = NewsBlackoutConfig()
        assert config.enabled is False

    def test_default_pre_close_minutes(self):
        """Default pre_close_minutes should be 10."""
        config = NewsBlackoutConfig()
        assert config.pre_close_minutes == 10

    def test_default_post_pause_minutes(self):
        """Default post_pause_minutes should be 30."""
        config = NewsBlackoutConfig()
        assert config.post_pause_minutes == 30

    def test_default_force_close_off(self):
        """Force close should default to OFF (FR-005)."""
        config = NewsBlackoutConfig()
        assert config.force_close is False

    def test_default_event_types(self):
        """Default event types should be NFP and IJC."""
        config = NewsBlackoutConfig()
        assert config.event_types == ["NFP", "IJC"]


class TestSessionBlackoutConfigDefaults:
    """Test SessionBlackoutConfig default values."""

    def test_default_disabled(self):
        """Session blackouts should be disabled by default."""
        config = SessionBlackoutConfig()
        assert config.enabled is False

    def test_default_pre_close_minutes(self):
        """Default pre_close_minutes should be 10."""
        config = SessionBlackoutConfig()
        assert config.pre_close_minutes == 10

    def test_default_post_pause_minutes(self):
        """Default post_pause_minutes for sessions should be 5."""
        config = SessionBlackoutConfig()
        assert config.post_pause_minutes == 5

    def test_default_ny_close_time(self):
        """Default NY close time should be 17:00."""
        config = SessionBlackoutConfig()
        assert config.ny_close_time == "17:00"

    def test_default_asian_open_time(self):
        """Default Asian open time should be 09:00."""
        config = SessionBlackoutConfig()
        assert config.asian_open_time == "09:00"

    def test_default_timezones(self):
        """Default timezones should be set correctly."""
        config = SessionBlackoutConfig()
        assert config.ny_timezone == "America/New_York"
        assert config.asian_timezone == "Asia/Tokyo"


class TestBlackoutConfigDefaults:
    """Test BlackoutConfig composite model."""

    def test_default_both_disabled(self):
        """Both news and session blackouts should be disabled by default."""
        config = BlackoutConfig()
        assert config.news.enabled is False
        assert config.sessions.enabled is False

    def test_any_enabled_false_when_both_disabled(self):
        """any_enabled should be False when both are disabled."""
        config = BlackoutConfig()
        assert config.any_enabled is False

    def test_any_enabled_true_when_news_enabled(self):
        """any_enabled should be True when news is enabled."""
        config = BlackoutConfig(news=NewsBlackoutConfig(enabled=True))
        assert config.any_enabled is True

    def test_any_enabled_true_when_sessions_enabled(self):
        """any_enabled should be True when sessions is enabled."""
        config = BlackoutConfig(sessions=SessionBlackoutConfig(enabled=True))
        assert config.any_enabled is True


class TestBlackoutConfigValidation:
    """Test pydantic validation constraints."""

    def test_pre_close_minutes_minimum(self):
        """pre_close_minutes cannot be negative."""
        with pytest.raises(ValueError):
            NewsBlackoutConfig(pre_close_minutes=-1)

    def test_pre_close_minutes_maximum(self):
        """pre_close_minutes cannot exceed 60."""
        with pytest.raises(ValueError):
            NewsBlackoutConfig(pre_close_minutes=61)

    def test_post_pause_minutes_news_maximum(self):
        """post_pause_minutes for news cannot exceed 120."""
        with pytest.raises(ValueError):
            NewsBlackoutConfig(post_pause_minutes=121)

    def test_valid_configuration(self):
        """Valid configuration should be accepted."""
        config = NewsBlackoutConfig(
            enabled=True,
            pre_close_minutes=15,
            post_pause_minutes=45,
        )
        assert config.enabled is True
        assert config.pre_close_minutes == 15
        assert config.post_pause_minutes == 45
