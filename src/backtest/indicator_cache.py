"""Indicator caching and precomputation utilities.

This module provides caching mechanisms for derived technical indicators
to eliminate redundant computation across parameter combinations within
a single backtest run.

Performance target: ≥80% reduction in repeated indicator compute time.
"""

# pylint: disable=unused-import

from typing import Dict, Any, Optional, Callable
import hashlib
import json
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

    def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], pd.Series],
        params: Optional[Dict[str, Any]] = None,
    ) -> pd.Series:
        """Retrieve cached series or compute if missing (lazy evaluation).

        This is the primary method for cache-aware indicator computation.

        Args:
            key: Unique identifier for the indicator series.
            compute_fn: Function to compute the indicator if not cached.
            params: Optional parameter dict to track for invalidation.

        Returns:
            Cached or freshly computed indicator series.
        """
        cached = self.get(key)
        if cached is not None:
            return cached

        # Cache miss: compute and store
        series = compute_fn()
        self.put(key, series)

        if params:
            param_sig = self._hash_params(params)
            if param_sig not in self._param_signatures:
                self._param_signatures.append(param_sig)

        return series

    @staticmethod
    def _hash_params(params: Dict[str, Any]) -> str:
        """Generate stable hash for parameter combination.

        Args:
            params: Dictionary of parameters.

        Returns:
            Hex digest of parameter hash.
        """
        canonical_json = json.dumps(params, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()[:16]

    def cache_size(self) -> int:
        """Return number of cached indicator series.

        Returns:
            Count of cached series.
        """
        return len(self._cache)

    def param_count(self) -> int:
        """Return number of unique parameter combinations tracked.

        Returns:
            Count of unique parameter signatures.
        """
        return len(self._param_signatures)
