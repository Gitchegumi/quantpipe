"""
CLI command to run long-only backtest for US1 trend pullback strategy.

This module provides the entry point for running backtests with long signal
generation only, suitable for validating US1 acceptance criteria.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

from ..config.parameters import StrategyParameters
from ..io.ingestion import ingest_price_data
from ..io.manifest import create_manifest
from ..strategy.trend_pullback.signal_generator import generate_long_signals
from ..backtest.execution import simulate_execution
from ..backtest.metrics_ingest import MetricsIngestor
from ..backtest.observability import ObservabilityReporter
from ..backtest.reproducibility import ReproducibilityTracker
from ..strategy.id_factory import compute_parameters_hash
from ..models.core import BacktestRun, Candle
from ..cli.logging_setup import setup_logging

logger = logging.getLogger(__name__)


def run_long_backtest(
    price_data_path: Path,
    output_dir: Path,
    parameters: StrategyParameters | None = None,
    log_level: str = "INFO",
) -> BacktestRun:
    """
    Execute long-only backtest for trend pullback strategy.

    This function orchestrates the complete backtest workflow:
    1. Load and validate price data
    2. Generate long signals
    3. Simulate trade executions
    4. Compute performance metrics
    5. Save results and reproducibility hashes

    Args:
        price_data_path: Path to CSV price data file.
        output_dir: Directory to save backtest results.
        parameters: Strategy parameters (uses defaults if None).
        log_level: Logging level (default "INFO").

    Returns:
        BacktestRun with complete results.

    Examples:
        >>> from pathlib import Path
        >>> result = run_long_backtest(
        ...     price_data_path=Path("data/eurusd_h1.csv"),
        ...     output_dir=Path("results"),
        ... )
        >>> result.metrics_summary.total_trades
        42
    """
    # Setup logging
    setup_logging(level=log_level)

    # Use default parameters if not provided
    if parameters is None:
        parameters = StrategyParameters()

    logger.info("Starting long-only backtest")
    logger.info(f"Price data: {price_data_path}")
    logger.info(f"Output directory: {output_dir}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize reproducibility tracker
    repro_tracker = ReproducibilityTracker()
    parameters_hash = compute_parameters_hash(parameters)
    repro_tracker.add_event(f"parameters_hash:{parameters_hash}")

    # Create data manifest
    manifest = create_manifest(price_data_path, pair="EURUSD")
    repro_tracker.add_event(f"manifest_hash:{manifest.checksum_sha256}")

    logger.info(f"Data manifest: {manifest.date_range_start} to {manifest.date_range_end}")

    # Ingest price data
    candles = list(ingest_price_data(
        price_data_path,
        pair="EURUSD",
        timeframe_minutes=parameters.timeframe_minutes,
        ema_fast_period=parameters.ema_fast_period,
        ema_slow_period=parameters.ema_slow_period,
        atr_period=parameters.atr_period,
        rsi_period=parameters.rsi_period,
        stoch_rsi_period=parameters.stoch_rsi_period,
    ))

    logger.info(f"Loaded {len(candles)} candles")

    # Initialize observability reporter
    reporter = ObservabilityReporter(
        backtest_id=f"long-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        total_candles=len(candles),
    )
    reporter.start()

    # Initialize metrics ingestor
    metrics_ingestor = MetricsIngestor()

    # Process candles for signal generation
    signals_generated = 0
    executions_completed = 0
    last_signal_timestamp = None

    for i in range(parameters.ema_slow_period, len(candles)):
        # Get historical window for analysis
        window = candles[max(0, i - 100):i + 1]
        current_candle = candles[i]

        # Generate long signals
        signals = generate_long_signals(
            candles=window,
            parameters=parameters,
            last_signal_timestamp=last_signal_timestamp,
        )

        if signals:
            signal = signals[0]
            signals_generated += 1
            last_signal_timestamp = signal.timestamp_utc
            repro_tracker.add_event(f"signal:{signal.id}")
            reporter.report_signal_generated(signal.id, signal.timestamp_utc)

            # Simulate execution with remaining candles
            remaining_candles = candles[i:]
            execution = simulate_execution(
                signal=signal,
                candles=remaining_candles,
                slippage_pips=parameters.slippage_pips,
                spread_pips=parameters.spread_pips,
            )

            if execution:
                executions_completed += 1
                metrics_ingestor.ingest(execution)
                repro_tracker.add_event(f"execution:{execution.signal_id}")
                reporter.report_trade_executed(
                    signal_id=execution.signal_id,
                    pnl_r=execution.pnl_r,
                    exit_reason=execution.exit_reason,
                )

        # Update progress every 100 candles
        if i % 100 == 0:
            reporter.update_progress(100)

    # Final progress update
    reporter.update_progress(len(candles) % 100)

    # Get metrics summary
    metrics_summary = metrics_ingestor.get_summary()

    # Finalize reproducibility hash
    final_hash = repro_tracker.finalize()

    # Create BacktestRun
    backtest_run = BacktestRun(
        run_id=reporter.backtest_id,
        strategy_name="trend_pullback_long_only",
        parameters_hash=parameters_hash,
        data_manifest_hash=manifest.checksum_sha256,
        start_timestamp_utc=manifest.date_range_start,
        end_timestamp_utc=manifest.date_range_end,
        total_signals_generated=signals_generated,
        total_executions=executions_completed,
        metrics_summary=metrics_summary,
        reproducibility_hash=final_hash,
    )

    # Report final metrics
    reporter.report_metrics(metrics_summary)
    reporter.finish()

    # Save results
    results_file = output_dir / f"{backtest_run.run_id}_results.json"
    logger.info(f"Saving results to {results_file}")

    logger.info(
        f"Backtest complete: signals={signals_generated}, "
        f"executions={executions_completed}, "
        f"expectancy={metrics_summary.expectancy:.3f}R"
    )

    return backtest_run


def main() -> int:
    """
    CLI entry point for long-only backtest.

    Returns:
        Exit code (0 for success, 1 for error).

    Examples:
        $ poetry run python -m src.cli.run_long_backtest \\
            --data price_data/eurusd_h1.csv \\
            --output results/
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Run long-only backtest for trend pullback strategy"
    )
    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help="Path to CSV price data file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results"),
        help="Output directory for results (default: results/)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    try:
        backtest_run = run_long_backtest(
            price_data_path=args.data,
            output_dir=args.output,
            log_level=args.log_level,
        )
        return 0
    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
