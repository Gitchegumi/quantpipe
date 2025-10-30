"""
Enumerations for directional backtesting system.

This module defines type-safe enumerations used throughout the
directional backtesting feature to constrain direction modes and
output format options.
"""

from enum import Enum


class DirectionMode(str, Enum):
    """
    Backtest direction mode enumeration.

    Constrains valid backtest modes to LONG-only, SHORT-only, or BOTH directions.
    Inherits from str to enable seamless CLI argument parsing and JSON serialization.

    Attributes:
        LONG: Process only long (buy) signals; ignore short opportunities.
        SHORT: Process only short (sell) signals; ignore long opportunities.
        BOTH: Process both long and short signals; apply conflict resolution.

    Examples:
        >>> DirectionMode.LONG.value
        'LONG'
        >>> DirectionMode.SHORT == "SHORT"
        True
        >>> list(DirectionMode)
        [<DirectionMode.LONG: 'LONG'>, <DirectionMode.SHORT: 'SHORT'>, <DirectionMode.BOTH: 'BOTH'>]
    """

    LONG = "LONG"
    SHORT = "SHORT"
    BOTH = "BOTH"


class OutputFormat(str, Enum):
    """
    Backtest output format enumeration.

    Constrains valid output formats to human-readable text or machine-readable JSON.
    Inherits from str to enable seamless CLI argument parsing.

    Attributes:
        TEXT: Human-readable tabular text output (default).
        JSON: Machine-readable JSON output for programmatic analysis.

    Examples:
        >>> OutputFormat.JSON.value
        'json'
        >>> OutputFormat.TEXT == "text"
        True
    """

    TEXT = "text"
    JSON = "json"
