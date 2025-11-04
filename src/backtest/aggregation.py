"""Portfolio aggregation logic (skeleton).

This initial implementation focuses on weighted PnL combination and exposes a
minimal interface that will evolve to handle exposure netting, drawdown, and
volatility metrics.

Future enhancements (see tasks T024, T067):
- Net exposure by instrument
- Portfolio drawdown stats
- Structured metrics emission
"""
from __future__ import annotations

from typing import Sequence, Mapping, Any
import logging

logger = logging.getLogger(__name__)

class PortfolioAggregator:
    """Aggregate per-strategy result dictionaries into a portfolio summary.

    Expected strategy result minimal contract (temporary): each result is a
    mapping containing at least 'name' and 'pnl' (float). Additional fields are
    ignored for now.

    Args:
        results: Sequence of mapping objects with keys: name, pnl.
        weights: Sequence of floats; if invalid or length mismatch, equal
                 weights fallback is applied.

    Returns:
        dict with keys: strategies_count, weighted_pnl, weights_applied
    """

    def aggregate(
            self,
            results: Sequence[Mapping[str, Any]],
            weights: Sequence[float]
        ) -> dict:
        if not results:
            raise ValueError("No strategy results provided for aggregation")

        n = len(results)
        use_weights = list(weights)

        # Validate weights length and normalization
        if len(use_weights) != n or not \
            use_weights or abs(sum(use_weights) - 1.0) > 1e-6:
            logger.warning(
                "Invalid weights provided (len=%d,sum=%.6f). \
Applying equal-weight fallback.",
                len(use_weights),
                sum(use_weights) if use_weights else 0.0,
            )
            use_weights = [1.0 / n] * n

        weighted_pnl = 0.0
        for w, result in zip(use_weights, results):
            pnl = float(result.get("pnl", 0.0))
            weighted_pnl += pnl * w

        summary = {
            "strategies_count": n,
            "weighted_pnl": weighted_pnl,
            "weights_applied": use_weights,
        }
        logger.info(
            "Aggregated portfolio strategies=%d weighted_pnl=%.4f", n, weighted_pnl
        )
        return summary

__all__ = ["PortfolioAggregator"]
