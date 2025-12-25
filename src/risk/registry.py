"""
Policy registry for string-based policy lookup.

The PolicyRegistry enables runtime selection of policies via CLI or config
by mapping string identifiers to policy classes.
"""

import logging
from typing import Any, TypeVar

logger = logging.getLogger(__name__)


# Type variable for policy classes
PolicyT = TypeVar("PolicyT")


class PolicyRegistry:
    """
    Registry for policy class lookup by string identifier.

    The registry enables runtime selection of policies via configuration
    or CLI arguments. Policy classes are registered with string keys and
    can be instantiated with optional parameters.

    Examples:
        >>> registry = PolicyRegistry()
        >>> registry.register("ATR", ATRStop, category="stop")
        >>> policy_class = registry.get("ATR", category="stop")
        >>> policy = policy_class(multiplier=2.0)
    """

    def __init__(self) -> None:
        """Initialize empty registry with category-based storage."""
        self._registries: dict[str, dict[str, type]] = {
            "stop": {},
            "tp": {},
            "sizer": {},
        }

    def register(
        self,
        name: str,
        policy_class: type[PolicyT],
        category: str,
    ) -> None:
        """
        Register a policy class with a string identifier.

        Args:
            name: String identifier for the policy (e.g., "ATR", "RiskMultiple").
            policy_class: The policy class to register.
            category: Policy category ("stop", "tp", or "sizer").

        Raises:
            ValueError: If category is not recognized.
        """
        if category not in self._registries:
            raise ValueError(
                "Category must be 'stop', 'tp', or 'sizer', got '%s'",
                category,
            )
        self._registries[category][name] = policy_class
        logger.debug("Registered %s policy: %s", category, name)

    def get(self, name: str, category: str) -> type[PolicyT]:
        """
        Get a policy class by name and category.

        Args:
            name: String identifier for the policy.
            category: Policy category ("stop", "tp", or "sizer").

        Returns:
            The registered policy class.

        Raises:
            KeyError: If policy name is not found in category.
            ValueError: If category is not recognized.
        """
        if category not in self._registries:
            raise ValueError(
                "Category must be 'stop', 'tp', or 'sizer', got '%s'",
                category,
            )
        if name not in self._registries[category]:
            available = list(self._registries[category].keys())
            raise KeyError(
                f"Policy '{name}' not found in '{category}' category. "
                f"Available: {available}"
            )
        return self._registries[category][name]

    def list_policies(self, category: str) -> list[str]:
        """
        List all registered policy names for a category.

        Args:
            category: Policy category ("stop", "tp", or "sizer").

        Returns:
            List of registered policy names.
        """
        if category not in self._registries:
            raise ValueError(
                f"Category must be 'stop', 'tp', or 'sizer', got '{category}'"
            )
        return list(self._registries[category].keys())

    def instantiate(
        self,
        name: str,
        category: str,
        **kwargs: Any,
    ) -> PolicyT:
        """
        Get and instantiate a policy with parameters.

        Args:
            name: String identifier for the policy.
            category: Policy category.
            **kwargs: Parameters to pass to policy constructor.

        Returns:
            Instantiated policy object.
        """
        policy_class = self.get(name, category)
        return policy_class(**kwargs)


# Global policy registry instance
policy_registry = PolicyRegistry()
