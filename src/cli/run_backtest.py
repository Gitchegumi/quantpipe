#!/usr/bin/env python3
"""
Unified backtest CLI with direction mode support and JSON output.

This CLI supports running backtests in three modes:
- LONG: Long-only signals (buy setups)
- SHORT: Short-only signals (sell setups)
- BOTH: Both long and short signals with conflict resolution

Output Formats:
- text: Human-readable console output (default)
- json: Machine-readable JSON format for programmatic processing

Multi-Strategy/Multi-Pair Support:
- --strategy: Accepts multiple strategy names (future: will run each strategy)
- --pair: Accepts multiple currency pairs (future: will run each pair)
- Current: Uses first strategy/pair; future iterations will loop over all

Usage:
    # Basic LONG backtest
    python -m src.cli.run_backtest --direction LONG --data <csv_path>
    
    # With explicit strategy and pair
    python -m src.cli.run_backtest --direction LONG --data <csv_path> \\
        --strategy trend-pullback --pair EURUSD
    
    # Multiple pairs (future support)
    python -m src.cli.run_backtest --direction LONG --data <csv_path> \\
        --pair EURUSD GBPUSD USDJPY
    
    # JSON output
    python -m src.cli.run_backtest --direction LONG --data <csv_path> \\
        --output-format json
    
    # Dry-run (signals only)
    python -m src.cli.run_backtest --direction LONG --data <csv_path> --dry-run
"""

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from ..backtest.orchestrator import BacktestOrchestrator
from ..cli.logging_setup import setup_logging
from ..config.parameters import StrategyParameters
from ..io.formatters import (
    format_json_output,
    format_text_output,
    generate_output_filename,
)
from ..io.ingestion import ingest_candles
from ..models.enums import DirectionMode, OutputFormat

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
    output_df = df[["timestamp_utc", "open", "high", "low", "close", "volume"]]

    # Save converted file
    converted_filename = f"converted_{csv_path.name}"
    converted_path = output_dir / converted_filename
    output_df.to_csv(converted_path, index=False)

    logger.info("Converted CSV saved to %s", converted_path)
    return converted_path





def main():
    """
    Main entry point for unified backtest CLI.

    Supports LONG, SHORT, and BOTH direction modes with text/JSON output.
    """
    parser = argparse.ArgumentParser(
        description="Run trend-pullback backtest with configurable direction"
    )

    parser.add_argument(
        "--direction",
        type=str,
        choices=["LONG", "SHORT", "BOTH"],
        default="LONG",
        help="Trading direction: LONG (buy only), SHORT (sell only), or BOTH",
    )

    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help="Path to CSV price data file (MetaTrader format or standard format)",
    )

    parser.add_argument(
        "--strategy",
        type=str,
        nargs="+",
        default=["trend-pullback"],
        help="Strategy name(s) to run (default: trend-pullback). Supports multiple: --strategy strat1 strat2",
    )

    parser.add_argument(
        "--pair",
        type=str,
        nargs="+",
        default=["EURUSD"],
        help="Currency pair(s) to backtest (default: EURUSD). Supports multiple: --pair EURUSD GBPUSD",
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

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate signals without execution (signal-only mode)",
    )

    args = parser.parse_args()

    # Validate data file exists
    if not args.data.exists():
        print(f"Error: Data file not found: {args.data}", file=sys.stderr)
        sys.exit(1)

    # Setup logging
    setup_logging(level=args.log_level)
    logger.info("Starting directional backtest")
    logger.info("Direction: %s", args.direction)
    logger.info("Strategy: %s", ", ".join(args.strategy))
    logger.info("Pair(s): %s", ", ".join(args.pair))
    logger.info("Data: %s", args.data)
    logger.info("Dry-run: %s", args.dry_run)

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Convert MetaTrader CSV if needed
    logger.info("Preprocessing CSV data")
    converted_csv = preprocess_metatrader_csv(args.data, args.output)

    # Load strategy parameters (using defaults)
    parameters = StrategyParameters()
    logger.info(
        "Using strategy parameters: EMA(%d/%d), ATR mult: %.1f",
        parameters.ema_fast,
        parameters.ema_slow,
        parameters.atr_stop_mult,
    )

    # Ingest candles
    logger.info("Ingesting candles from %s", converted_csv)
    candles = list(
        ingest_candles(
            csv_path=converted_csv,
            ema_fast=parameters.ema_fast,
            ema_slow=parameters.ema_slow,
            atr_period=parameters.atr_length,
            rsi_period=parameters.rsi_length,
            stoch_rsi_period=parameters.rsi_length,
            expected_timeframe_minutes=1,
            allow_gaps=True,
        )
    )
    logger.info("Loaded %d candles", len(candles))

    # Create orchestrator
    direction_mode = DirectionMode[args.direction]
    orchestrator = BacktestOrchestrator(
        direction_mode=direction_mode, dry_run=args.dry_run
    )

    # Run backtest
    # TODO: Future enhancement - loop over multiple pairs and strategies:
    # for pair in args.pair:
    #     for strategy in args.strategy:
    #         result = run_strategy_on_pair(pair, strategy, candles)
    # For now, use first pair/strategy from lists
    pair = args.pair[0]
    strategy = args.strategy[0]  # Currently only trend-pullback supported
    
    run_id = f"{args.direction.lower()}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
    logger.info("Running backtest with run_id=%s, pair=%s, strategy=%s", run_id, pair, strategy)

    # Build signal parameters from strategy config
    signal_params = {
        "ema_fast": parameters.ema_fast,
        "ema_slow": parameters.ema_slow,
        "atr_stop_mult": parameters.atr_stop_mult,
        "target_r_mult": parameters.target_r_mult,
        "cooldown_candles": parameters.cooldown_candles,
        "rsi_length": parameters.rsi_length,
    }

    result = orchestrator.run_backtest(
        candles=candles,
        pair=pair,
        run_id=run_id,
        **signal_params,
    )

    logger.info("Backtest complete: %s", result.run_id)

    # Format output
    output_format = (
        OutputFormat.JSON if args.output_format == "json" else OutputFormat.TEXT
    )

    if output_format == OutputFormat.JSON:
        output_content = format_json_output(result)
    else:
        output_content = format_text_output(result)

    # Generate output filename
    output_filename = generate_output_filename(
        direction=direction_mode,
        output_format=output_format,
        timestamp=result.start_time,
    )
    output_path = args.output / output_filename

    # Write output file
    output_path.write_text(output_content)
    logger.info("Results written to %s", output_path)

    # Print summary to console
    if output_format == OutputFormat.TEXT:
        print(output_content)
    else:
        print(f"Results saved to: {output_path}")
        print(f"Direction: {result.direction_mode}")
        print(f"Total candles: {result.total_candles}")
        if result.metrics and hasattr(result.metrics, "combined"):
            metrics = result.metrics.combined
            print(f"Trades: {metrics.trade_count}")
            print(f"Win rate: {metrics.win_rate:.2%}")
        elif result.metrics:
            print(f"Trades: {result.metrics.trade_count}")
            print(f"Win rate: {result.metrics.win_rate:.2%}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
