"""
Simple CLI command to run long-only backtest.

Minimal implementation for MVP testing.
"""

# pylint: disable=broad-exception-caught

import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from ..backtest.execution import simulate_execution
from ..backtest.metrics_ingest import MetricsIngestor
from ..backtest.observability import ObservabilityReporter
from ..cli.logging_setup import setup_logging
from ..config.parameters import StrategyParameters
from ..io.legacy_ingestion import ingest_candles
from ..strategy.trend_pullback.signal_generator import generate_long_signals


logger = logging.getLogger(__name__)


def preprocess_metatrader_csv(csv_path: Path, output_dir: Path) -> Path:
    """
    Convert MetaTrader CSV format to expected format.

    Args:
        csv_path: Path to MetaTrader CSV (Date,Time,O,H,L,C,V).
        output_dir: Directory to save converted CSV.

    Returns:
        Path to converted CSV file.
    """
    # Check if CSV is already in converted format (has timestamp_utc header)
    with open(csv_path, encoding="utf-8") as f:
        first_line = f.readline().strip()
        if "timestamp_utc" in first_line.lower():
            logger.info("CSV already in converted format, using as-is")
            return csv_path

    logger.info("Converting MetaTrader CSV format")

    # Read CSV (MetaTrader format: Date,Time,Open,High,Low,Close,Volume)
    df = pd.read_csv(
        csv_path,
        header=None,
        names=["date", "time", "open", "high", "low", "close", "volume"],
    )

    # Combine date and time into timestamp
    df["timestamp_utc"] = pd.to_datetime(
        df["date"] + " " + df["time"], format="%Y.%m.%d %H:%M"
    )

    # Select required columns
    df = df[["timestamp_utc", "open", "high", "low", "close", "volume"]]

    # Save converted CSV
    output_path = output_dir / f"converted_{csv_path.name}"
    df.to_csv(output_path, index=False)
    logger.info("Saved converted CSV: %s", output_path)

    return output_path


def run_simple_backtest(
    price_data_path: Path,
    output_dir: Path,
    parameters: StrategyParameters | None = None,
    log_level: str = "INFO",
) -> dict:
    """
    Run simplified long-only backtest.

    Args:
        price_data_path: Path to CSV file.
        output_dir: Output directory for results.
        parameters: Strategy parameters (defaults if None).
        log_level: Logging level.
        fill_gaps: If True, fill gaps with synthetic candles (default False for tests).

    Returns:
        Dictionary with backtest results.
    """
    # Setup
    setup_logging(level=log_level)
    if parameters is None:
        parameters = StrategyParameters()

    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting backtest: %s", price_data_path)

    # Convert CSV if needed
    converted_csv = preprocess_metatrader_csv(price_data_path, output_dir)

    # Ingest candles
    logger.info("Ingesting candles...")
    candles = list(
        ingest_candles(
            csv_path=converted_csv,
            ema_fast=parameters.ema_fast,
            ema_slow=parameters.ema_slow,
            atr_period=parameters.atr_length,
            rsi_period=parameters.rsi_length,
            stoch_rsi_period=parameters.rsi_length,
            expected_timeframe_minutes=1,  # M1 data
            allow_gaps=True,  # FX data has natural gaps (weekends)
        )
    )

    logger.info("Loaded %d candles", len(candles))

    # Setup reporting
    reporter = ObservabilityReporter(
        backtest_id=f"simple-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        total_candles=len(candles),
    )
    reporter.start()

    # Setup metrics
    metrics = MetricsIngestor()

    # Process candles
    signals_generated = 0
    params_dict = {
        "ema_fast": parameters.ema_fast,
        "ema_slow": parameters.ema_slow,
        "rsi_period": parameters.rsi_length,
        "atr_multiplier": parameters.atr_stop_mult,
        "risk_reward_ratio": parameters.target_r_mult,
    }

    for i in range(parameters.ema_slow, len(candles)):
        window = candles[max(0, i - 100) : i + 1]

        # Generate signals
        signals = generate_long_signals(
            candles=window,
            parameters=params_dict,
        )

        if signals:
            signal = signals[0]
            signals_generated += 1
            reporter.report_signal_generated(signal.id, signal.timestamp_utc)

            # Simulate execution
            remaining_candles = candles[i:]
            execution = simulate_execution(
                signal=signal,
                candles=remaining_candles,
                slippage_pips=0.5,
                spread_pips=1.0,
            )

            if execution:
                metrics.ingest(execution)
                reporter.report_trade_executed(
                    signal_id=execution.signal_id,
                    pnl_r=execution.pnl_r,
                    exit_reason=execution.exit_reason,
                )

        # Update progress
        if i % 100 == 0:
            reporter.update_progress(100)

    # Final progress
    reporter.update_progress(len(candles) % 100)

    # Get summary
    summary = metrics.get_summary()
    reporter.report_metrics(summary)
    reporter.finish()

    logger.info("Backtest complete: %d signals generated", signals_generated)

    return {
        "strategy_name": "trend_pullback_long_only",
        "signals_generated": signals_generated,
        "trade_count": summary.trade_count,
        "win_rate": summary.win_rate,
        "expectancy": summary.expectancy,
        "avg_r": summary.avg_r,
        "sharpe_estimate": summary.sharpe_estimate,
        "profit_factor": summary.profit_factor,
        "max_drawdown_r": summary.max_drawdown_r,
    }


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run long-only backtest")
    parser.add_argument("--data", type=Path, required=True, help="Path to CSV file")
    parser.add_argument(
        "--output", type=Path, default=Path("results"), help="Output directory"
    )
    parser.add_argument(
        "--log-level", choices=["DEBUG", "INFO", "WARNING"], default="INFO"
    )

    args = parser.parse_args()

    try:
        result = run_simple_backtest(
            price_data_path=args.data,
            output_dir=args.output,
            log_level=args.log_level,
        )
        print(f"\nResults: {result}")
        return 0
    except Exception as e:
        logger.error("Backtest failed: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
