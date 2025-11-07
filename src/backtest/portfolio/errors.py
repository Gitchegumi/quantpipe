"""Custom exceptions for portfolio operations.

This module defines exception classes for portfolio-specific error conditions
during multi-symbol backtesting.
"""


class PortfolioError(Exception):
    """Base exception for portfolio operations."""


class SymbolNotFoundError(PortfolioError):
    """Raised when a requested symbol's dataset is not found."""


class InsufficientOverlapError(PortfolioError):
    """Raised when datasets lack sufficient temporal overlap."""


class AllocationError(PortfolioError):
    """Raised when allocation computation fails."""


class CorrelationError(PortfolioError):
    """Raised when correlation computation fails."""


class SymbolIsolationError(PortfolioError):
    """Raised when a symbol must be isolated due to runtime failure."""


class InvalidWeightError(PortfolioError):
    """Raised when allocation weights are invalid."""
