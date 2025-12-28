"""Strategy registry for multi-strategy orchestration.

This module provides a lightweight in-memory registry used to:
- Register strategy callables (backtest entry points or signal generators)
- Retrieve strategies by name
- List available strategies and metadata (tags)

Design Goals (per multi-strategy plan):
- Isolation: registry only stores callable references + metadata
- Determinism: insertion order preserved for predictable iteration
- Simplicity: no external storage; in-memory suffices (Principle VII)

NOTE: This is a foundational skeleton. Full validation (configs, risk limits)
will be layered in subsequent tasks (see tasks T009, T017).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegisteredStrategy:
    """Immutable representation of a registered strategy.

    Attributes:
        name: Unique strategy identifier.
        func: Callable that executes the strategy or produces a result dict.
        tags: Optional list of classification/filtering tags.
        version: Optional semantic version string for reproducibility tracking.
    """

    name: str
    func: Callable
    tags: List[str]
    version: str | None = None


class StrategyRegistry:
    """In-memory registry for strategies.

    Provides simple methods to register and retrieve strategies. Logging uses
    lazy formatting to comply with project standards.
    """

    def __init__(self) -> None:
        self._strategies: Dict[str, RegisteredStrategy] = {}
        logger.info("Initialized StrategyRegistry (empty)")

    # --- Registration & Retrieval -------------------------------------------------
    def register(
        self,
        name: str,
        func: Callable,
        tags: Optional[Iterable[str]] = None,
        version: str | None = None,
        overwrite: bool = False,
        validate_on_register: bool = False,
    ) -> RegisteredStrategy:
        """Register a strategy callable.

        Args:
            name: Unique identifier.
            func: Callable implementing the strategy. Must be deterministic
                  given identical inputs.
            tags: Optional iterable of tag strings.
            version: Optional semantic version string.
            overwrite: Allow replacing an existing strategy with same name.
            validate_on_register: If True, validate strategy contract before
                registering. Raises StrategyValidationError on failure.

        Returns:
            RegisteredStrategy instance.

        Raises:
            ValueError: If name already exists and overwrite=False.
            StrategyValidationError: If validate_on_register=True and validation fails.
        """
        if name in self._strategies and not overwrite:
            raise ValueError(f"Strategy '{name}' already registered")

        # Validate strategy contract if requested
        if validate_on_register:
            from src.strategy.validator import validate_strategy

            validate_strategy(func, strict=True)

        strategy = RegisteredStrategy(
            name=name,
            func=func,
            tags=list(tags) if tags else [],
            version=version,
        )
        self._strategies[name] = strategy
        logger.info(
            "Registered strategy name=%s tags=%d overwrite=%s validated=%s",
            name,
            len(strategy.tags),
            overwrite,
            validate_on_register,
        )
        return strategy

    def get(self, name: str) -> RegisteredStrategy:
        """Retrieve a registered strategy by name.

        Raises:
            KeyError: If strategy name is unknown.
        """
        try:
            return self._strategies[name]
        except KeyError as exc:
            logger.error("Unknown strategy requested name=%s", name)
            raise exc

    def list(self) -> List[RegisteredStrategy]:
        """Return all registered strategies preserving insertion order."""
        return list(self._strategies.values())

    def filter(
        self,
        names: Optional[Iterable[str]] = None,
        tags: Optional[Iterable[str]] = None,
    ) -> List[RegisteredStrategy]:
        """Filter strategies by names and/or tags.

        Args:
            names: Optional list of names to include.
            tags: Optional list of tags; strategy must contain ALL provided tags.
        """
        strategies = self.list()
        if names:
            name_set = set(names)
            strategies = [s for s in strategies if s.name in name_set]
        if tags:
            tag_set = set(tags)
            strategies = [s for s in strategies if tag_set.issubset(set(s.tags))]
        logger.debug("Filtered strategies count=%d", len(strategies))
        return strategies

    # --- Introspection ------------------------------------------------------------
    def count(self) -> int:
        """Return number of registered strategies."""
        return len(self._strategies)

    def has(self, name: str) -> bool:
        """Return True if a strategy with 'name' is registered."""
        return name in self._strategies


__all__ = ["StrategyRegistry", "RegisteredStrategy"]
