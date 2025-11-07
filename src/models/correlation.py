"""Correlation computation entities for portfolio backtesting.

This module defines data structures for tracking rolling correlation state
and correlation matrix storage.
"""
from collections import deque
from datetime import UTC, datetime
from typing import Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from src.models.portfolio import CurrencyPair


class CorrelationWindowState(BaseModel):
    """Rolling correlation computation state for a pair of symbols.

    Attributes:
        pair_a: First currency pair
        pair_b: Second currency pair
        window: Target window length (default 100)
        values_a: Rolling window of returns for pair_a
        values_b: Rolling window of returns for pair_b
        provisional_min: Minimum length for provisional evaluation (default 20)
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    pair_a: CurrencyPair
    pair_b: CurrencyPair
    window: int = Field(default=100, ge=1)
    values_a: deque = Field(default_factory=lambda: deque(maxlen=100))
    values_b: deque = Field(default_factory=lambda: deque(maxlen=100))
    provisional_min: int = Field(default=20, ge=1)

    def update(self, price_a: float, price_b: float) -> Optional[float]:
        """Update rolling window and compute correlation if ready.

        Args:
            price_a: New price for pair_a
            price_b: New price for pair_b

        Returns:
            Current correlation coefficient if provisional_min met, else None
        """
        # pylint: disable=no-member
        self.values_a.append(price_a)
        self.values_b.append(price_b)

        if len(self.values_a) < self.provisional_min:
            return None

        # Compute correlation using numpy
        arr_a = np.array(self.values_a)
        arr_b = np.array(self.values_b)

        # Handle edge case of zero variance
        if np.std(arr_a) == 0 or np.std(arr_b) == 0:
            return 0.0

        correlation = np.corrcoef(arr_a, arr_b)[0, 1]
        return float(correlation)

    def is_ready(self) -> bool:
        """Check if window is at target length.

        Returns:
            True if window length equals target, False otherwise
        """
        return len(self.values_a) >= self.window


class CorrelationMatrix(BaseModel):
    """Current pairwise correlation values.

    Attributes:
        values: Dictionary mapping pair tokens to correlation values
        timestamp: Last update timestamp
    """

    values: dict[str, float] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def make_key(pair_a: CurrencyPair, pair_b: CurrencyPair) -> str:
        """Create lexicographically ordered key for pair.

        Args:
            pair_a: First currency pair
            pair_b: Second currency pair

        Returns:
            Sorted key string (e.g., 'EURUSD:GBPUSD')
        """
        codes = sorted([pair_a.code, pair_b.code])
        return f"{codes[0]}:{codes[1]}"

    def get_correlation(
        self, pair_a: CurrencyPair, pair_b: CurrencyPair
    ) -> float:
        """Get correlation between two pairs.

        Args:
            pair_a: First currency pair
            pair_b: Second currency pair

        Returns:
            Correlation value, or 0.0 if not found
        """
        key = self.make_key(pair_a, pair_b)
        return self.values.get(key, 0.0)  # pylint: disable=no-member

    def set_correlation(
        self, pair_a: CurrencyPair, pair_b: CurrencyPair, correlation: float
    ) -> None:
        """Set correlation between two pairs.

        Args:
            pair_a: First currency pair
            pair_b: Second currency pair
            correlation: Correlation value to set
        """
        key = self.make_key(pair_a, pair_b)
        self.values[key] = correlation
        self.timestamp = datetime.now(UTC)
