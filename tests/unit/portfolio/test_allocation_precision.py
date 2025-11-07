"""Unit tests for allocation engine precision.

Tests verify:
- Largest remainder rounding ensures allocation sum equals total capital
- No rounding errors accumulate
- Edge cases (small capital, many symbols, unequal weights) handled correctly
"""
import pytest

from src.backtest.portfolio.allocation_engine import AllocationEngine
from src.models.allocation import AllocationRequest
from src.models.portfolio import CurrencyPair


class TestAllocationPrecision:
    """Test allocation engine sum precision via largest remainder rounding."""

    def test_equal_weight_sum_precision(self):
        """Verify equal-weight allocations sum exactly to capital."""
        engine = AllocationEngine(rounding_dp=2)

        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
            CurrencyPair(code="USDJPY"),
        ]

        capital = 10000.0
        volatility = {"EURUSD": 0.5, "GBPUSD": 0.6, "USDJPY": 0.4}

        request = AllocationRequest(
            symbols=symbols,
            volatility=volatility,
            capital=capital,
        )

        response = engine.allocate(request)

        # Sum must equal capital exactly
        total = sum(response.allocations.values())
        assert total == capital
        assert abs(total - capital) < 1e-10

    def test_custom_weights_sum_precision(self):
        """Verify custom weight allocations sum exactly to capital."""
        engine = AllocationEngine(rounding_dp=2)

        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
            CurrencyPair(code="USDJPY"),
        ]

        capital = 25000.0
        volatility = {"EURUSD": 0.5, "GBPUSD": 0.6, "USDJPY": 0.4}
        base_weights = {"EURUSD": 0.5, "GBPUSD": 0.3, "USDJPY": 0.2}

        request = AllocationRequest(
            symbols=symbols,
            volatility=volatility,
            base_weights=base_weights,
            capital=capital,
        )

        response = engine.allocate(request)

        # Sum must equal capital exactly
        total = sum(response.allocations.values())
        assert total == capital

    def test_many_symbols_no_rounding_error(self):
        """Verify many symbols don't accumulate rounding errors."""
        engine = AllocationEngine(rounding_dp=2)

        # Create 10 symbols
        symbol_codes = [
            "EURUSD",
            "GBPUSD",
            "USDJPY",
            "AUDUSD",
            "NZDUSD",
            "USDCAD",
            "USDCHF",
            "EURGBP",
            "EURJPY",
            "GBPJPY",
        ]
        symbols = [CurrencyPair(code=code) for code in symbol_codes]

        capital = 100000.0
        volatility = {code: 0.5 for code in symbol_codes}

        request = AllocationRequest(
            symbols=symbols,
            volatility=volatility,
            capital=capital,
        )

        response = engine.allocate(request)

        # Sum must equal capital exactly
        total = sum(response.allocations.values())
        assert total == capital
        assert len(response.allocations) == 10

    def test_small_capital_precision(self):
        """Verify precision maintained with small capital amounts."""
        engine = AllocationEngine(rounding_dp=2)

        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
        ]

        capital = 100.0  # Small capital
        volatility = {"EURUSD": 0.5, "GBPUSD": 0.6}

        request = AllocationRequest(
            symbols=symbols,
            volatility=volatility,
            capital=capital,
        )

        response = engine.allocate(request)

        # Sum must equal capital exactly
        total = sum(response.allocations.values())
        assert total == capital

    def test_odd_capital_amount_precision(self):
        """Verify precision with odd capital amounts causing rounding."""
        engine = AllocationEngine(rounding_dp=2)

        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
            CurrencyPair(code="USDJPY"),
        ]

        # Odd amount that will require rounding adjustment
        capital = 10000.33
        volatility = {"EURUSD": 0.5, "GBPUSD": 0.6, "USDJPY": 0.4}

        request = AllocationRequest(
            symbols=symbols,
            volatility=volatility,
            capital=capital,
        )

        response = engine.allocate(request)

        # Sum must equal capital exactly
        total = sum(response.allocations.values())
        assert abs(total - capital) < 1e-10

    def test_all_allocations_non_negative(self):
        """Verify all allocations are non-negative after rounding."""
        engine = AllocationEngine(rounding_dp=2)

        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
            CurrencyPair(code="USDJPY"),
        ]

        capital = 10000.0
        volatility = {"EURUSD": 0.5, "GBPUSD": 0.6, "USDJPY": 0.4}

        request = AllocationRequest(
            symbols=symbols,
            volatility=volatility,
            capital=capital,
        )

        response = engine.allocate(request)

        # All allocations must be non-negative
        for allocation in response.allocations.values():
            assert allocation >= 0.0

    def test_single_symbol_receives_all_capital(self):
        """Verify single symbol receives entire capital allocation."""
        engine = AllocationEngine(rounding_dp=2)

        symbols = [CurrencyPair(code="EURUSD")]
        capital = 50000.0
        volatility = {"EURUSD": 0.5}

        request = AllocationRequest(
            symbols=symbols,
            volatility=volatility,
            capital=capital,
        )

        response = engine.allocate(request)

        # Single symbol gets all capital
        assert response.allocations["EURUSD"] == capital
        assert sum(response.allocations.values()) == capital

    def test_equal_weight_convenience_method(self):
        """Verify equal_weight convenience method maintains precision."""
        engine = AllocationEngine(rounding_dp=2)

        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
            CurrencyPair(code="USDJPY"),
        ]

        capital = 15000.0

        response = engine.allocate_equal_weight(symbols, capital)

        # Sum must equal capital exactly
        total = sum(response.allocations.values())
        assert total == capital

        # Each symbol should get approximately equal weight
        expected_per_symbol = capital / 3
        for allocation in response.allocations.values():
            assert abs(allocation - expected_per_symbol) < 1.0

    def test_missing_volatility_raises_error(self):
        """Verify ValueError raised when volatility missing for symbol."""
        engine = AllocationEngine(rounding_dp=2)

        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
        ]

        capital = 10000.0
        volatility = {"EURUSD": 0.5}  # Missing GBPUSD

        request = AllocationRequest(
            symbols=symbols,
            volatility=volatility,
            capital=capital,
        )

        with pytest.raises(ValueError, match="Missing volatility data"):
            engine.allocate(request)

    def test_missing_base_weight_raises_error(self):
        """Verify ValueError raised when base weight missing for symbol."""
        engine = AllocationEngine(rounding_dp=2)

        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
            CurrencyPair(code="USDJPY"),
        ]

        capital = 10000.0
        volatility = {"EURUSD": 0.5, "GBPUSD": 0.6, "USDJPY": 0.4}
        # Weights sum to 1.0 but missing USDJPY - will be caught by engine
        base_weights = {"EURUSD": 0.6, "GBPUSD": 0.4}

        # This passes pydantic validation but fails engine validation
        request = AllocationRequest(
            symbols=symbols,
            volatility=volatility,
            base_weights=base_weights,
            capital=capital,
        )

        with pytest.raises(ValueError, match="Missing base weight"):
            engine.allocate(request)

    def test_negative_rounding_dp_raises_error(self):
        """Verify ValueError raised for negative rounding decimal places."""
        with pytest.raises(ValueError, match="rounding_dp must be non-negative"):
            AllocationEngine(rounding_dp=-1)

    def test_diversification_ratio_bounds(self):
        """Verify diversification ratio stays in valid [0, 1] range."""
        engine = AllocationEngine(rounding_dp=2)

        symbols = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
            CurrencyPair(code="USDJPY"),
        ]

        capital = 10000.0
        volatility = {"EURUSD": 0.5, "GBPUSD": 0.6, "USDJPY": 0.4}

        # Test with high correlation
        from src.models.correlation import CorrelationMatrix

        high_corr_matrix = {
            CorrelationMatrix.make_key(symbols[0], symbols[1]): 0.9,
            CorrelationMatrix.make_key(symbols[0], symbols[2]): 0.9,
            CorrelationMatrix.make_key(symbols[1], symbols[2]): 0.9,
        }

        request = AllocationRequest(
            symbols=symbols,
            volatility=volatility,
            correlation_matrix=high_corr_matrix,
            capital=capital,
        )

        response = engine.allocate(request)

        # Diversification ratio must be in [0, 1]
        assert 0.0 <= response.diversification_ratio <= 1.0

        # High correlation should reduce diversification
        assert response.diversification_ratio < 0.6
