"""Timeframe parsing and validation for multi-timeframe backtesting.

This module provides utilities for parsing and validating timeframe strings
(e.g., '15m', '1h', '1d') used in the backtesting system.

Core Pipeline Integration:
- CLI: --timeframe argument parsed via parse_timeframe()
- Config: backtest.timeframe field validated via validate_timeframe()
- API: timeframe parameter in backtest() function

Supported Formats (FR-003, FR-012, FR-013):
- Xm: X minutes (e.g., '1m', '5m', '15m', '7m', '90m')
- Xh: X hours (e.g., '1h', '2h', '4h', '8h')
- Xd: X days (e.g., '1d')

Where X is a positive integer >= 1.
"""

import re
from dataclasses import dataclass

# Regex pattern for valid timeframe formats: Xm, Xh, or Xd where X >= 1
TIMEFRAME_PATTERN = re.compile(r"^(\d+)(m|h|d)$", re.IGNORECASE)

# Conversion factors to minutes
UNIT_TO_MINUTES = {
    "m": 1,
    "h": 60,
    "d": 1440,
}


@dataclass
class Timeframe:
    """Represents a validated timeframe for backtesting.

    Attributes:
        period_minutes: Total period in minutes (e.g., 120 for '2h').
        original_input: Original user input string (e.g., '2h').
        is_valid: Whether the timeframe is valid.
    """

    period_minutes: int
    original_input: str
    is_valid: bool = True


def parse_timeframe(tf_str: str) -> Timeframe:
    """Parse a timeframe string into a Timeframe object.

    Args:
        tf_str: Timeframe string in format Xm, Xh, or Xd (e.g., '15m', '2h', '1d').

    Returns:
        Timeframe: Parsed timeframe with period_minutes calculated.

    Raises:
        ValueError: If the timeframe format is invalid or value is < 1.

    Examples:
        >>> parse_timeframe('15m')
        Timeframe(period_minutes=15, original_input='15m', is_valid=True)
        >>> parse_timeframe('2h')
        Timeframe(period_minutes=120, original_input='2h', is_valid=True)
        >>> parse_timeframe('1d')
        Timeframe(period_minutes=1440, original_input='1d', is_valid=True)
    """
    if not tf_str or not isinstance(tf_str, str):
        raise ValueError(
            f"Invalid timeframe: '{tf_str}'. "
            "Expected format: Xm, Xh, or Xd (e.g., '15m', '2h', '1d')."
        )

    tf_str = tf_str.strip()
    match = TIMEFRAME_PATTERN.match(tf_str)

    if not match:
        raise ValueError(
            f"Invalid timeframe format: '{tf_str}'. "
            "Expected format: Xm, Xh, or Xd where X is a positive integer >= 1. "
            "Examples: '1m', '15m', '1h', '4h', '1d'."
        )

    value = int(match.group(1))
    unit = match.group(2).lower()

    if value < 1:
        raise ValueError(
            f"Invalid timeframe value: '{tf_str}'. "
            "Value must be >= 1. Examples: '1m', '15m', '1h'."
        )

    period_minutes = value * UNIT_TO_MINUTES[unit]

    return Timeframe(
        period_minutes=period_minutes,
        original_input=tf_str.lower(),
        is_valid=True,
    )


def validate_timeframe(tf: Timeframe) -> None:
    """Validate a Timeframe object.

    Args:
        tf: Timeframe object to validate.

    Raises:
        ValueError: If the timeframe is invalid.
    """
    if not tf.is_valid:
        raise ValueError(f"Invalid timeframe: {tf.original_input}")

    if tf.period_minutes < 1:
        raise ValueError(
            f"Timeframe period must be >= 1 minute, got {tf.period_minutes}"
        )


def format_timeframe(minutes: int) -> str:
    """Format a period in minutes as a human-readable timeframe string.

    Args:
        minutes: Period in minutes.

    Returns:
        Human-readable string (e.g., '15m', '2h', '1d').
    """
    if minutes >= 1440 and minutes % 1440 == 0:
        return f"{minutes // 1440}d"
    elif minutes >= 60 and minutes % 60 == 0:
        return f"{minutes // 60}h"
    else:
        return f"{minutes}m"
