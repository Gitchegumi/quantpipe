"""Strategy contract validation module.

This module provides validation utilities to check that strategies
conform to the Strategy Protocol before execution, enabling fail-fast
behavior with clear, actionable error messages.

Example:
    from src.strategy.validator import validate_strategy, StrategyValidationError

    try:
        result = validate_strategy(MyStrategy, strict=True)
    except StrategyValidationError as e:
        print(f"Validation failed: {e.errors}")
"""

import inspect
import logging
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating a strategy against the Strategy Protocol contract.

    Attributes:
        is_valid: True if strategy passes all validation checks.
        errors: List of validation error messages.
        strategy_name: Name extracted from strategy metadata (if available).
        checked_methods: Methods that were validated.
        suggestions: Suggested fixes for each error.
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    strategy_name: str = "unknown"
    checked_methods: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class StrategyValidationError(Exception):
    """Exception raised when strategy validation fails.

    Attributes:
        message: Human-readable error summary.
        errors: Detailed list of validation failures.
        suggestions: Suggested fixes for each error.
    """

    def __init__(
        self,
        message: str,
        errors: list[str] | None = None,
        suggestions: list[str] | None = None,
    ) -> None:
        """Initialize StrategyValidationError.

        Args:
            message: Human-readable error summary.
            errors: Detailed list of validation failures.
            suggestions: Suggested fixes for each error.
        """
        super().__init__(message)
        self.message = message
        self.errors = errors or []
        self.suggestions = suggestions or []

    def __str__(self) -> str:
        """Return formatted error message with details."""
        parts = [self.message]
        if self.errors:
            parts.append("\nErrors:")
            for error in self.errors:
                parts.append(f"  - {error}")
        if self.suggestions:
            parts.append("\nSuggestions:")
            for suggestion in self.suggestions:
                parts.append(f"  - {suggestion}")
        return "\n".join(parts)


def validate_strategy(
    strategy: type | object,
    strict: bool = True,
) -> ValidationResult:
    """Validate a strategy against the Strategy Protocol contract.

    Args:
        strategy: Strategy class or instance to validate.
        strict: If True, raises StrategyValidationError on failure.
                If False, returns ValidationResult with errors.

    Returns:
        ValidationResult with is_valid, errors, and suggestions.

    Raises:
        StrategyValidationError: If strict=True and validation fails.
    """
    errors: list[str] = []
    suggestions: list[str] = []
    checked_methods: list[str] = []
    strategy_name = "unknown"

    # Get the instance if a class was passed
    instance = strategy if not isinstance(strategy, type) else None
    strategy_class = strategy if isinstance(strategy, type) else type(strategy)

    # Check for metadata property
    checked_methods.append("metadata")
    if not _has_property(strategy_class, "metadata"):
        errors.append("Missing required property: metadata")
        suggestions.append(
            "Add property: @property\\ndef metadata(self) -> StrategyMetadata: ..."
        )
    else:
        # Try to get metadata if we have an instance
        if instance is not None:
            try:
                metadata = instance.metadata
                strategy_name = getattr(metadata, "name", "unknown")
                # Validate metadata fields
                _validate_metadata_fields(metadata, errors, suggestions)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                errors.append(f"metadata property raised exception: {exc}")
                suggestions.append(
                    "Ensure metadata property returns valid StrategyMetadata"
                )

    # Check for generate_signals method
    checked_methods.append("generate_signals")
    if not hasattr(strategy_class, "generate_signals"):
        errors.append(
            "Missing required method: generate_signals(candles, parameters) -> list"
        )
        suggestions.append(
            "Add method: def generate_signals(self, candles: list, "
            "parameters: dict) -> list: ..."
        )
    elif not callable(getattr(strategy_class, "generate_signals", None)):
        errors.append("generate_signals must be callable")
        suggestions.append("Ensure generate_signals is a method, not an attribute")
    else:
        # Validate signature
        _validate_generate_signals_signature(strategy_class, errors, suggestions)

    is_valid = len(errors) == 0
    result = ValidationResult(
        is_valid=is_valid,
        errors=errors,
        strategy_name=strategy_name,
        checked_methods=checked_methods,
        suggestions=suggestions,
    )

    if not is_valid and strict:
        raise StrategyValidationError(
            message=f"Strategy '{strategy_name}' failed validation",
            errors=errors,
            suggestions=suggestions,
        )

    logger.info(
        "Strategy validation complete: name=%s is_valid=%s errors=%d",
        strategy_name,
        is_valid,
        len(errors),
    )

    return result


def _has_property(cls: type, name: str) -> bool:
    """Check if a class has a property with the given name."""
    for klass in cls.__mro__:
        if name in klass.__dict__:
            attr = klass.__dict__[name]
            if isinstance(attr, property):
                return True
    # Also check if it's accessible as an attribute (for Protocol compatibility)
    return hasattr(cls, name)


def _validate_metadata_fields(
    metadata: Any,
    errors: list[str],
    suggestions: list[str],
) -> None:
    """Validate that metadata has required non-empty fields."""
    # Check name
    name = getattr(metadata, "name", None)
    if not name or not isinstance(name, str) or not name.strip():
        errors.append("metadata.name must be a non-empty string")
        suggestions.append(
            'Set metadata.name to a unique identifier, e.g., "my_strategy"'
        )

    # Check version
    version = getattr(metadata, "version", None)
    if not version or not isinstance(version, str) or not version.strip():
        errors.append("metadata.version must be a non-empty string")
        suggestions.append('Set metadata.version to a semantic version, e.g., "1.0.0"')

    # Check required_indicators
    indicators = getattr(metadata, "required_indicators", None)
    if indicators is None or not isinstance(indicators, list):
        errors.append("metadata.required_indicators must be a list")
        suggestions.append(
            "Set metadata.required_indicators to a list of indicator names, "
            'e.g., ["ema20", "rsi14"]'
        )
    elif len(indicators) == 0:
        errors.append("metadata.required_indicators must not be empty")
        suggestions.append(
            'Add at least one indicator to required_indicators, e.g., ["ema20"]'
        )


def _validate_generate_signals_signature(
    strategy_class: type,
    errors: list[str],
    suggestions: list[str],
) -> None:
    """Validate generate_signals method has correct signature."""
    method = getattr(strategy_class, "generate_signals", None)
    if method is None:
        return

    try:
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())

        # Expected: self, candles, parameters (and optionally direction)
        if len(params) < 3:
            errors.append(
                f"generate_signals has {len(params)} parameters, expected at least 3 "
                "(self, candles, parameters)"
            )
            suggestions.append(
                "Update signature to: def generate_signals(self, candles: list, "
                "parameters: dict) -> list:"
            )
        else:
            # Check parameter names (flexible - just ensure they exist)
            if "candles" not in params and params[1] != "candles":
                errors.append(
                    f"generate_signals second parameter should be 'candles', got '{params[1]}'"
                )
            if "parameters" not in params and params[2] != "parameters":
                errors.append(
                    f"generate_signals third parameter should be 'parameters', "
                    f"got '{params[2]}'"
                )
    except (ValueError, TypeError) as exc:
        logger.debug("Could not inspect generate_signals signature: %s", exc)


__all__ = [
    "ValidationResult",
    "StrategyValidationError",
    "validate_strategy",
]
