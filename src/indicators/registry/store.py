"""Indicator registry storage and management.

This module provides the storage and API for registering, unregistering,
and retrieving indicator specifications.
"""

import logging
from typing import Dict, List, Optional

from .specs import IndicatorSpec

logger = logging.getLogger(__name__)


class IndicatorRegistry:
    """Registry for managing indicator specifications."""

    def __init__(self) -> None:
        """Initialize the indicator registry."""
        self._indicators: Dict[str, IndicatorSpec] = {}

    def register(self, spec: IndicatorSpec) -> None:
        """Register an indicator specification.

        Args:
            spec: The indicator specification to register.

        Raises:
            ValueError: If an indicator with the same name already exists.
        """
        if spec.name in self._indicators:
            raise ValueError(
                f"Indicator '{spec.name}' is already registered"
            )

        self._indicators[spec.name] = spec
        logger.info("Registered indicator: %s (v%s)", spec.name, spec.version)

    def unregister(self, name: str) -> None:
        """Unregister an indicator by name.

        Args:
            name: The indicator name to unregister.

        Raises:
            KeyError: If the indicator is not registered.
        """
        if name not in self._indicators:
            raise KeyError(f"Indicator '{name}' is not registered")

        del self._indicators[name]
        logger.info("Unregistered indicator: %s", name)

    def get(self, name: str) -> Optional[IndicatorSpec]:
        """Get an indicator specification by name.

        Args:
            name: The indicator name.

        Returns:
            Optional[IndicatorSpec]: The indicator spec, or None if not found.
        """
        return self._indicators.get(name)

    def list_all(self) -> List[str]:
        """List all registered indicator names.

        Returns:
            List[str]: List of registered indicator names.
        """
        return list(self._indicators.keys())

    def exists(self, name: str) -> bool:
        """Check if an indicator is registered.

        Args:
            name: The indicator name.

        Returns:
            bool: True if registered, False otherwise.
        """
        return name in self._indicators

    def clear(self) -> None:
        """Clear all registered indicators (primarily for testing)."""
        self._indicators.clear()
        logger.info("Cleared indicator registry")


# Global registry instance
_global_registry = IndicatorRegistry()


def get_registry() -> IndicatorRegistry:
    """Get the global indicator registry.

    Returns:
        IndicatorRegistry: The global registry instance.
    """
    return _global_registry


def register_indicator(spec: IndicatorSpec) -> None:
    """Register an indicator in the global registry.

    Args:
        spec: The indicator specification to register.
    """
    _global_registry.register(spec)


def unregister_indicator(name: str) -> None:
    """Unregister an indicator from the global registry.

    Args:
        name: The indicator name to unregister.
    """
    _global_registry.unregister(name)


def get_indicator(name: str) -> Optional[IndicatorSpec]:
    """Get an indicator specification from the global registry.

    Args:
        name: The indicator name.

    Returns:
        Optional[IndicatorSpec]: The indicator spec, or None if not found.
    """
    return _global_registry.get(name)


def list_indicators() -> List[str]:
    """List all registered indicator names.

    Returns:
        List[str]: List of registered indicator names.
    """
    return _global_registry.list_all()
