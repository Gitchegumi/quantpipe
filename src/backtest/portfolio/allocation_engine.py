"""Portfolio capital allocation engine.

This module implements capital allocation logic using largest remainder
rounding to ensure allocations sum precisely to total capital. Supports
equal-weight and custom base weight strategies with correlation adjustments.

Per research Decision 6 and contracts/portfolio-allocation.yaml.
"""
import logging
from typing import Optional

from src.models.allocation import AllocationRequest, AllocationResponse
from src.models.portfolio import CurrencyPair

logger = logging.getLogger(__name__)


class AllocationEngine:
    """Manages capital allocation across portfolio symbols.

    Implements largest remainder method to ensure precise capital sum.
    Supports equal-weight and custom base weight strategies.

    Attributes:
        rounding_dp: Decimal places for allocation rounding (default 2)
    """

    def __init__(self, rounding_dp: int = 2):
        """Initialize allocation engine.

        Args:
            rounding_dp: Decimal places for allocation rounding (default 2)

        Raises:
            ValueError: If rounding_dp < 0
        """
        if rounding_dp < 0:
            raise ValueError("rounding_dp must be non-negative")

        self.rounding_dp = rounding_dp

    def allocate(self, request: AllocationRequest) -> AllocationResponse:
        """Compute capital allocation across symbols.

        Implements largest remainder rounding to ensure allocations sum
        precisely to total capital.

        Args:
            request: AllocationRequest with symbols, volatility, capital

        Returns:
            AllocationResponse with per-symbol allocations

        Raises:
            ValueError: If volatility missing for any symbol
        """
        # Validate volatility coverage
        symbol_codes = [pair.code for pair in request.symbols]
        for code in symbol_codes:
            if code not in request.volatility:
                raise ValueError(
                    f"Missing volatility data for symbol {code}"
                )

        # Determine base weights
        if request.base_weights:
            weights = self._validate_base_weights(
                request.base_weights, symbol_codes
            )
        else:
            # Equal weight by default
            equal_weight = 1.0 / len(symbol_codes)
            weights = {code: equal_weight for code in symbol_codes}

        # Calculate raw allocations
        raw_allocations = {
            code: weights[code] * request.capital for code in symbol_codes
        }

        # Apply largest remainder rounding
        allocations = self._apply_largest_remainder_rounding(
            raw_allocations, request.capital
        )

        # Calculate diversification ratio
        diversification = self._calculate_diversification_ratio(
            request.symbols, request.correlation_matrix
        )

        logger.info(
            "Allocated capital across %d symbols (diversification: %.3f)",
            len(allocations),
            diversification,
        )

        return AllocationResponse(
            allocations=allocations,
            diversification_ratio=diversification,
        )

    def _validate_base_weights(
        self, base_weights: dict[str, float], symbol_codes: list[str]
    ) -> dict[str, float]:
        """Validate and normalize base weights.

        Args:
            base_weights: Raw base weights from request
            symbol_codes: List of symbol codes to validate against

        Returns:
            Validated and potentially normalized weights

        Raises:
            ValueError: If weights missing for any symbol
        """
        for code in symbol_codes:
            if code not in base_weights:
                raise ValueError(
                    f"Missing base weight for symbol {code}"
                )

        # Weights already validated by pydantic (sum ~1.0, non-negative)
        return base_weights

    def _apply_largest_remainder_rounding(
        self, raw_allocations: dict[str, float], total_capital: float
    ) -> dict[str, float]:
        """Apply largest remainder method to ensure sum equals capital.

        This ensures that after rounding, the sum of allocations exactly
        equals the total capital by adjusting the symbol with the largest
        fractional remainder.

        Args:
            raw_allocations: Raw float allocations per symbol
            total_capital: Total capital that allocations must sum to

        Returns:
            Rounded allocations summing to total_capital
        """
        # Round all allocations
        rounded = {}
        remainders = {}

        for symbol, value in raw_allocations.items():
            rounded_value = round(value, self.rounding_dp)
            rounded[symbol] = rounded_value
            remainders[symbol] = value - rounded_value

        # Calculate rounding error
        rounded_sum = sum(rounded.values())
        error = round(total_capital - rounded_sum, self.rounding_dp)

        # If there's error, adjust symbol with largest remainder
        if abs(error) > 0:
            # Find symbol with largest absolute remainder
            max_symbol = max(remainders, key=lambda s: abs(remainders[s]))

            # Adjust by the error amount
            rounded[max_symbol] = round(
                rounded[max_symbol] + error, self.rounding_dp
            )

            logger.debug(
                "Applied largest remainder correction: %s adjusted by %.4f",
                max_symbol,
                error,
            )

        return rounded

    def _calculate_diversification_ratio(
        self,
        symbols: list[CurrencyPair],
        correlation_matrix: dict[str, float],
    ) -> float:
        """Calculate portfolio diversification ratio.

        Measures diversification effectiveness as ratio of uncorrelated
        variance to actual portfolio variance. Higher values indicate
        better diversification.

        For equal-weighted portfolio:
        - diversification_ratio = 1/sqrt(1 + avg_correlation * (n-1))

        Where:
        - n = number of symbols
        - avg_correlation = mean pairwise correlation

        Args:
            symbols: List of currency pairs
            correlation_matrix: Pairwise correlation values

        Returns:
            Diversification ratio in [0, 1]
        """
        n_symbols = len(symbols)

        if n_symbols == 1:
            # Single symbol has no diversification
            return 0.0

        # Calculate average pairwise correlation
        correlations = []
        for i, pair_a in enumerate(symbols):
            for pair_b in symbols[i + 1 :]:
                from src.models.correlation import CorrelationMatrix

                key = CorrelationMatrix.make_key(pair_a, pair_b)
                correlation = correlation_matrix.get(key, 0.0)
                correlations.append(correlation)

        avg_corr = (
            sum(correlations) / len(correlations) if correlations else 0.0
        )

        # Calculate diversification ratio
        # Formula: 1 / sqrt(1 + avg_corr * (n-1))
        denominator = 1.0 + avg_corr * (n_symbols - 1)
        ratio = 1.0 / (denominator**0.5) if denominator > 0 else 0.0

        return min(ratio, 1.0)  # Ensure in [0, 1]

    def allocate_equal_weight(
        self,
        symbols: list[CurrencyPair],
        capital: float,
        correlation_matrix: Optional[dict[str, float]] = None,
    ) -> AllocationResponse:
        """Convenience method for equal-weight allocation.

        Args:
            symbols: List of currency pairs
            capital: Total capital to allocate
            correlation_matrix: Optional correlation matrix for diversification

        Returns:
            AllocationResponse with equal allocations
        """
        # Create dummy volatility (not used for equal weight)
        volatility = {pair.code: 1.0 for pair in symbols}

        request = AllocationRequest(
            symbols=symbols,
            volatility=volatility,
            correlation_matrix=correlation_matrix or {},
            capital=capital,
        )

        return self.allocate(request)
