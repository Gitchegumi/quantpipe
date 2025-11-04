"""Weights parsing and normalization for multi-strategy aggregation.

This module provides utilities to parse user-supplied strategy weights,
validate them, and apply equal-weight fallback when needed per FR-014.

Validation rule (from spec): Weights must match strategy count and sum to
~1.0 (tolerance 1e-6); otherwise apply equal-weight and log warning.
"""

from typing import Sequence
import logging

logger = logging.getLogger(__name__)


def parse_and_normalize_weights(
    weights: Sequence[float] | None,
    strategy_count: int,
) -> list[float]:
    """
    Parse and normalize strategy weights with fallback to equal-weight.

    Args:
        weights: User-supplied weights (may be None, empty, or invalid).
        strategy_count: Number of strategies requiring weights.

    Returns:
        Normalized list of weights summing to 1.0.

    Raises:
        ValueError: If strategy_count is zero or negative.

    Examples:
        >>> parse_and_normalize_weights([0.6, 0.4], 2)
        [0.6, 0.4]
        >>> parse_and_normalize_weights(None, 3)  # doctest: +SKIP
        # Logs warning, returns [0.333..., 0.333..., 0.333...]
        >>> parse_and_normalize_weights([0.5, 0.6], 3)  # doctest: +SKIP
        # Logs warning (mismatch), returns [0.333..., 0.333..., 0.333...]
    """
    if strategy_count <= 0:
        raise ValueError("strategy_count must be positive")

    # No weights provided → equal-weight fallback
    if not weights:
        equal_weight = 1.0 / strategy_count
        logger.warning(
            "No weights provided; applying equal-weight fallback (%.6f per strategy)",
            equal_weight,
        )
        return [equal_weight] * strategy_count

    use_weights = list(weights)

    # Validate length match
    if len(use_weights) != strategy_count:
        logger.warning(
            "Weights length mismatch (expected=%d, got=%d); applying equal-weight fallback",
            strategy_count,
            len(use_weights),
        )
        equal_weight = 1.0 / strategy_count
        return [equal_weight] * strategy_count

    # Validate sum
    weight_sum = sum(use_weights)
    if abs(weight_sum - 1.0) > 1e-6:
        logger.warning(
            "Weights sum=%.6f (expected ~1.0); applying equal-weight fallback",
            weight_sum,
        )
        equal_weight = 1.0 / strategy_count
        return [equal_weight] * strategy_count

    # Valid weights
    return use_weights


__all__ = ["parse_and_normalize_weights"]
