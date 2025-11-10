"""Indicator specification data structures.

This module defines the core data structures for indicator specifications
in the registry system.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

import pandas as pd


@dataclass
class IndicatorSpec:
    """Specification for a registered indicator.

    Attributes:
        name: Unique indicator identifier.
        requires: List of required columns (core or other indicators).
        provides: List of columns this indicator will create.
        compute: Function that computes the indicator.
        version: Semantic version string.
        params: Default parameters for the compute function.
    """

    name: str
    requires: List[str]
    provides: List[str]
    compute: Callable[[pd.DataFrame, Dict[str, Any]], Dict[str, pd.Series]]
    version: str = "1.0.0"
    params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate indicator spec after initialization."""
        if not self.name:
            raise ValueError("Indicator name cannot be empty")

        if not self.requires:
            raise ValueError(f"Indicator '{self.name}' must specify required columns")

        if not self.provides:
            raise ValueError(
                f"Indicator '{self.name}' must specify provided columns"
            )

        if not callable(self.compute):
            raise ValueError(
                f"Indicator '{self.name}' compute must be callable"
            )
