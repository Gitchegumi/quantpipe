"""Independent multi-symbol backtest runner.

This module implements independent multi-symbol execution mode where each
symbol runs its backtest in isolation with no shared capital or risk state.
Results are aggregated for reporting but execution is completely isolated.
"""

import logging
from pathlib import Path
from typing import Optional

from src.backtest.orchestrator import BacktestOrchestrator
from src.backtest.portfolio.errors import PortfolioError
from src.config.parameters import StrategyParameters
from src.data_io.legacy_ingestion import ingest_candles
from src.models.directional import BacktestResult
from src.models.enums import DirectionMode
from src.models.portfolio import CurrencyPair, SymbolConfig

logger = logging.getLogger(__name__)


class IndependentRunner:
    """Executes isolated backtests across multiple symbols.

    Each symbol runs independently with its own capital allocation,
    risk limits, and execution context. No correlation or capital pooling.
    """

    def __init__(
        self,
        symbols: list[CurrencyPair],
        symbol_configs: Optional[dict[str, SymbolConfig]] = None,
        data_dir: Path = Path("price_data/processed"),
    ):
        """Initialize independent runner.

        Args:
            symbols: List of currency pairs to backtest
            symbol_configs: Optional per-symbol configuration overrides
            data_dir: Directory containing processed datasets
        """
        self.symbols = symbols
        self.symbol_configs = symbol_configs or {}
        self.data_dir = data_dir
        self._results: dict[str, BacktestResult] = {}
        self._failures: dict[str, str] = {}

    def run(
        self,
        strategy_params: StrategyParameters,
        mode: DirectionMode,
        output_dir: Path,
    ) -> dict[str, BacktestResult]:
        """Run independent backtests for all enabled symbols.

        Args:
            strategy_params: Strategy parameters to use
            mode: Directional mode (LONG/SHORT/BOTH)
            output_dir: Directory for output files

        Returns:
            Dictionary mapping symbol codes to backtest results
        """
        logger.info(
            "Starting independent multi-symbol run for %d symbols",
            len(self.symbols),
        )

        for pair in self.symbols:
            # Check if symbol is enabled
            config = self.symbol_configs.get(pair.code)
            if config and not config.enabled:
                logger.info("Skipping disabled symbol: %s", pair.code)
                continue

            # Run isolated backtest for this symbol
            try:
                result = self._run_symbol_backtest(
                    pair=pair,
                    strategy_params=strategy_params,
                    mode=mode,
                    output_dir=output_dir,
                )
                self._results[pair.code] = result

                # Get trade count from metrics (handle both MetricsSummary and
                # DirectionalMetrics)
                trade_count = self._get_trade_count(result)
                logger.info(
                    "Completed backtest for %s: %d trades",
                    pair.code,
                    trade_count,
                )

            except (FileNotFoundError, ValueError, PortfolioError) as exc:
                error_msg = f"Backtest failed for {pair.code}: {exc}"
                logger.warning(error_msg)
                self._failures[pair.code] = str(exc)
                # Continue with remaining symbols (isolation principle)

        logger.info(
            "Independent run complete: %d successful, %d failed",
            len(self._results),
            len(self._failures),
        )

        return self._results

    def _run_symbol_backtest(
        self,
        pair: CurrencyPair,
        strategy_params: StrategyParameters,
        mode: DirectionMode,
        output_dir: Path,
    ) -> BacktestResult:
        """Run backtest for a single symbol.

        Args:
            pair: Currency pair to backtest
            strategy_config: Strategy configuration
            mode: Directional mode
            output_dir: Output directory

        Returns:
            BacktestResult for this symbol

        Raises:
            FileNotFoundError: If dataset not found
            Exception: If backtest execution fails
        """
        # Construct dataset path
        dataset_path = self._get_dataset_path(pair)

        if not dataset_path.exists():
            raise FileNotFoundError(
                f"Dataset not found for {pair.code} at {dataset_path}"
            )

        # Create symbol-specific output directory
        symbol_output_dir = output_dir / pair.code.lower()
        symbol_output_dir.mkdir(parents=True, exist_ok=True)

        # Load candles using existing ingestion
        logger.debug("Loading dataset for %s", pair.code)
        candles = list(ingest_candles(dataset_path))

        # Create orchestrator
        orchestrator = BacktestOrchestrator(
            direction_mode=mode,
            dry_run=False,
        )

        # Run backtest
        run_id = f"{pair.code.lower()}_{mode.value.lower()}"
        logger.debug("Running backtest for %s with run_id %s", pair.code, run_id)

        result = orchestrator.run_backtest(
            candles=candles,
            pair=pair.code,
            run_id=run_id,
            ema_fast=strategy_params.ema_fast,
            ema_slow=strategy_params.ema_slow,
            atr_stop_mult=strategy_params.atr_stop_mult,
            target_r_mult=strategy_params.target_r_mult,
            cooldown_candles=strategy_params.cooldown_candles,
            rsi_length=strategy_params.rsi_length,
        )

        return result

    def _get_dataset_path(self, pair: CurrencyPair) -> Path:
        """Get path to processed dataset for a symbol.

        Args:
            pair: Currency pair

        Returns:
            Path to processed CSV file
        """
        # Standard path: price_data/processed/{symbol}/test/{symbol}_test.csv
        return (
            self.data_dir / pair.code.lower() / "test" / f"{pair.code.lower()}_test.csv"
        )

    def get_results(self) -> dict[str, BacktestResult]:
        """Get successful backtest results.

        Returns:
            Dictionary mapping symbol codes to results
        """
        return self._results.copy()

    def get_failures(self) -> dict[str, str]:
        """Get failed symbol backtest error messages.

        Returns:
            Dictionary mapping symbol codes to error messages
        """
        return self._failures.copy()

    def _get_trade_count(self, result: BacktestResult) -> int:
        """Extract trade count from BacktestResult metrics.

        Handles both MetricsSummary (LONG/SHORT) and DirectionalMetrics (BOTH).

        Args:
            result: BacktestResult to extract trade count from

        Returns:
            Number of trades executed
        """
        if hasattr(result.metrics, "combined"):
            # DirectionalMetrics (BOTH mode)
            return result.metrics.combined.trade_count
        # MetricsSummary (LONG/SHORT mode)
        return result.metrics.trade_count

    def _get_win_rate(self, result: BacktestResult) -> float:
        """Extract win rate from BacktestResult metrics.

        Handles both MetricsSummary (LONG/SHORT) and DirectionalMetrics (BOTH).

        Args:
            result: BacktestResult to extract win rate from

        Returns:
            Win rate as fraction (0.0 to 1.0)
        """
        if hasattr(result.metrics, "combined"):
            # DirectionalMetrics (BOTH mode)
            return result.metrics.combined.win_rate
        # MetricsSummary (LONG/SHORT mode)
        return result.metrics.win_rate

    def get_summary(self) -> dict:
        """Get summary statistics across all symbols.

        Returns:
            Dictionary with aggregate statistics
        """
        if not self._results:
            return {
                "total_symbols": len(self.symbols),
                "successful": 0,
                "failed": len(self._failures),
                "total_trades": 0,
                "average_win_rate": 0.0,
            }

        total_trades = sum(self._get_trade_count(r) for r in self._results.values())
        win_rates = [
            self._get_win_rate(r)
            for r in self._results.values()
            if self._get_trade_count(r) > 0
        ]
        avg_win_rate = sum(win_rates) / len(win_rates) if win_rates else 0.0

        return {
            "total_symbols": len(self.symbols),
            "successful": len(self._results),
            "failed": len(self._failures),
            "total_trades": total_trades,
            "average_win_rate": avg_win_rate,
        }
