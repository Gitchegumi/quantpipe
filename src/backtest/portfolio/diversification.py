"""Diversification metrics for portfolio analysis.

This module provides diversification ratio calculations measuring portfolio
variance reduction compared to an uncorrelated baseline. Used by allocation
engine and portfolio analysis tools.

Per research Decision 6 and portfolio metrics requirements.
"""
import logging
from typing import Optional

from src.models.correlation import CorrelationMatrix
from src.models.portfolio import CurrencyPair

logger = logging.getLogger(__name__)


def calculate_diversification_ratio(
    symbols: list[CurrencyPair],
    correlation_matrix: dict[str, float],
    weights: Optional[dict[str, float]] = None,
) -> float:
    """Calculate portfolio diversification ratio.

    Measures diversification effectiveness as ratio of uncorrelated
    variance to actual portfolio variance. Higher values indicate
    better diversification.

    For equal-weighted portfolio (or when weights not provided):
    - diversification_ratio = 1/sqrt(1 + avg_correlation * (n-1))

    Where:
    - n = number of symbols
    - avg_correlation = mean pairwise correlation

    For weighted portfolio:
    - Uses weighted average of correlations based on portfolio weights

    Args:
        symbols: List of currency pairs
        correlation_matrix: Pairwise correlation values (key: sorted pair token)
        weights: Optional per-symbol weights (must sum to ~1.0)

    Returns:
        Diversification ratio in [0, 1] where:
        - 0 = no diversification (single asset or perfect correlation)
        - 1 = perfect diversification (zero correlation)

    Raises:
        ValueError: If weights provided but don't sum to ~1.0
    """
    n_symbols = len(symbols)

    if n_symbols == 1:
        # Single symbol has no diversification
        return 0.0

    # Validate weights if provided
    if weights:
        weight_sum = sum(weights.values())
        if not 0.99 <= weight_sum <= 1.01:
            raise ValueError(
                f"Weights must sum to approximately 1.0, got {weight_sum:.4f}"
            )

    # Calculate average pairwise correlation
    correlations = []
    correlation_weights = []

    for i, pair_a in enumerate(symbols):
        for pair_b in symbols[i + 1 :]:
            key = CorrelationMatrix.make_key(pair_a, pair_b)
            correlation = correlation_matrix.get(key, 0.0)
            correlations.append(correlation)

            # If weights provided, weight this correlation by product of pair weights
            if weights:
                weight_a = weights.get(pair_a.code, 0.0)
                weight_b = weights.get(pair_b.code, 0.0)
                correlation_weights.append(weight_a * weight_b)

    if not correlations:
        return 0.0

    # Calculate weighted or simple average correlation
    if weights and correlation_weights:
        total_weight = sum(correlation_weights)
        avg_corr = (
            sum(c * w for c, w in zip(correlations, correlation_weights))
            / total_weight
            if total_weight > 0
            else 0.0
        )
    else:
        avg_corr = sum(correlations) / len(correlations)

    # Calculate diversification ratio
    # Formula: 1 / sqrt(1 + avg_corr * (n-1))
    denominator = 1.0 + avg_corr * (n_symbols - 1)
    ratio = 1.0 / (denominator**0.5) if denominator > 0 else 0.0

    return min(ratio, 1.0)  # Ensure in [0, 1]


def calculate_effective_number_of_assets(
    symbols: list[CurrencyPair],
    correlation_matrix: dict[str, float],
    weights: Optional[dict[str, float]] = None,
) -> float:
    """Calculate effective number of independent assets.

    Estimates how many truly independent (uncorrelated) assets the portfolio
    is equivalent to, accounting for correlations.

    Formula: N_eff = 1 / sum_i(sum_j(w_i * w_j * correlation_ij))

    For equal weights and average correlation rho:
    - N_eff ≈ N / (1 + rho * (N-1))

    Args:
        symbols: List of currency pairs
        correlation_matrix: Pairwise correlation values
        weights: Optional per-symbol weights (equal-weight if None)

    Returns:
        Effective number of assets (typically 1.0 to N)
    """
    n_symbols = len(symbols)

    if n_symbols == 1:
        return 1.0

    # Default to equal weights if not provided
    if not weights:
        equal_weight = 1.0 / n_symbols
        weights = {pair.code: equal_weight for pair in symbols}

    # Calculate weighted correlation sum
    weighted_corr_sum = 0.0

    for i, pair_a in enumerate(symbols):
        weight_a = weights.get(pair_a.code, 0.0)

        for j, pair_b in enumerate(symbols):
            weight_b = weights.get(pair_b.code, 0.0)

            if i == j:
                # Self-correlation is 1.0
                correlation = 1.0
            else:
                key = CorrelationMatrix.make_key(pair_a, pair_b)
                correlation = correlation_matrix.get(key, 0.0)

            weighted_corr_sum += weight_a * weight_b * correlation

    # Effective number of assets
    n_effective = 1.0 / weighted_corr_sum if weighted_corr_sum > 0 else float(n_symbols)

    return min(n_effective, float(n_symbols))  # Cap at actual number


def estimate_portfolio_variance_reduction(
    symbols: list[CurrencyPair],
    correlation_matrix: dict[str, float],
    weights: Optional[dict[str, float]] = None,
) -> float:
    """Estimate portfolio variance reduction vs single-asset baseline.

    Calculates the reduction in portfolio variance achieved through
    diversification compared to holding a single asset.

    Returns:
        Variance reduction ratio in [0, 1] where:
        - 0 = no reduction (single asset or perfect correlation)
        - 1 = maximum reduction (zero correlation)
    """
    n_symbols = len(symbols)

    if n_symbols == 1:
        return 0.0

    # Calculate diversification ratio
    div_ratio = calculate_diversification_ratio(symbols, correlation_matrix, weights)

    # Variance reduction is related to diversification ratio
    # For equal-weighted portfolio: reduction ≈ 1 - 1/N * (1 + avg_corr * (N-1))
    # Simplified: reduction ≈ 1 - 1/(N * div_ratio^2)

    if div_ratio > 0:
        variance_ratio = 1.0 / (n_symbols * div_ratio * div_ratio)
        reduction = 1.0 - variance_ratio
        return max(0.0, min(reduction, 1.0))  # Ensure [0, 1]

    return 0.0
