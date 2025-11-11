"""Indicator registry package for pluggable indicator management.

This package provides a registry system for managing indicator computations
in a pluggable, decoupled manner.
"""

from .specs import IndicatorSpec
from .store import (
    get_indicator,
    get_registry,
    list_indicators,
    register_indicator,
    unregister_indicator,
)


__all__ = [
    "IndicatorSpec",
    "register_indicator",
    "unregister_indicator",
    "get_indicator",
    "list_indicators",
    "get_registry",
]
