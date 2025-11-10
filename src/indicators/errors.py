"""Error types for indicator enrichment operations.

This module defines specific exceptions for indicator enrichment,
enabling clear error handling in strict and non-strict modes.
"""


class EnrichmentError(Exception):
    """Base exception for enrichment-related errors."""


class UnknownIndicatorError(EnrichmentError):
    """Raised when a requested indicator is not registered.

    This error is raised in strict mode when attempting to compute
    an indicator that doesn't exist in the registry.

    Attributes:
        indicator_name: Name of the unknown indicator.
        available: List of available indicator names.
    """

    def __init__(self, indicator_name: str, available: list[str]):
        """Initialize the error.

        Args:
            indicator_name: Name of the unknown indicator.
            available: List of available indicator names.
        """
        self.indicator_name = indicator_name
        self.available = available
        super().__init__(
            f"Unknown indicator '{indicator_name}'. "
            f"Available: {', '.join(sorted(available))}"
        )


class DuplicateIndicatorError(EnrichmentError):
    """Raised when duplicate indicators are requested.

    This prevents ambiguous overwrite scenarios where the same
    indicator is requested multiple times.

    Attributes:
        duplicates: Set of duplicate indicator names.
    """

    def __init__(self, duplicates: set[str]):
        """Initialize the error.

        Args:
            duplicates: Set of duplicate indicator names.
        """
        self.duplicates = duplicates
        dup_list = ", ".join(sorted(duplicates))
        super().__init__(f"Duplicate indicator names in request: {dup_list}")


class ImmutabilityViolationError(EnrichmentError):
    """Raised when core dataset has been mutated during enrichment.

    This error indicates a programming error where the enrichment
    process modified the original core dataset, violating the
    immutability contract.

    Attributes:
        original_hash: Hash of core dataset before enrichment.
        current_hash: Hash of core dataset after enrichment.
    """

    def __init__(self, original_hash: str, current_hash: str):
        """Initialize the error.

        Args:
            original_hash: Hash of core dataset before enrichment.
            current_hash: Hash of core dataset after enrichment.
        """
        self.original_hash = original_hash
        self.current_hash = current_hash
        super().__init__(
            f"Core dataset mutated during enrichment. "
            f"Original hash: {original_hash[:8]}..., "
            f"Current hash: {current_hash[:8]}..."
        )
