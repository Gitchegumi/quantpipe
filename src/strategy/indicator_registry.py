"""Indicator registry enforcement for strategy-owned indicator model.

This module enforces the architectural principle that indicators must be
declared solely within strategy modules (FR-004: Strategy Ownership Isolation).

The indicator registry provides:
1. Read-only access to strategy-declared indicators
2. Audit trail for indicator usage across scan/simulation phases
3. Validation that no indicators are defined/mutated outside strategy layer
"""

import logging
from typing import Optional

from src.strategy.base import Strategy


logger = logging.getLogger(__name__)


class IndicatorRegistry:
    """Registry for strategy-declared indicators with ownership enforcement.

    This registry ensures that:
    - Indicators are declared only in strategy metadata
    - No indicators are added/removed/modified outside the strategy
    - Indicator list is immutable once extracted from strategy
    - Audit trail tracks indicator usage across execution phases

    Example:
        >>> registry = IndicatorRegistry(strategy)
        >>> indicator_names = registry.get_indicator_names()
        >>> registry.validate_no_extras(actual_indicators)
    """

    def __init__(self, strategy: Strategy):
        """Initialize indicator registry from strategy.

        Args:
            strategy: Strategy instance declaring required indicators

        Raises:
            ValueError: If strategy missing metadata or required_indicators
        """
        self.strategy = strategy
        self._indicator_names: Optional[list[str]] = None
        self._extract_indicators()

    def _extract_indicators(self) -> None:
        """Extract indicator names from strategy metadata.

        Raises:
            ValueError: If strategy metadata invalid
        """
        if not hasattr(self.strategy, "metadata"):
            msg = "Strategy must provide metadata property"
            logger.error(msg)
            raise ValueError(msg)

        metadata = self.strategy.metadata
        if not hasattr(metadata, "required_indicators"):
            msg = "Strategy metadata must declare required_indicators"
            logger.error(msg)
            raise ValueError(msg)

        # Create immutable copy
        self._indicator_names = tuple(metadata.required_indicators)

        logger.info(
            "Registered %d indicators from strategy '%s': %s",
            len(self._indicator_names),
            metadata.name,
            self._indicator_names,
        )

    def get_indicator_names(self) -> tuple[str, ...]:
        """Get immutable tuple of indicator names.

        Returns:
            Tuple of indicator names in declaration order

        Raises:
            RuntimeError: If registry not initialized
        """
        if self._indicator_names is None:
            raise RuntimeError("Indicator registry not initialized")

        return self._indicator_names

    def get_indicator_count(self) -> int:
        """Get count of declared indicators.

        Returns:
            Number of indicators declared by strategy
        """
        return len(self.get_indicator_names())

    def validate_exact_match(self, actual_indicators: list[str]) -> None:
        """Validate that actual indicators exactly match declared indicators.

        Args:
            actual_indicators: List of indicator names actually used

        Raises:
            ValueError: If indicators don't match (extras or missing)
        """
        declared = set(self.get_indicator_names())
        actual = set(actual_indicators)

        extras = actual - declared
        missing = declared - actual

        if extras or missing:
            msg = "Indicator mismatch - Extras: %s, Missing: %s"
            logger.error(msg, sorted(extras), sorted(missing))
            raise ValueError(msg % (sorted(extras), sorted(missing)))

        logger.debug(
            "Indicator validation passed: all %d indicators match", len(declared)
        )

    def validate_no_extras(self, actual_indicators: list[str]) -> None:
        """Validate that no extra indicators exist beyond declared set.

        This allows for missing indicators (e.g., during warm-up) but
        prohibits any indicators not declared by the strategy.

        Args:
            actual_indicators: List of indicator names actually present

        Raises:
            ValueError: If extra indicators found
        """
        declared = set(self.get_indicator_names())
        actual = set(actual_indicators)

        extras = actual - declared

        if extras:
            msg = "Unauthorized indicators found: %s"
            logger.error(msg, sorted(extras))
            raise ValueError(msg % str(sorted(extras)))

        logger.debug("No unauthorized indicators found")

    def validate_subset(self, actual_indicators: list[str]) -> None:
        """Validate that actual indicators are a subset of declared indicators.

        Args:
            actual_indicators: List of indicator names actually used

        Raises:
            ValueError: If any indicator not declared by strategy
        """
        declared = set(self.get_indicator_names())
        actual = set(actual_indicators)

        if not actual.issubset(declared):
            unauthorized = actual - declared
            msg = "Indicators not declared by strategy: %s"
            logger.error(msg, sorted(unauthorized))
            raise ValueError(msg % str(sorted(unauthorized)))

        logger.debug("All %d indicators are declared by strategy", len(actual))

    def is_zero_indicator_strategy(self) -> bool:
        """Check if strategy declares zero indicators.

        Returns:
            True if strategy declares no indicators (edge case)
        """
        return self.get_indicator_count() == 0

    def get_indicator_mapping(self) -> dict[str, int]:
        """Get ordered mapping of indicator names to indices.

        Returns:
            Dictionary mapping indicator names to declaration order indices
        """
        return {name: idx for idx, name in enumerate(self.get_indicator_names())}

    def __repr__(self) -> str:
        """String representation of registry."""
        count = self.get_indicator_count()
        return f"IndicatorRegistry(indicators={count}, strategy={self.strategy.metadata.name})"
