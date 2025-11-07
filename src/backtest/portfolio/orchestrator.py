"""Portfolio orchestrator for multi-symbol backtesting.

This module coordinates portfolio-mode execution across multiple symbols with
shared capital, correlation tracking, and unified position management.

Per FR-010, FR-022, and research decisions for portfolio mode implementation.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.backtest.portfolio.allocation_engine import AllocationEngine
from src.backtest.portfolio.correlation_service import CorrelationService
from src.backtest.portfolio.snapshot_logger import SnapshotLogger
from src.config.parameters import StrategyParameters
from src.models.allocation import AllocationRequest
from src.models.directional import BacktestResult
from src.models.enums import DirectionMode
from src.models.portfolio import CurrencyPair, PortfolioConfig
from src.models.snapshots import PortfolioSnapshotRecord

logger = logging.getLogger(__name__)


class PortfolioOrchestrator:
    """Coordinates multi-symbol portfolio backtesting execution.

    Manages shared capital pool, correlation tracking, capital allocation,
    and unified timestamp iteration across symbols. Generates portfolio-level
    metrics and periodic snapshots.

    Attributes:
        symbols: List of currency pairs in portfolio
        portfolio_config: Portfolio-level configuration
        initial_capital: Starting capital for portfolio
        correlation_service: Correlation matrix calculator
        allocation_engine: Capital allocation engine
        snapshot_logger: Snapshot recording logger (optional)
    """

    def __init__(
        self,
        symbols: list[CurrencyPair],
        portfolio_config: PortfolioConfig,
        data_dir: Path = Path("price_data/processed"),
    ):
        """Initialize portfolio orchestrator.

        Args:
            symbols: List of currency pairs to include in portfolio
            portfolio_config: Portfolio configuration
            data_dir: Directory containing processed datasets
        """
        self.symbols = symbols
        self.portfolio_config = portfolio_config
        self.data_dir = data_dir
        self.initial_capital = portfolio_config.initial_capital

        # Initialize services
        self.correlation_service = CorrelationService(
            window_size=100,  # Per FR-010
            provisional_min=20,  # Per FR-010
        )

        self.allocation_engine = AllocationEngine(rounding_dp=2)

        self.snapshot_logger: Optional[SnapshotLogger] = None

        # Runtime state
        self._current_capital = self.initial_capital
        self._per_symbol_results: dict[str, BacktestResult] = {}
        self._failures: dict[str, str] = {}
        self._active_symbols: set[str] = {pair.code for pair in symbols}

        # Register symbols with correlation service
        for pair in symbols:
            self.correlation_service.register_symbol(pair)

        logger.info(
            "Initialized PortfolioOrchestrator: %d symbols, capital=%.2f",
            len(symbols),
            self.initial_capital,
        )

    def run(
        self,
        strategy_params: StrategyParameters,  # pylint: disable=unused-argument
        mode: DirectionMode,
        output_dir: Path,
        snapshot_interval: Optional[int] = None,
    ) -> dict[str, BacktestResult]:
        """Run portfolio backtest across all symbols.

        This is a foundational implementation that will be enhanced iteratively.
        Currently raises NotImplementedError as full portfolio execution logic
        requires additional components (price synchronization, signal coordination,
        position management integration).

        Args:
            strategy_params: Strategy parameters
            mode: Direction mode (LONG/SHORT/BOTH)
            output_dir: Output directory
            snapshot_interval: Snapshot interval in bars (None disables snapshots)

        Returns:
            Dictionary mapping symbol codes to backtest results

        Raises:
            NotImplementedError: Full portfolio orchestration not yet implemented
        """
        logger.info(
            "Portfolio orchestrator run requested for %d symbols in %s mode",
            len(self.symbols),
            mode.value,
        )

        # Setup snapshot logger if interval provided
        if snapshot_interval:
            snapshot_path = (
                output_dir
                / (
                    f"portfolio_snapshots_"
                    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
                )
            )
            self.snapshot_logger = SnapshotLogger(
                output_path=snapshot_path, interval=snapshot_interval
            )

        # Full implementation deferred:
        # 1. Load and synchronize price data across symbols
        # 2. Iterate unified timestamp sequence
        # 3. Update correlation matrix at each timestamp
        # 4. Allocate capital using allocation engine
        # 5. Generate signals per symbol
        # 6. Execute trades within allocated capital
        # 7. Track portfolio-level metrics
        # 8. Record snapshots at intervals
        # 9. Handle symbol failures per Decision 5

        raise NotImplementedError(
            "Full portfolio orchestration requires integration with "
            "price synchronization, signal generation, and position management. "
            "This foundational component is ready for incremental enhancement."
        )

    def get_results(self) -> dict[str, BacktestResult]:
        """Get per-symbol backtest results.

        Returns:
            Dictionary mapping symbol codes to backtest results
        """
        return self._per_symbol_results.copy()

    def get_failures(self) -> dict[str, str]:
        """Get symbol failures with error messages.

        Returns:
            Dictionary mapping failed symbol codes to error messages
        """
        return self._failures.copy()

    def get_portfolio_capital(self) -> float:
        """Get current portfolio capital.

        Returns:
            Current total portfolio capital
        """
        return self._current_capital

    def allocate_capital(
        self, volatility: dict[str, float]
    ) -> dict[str, float]:
        """Allocate capital across active symbols.

        Uses allocation engine with current correlation matrix and symbol
        volatilities to compute per-symbol capital allocation.

        Args:
            volatility: Per-symbol volatility metrics

        Returns:
            Dictionary mapping symbol codes to allocated capital amounts
        """
        active_pairs = [
            pair for pair in self.symbols if pair.code in self._active_symbols
        ]

        if not active_pairs:
            logger.warning("No active symbols for capital allocation")
            return {}

        # Build allocation request
        request = AllocationRequest(
            symbols=active_pairs,
            volatility=volatility,
            correlation_matrix=self.correlation_service.get_matrix().values,
            capital=self._current_capital,
        )

        # Compute allocation
        response = self.allocation_engine.allocate(request)

        logger.info(
            "Allocated capital across %d symbols (diversification: %.3f)",
            len(response.allocations),
            response.diversification_ratio,
        )

        return response.allocations

    def mark_symbol_failed(self, symbol: CurrencyPair, error: str) -> None:
        """Mark a symbol as failed and exclude from further processing.

        Per research Decision 5: failed symbols are removed from correlation
        calculations and capital allocation.

        Args:
            symbol: Currency pair that failed
            error: Error message describing failure
        """
        if symbol.code in self._active_symbols:
            self._active_symbols.remove(symbol.code)
            self._failures[symbol.code] = error
            self.correlation_service.mark_symbol_failed(symbol)

            logger.warning(
                "Marked symbol %s as failed: %s (active symbols: %d)",
                symbol.code,
                error,
                len(self._active_symbols),
            )

    def record_snapshot(
        self,
        *,
        timestamp: datetime,
        positions: dict[str, float],
        unrealized_pnl: dict[str, float],
        portfolio_pnl: float,
        exposure: float,
    ) -> None:
        """Record portfolio snapshot.

        Args:
            timestamp: Current timestamp
            positions: Per-symbol position sizes
            unrealized_pnl: Per-symbol unrealized P&L
            portfolio_pnl: Total portfolio P&L
            exposure: Portfolio exposure ratio
        """
        if not self.snapshot_logger:
            return

        # Get current correlation window size (average across pairs)
        # This is a simplified approach - could be enhanced
        corr_window = 0
        if self.correlation_service.windows:
            window_sizes = [
                len(w.values_a) for w in self.correlation_service.windows.values()
            ]
            corr_window = (
                int(sum(window_sizes) / len(window_sizes)) if window_sizes else 0
            )

        # Get diversification ratio from latest allocation
        # This would come from the most recent allocation response
        # For now, use a placeholder - will be enhanced when integrated
        diversification = 0.0

        snapshot = PortfolioSnapshotRecord(
            t=timestamp,
            positions=positions,
            unrealized=unrealized_pnl,
            portfolio_pnl=portfolio_pnl,
            exposure=exposure,
            diversification_ratio=diversification,
            corr_window=corr_window,
        )

        self.snapshot_logger.record(snapshot)
