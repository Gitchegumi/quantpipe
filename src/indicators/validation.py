"""Indicator enrichment validation utilities.

This module provides validation utilities for indicator enrichment operations,
including duplicate detection and request validation.
"""

import logging


logger = logging.getLogger(__name__)


def validate_unique_indicators(indicators: list[str]) -> None:
    """Validate that indicator list contains no duplicates.

    Args:
        indicators: List of indicator names.

    Raises:
        ValueError: If duplicate indicator names are found.
    """
    seen = set()
    duplicates = set()

    for indicator in indicators:
        if indicator in seen:
            duplicates.add(indicator)
        seen.add(indicator)

    if duplicates:
        raise ValueError(f"Duplicate indicator names: {', '.join(sorted(duplicates))}")

    logger.debug("Indicator uniqueness validation passed")


def validate_indicator_names(indicators: list[str]) -> None:
    """Validate that indicator names are non-empty and properly formatted.

    Args:
        indicators: List of indicator names.

    Raises:
        ValueError: If any indicator name is invalid.
    """
    if not indicators:
        raise ValueError("Indicator list cannot be empty")

    for indicator in indicators:
        if not indicator or not isinstance(indicator, str):
            raise ValueError(f"Invalid indicator name: {repr(indicator)}")

        if not indicator.strip():
            raise ValueError("Indicator name cannot be whitespace-only")

    logger.debug("Indicator name validation passed")
