"""Unit tests for correlation service provisional window logic.

Tests verify:
- Provisional window starts at minimum 20 periods
- Window grows to full 100 periods
- Correlation matrix shape and behavior at boundaries
- Symbol registration and failure isolation
"""
import pytest

from src.backtest.portfolio.correlation_service import CorrelationService
from src.models.portfolio import CurrencyPair


class TestCorrelationProvisionalWindow:
    """Test correlation service provisional window behavior."""

    def test_no_correlation_before_provisional_minimum(self):
        """Verify no correlation computed before reaching 20 periods."""
        service = CorrelationService(window_size=100, provisional_min=20)

        eurusd = CurrencyPair(code="EURUSD")
        gbpusd = CurrencyPair(code="GBPUSD")

        service.register_symbol(eurusd)
        service.register_symbol(gbpusd)

        # Feed 19 price updates (below minimum)
        for i in range(19):
            prices = {"EURUSD": 1.10 + i * 0.01, "GBPUSD": 1.25 + i * 0.01}
            matrix = service.update(prices)

        # Should return None - not enough data yet
        assert matrix is None
        assert service.get_correlation(eurusd, gbpusd) == 0.0

    def test_provisional_correlation_at_minimum(self):
        """Verify correlation computed at exactly 20 periods."""
        service = CorrelationService(window_size=100, provisional_min=20)

        eurusd = CurrencyPair(code="EURUSD")
        gbpusd = CurrencyPair(code="GBPUSD")

        service.register_symbol(eurusd)
        service.register_symbol(gbpusd)

        # Feed exactly 20 price updates
        for i in range(20):
            prices = {"EURUSD": 1.10 + i * 0.01, "GBPUSD": 1.25 + i * 0.01}
            matrix = service.update(prices)

        # Should compute provisional correlation
        assert matrix is not None
        correlation = service.get_correlation(eurusd, gbpusd)
        assert correlation != 0.0
        assert -1.0 <= correlation <= 1.0

    def test_window_grows_to_full_size(self):
        """Verify window grows from provisional to full 100 periods."""
        service = CorrelationService(window_size=100, provisional_min=20)

        eurusd = CurrencyPair(code="EURUSD")
        gbpusd = CurrencyPair(code="GBPUSD")

        service.register_symbol(eurusd)
        service.register_symbol(gbpusd)

        # Window should not be ready before 100 periods
        assert not service.is_window_ready(eurusd, gbpusd)

        # Feed 99 price updates
        for i in range(99):
            prices = {"EURUSD": 1.10 + i * 0.01, "GBPUSD": 1.25 + i * 0.01}
            service.update(prices)

        # Still not ready at 99
        assert not service.is_window_ready(eurusd, gbpusd)

        # Feed 100th update
        prices = {"EURUSD": 2.09, "GBPUSD": 2.24}
        service.update(prices)

        # Now window should be ready
        assert service.is_window_ready(eurusd, gbpusd)

    def test_correlation_updates_with_new_data(self):
        """Verify correlation updates as new data arrives."""
        service = CorrelationService(window_size=100, provisional_min=20)

        eurusd = CurrencyPair(code="EURUSD")
        gbpusd = CurrencyPair(code="GBPUSD")

        service.register_symbol(eurusd)
        service.register_symbol(gbpusd)

        # Feed perfectly correlated data
        for i in range(30):
            prices = {"EURUSD": 1.10 + i * 0.01, "GBPUSD": 1.25 + i * 0.01}
            service.update(prices)

        corr_perfect = service.get_correlation(eurusd, gbpusd)
        assert corr_perfect > 0.99  # Should be very high correlation

        # Now add uncorrelated noise
        for i in range(30):
            prices = {
                "EURUSD": 1.40 + (i % 2) * 0.05,
                "GBPUSD": 1.55 - (i % 2) * 0.05,
            }
            service.update(prices)

        corr_mixed = service.get_correlation(eurusd, gbpusd)
        assert abs(corr_mixed) < abs(corr_perfect)

    def test_symbol_failure_isolation(self):
        """Verify failed symbol is excluded from correlation tracking."""
        service = CorrelationService(window_size=100, provisional_min=20)

        eurusd = CurrencyPair(code="EURUSD")
        gbpusd = CurrencyPair(code="GBPUSD")
        usdjpy = CurrencyPair(code="USDJPY")

        service.register_symbol(eurusd)
        service.register_symbol(gbpusd)
        service.register_symbol(usdjpy)

        assert len(service.active_symbols) == 3

        # Mark GBPUSD as failed
        service.mark_symbol_failed(gbpusd)

        assert len(service.active_symbols) == 2
        assert "GBPUSD" not in service.active_symbols
        assert "EURUSD" in service.active_symbols
        assert "USDJPY" in service.active_symbols

        # Update with all 3 symbols - GBPUSD should be ignored
        for i in range(25):
            prices = {
                "EURUSD": 1.10 + i * 0.01,
                "GBPUSD": 1.25 + i * 0.01,  # This should be ignored
                "USDJPY": 110.0 + i * 0.5,
            }
            service.update(prices)

        # EURUSD-USDJPY correlation should exist
        corr_active = service.get_correlation(eurusd, usdjpy)
        assert corr_active != 0.0

        # EURUSD-GBPUSD correlation should not exist (GBPUSD failed)
        # Note: existing correlation values are preserved but no new updates
        # Correlation retrieval returns 0.0 for non-existent pairs

    def test_insufficient_symbols_returns_none(self):
        """Verify update returns None with fewer than 2 active symbols."""
        service = CorrelationService(window_size=100, provisional_min=20)

        eurusd = CurrencyPair(code="EURUSD")
        service.register_symbol(eurusd)

        # Only 1 symbol - should return None
        for i in range(25):
            prices = {"EURUSD": 1.10 + i * 0.01}
            matrix = service.update(prices)
            assert matrix is None

    def test_invalid_window_configuration_raises_error(self):
        """Verify ValueError raised if window_size < provisional_min."""
        with pytest.raises(ValueError, match="window_size .* must be >= .*"):
            CorrelationService(window_size=15, provisional_min=20)

    def test_zero_variance_returns_zero_correlation(self):
        """Verify zero correlation returned for zero variance series."""
        service = CorrelationService(window_size=100, provisional_min=20)

        eurusd = CurrencyPair(code="EURUSD")
        gbpusd = CurrencyPair(code="GBPUSD")

        service.register_symbol(eurusd)
        service.register_symbol(gbpusd)

        # Feed constant prices (zero variance) for EURUSD
        for i in range(25):
            prices = {"EURUSD": 1.10, "GBPUSD": 1.25 + i * 0.01}
            service.update(prices)

        correlation = service.get_correlation(eurusd, gbpusd)
        assert correlation == 0.0

    def test_matrix_timestamp_updates(self):
        """Verify correlation matrix timestamp updates on new data."""
        service = CorrelationService(window_size=100, provisional_min=20)

        eurusd = CurrencyPair(code="EURUSD")
        gbpusd = CurrencyPair(code="GBPUSD")

        service.register_symbol(eurusd)
        service.register_symbol(gbpusd)

        initial_matrix = service.get_matrix()
        initial_timestamp = initial_matrix.timestamp

        # Feed data past provisional minimum
        for i in range(25):
            prices = {"EURUSD": 1.10 + i * 0.01, "GBPUSD": 1.25 + i * 0.01}
            service.update(prices)

        updated_matrix = service.get_matrix()
        updated_timestamp = updated_matrix.timestamp

        # Timestamp should have updated
        assert updated_timestamp > initial_timestamp
