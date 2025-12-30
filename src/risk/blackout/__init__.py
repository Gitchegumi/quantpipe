"""
Blackout window management for backtesting.

This module provides rule-based blackout windows for avoiding trade entries
during high-impact economic news events (NFP, IJC) and low-liquidity session
gaps (NY close → Asian open).

Example:
    >>> from src.risk.blackout import BlackoutConfig, NewsBlackoutConfig
    >>> from src.risk.blackout import generate_news_calendar
    >>> from datetime import date
    >>> config = BlackoutConfig(news=NewsBlackoutConfig(enabled=True))
    >>> events = generate_news_calendar(date(2023, 1, 1), date(2023, 12, 31))
"""

from src.risk.blackout.calendar import (
    NewsEvent,
    generate_ijc_events,
    generate_news_calendar,
    generate_nfp_events,
)
from src.risk.blackout.config import (
    BlackoutConfig,
    NewsBlackoutConfig,
    SessionBlackoutConfig,
    SessionOnlyConfig,
)
from src.risk.blackout.holidays import (
    get_us_holidays_for_year,
    is_us_market_holiday,
)
from src.risk.blackout.windows import (
    BlackoutWindow,
    expand_news_windows,
    expand_session_windows,
    is_in_blackout,
    merge_overlapping_windows,
)
from src.risk.blackout.sessions import (
    TradingSession,
    TRADING_SESSIONS,
    get_session,
    get_allowed_session_windows,
    build_session_only_blackouts,
)


__all__ = [
    # Config models
    "BlackoutConfig",
    "NewsBlackoutConfig",
    "SessionBlackoutConfig",
    "SessionOnlyConfig",
    # Data classes
    "NewsEvent",
    "BlackoutWindow",
    "TradingSession",
    # Calendar generation
    "generate_nfp_events",
    "generate_ijc_events",
    "generate_news_calendar",
    # Window management
    "expand_news_windows",
    "expand_session_windows",
    "merge_overlapping_windows",
    "is_in_blackout",
    # Holiday detection
    "is_us_market_holiday",
    "get_us_holidays_for_year",
    # Session-only trading
    "TRADING_SESSIONS",
    "get_session",
    "get_allowed_session_windows",
    "build_session_only_blackouts",
]
