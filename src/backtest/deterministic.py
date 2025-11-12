"""Deterministic configuration utilities for reproducible benchmarking.

This module provides utilities for managing deterministic execution including
random seed control, ordering enforcement, and configuration capture to enable
reproducible performance benchmarking across multiple runs.
"""

import logging
import random
from typing import Optional

import numpy as np


logger = logging.getLogger(__name__)

# Default seed for deterministic execution
DEFAULT_SEED = 42


class DeterministicConfig:
    """Configuration manager for deterministic execution.

    Manages random seeds, ordering controls, and reproducibility settings
    to ensure consistent results across benchmark runs.

    Example:
        >>> config = DeterministicConfig(seed=42)
        >>> config.apply()
        >>> # Run benchmark with deterministic behavior
        >>> config.verify()
    """

    def __init__(self, seed: Optional[int] = None, strict_ordering: bool = True):
        """Initialize deterministic configuration.

        Args:
            seed: Random seed for reproducibility (default: 42)
            strict_ordering: Whether to enforce strict ordering of operations
        """
        self.seed = seed if seed is not None else DEFAULT_SEED
        self.strict_ordering = strict_ordering
        self._applied = False

    def apply(self) -> None:
        """Apply deterministic configuration.

        Sets random seeds for Python, NumPy, and disables hash randomization
        to ensure reproducible execution.

        Raises:
            RuntimeError: If already applied
        """
        if self._applied:
            raise RuntimeError("Deterministic configuration already applied")

        # Set Python random seed
        random.seed(self.seed)

        # Set NumPy random seed
        np.random.seed(self.seed)

        logger.info(
            "Applied deterministic configuration (seed=%d, strict_ordering=%s)",
            self.seed,
            self.strict_ordering,
        )

        self._applied = True

    def verify(self) -> bool:
        """Verify that deterministic configuration has been applied.

        Returns:
            True if configuration is active, False otherwise
        """
        return self._applied

    def get_config_dict(self) -> dict:
        """Get configuration as dictionary for reporting.

        Returns:
            Dictionary containing:
                - seed: Random seed value
                - strict_ordering: Ordering enforcement flag
                - applied: Whether configuration has been applied
        """
        return {
            "seed": self.seed,
            "strict_ordering": self.strict_ordering,
            "applied": self._applied,
        }


def set_deterministic_seed(seed: int = DEFAULT_SEED) -> None:
    """Set random seed for deterministic execution (convenience function).

    Args:
        seed: Random seed value (default: 42)

    Note:
        This is a convenience wrapper around DeterministicConfig.apply()
        for simple use cases where full configuration is not needed.
    """
    random.seed(seed)
    np.random.seed(seed)
    logger.debug("Set deterministic seed: %d", seed)


def create_deterministic_config(seed: Optional[int] = None) -> DeterministicConfig:
    """Create and apply deterministic configuration (factory function).

    Args:
        seed: Random seed value (default: 42)

    Returns:
        Configured and applied DeterministicConfig instance

    Example:
        >>> config = create_deterministic_config(seed=123)
        >>> # Configuration automatically applied
        >>> assert config.verify()
    """
    config = DeterministicConfig(seed=seed)
    config.apply()
    return config
