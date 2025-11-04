"""Portfolio aggregation logic for multi-strategy execution.

This module implements aggregation of per-strategy results into portfolio-level
metrics including:
- Weighted PnL combination
- Net exposure by instrument
- Portfolio drawdown statistics
- Instrument count aggregation

Per FR-013 and FR-014, supports configurable weights with equal-weight fallback.
"""
from __future__ import annotations

import logging
from typing import Any, Mapping, Sequence

logger = logging.getLogger(__name__)


class PortfolioAggregator:
    """
    Aggregate per-strategy results into portfolio-level metrics.

    Combines PnL with configurable weights, calculates net exposure across
    instruments, and computes portfolio-level statistics per FR-013/FR-014.

    Examples:
        >>> aggregator = PortfolioAggregator()
        >>> results = [
        ...     {"name": "alpha", "pnl": 100.0, "max_drawdown": 0.05,
        ...      "exposure": {"EURUSD": 0.02}},
        ...     {"name": "beta", "pnl": 50.0, "max_drawdown": 0.03,
        ...      "exposure": {"EURUSD": -0.01}},
        ... ]
        >>> summary = aggregator.aggregate(results, [0.6, 0.4])
        >>> summary["weighted_pnl"]
        80.0
    """

    def aggregate(
        self, results: Sequence[Mapping[str, Any]], weights: Sequence[float]
    ) -> dict:
        """
        Aggregate per-strategy results into portfolio summary.

        Args:
            results: Sequence of strategy result dicts with keys: name, pnl,
                max_drawdown (optional), exposure (optional dict).
            weights: Strategy weights (must sum to ~1.0).

        Returns:
            Dictionary with portfolio-level metrics:
                - strategies_count: Number of strategies
                - weighted_pnl: Weighted portfolio PnL
                - max_drawdown: Maximum drawdown across strategies
                - net_exposure_by_instrument: Aggregated net exposure
                - weights_applied: Normalized weights used
                - instruments_count: Distinct instruments

        Raises:
            ValueError: If results is empty.

        Examples:
            >>> agg = PortfolioAggregator()
            >>> res = [{"name": "s1", "pnl": 100}]
            >>> agg.aggregate(res, [1.0])["weighted_pnl"]
            100.0
        """
        if not results:
            raise ValueError("No strategy results provided for aggregation")

        n_strategies = len(results)
        use_weights = list(weights)

        # Validate weights length and normalization
        if (
            len(use_weights) != n_strategies
            or not use_weights
            or abs(sum(use_weights) - 1.0) > 1e-6
        ):
            logger.warning(
                "Invalid weights provided (len=%d,sum=%.6f). "
                "Applying equal-weight fallback.",
                len(use_weights),
                sum(use_weights) if use_weights else 0.0,
            )
            use_weights = [1.0 / n_strategies] * n_strategies

        # Aggregate weighted PnL
        weighted_pnl = 0.0
        for weight, result in zip(use_weights, results):
            pnl = float(result.get("pnl", 0.0))
            weighted_pnl += pnl * weight

        # Aggregate max drawdown (take worst across strategies)
        max_drawdown = 0.0
        for result in results:
            dd = float(result.get("max_drawdown", 0.0))
            max_drawdown = max(max_drawdown, dd)

        # Aggregate net exposure by instrument (FR-013)
        net_exposure: dict[str, float] = {}
        for weight, result in zip(use_weights, results):
            exposure = result.get("exposure", {})
            if not isinstance(exposure, dict):
                continue
            for instrument, value in exposure.items():
                net_exposure[instrument] = (
                    net_exposure.get(instrument, 0.0) + value * weight
                )

        instruments_count = len(net_exposure)

        summary = {
            "strategies_count": n_strategies,
            "weighted_pnl": weighted_pnl,
            "max_drawdown": max_drawdown,
            "net_exposure_by_instrument": net_exposure,
            "weights_applied": use_weights,
            "instruments_count": instruments_count,
        }

        logger.info(
            "Aggregated portfolio: strategies=%d instruments=%d weighted_pnl=%.4f",
            n_strategies,
            instruments_count,
            weighted_pnl,
        )
        return summary


__all__ = ["PortfolioAggregator"]
