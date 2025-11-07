"""Correlation computation service for portfolio backtesting.

This module provides a rolling window correlation calculator that maintains
pairwise correlation state across multiple symbols. It implements provisional
window logic (minimum 20 periods) that grows to a full 100-period window per
FR-010 and research Decision 8.

The service manages:
- Per-pair rolling correlation windows
- Provisional correlation calculation (≥20 periods)
- Full window correlation (100 periods)
- Correlation matrix updates
- Symbol failure isolation
"""
import logging
from typing import Optional

from src.models.correlation import (
    CorrelationMatrix,
    CorrelationWindowState,
)
from src.models.portfolio import CurrencyPair

logger = logging.getLogger(__name__)


class CorrelationService:
    """Manages rolling correlation computations across symbol pairs.

    Maintains pairwise correlation windows and generates correlation matrix
    updates. Implements provisional window logic starting at 20 periods
    minimum, growing to full 100-period window.

    Attributes:
        window_size: Target window length (default 100)
        provisional_min: Minimum length for provisional evaluation (default 20)
        correlation_threshold: Default correlation threshold (default 0.8)
        threshold_overrides: Per-pair threshold overrides
        windows: Dictionary mapping pair keys to CorrelationWindowState
        active_symbols: Set of currently active symbols (excludes failures)
        correlation_matrix: Current correlation matrix
    """

    def __init__(
        self,
        window_size: int = 100,
        provisional_min: int = 20,
        correlation_threshold: float = 0.8,
        threshold_overrides: Optional[dict[str, float]] = None,
    ):
        """Initialize correlation service.

        Args:
            window_size: Target window length (default 100)
            provisional_min: Minimum length for provisional evaluation (default 20)
            correlation_threshold: Default correlation threshold (default 0.8)
            threshold_overrides: Optional per-pair threshold overrides
                (key: sorted pair token e.g. "EURUSD:GBPUSD", value: threshold)

        Raises:
            ValueError: If window_size < provisional_min
        """
        if window_size < provisional_min:
            raise ValueError(
                f"window_size ({window_size}) must be >= "
                f"provisional_min ({provisional_min})"
            )

        self.window_size = window_size
        self.provisional_min = provisional_min
        self.correlation_threshold = correlation_threshold
        self.threshold_overrides = threshold_overrides or {}
        self.windows: dict[str, CorrelationWindowState] = {}
        self.active_symbols: set[str] = set()
        self.correlation_matrix = CorrelationMatrix()

    def register_symbol(self, symbol: CurrencyPair) -> None:
        """Register a symbol for correlation tracking.

        Args:
            symbol: Currency pair to register
        """
        if symbol.code not in self.active_symbols:
            self.active_symbols.add(symbol.code)
            logger.info("Registered symbol for correlation tracking: %s", symbol.code)

    def mark_symbol_failed(self, symbol: CurrencyPair) -> None:
        """Mark a symbol as failed and exclude from future correlations.

        Per research Decision 5: failed symbols are removed from correlation
        calculations to avoid invalid metrics.

        Args:
            symbol: Currency pair that failed
        """
        if symbol.code in self.active_symbols:
            self.active_symbols.remove(symbol.code)
            logger.warning(
                "Marked symbol %s as failed; excluded from correlation tracking",
                symbol.code,
            )

    def update(
        self, prices: dict[str, float]
    ) -> Optional[CorrelationMatrix]:
        """Update correlation windows with new prices.

        Processes all active symbol pairs, updates rolling windows, and
        computes correlations. Returns updated correlation matrix if any
        correlations are ready (provisional window met).

        Args:
            prices: Dictionary mapping symbol codes to current prices

        Returns:
            Updated CorrelationMatrix if any correlations ready, else None
        """
        active_pairs = [
            CurrencyPair(code=code) for code in sorted(self.active_symbols)
        ]

        if len(active_pairs) < 2:
            return None

        any_updated = False

        # Update all pairwise windows
        for i, pair_a in enumerate(active_pairs):
            for pair_b in active_pairs[i + 1 :]:
                if pair_a.code not in prices or pair_b.code not in prices:
                    continue

                key = CorrelationMatrix.make_key(pair_a, pair_b)

                # Initialize window if needed
                if key not in self.windows:
                    self.windows[key] = CorrelationWindowState(
                        pair_a=pair_a,
                        pair_b=pair_b,
                        window=self.window_size,
                        provisional_min=self.provisional_min,
                    )

                window = self.windows[key]
                correlation = window.update(prices[pair_a.code], prices[pair_b.code])

                if correlation is not None:
                    self.correlation_matrix.set_correlation(
                        pair_a, pair_b, correlation
                    )
                    any_updated = True

        return self.correlation_matrix if any_updated else None

    def get_correlation(
        self, pair_a: CurrencyPair, pair_b: CurrencyPair
    ) -> float:
        """Get current correlation between two pairs.

        Args:
            pair_a: First currency pair
            pair_b: Second currency pair

        Returns:
            Correlation value, or 0.0 if not available
        """
        return self.correlation_matrix.get_correlation(pair_a, pair_b)

    def get_matrix(self) -> CorrelationMatrix:
        """Get current correlation matrix.

        Returns:
            Current CorrelationMatrix instance
        """
        return self.correlation_matrix

    def is_window_ready(
        self, pair_a: CurrencyPair, pair_b: CurrencyPair
    ) -> bool:
        """Check if window is at full target length.

        Args:
            pair_a: First currency pair
            pair_b: Second currency pair

        Returns:
            True if window at target length, False otherwise
        """
        key = CorrelationMatrix.make_key(pair_a, pair_b)
        if key not in self.windows:
            return False
        return self.windows[key].is_ready()

    def get_threshold(
        self, pair_a: CurrencyPair, pair_b: CurrencyPair
    ) -> float:
        """Get correlation threshold for a specific pair.

        Returns pair-specific override if configured, otherwise default threshold.
        Per Decision 8: normalized pair key ordering for stable lookup.

        Args:
            pair_a: First currency pair
            pair_b: Second currency pair

        Returns:
            Correlation threshold for this pair
        """
        key = CorrelationMatrix.make_key(pair_a, pair_b)
        return self.threshold_overrides.get(key, self.correlation_threshold)

    def is_highly_correlated(
        self, pair_a: CurrencyPair, pair_b: CurrencyPair
    ) -> bool:
        """Check if two pairs are highly correlated above threshold.

        Args:
            pair_a: First currency pair
            pair_b: Second currency pair

        Returns:
            True if correlation exceeds threshold, False otherwise
        """
        correlation = abs(self.get_correlation(pair_a, pair_b))
        threshold = self.get_threshold(pair_a, pair_b)
        return correlation > threshold

    def set_threshold_override(
        self, pair_a: CurrencyPair, pair_b: CurrencyPair, threshold: float
    ) -> None:
        """Set correlation threshold override for specific pair.

        Args:
            pair_a: First currency pair
            pair_b: Second currency pair
            threshold: Threshold value to set

        Raises:
            ValueError: If threshold not in [-1, 1]
        """
        if not -1.0 <= threshold <= 1.0:
            raise ValueError(
                f"Threshold must be in [-1, 1], got {threshold}"
            )

        key = CorrelationMatrix.make_key(pair_a, pair_b)
        self.threshold_overrides[key] = threshold
        logger.info(
            "Set correlation threshold override: %s = %.2f",
            key,
            threshold,
        )
