"""Integration test for 3-symbol portfolio primitives.

Tests coordinated operation of correlation service, allocation engine,
and snapshot logger with realistic multi-symbol price data.

Per Phase 5 completion: validates portfolio components work together
even though full orchestrator execution is not yet implemented.
"""
from datetime import UTC, datetime

from src.backtest.portfolio.allocation_engine import AllocationEngine
from src.backtest.portfolio.correlation_service import CorrelationService
from src.backtest.portfolio.snapshot_logger import SnapshotLogger
from src.models.allocation import AllocationRequest
from src.models.portfolio import CurrencyPair
from src.models.snapshots import PortfolioSnapshotRecord


class TestPortfolioThreeSymbolsPrimitives:
    """Test portfolio primitives with 3-symbol coordinated workflow."""

    def test_correlation_allocation_snapshot_integration(self, tmp_path):
        """Verify correlation → allocation → snapshot pipeline with 3 symbols."""
        # Setup
        eurusd = CurrencyPair(code="EURUSD")
        gbpusd = CurrencyPair(code="GBPUSD")
        usdjpy = CurrencyPair(code="USDJPY")

        correlation_service = CorrelationService(
            window_size=30, provisional_min=10
        )
        allocation_engine = AllocationEngine(rounding_dp=2)
        snapshot_path = tmp_path / "snapshots.jsonl"
        snapshot_logger = SnapshotLogger(
            output_path=snapshot_path, interval=5
        )
        snapshot_logger.open()

        # Register symbols
        for pair in [eurusd, gbpusd, usdjpy]:
            correlation_service.register_symbol(pair)

        # Feed 15 candles of semi-correlated price data
        prices_sequence = []
        for i in range(15):
            prices = {
                "EURUSD": 1.10 + i * 0.002 + (i % 3) * 0.001,
                "GBPUSD": 1.25 + i * 0.003 + (i % 2) * 0.001,
                "USDJPY": 110.0 + i * 0.1 - (i % 4) * 0.05,
            }
            prices_sequence.append(prices)
            correlation_service.update(prices)

        # Verify correlation matrix is ready (>= provisional_min)
        matrix = correlation_service.get_matrix()
        assert len(matrix.values) == 3  # 3 pairs: EUR:GBP, EUR:JPY, GBP:JPY
        assert "EURUSD:GBPUSD" in matrix.values
        assert "EURUSD:USDJPY" in matrix.values
        assert "GBPUSD:USDJPY" in matrix.values

        # Create allocation request
        volatility = {"EURUSD": 0.008, "GBPUSD": 0.012, "USDJPY": 0.010}
        request = AllocationRequest(
            symbols=[eurusd, gbpusd, usdjpy],
            volatility=volatility,
            correlation_matrix=matrix.values,
            capital=10000.0,
        )

        # Allocate capital
        response = allocation_engine.allocate(request)
        assert len(response.allocations) == 3
        assert "EURUSD" in response.allocations
        assert "GBPUSD" in response.allocations
        assert "USDJPY" in response.allocations

        # Verify allocation sum precision
        total = sum(response.allocations.values())
        assert abs(total - 10000.0) < 0.01

        # Verify diversification ratio present
        assert 0.0 <= response.diversification_ratio <= 1.0

        # Log snapshots at every 5th candle
        positions = {
            "EURUSD": 0.5,
            "GBPUSD": 0.3,
            "USDJPY": 0.2,
        }
        unrealized_pnl = {
            "EURUSD": 50.0,
            "GBPUSD": 30.0,
            "USDJPY": -10.0,
        }

        for i, _ in enumerate(prices_sequence):
            snapshot = PortfolioSnapshotRecord(
                t=datetime(2025, 11, 6, 10, i, 0, tzinfo=UTC),
                positions=positions,
                unrealized=unrealized_pnl,
                portfolio_pnl=sum(unrealized_pnl.values()),
                exposure=0.8,
                diversification_ratio=response.diversification_ratio,
                corr_window=len(prices_sequence),
            )
            snapshot_logger.record(snapshot)

        snapshot_logger.close()

        # Verify snapshots were written (15 candles / 5 interval = 3 snapshots)
        assert snapshot_path.exists()
        with open(snapshot_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 3

    def test_correlation_threshold_affects_allocation(self):
        """Verify high correlation affects diversification ratio in allocation."""
        eurusd = CurrencyPair(code="EURUSD")
        gbpusd = CurrencyPair(code="GBPUSD")

        correlation_service = CorrelationService(provisional_min=5)
        allocation_engine = AllocationEngine()

        correlation_service.register_symbol(eurusd)
        correlation_service.register_symbol(gbpusd)

        # Feed highly correlated data (same trend)
        for i in range(10):
            prices = {"EURUSD": 1.10 + i * 0.01, "GBPUSD": 1.25 + i * 0.012}
            correlation_service.update(prices)

        matrix_high_corr = correlation_service.get_matrix()
        # pylint: disable=no-member
        correlation = list(matrix_high_corr.values.values())[0]
        assert abs(correlation) > 0.95  # Very high correlation

        # Allocate with high correlation
        volatility = {"EURUSD": 0.01, "GBPUSD": 0.01}
        request = AllocationRequest(
            symbols=[eurusd, gbpusd],
            volatility=volatility,
            correlation_matrix=matrix_high_corr.values,
            capital=10000.0,
        )

        response = allocation_engine.allocate(request)

        # With high correlation, diversification ratio should be low
        assert response.diversification_ratio < 0.8

    def test_failed_symbol_excluded_from_pipeline(self):
        """Verify failed symbol isolation throughout correlation-allocation pipeline."""
        eurusd = CurrencyPair(code="EURUSD")
        gbpusd = CurrencyPair(code="GBPUSD")
        usdjpy = CurrencyPair(code="USDJPY")

        correlation_service = CorrelationService(provisional_min=5)
        allocation_engine = AllocationEngine()

        for pair in [eurusd, gbpusd, usdjpy]:
            correlation_service.register_symbol(pair)

        # Feed initial data
        for i in range(10):
            prices = {
                "EURUSD": 1.10 + i * 0.01,
                "GBPUSD": 1.25 + i * 0.012,
                "USDJPY": 110.0 + i * 0.5,
            }
            correlation_service.update(prices)

        # Allocate with all 3 symbols
        volatility_all = {
            "EURUSD": 0.01,
            "GBPUSD": 0.012,
            "USDJPY": 0.010,
        }
        matrix = correlation_service.get_matrix()
        request_all = AllocationRequest(
            symbols=[eurusd, gbpusd, usdjpy],
            volatility=volatility_all,
            correlation_matrix=matrix.values,
            capital=10000.0,
        )
        response_all = allocation_engine.allocate(request_all)
        assert len(response_all.allocations) == 3

        # Mark GBPUSD as failed
        correlation_service.mark_symbol_failed(gbpusd)

        # Continue updates without GBPUSD
        for i in range(10, 15):
            prices = {"EURUSD": 1.10 + i * 0.01, "USDJPY": 110.0 + i * 0.5}
            correlation_service.update(prices)

        # Allocate with only 2 active symbols
        volatility_active = {"EURUSD": 0.01, "USDJPY": 0.010}
        matrix_after = correlation_service.get_matrix()
        request_active = AllocationRequest(
            symbols=[eurusd, usdjpy],  # Only active symbols
            volatility=volatility_active,
            correlation_matrix={
                # pylint: disable=no-member
                k: v
                for k, v in matrix_after.values.items()
                if "GBPUSD" not in k
            },
            capital=10000.0,
        )
        response_active = allocation_engine.allocate(request_active)

        # Only active symbols should be allocated
        assert len(response_active.allocations) == 2
        assert "EURUSD" in response_active.allocations
        assert "GBPUSD" not in response_active.allocations
        assert "USDJPY" in response_active.allocations

        # Capital still fully allocated
        total = sum(response_active.allocations.values())
        assert abs(total - 10000.0) < 0.01

    def test_snapshot_interval_respected_across_symbols(self, tmp_path):
        """Verify snapshot interval honored with multi-symbol updates."""
        snapshot_path = tmp_path / "interval_test.jsonl"
        logger = SnapshotLogger(output_path=snapshot_path, interval=10)
        logger.open()

        positions = {"EURUSD": 0.5, "GBPUSD": 0.5}
        pnl = {"EURUSD": 100.0, "GBPUSD": 50.0}

        # Log 30 snapshots (should write at 10, 20, 30 with interval=10)
        for i in range(1, 31):
            snapshot = PortfolioSnapshotRecord(
                t=datetime(2025, 11, 6, 10, 0, i, tzinfo=UTC),
                positions=positions,
                unrealized=pnl,
                portfolio_pnl=sum(pnl.values()),
                exposure=0.9,
                diversification_ratio=0.9,
                corr_window=100,
            )
            logger.record(snapshot)

        logger.close()

        # Should log at 10, 20, 30 (3 snapshots)
        with open(snapshot_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 3

    def test_allocation_precision_with_portfolio_capital(self):
        """Verify allocation rounding precision with realistic portfolio capital."""
        eurusd = CurrencyPair(code="EURUSD")
        gbpusd = CurrencyPair(code="GBPUSD")
        usdjpy = CurrencyPair(code="USDJPY")

        allocation_engine = AllocationEngine(rounding_dp=2)

        # Different volatilities
        volatility = {"EURUSD": 0.008, "GBPUSD": 0.015, "USDJPY": 0.012}

        # Low correlation matrix
        correlation = {
            "EURUSD:GBPUSD": 0.2,
            "EURUSD:USDJPY": 0.1,
            "GBPUSD:USDJPY": 0.15,
        }

        request = AllocationRequest(
            symbols=[eurusd, gbpusd, usdjpy],
            volatility=volatility,
            correlation_matrix=correlation,
            capital=50000.0,  # Larger portfolio
        )

        response = allocation_engine.allocate(request)

        # Verify sum precision
        total = sum(response.allocations.values())
        assert abs(total - 50000.0) < 0.01

        # Verify all allocations are 2 decimal places
        for allocation in response.allocations.values():
            rounded = round(allocation, 2)
            assert abs(allocation - rounded) < 1e-10
