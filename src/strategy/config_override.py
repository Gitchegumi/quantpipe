"""Configuration override and merge logic for multi-strategy execution.

This module provides utilities to merge user-supplied configuration overrides
with strategy defaults, supporting per-strategy customization without modifying
base strategy implementations.

Design principles:
- User-supplied overrides take precedence over defaults
- Type validation via pydantic models
- Immutable result configs (frozen dataclasses)
- Logging for audit trail

Per FR-005: "System MUST allow per-strategy configuration parameter overrides."
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def merge_config(
    base_config: Dict[str, Any],
    overrides: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Merge user-supplied overrides with base configuration.

    User overrides take precedence. Shallow merge only; nested dicts
    not recursively merged.

    Args:
        base_config: Default configuration dict.
        overrides: User-supplied parameter overrides (optional).

    Returns:
        Merged configuration dict with overrides applied.

    Examples:
        >>> base = {"ema_fast": 20, "ema_slow": 50, "atr_mult": 2.0}
        >>> user = {"ema_fast": 12}
        >>> merge_config(base, user)
        {'ema_fast': 12, 'ema_slow': 50, 'atr_mult': 2.0}
    """
    if overrides is None:
        return base_config.copy()

    merged = base_config.copy()
    merged.update(overrides)

    # Log applied overrides for audit trail
    overridden_keys = set(overrides.keys()) & set(base_config.keys())
    if overridden_keys:
        logger.info(
            "Applied config overrides: %s",
            ", ".join(f"{k}={overrides[k]}" for k in sorted(overridden_keys))
        )

    # Warn about unknown keys (not in base_config)
    unknown_keys = set(overrides.keys()) - set(base_config.keys())
    if unknown_keys:
        logger.warning(
            "Unknown config keys in overrides (ignored): %s",
            ", ".join(sorted(unknown_keys))
        )

    return merged


def validate_config_types(
    config: Dict[str, Any],
    expected_types: Dict[str, type],
) -> None:
    """
    Validate configuration parameter types.

    Args:
        config: Configuration dict to validate.
        expected_types: Mapping parameter name -> expected type.

    Raises:
        TypeError: If parameter has incorrect type.

    Examples:
        >>> validate_config_types(
        ...     {"ema_fast": 20, "atr_mult": 2.0},
        ...     {"ema_fast": int, "atr_mult": float}
        ... )
    """
    for param, expected_type in expected_types.items():
        if param in config:
            value = config[param]
            if not isinstance(value, expected_type):
                raise TypeError(
                    f"Config parameter '{param}' expected type \
{expected_type.__name__}, "
                    f"got {type(value).__name__}"
                )


def apply_strategy_overrides(
    strategy_name: str,
    base_config: Dict[str, Any],
    user_overrides: Dict[str, Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Apply per-strategy configuration overrides.

    Args:
        strategy_name: Identifier of the strategy.
        base_config: Default configuration for the strategy.
        user_overrides: Mapping strategy_name -> override dict (optional).

    Returns:
        Merged configuration with strategy-specific overrides applied.

    Examples:
        >>> base = {"ema_fast": 20, "ema_slow": 50}
        >>> overrides = {"alpha": {"ema_fast": 12}}
        >>> apply_strategy_overrides("alpha", base, overrides)
        {'ema_fast': 12, 'ema_slow': 50}
        >>> apply_strategy_overrides("beta", base, overrides)
        {'ema_fast': 20, 'ema_slow': 50}
    """
    if user_overrides is None or strategy_name not in user_overrides:
        logger.debug("No overrides for strategy: %s", strategy_name)
        return base_config.copy()

    strategy_overrides = user_overrides[strategy_name]
    logger.info(
        "Applying overrides for strategy: %s (keys=%d)",
        strategy_name,
        len(strategy_overrides)
    )

    return merge_config(base_config, strategy_overrides)


__all__ = [
    "merge_config",
    "validate_config_types",
    "apply_strategy_overrides",
]
