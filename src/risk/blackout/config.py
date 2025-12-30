"""
Blackout configuration with pydantic validation.

This module defines configuration models for news and session blackout windows,
including timing offsets and force-close behavior settings.
"""


from pydantic import BaseModel, Field


class NewsBlackoutConfig(BaseModel):
    """
    Configuration for news-based blackout windows.

    Attributes:
        enabled: Enable news blackouts (default: False).
        pre_close_minutes: Minutes before event to start blackout (default: 10).
        post_pause_minutes: Minutes after event to end blackout (default: 30).
        force_close: Force-close open positions at blackout start (default: False).
        event_types: Event types to include (default: ["NFP", "IJC"]).

    Example:
        >>> config = NewsBlackoutConfig(enabled=True)
        >>> config.pre_close_minutes
        10
    """

    enabled: bool = False
    pre_close_minutes: int = Field(default=10, ge=0, le=60)
    post_pause_minutes: int = Field(default=30, ge=0, le=120)
    force_close: bool = False
    event_types: list[str] = Field(default_factory=lambda: ["NFP", "IJC"])


class SessionBlackoutConfig(BaseModel):
    """
    Configuration for session-based blackout windows.

    Attributes:
        enabled: Enable session blackouts (default: False).
        pre_close_minutes: Minutes before NY close to start (default: 10).
        post_pause_minutes: Minutes after Asian open to end (default: 5).
        force_close: Force-close open positions (default: False).
        ny_close_time: NY close time in HH:MM format (default: "17:00").
        asian_open_time: Asian open time in HH:MM format (default: "09:00").
        ny_timezone: Timezone for NY close (default: "America/New_York").
        asian_timezone: Timezone for Asian open (default: "Asia/Tokyo").

    Example:
        >>> config = SessionBlackoutConfig(enabled=True)
        >>> config.ny_close_time
        '17:00'
    """

    enabled: bool = False
    pre_close_minutes: int = Field(default=10, ge=0, le=60)
    post_pause_minutes: int = Field(default=5, ge=0, le=60)
    force_close: bool = False
    ny_close_time: str = "17:00"
    asian_open_time: str = "09:00"
    ny_timezone: str = "America/New_York"
    asian_timezone: str = "Asia/Tokyo"


class BlackoutConfig(BaseModel):
    """
    Top-level configuration combining news and session blackouts.

    Attributes:
        news: News blackout settings.
        sessions: Session blackout settings.

    Example:
        >>> config = BlackoutConfig()
        >>> config.news.enabled
        False
        >>> config.sessions.enabled
        False
    """

    news: NewsBlackoutConfig = Field(default_factory=NewsBlackoutConfig)
    sessions: SessionBlackoutConfig = Field(default_factory=SessionBlackoutConfig)

    @property
    def any_enabled(self) -> bool:
        """Return True if any blackout type is enabled."""
        return self.news.enabled or self.sessions.enabled
