"""Unit tests for diversification ratio monotonic behavior.

Tests verify:
- Diversification ratio decreases as correlations increase
- Ratio bounds [0, 1] maintained
- Edge cases (single asset, perfect correlation, zero correlation)
- Weighted vs equal-weight calculations
- Effective number of assets calculation
"""
import pytest

from src.backtest.portfolio.diversification import (
    calculate_diversification_ratio,
    calculate_effective_number_of_assets,
    estimate_portfolio_variance_reduction,
)
from src.models.correlation import CorrelationMatrix
from src.models.portfolio import CurrencyPair


class TestDiversificationRatioMonotonic:
    """Test diversification ratio monotonic behavior with correlations."""

    def test_ratio_decreases_with_increasing_correlation(self):
        """Verify diversification ratio decreases as correlation increases."""
        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
            CurrencyPair(code="USDJPY"),
        ]

        # Test with increasing correlation levels
        correlations = [0.0, 0.3, 0.5, 0.7, 0.9]
        ratios = []

        for corr in correlations:
            corr_matrix = {
                CorrelationMatrix.make_key(symbols[0], symbols[1]): corr,
                CorrelationMatrix.make_key(symbols[0], symbols[2]): corr,
                CorrelationMatrix.make_key(symbols[1], symbols[2]): corr,
            }

            ratio = calculate_diversification_ratio(symbols, corr_matrix)
            ratios.append(ratio)

        # Verify monotonic decrease
        for i in range(len(ratios) - 1):
            assert ratios[i] > ratios[i + 1], (
                f"Ratio should decrease: "
                f"corr={correlations[i]:.1f} ratio={ratios[i]:.4f}, "
                f"corr={correlations[i+1]:.1f} ratio={ratios[i+1]:.4f}"
            )

    def test_ratio_increases_with_decreasing_correlation(self):
        """Verify diversification ratio increases as correlation decreases."""
        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
        ]

        # Test with decreasing correlation levels (avoid -0.3 which caps at 1.0)
        correlations = [0.9, 0.6, 0.3, 0.1]
        ratios = []

        for corr in correlations:
            corr_matrix = {
                CorrelationMatrix.make_key(symbols[0], symbols[1]): corr,
            }

            ratio = calculate_diversification_ratio(symbols, corr_matrix)
            ratios.append(ratio)

        # Verify monotonic increase (or equal when capped at 1.0)
        for i in range(len(ratios) - 1):
            assert ratios[i] <= ratios[i + 1]

    def test_single_asset_returns_zero(self):
        """Verify single asset has zero diversification."""
        symbols = [CurrencyPair(code="EURUSD")]
        ratio = calculate_diversification_ratio(symbols, {})

        assert ratio == 0.0

    def test_perfect_correlation_low_ratio(self):
        """Verify perfect correlation produces low diversification ratio."""
        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
            CurrencyPair(code="USDJPY"),
        ]

        # Perfect correlation (1.0)
        corr_matrix = {
            CorrelationMatrix.make_key(symbols[0], symbols[1]): 1.0,
            CorrelationMatrix.make_key(symbols[0], symbols[2]): 1.0,
            CorrelationMatrix.make_key(symbols[1], symbols[2]): 1.0,
        }

        ratio = calculate_diversification_ratio(symbols, corr_matrix)

        # With perfect correlation, ratio should approach 1/sqrt(N)
        expected_approx = 1.0 / (3**0.5)
        assert abs(ratio - expected_approx) < 0.01

    def test_zero_correlation_high_ratio(self):
        """Verify zero correlation produces high diversification ratio."""
        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
            CurrencyPair(code="USDJPY"),
        ]

        # Zero correlation
        corr_matrix = {
            CorrelationMatrix.make_key(symbols[0], symbols[1]): 0.0,
            CorrelationMatrix.make_key(symbols[0], symbols[2]): 0.0,
            CorrelationMatrix.make_key(symbols[1], symbols[2]): 0.0,
        }

        ratio = calculate_diversification_ratio(symbols, corr_matrix)

        # With zero correlation, ratio should be 1.0
        assert abs(ratio - 1.0) < 0.01

    def test_ratio_bounds_maintained(self):
        """Verify diversification ratio stays in [0, 1] for all correlations."""
        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
        ]

        # Test extreme correlations
        for corr in [-1.0, -0.5, 0.0, 0.5, 1.0]:
            corr_matrix = {
                CorrelationMatrix.make_key(symbols[0], symbols[1]): corr,
            }

            ratio = calculate_diversification_ratio(symbols, corr_matrix)
            assert 0.0 <= ratio <= 1.0

    def test_weighted_vs_equal_weight(self):
        """Verify weighted calculation differs from equal-weight."""
        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
            CurrencyPair(code="USDJPY"),
        ]

        corr_matrix = {
            CorrelationMatrix.make_key(symbols[0], symbols[1]): 0.8,
            CorrelationMatrix.make_key(symbols[0], symbols[2]): 0.3,
            CorrelationMatrix.make_key(symbols[1], symbols[2]): 0.5,
        }

        # Equal weight
        ratio_equal = calculate_diversification_ratio(symbols, corr_matrix)

        # Heavy weight on EURUSD-GBPUSD (high correlation pair)
        weights_heavy_corr = {"EURUSD": 0.5, "GBPUSD": 0.4, "USDJPY": 0.1}
        ratio_weighted = calculate_diversification_ratio(
            symbols, corr_matrix, weights_heavy_corr
        )

        # Weighted ratio should be lower (more weight on high correlation)
        assert ratio_weighted < ratio_equal

    def test_effective_assets_single_symbol(self):
        """Verify effective assets equals 1 for single symbol."""
        symbols = [CurrencyPair(code="EURUSD")]
        n_eff = calculate_effective_number_of_assets(symbols, {})

        assert n_eff == 1.0

    def test_effective_assets_zero_correlation(self):
        """Verify effective assets equals N for zero correlation."""
        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
            CurrencyPair(code="USDJPY"),
        ]

        corr_matrix = {
            CorrelationMatrix.make_key(symbols[0], symbols[1]): 0.0,
            CorrelationMatrix.make_key(symbols[0], symbols[2]): 0.0,
            CorrelationMatrix.make_key(symbols[1], symbols[2]): 0.0,
        }

        n_eff = calculate_effective_number_of_assets(symbols, corr_matrix)

        # Should be close to 3.0
        assert abs(n_eff - 3.0) < 0.1

    def test_effective_assets_perfect_correlation(self):
        """Verify effective assets approaches 1 for perfect correlation."""
        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
            CurrencyPair(code="USDJPY"),
        ]

        corr_matrix = {
            CorrelationMatrix.make_key(symbols[0], symbols[1]): 1.0,
            CorrelationMatrix.make_key(symbols[0], symbols[2]): 1.0,
            CorrelationMatrix.make_key(symbols[1], symbols[2]): 1.0,
        }

        n_eff = calculate_effective_number_of_assets(symbols, corr_matrix)

        # Should be close to 1.0
        assert abs(n_eff - 1.0) < 0.1

    def test_effective_assets_decreases_with_correlation(self):
        """Verify effective assets decreases as correlation increases."""
        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
        ]

        correlations = [0.0, 0.5, 0.9]
        n_effs = []

        for corr in correlations:
            corr_matrix = {
                CorrelationMatrix.make_key(symbols[0], symbols[1]): corr,
            }
            n_eff = calculate_effective_number_of_assets(symbols, corr_matrix)
            n_effs.append(n_eff)

        # Verify monotonic decrease
        for i in range(len(n_effs) - 1):
            assert n_effs[i] > n_effs[i + 1]

    def test_variance_reduction_bounds(self):
        """Verify variance reduction stays in [0, 1]."""
        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
        ]

        for corr in [-1.0, 0.0, 0.5, 1.0]:
            corr_matrix = {
                CorrelationMatrix.make_key(symbols[0], symbols[1]): corr,
            }

            reduction = estimate_portfolio_variance_reduction(symbols, corr_matrix)
            assert 0.0 <= reduction <= 1.0

    def test_variance_reduction_decreases_with_correlation(self):
        """Verify variance reduction decreases as correlation increases."""
        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
            CurrencyPair(code="USDJPY"),
        ]

        correlations = [0.0, 0.3, 0.6, 0.9]
        reductions = []

        for corr in correlations:
            corr_matrix = {
                CorrelationMatrix.make_key(symbols[0], symbols[1]): corr,
                CorrelationMatrix.make_key(symbols[0], symbols[2]): corr,
                CorrelationMatrix.make_key(symbols[1], symbols[2]): corr,
            }

            reduction = estimate_portfolio_variance_reduction(symbols, corr_matrix)
            reductions.append(reduction)

        # Verify monotonic decrease
        for i in range(len(reductions) - 1):
            assert reductions[i] > reductions[i + 1]

    def test_invalid_weights_raise_error(self):
        """Verify ValueError raised for weights not summing to 1.0."""
        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
        ]

        corr_matrix = {
            CorrelationMatrix.make_key(symbols[0], symbols[1]): 0.5,
        }

        # Weights sum to 1.5 (invalid)
        weights = {"EURUSD": 0.8, "GBPUSD": 0.7}

        with pytest.raises(ValueError, match="Weights must sum to approximately 1.0"):
            calculate_diversification_ratio(symbols, corr_matrix, weights)
