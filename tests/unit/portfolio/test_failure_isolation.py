"""Tests for failure isolation in portfolio mode.

Verifies that failed symbols are properly excluded from:
- Correlation matrix calculations
- Capital allocation
- Portfolio metrics
- Active symbol tracking

Per Decision 5: failed symbols must be isolated to prevent invalid metrics.
"""

from src.backtest.portfolio.correlation_service import CorrelationService
from src.backtest.portfolio.orchestrator import PortfolioOrchestrator
from src.models.portfolio import CurrencyPair, PortfolioConfig


class TestCorrelationServiceFailureIsolation:
    """Test correlation service excludes failed symbols."""

    def test_failed_symbol_excluded_from_updates(self):
        """Verify failed symbol is excluded from correlation updates."""
        service = CorrelationService()

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
        assert "EURUSD" in service.active_symbols
        assert "GBPUSD" not in service.active_symbols
        assert "USDJPY" in service.active_symbols

    def test_failed_symbol_removed_from_correlation_calculations(self):
        """Verify failed symbol is not included in new correlation updates."""
        service = CorrelationService(provisional_min=5)

        eurusd = CurrencyPair(code="EURUSD")
        gbpusd = CurrencyPair(code="GBPUSD")

        service.register_symbol(eurusd)
        service.register_symbol(gbpusd)

        # Update with correlated data
        for i in range(10):
            prices = {"EURUSD": 1.10 + i * 0.01, "GBPUSD": 1.25 + i * 0.012}
            service.update(prices)

        # Matrix should have correlation for the pair
        matrix = service.get_matrix()
        key = "EURUSD:GBPUSD"
        assert key in matrix.values
        initial_corr = matrix.values[key]
        initial_ts = matrix.timestamp

        # Mark GBPUSD as failed
        service.mark_symbol_failed(gbpusd)

        # Continue updates with only EURUSD (should not update matrix)
        for i in range(10, 15):
            prices = {"EURUSD": 1.10 + i * 0.01}
            result = service.update(prices)
            # No updates because only 1 active symbol
            assert result is None

        # Matrix should retain old value but timestamp unchanged
        matrix = service.get_matrix()
        assert key in matrix.values
        assert matrix.values[key] == initial_corr
        assert matrix.timestamp == initial_ts

    def test_failed_symbol_cannot_get_correlation(self):
        """Verify correlation stops updating for failed symbol."""
        service = CorrelationService(provisional_min=5)

        eurusd = CurrencyPair(code="EURUSD")
        gbpusd = CurrencyPair(code="GBPUSD")
        usdjpy = CurrencyPair(code="USDJPY")

        service.register_symbol(eurusd)
        service.register_symbol(gbpusd)
        service.register_symbol(usdjpy)

        # Feed data for all three
        for i in range(10):
            prices = {
                "EURUSD": 1.10 + i * 0.01,
                "GBPUSD": 1.25 + i * 0.012,
                "USDJPY": 110.0 + i * 0.5,
            }
            service.update(prices)

        # Should have 3 correlations (EURUSD:GBPUSD, EURUSD:USDJPY, GBPUSD:USDJPY)
        matrix_before = service.get_matrix()
        assert len(matrix_before.values) == 3
        # pylint: disable=no-member
        gbp_eur_before = matrix_before.values.get("EURUSD:GBPUSD")
        # pylint: disable=no-member
        gbp_jpy_before = matrix_before.values.get("GBPUSD:USDJPY")

        # Mark GBPUSD as failed
        service.mark_symbol_failed(gbpusd)

        # Continue with only EURUSD and USDJPY
        for i in range(10, 15):
            prices = {"EURUSD": 1.10 + i * 0.01, "USDJPY": 110.0 + i * 0.5}
            service.update(prices)

        # Matrix still has old GBPUSD correlations (not removed)
        # but they haven't been updated (frozen at old values)
        matrix_after = service.get_matrix()
        assert len(matrix_after.values) == 3

        # GBPUSD correlations unchanged (frozen)
        assert matrix_after.values["EURUSD:GBPUSD"] == gbp_eur_before
        assert matrix_after.values["GBPUSD:USDJPY"] == gbp_jpy_before

        # EURUSD:USDJPY correlation continues updating (different value)
        assert "EURUSD:USDJPY" in matrix_after.values

    def test_mark_failed_idempotent(self):
        """Verify marking already-failed symbol is safe."""
        service = CorrelationService()

        eurusd = CurrencyPair(code="EURUSD")
        service.register_symbol(eurusd)

        assert len(service.active_symbols) == 1

        # Mark as failed multiple times
        service.mark_symbol_failed(eurusd)
        service.mark_symbol_failed(eurusd)
        service.mark_symbol_failed(eurusd)

        # Should only affect state once
        assert len(service.active_symbols) == 0


class TestOrchestratorFailureIsolation:
    """Test orchestrator excludes failed symbols from portfolio operations."""

    def test_failed_symbol_excluded_from_active_tracking(self):
        """Verify failed symbol removed from active symbols set."""
        eurusd = CurrencyPair(code="EURUSD")
        gbpusd = CurrencyPair(code="GBPUSD")
        usdjpy = CurrencyPair(code="USDJPY")

        config = PortfolioConfig()

        orchestrator = PortfolioOrchestrator(
            symbols=[eurusd, gbpusd, usdjpy],
            portfolio_config=config,
            initial_capital=10000.0,
        )

        # Initially all active
        assert len(orchestrator._active_symbols) == 3

        # Mark GBPUSD as failed
        orchestrator.mark_symbol_failed(gbpusd, "Data loading error")

        assert len(orchestrator._active_symbols) == 2
        assert "EURUSD" in orchestrator._active_symbols
        assert "GBPUSD" not in orchestrator._active_symbols
        assert "USDJPY" in orchestrator._active_symbols

    def test_failed_symbol_recorded_in_failures_dict(self):
        """Verify failure tracking maintains error messages."""
        eurusd = CurrencyPair(code="EURUSD")
        gbpusd = CurrencyPair(code="GBPUSD")

        config = PortfolioConfig()

        orchestrator = PortfolioOrchestrator(
            symbols=[eurusd, gbpusd],
            portfolio_config=config,
            initial_capital=10000.0,
        )

        # No failures initially
        assert len(orchestrator.get_failures()) == 0

        # Mark GBPUSD as failed
        error_msg = "Dataset file not found"
        orchestrator.mark_symbol_failed(gbpusd, error_msg)

        failures = orchestrator.get_failures()
        assert len(failures) == 1
        assert "GBPUSD" in failures
        assert failures["GBPUSD"] == error_msg

    def test_failed_symbol_excluded_from_allocation(self):
        """Verify failed symbol not included in capital allocation."""
        eurusd = CurrencyPair(code="EURUSD")
        gbpusd = CurrencyPair(code="GBPUSD")
        usdjpy = CurrencyPair(code="USDJPY")

        config = PortfolioConfig()

        orchestrator = PortfolioOrchestrator(
            symbols=[eurusd, gbpusd, usdjpy],
            portfolio_config=config,
            initial_capital=30000.0,
        )

        # Mark GBPUSD as failed before allocation
        orchestrator.mark_symbol_failed(gbpusd, "Risk breach")

        # Allocate capital (equal volatility for simplicity)
        volatility = {"EURUSD": 0.01, "GBPUSD": 0.01, "USDJPY": 0.01}
        allocations = orchestrator.allocate_capital(volatility)

        # Should only allocate to active symbols
        assert "EURUSD" in allocations
        assert "GBPUSD" not in allocations
        assert "USDJPY" in allocations
        assert len(allocations) == 2

        # Total allocated should equal capital
        total = sum(allocations.values())
        assert abs(total - 30000.0) < 0.01

    def test_failed_symbol_excluded_from_correlation_tracking(self):
        """Verify orchestrator propagates failure to correlation service."""
        eurusd = CurrencyPair(code="EURUSD")
        gbpusd = CurrencyPair(code="GBPUSD")

        config = PortfolioConfig()

        orchestrator = PortfolioOrchestrator(
            symbols=[eurusd, gbpusd],
            portfolio_config=config,
            initial_capital=10000.0,
        )

        # Initially both registered
        assert len(orchestrator.correlation_service.active_symbols) == 2

        # Mark GBPUSD as failed
        orchestrator.mark_symbol_failed(gbpusd, "Invalid data")

        # Correlation service should reflect failure
        assert len(orchestrator.correlation_service.active_symbols) == 1
        assert "EURUSD" in orchestrator.correlation_service.active_symbols
        assert "GBPUSD" not in orchestrator.correlation_service.active_symbols

    def test_all_symbols_failed_allocation_empty(self):
        """Verify allocation returns empty dict when all symbols fail."""
        eurusd = CurrencyPair(code="EURUSD")
        gbpusd = CurrencyPair(code="GBPUSD")

        config = PortfolioConfig()

        orchestrator = PortfolioOrchestrator(
            symbols=[eurusd, gbpusd],
            portfolio_config=config,
            initial_capital=10000.0,
        )

        # Fail all symbols
        orchestrator.mark_symbol_failed(eurusd, "Error 1")
        orchestrator.mark_symbol_failed(gbpusd, "Error 2")

        # Allocation should be empty
        volatility = {"EURUSD": 0.01, "GBPUSD": 0.01}
        allocations = orchestrator.allocate_capital(volatility)

        assert len(allocations) == 0

    def test_mark_failed_idempotent_orchestrator(self):
        """Verify marking same symbol failed multiple times is safe."""
        eurusd = CurrencyPair(code="EURUSD")

        config = PortfolioConfig()

        orchestrator = PortfolioOrchestrator(
            symbols=[eurusd],
            portfolio_config=config,
            initial_capital=10000.0,
        )

        # Mark as failed multiple times
        orchestrator.mark_symbol_failed(eurusd, "Error 1")
        orchestrator.mark_symbol_failed(eurusd, "Error 2")
        orchestrator.mark_symbol_failed(eurusd, "Error 3")

        # Should only record once (last error message)
        assert len(orchestrator._active_symbols) == 0
        failures = orchestrator.get_failures()
        assert len(failures) == 1
        assert failures["EURUSD"] == "Error 1"  # First call sets it
