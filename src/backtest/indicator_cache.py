"""Indicator caching and precomputation utilities.

This module provides caching mechanisms for derived technical indicators
to eliminate redundant computation across parameter combinations within
a single backtest run.

Performance target: ≥80% reduction in repeated indicator compute time.
"""

# pylint: disable=unused-import

from typing import Dict, Any, Optional
import pandas as pd


class IndicatorCache:
    """Lazy-computed cache for technical indicator series.

    Attributes:
        _cache: Internal storage for computed indicator series.
        _dataset_id: Identifier for source dataset to invalidate on data changes.
        _param_signatures: List of parameter combinations cached.
    """

    def __init__(self, dataset_id: Optional[str] = None):
        """Initialize empty indicator cache.

        Args:
            dataset_id: Optional identifier for the source dataset.
        """
        self._cache: Dict[str, pd.Series] = {}
        self._dataset_id = dataset_id
        self._param_signatures: list = []

    def get(self, key: str) -> Optional[pd.Series]:
        """Retrieve cached indicator series by key.

        Args:
            key: Unique identifier for the indicator series.

        Returns:
            Cached series if exists, None otherwise.
        """
        return self._cache.get(key)

    def put(self, key: str, series: pd.Series) -> None:
        """Store indicator series in cache.

        Args:
            key: Unique identifier for the indicator series.
            series: Computed indicator series to cache.
        """
        self._cache[key] = series

    def clear(self) -> None:
        """Clear all cached indicators."""
        self._cache.clear()
        self._param_signatures.clear()
