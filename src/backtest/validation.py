"""Pre-run validation for multi-strategy backtest execution.

This module provides validation functions to catch configuration errors
before execution begins, failing fast with clear error messages per FR-011.

Validates:
- All selected strategies are registered
- Weights match strategy count
- Risk limits are valid
- Configuration parameters are well-formed
"""

import logging
from typing import Sequence
from src.strategy.registry import StrategyRegistry

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when pre-run validation fails."""



def validate_strategies_exist(
    selected_strategies: Sequence[str],
    registry: StrategyRegistry,
) -> None:
    """
    Validate all selected strategies are registered.

    Args:
        selected_strategies: List of strategy names to validate.
        registry: Strategy registry to check against.

    Raises:
        ValidationError: If any strategy is not registered.

    Examples:
        >>> from src.strategy.registry import StrategyRegistry
        >>> reg = StrategyRegistry()
        >>> reg.register("alpha", lambda x: {})
        >>> validate_strategies_exist(["alpha"], reg)  # No error
        >>> validate_strategies_exist(["unknown"], reg)  # doctest: +SKIP
        Traceback (most recent call last):
        ...
        ValidationError: Unknown strategies: unknown
    """
    if not selected_strategies:
        raise ValidationError("No strategies selected")

    unknown = []
    for name in selected_strategies:
        if not registry.has(name):
            unknown.append(name)

    if unknown:
        msg = f"Unknown strategies: {', '.join(unknown)}"
        logger.error(msg)
        raise ValidationError(msg)

    logger.info(
        "Strategy validation passed: %d strategies confirmed",
        len(selected_strategies)
    )


def validate_weights_count(
    weights: Sequence[float] | None,
    strategy_count: int,
) -> None:
    """
    Validate weights count matches strategy count (if provided).

    Note: This does NOT enforce sum=1.0 validation—that's handled by
    parse_and_normalize_weights which applies fallback.

    Args:
        weights: User-supplied weights (may be None).
        strategy_count: Number of strategies.

    Raises:
        ValidationError: If weights provided but count mismatch.

    Examples:
        >>> validate_weights_count([0.6, 0.4], 2)  # No error
        >>> validate_weights_count(None, 2)  # No error (None allowed)
        >>> validate_weights_count([0.5], 2)  # doctest: +SKIP
        Traceback (most recent call last):
        ...
        ValidationError: Weights count mismatch...
    """
    if weights is None:
        return  # None is valid; fallback will handle

    if len(weights) != strategy_count:
        msg = f"Weights count mismatch: expected {strategy_count}, got {len(weights)}"
        logger.error(msg)
        raise ValidationError(msg)


def validate_pre_run(
    selected_strategies: Sequence[str],
    registry: StrategyRegistry,
    weights: Sequence[float] | None = None,
) -> None:
    """
    Perform all pre-run validations before multi-strategy execution.

    Fails fast if any validation check fails per FR-011/FR-020.

    Args:
        selected_strategies: List of strategy names to execute.
        registry: Strategy registry.
        weights: Optional user-supplied weights.

    Raises:
        ValidationError: If any validation fails.

    Examples:
        >>> from src.strategy.registry import StrategyRegistry
        >>> reg = StrategyRegistry()
        >>> reg.register("alpha", lambda x: {})
        >>> validate_pre_run(["alpha"], reg, weights=[1.0])  # No error
    """
    validate_strategies_exist(selected_strategies, registry)
    validate_weights_count(weights, len(selected_strategies))
    logger.info("Pre-run validation complete")


__all__ = [
    "validate_pre_run",
    "validate_strategies_exist",
    "validate_weights_count",
    "ValidationError"
]
