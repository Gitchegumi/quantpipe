#!/usr/bin/env python3
"""
Split-mode backtest CLI for partition-based evaluation.

This CLI runs backtests separately on test and validation partitions,
enabling reproducible evaluation with distinct training/validation phases.

Usage:
    # Basic split-mode backtest
    python -m src.cli.run_split_backtest --symbol eurusd --direction LONG

    # With custom processed data path
    python -m src.cli.run_split_backtest --symbol eurusd --direction LONG \\
        --processed-path price_data/processed

    # JSON output
    python -m src.cli.run_split_backtest --symbol eurusd --direction LONG \\
        --output-format json

Feature: 004-timeseries-dataset
Task: T032 - Add split-mode CLI
"""

# pylint: disable=f-string-without-interpolation line-too-long

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from ..backtest.orchestrator import BacktestOrchestrator
from ..cli.logging_setup import setup_logging
from ..config.parameters import StrategyParameters
from ..data_io.formatters import format_split_mode_json, format_split_mode_text
from ..data_io.partition_loader import check_partitions_exist, load_both_partitions
from ..models.directional import PartitionMetrics, SplitModeResult
from ..models.enums import DirectionMode, OutputFormat


logger = logging.getLogger(__name__)


def main():
    """Run split-mode backtest on test and validation partitions."""
    parser = argparse.ArgumentParser(
        description="Run split-mode backtest on test/validation partitions"
    )

    parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="Symbol to backtest (e.g., eurusd)",
    )

    parser.add_argument(
        "--direction",
        type=str,
        choices=["LONG", "SHORT", "BOTH"],
        default="LONG",
        help="Trading direction: LONG (buy only), SHORT (sell only), or BOTH",
    )

    parser.add_argument(
        "--processed-path",
        type=Path,
        default=Path("price_data/processed"),
        help="Path to processed partitions directory (default: price_data/processed)",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results"),
        help="Output directory for results (default: results/)",
    )

    parser.add_argument(
        "--output-format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format: text (human-readable) or json (machine-readable)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(level=args.log_level)
    logger.info("Starting split-mode backtest")
    logger.info("Symbol: %s", args.symbol)
    logger.info("Direction: %s", args.direction)
    logger.info("Processed path: %s", args.processed_path)

    # Check partitions exist (T031 - missing partition guard)
    status = check_partitions_exist(args.symbol, args.processed_path)
    missing = [k for k, v in status.items() if k != "metadata" and not v]

    if missing:
        logger.error(
            "Missing partitions for symbol %s: %s",
            args.symbol,
            missing,
        )
        logger.error(
            "Run: poetry run build-dataset --symbol %s",
            args.symbol,
        )
        print(
            f"Error: Missing partitions for {args.symbol}: {missing}",
            file=sys.stderr,
        )
        print(
            f"Run: poetry run build-dataset --symbol {args.symbol}",
            file=sys.stderr,
        )
        sys.exit(1)

    logger.info("✓ Partitions found for symbol %s", args.symbol)

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Load strategy parameters (using defaults)
    parameters = StrategyParameters()
    logger.info(
        "Using strategy parameters: EMA(%d/%d), ATR mult: %.1f",
        parameters.ema_fast,
        parameters.ema_slow,
        parameters.atr_stop_mult,
    )

    # Load both partitions
    logger.info("Loading test and validation partitions")
    partitions = load_both_partitions(
        symbol=args.symbol,
        processed_path=args.processed_path,
        ema_fast=parameters.ema_fast,
        ema_slow=parameters.ema_slow,
        atr_period=parameters.atr_length,
        rsi_period=parameters.rsi_length,
        stoch_rsi_period=parameters.rsi_length,
        expected_timeframe_minutes=1,
        allow_gaps=True,
    )

    test_candles = partitions["test"]
    validation_candles = partitions["validation"]

    logger.info("Loaded %d test candles", len(test_candles))
    logger.info("Loaded %d validation candles", len(validation_candles))

    # Create orchestrator
    direction_mode = DirectionMode[args.direction]
    orchestrator = BacktestOrchestrator(direction_mode=direction_mode, dry_run=False)

    # Build signal parameters from strategy config
    signal_params = {
        "ema_fast": parameters.ema_fast,
        "ema_slow": parameters.ema_slow,
        "atr_stop_mult": parameters.atr_stop_mult,
        "target_r_mult": parameters.target_r_mult,
        "cooldown_candles": parameters.cooldown_candles,
        "rsi_length": parameters.rsi_length,
    }

    # Run backtest on test partition
    logger.info("Running backtest on TEST partition")
    start_time = datetime.now(UTC)

    test_run_id = (
        f"{args.direction.lower()}_test_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
    )
    test_result = orchestrator.run_backtest(
        candles=test_candles,
        pair=args.symbol,
        run_id=test_run_id,
        **signal_params,
    )

    logger.info(
        "Test partition backtest complete: %d trades",
        (
            test_result.metrics.trade_count
            if hasattr(test_result.metrics, "trade_count")
            else 0
        ),
    )

    # Run backtest on validation partition
    logger.info("Running backtest on VALIDATION partition")
    validation_run_id = f"{args.direction.lower()}_validation_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
    validation_result = orchestrator.run_backtest(
        candles=validation_candles,
        pair=args.symbol,
        run_id=validation_run_id,
        **signal_params,
    )

    end_time = datetime.now(UTC)

    logger.info(
        "Validation partition backtest complete: %d trades",
        (
            validation_result.metrics.trade_count
            if hasattr(validation_result.metrics, "trade_count")
            else 0
        ),
    )

    # Create split-mode result
    split_run_id = f"split_{args.direction.lower()}_{args.symbol}_{start_time.strftime('%Y%m%d_%H%M%S')}"

    split_result = SplitModeResult(
        run_id=split_run_id,
        symbol=args.symbol,
        direction_mode=args.direction,
        start_time=start_time,
        end_time=end_time,
        test_partition=PartitionMetrics(
            partition="test",
            metrics=test_result.metrics,
        ),
        validation_partition=PartitionMetrics(
            partition="validation",
            metrics=validation_result.metrics,
        ),
    )

    logger.info("Split-mode backtest complete: %s", split_result.run_id)

    # Format output
    output_format = (
        OutputFormat.JSON if args.output_format == "json" else OutputFormat.TEXT
    )

    if output_format == OutputFormat.JSON:
        output_content = format_split_mode_json(split_result)
    else:
        output_content = format_split_mode_text(split_result)

    # Generate output filename
    output_filename = f"split_{args.direction.lower()}_{args.symbol}_{start_time.strftime('%Y%m%d_%H%M%S')}.{'json' if output_format == OutputFormat.JSON else 'txt'}"
    output_path = args.output / output_filename

    # Write output file
    output_path.write_text(output_content)
    logger.info("Results written to %s", output_path)

    # Print summary to console
    if output_format == OutputFormat.TEXT:
        print(output_content)
    else:
        print(f"Results saved to: {output_path}")
        print(f"Symbol: {args.symbol}")
        print(f"Direction: {args.direction}")
        print(f"\nTest Partition:")
        if hasattr(split_result.test_partition.metrics, "combined"):
            metrics = split_result.test_partition.metrics.combined
        else:
            metrics = split_result.test_partition.metrics
        print(f"  Trades: {metrics.trade_count}")
        print(f"  Win rate: {metrics.win_rate:.2%}")
        print(f"  Average R: {metrics.avg_r:.2f}")

        print(f"\nValidation Partition:")
        if hasattr(split_result.validation_partition.metrics, "combined"):
            metrics = split_result.validation_partition.metrics.combined
        else:
            metrics = split_result.validation_partition.metrics
        print(f"  Trades: {metrics.trade_count}")
        print(f"  Win rate: {metrics.win_rate:.2%}")
        print(f"  Average R: {metrics.avg_r:.2f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
