#!/usr/bin/env python3
# pylint: disable=too-many-lines
# ^ This is the main CLI orchestrator - refactoring to smaller modules
#   would reduce cohesion. Acceptable for a CLI entry point.
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
import json
import logging
import math
import sys
from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from ..backtest.metrics import MetricsSummary
from ..backtest.orchestrator import BacktestOrchestrator
from ..cli.logging_setup import setup_logging
from ..config.parameters import StrategyParameters
from ..io.formatters import (
    format_json_output,
    format_text_output,
    generate_output_filename,
)
from ..io.ingestion import ingest_ohlcv_data  # pylint: disable=no-name-in-module
from ..models.core import BacktestRun
from ..models.enums import DirectionMode, OutputFormat


logger = logging.getLogger(__name__)


def format_backtest_results_as_json(
    run_metadata: BacktestRun, metrics: MetricsSummary
) -> str:
    """
    Format backtest run metadata and metrics as JSON.

    Args:
        run_metadata: BacktestRun object with run information.
        metrics: MetricsSummary object with backtest metrics.

    Returns:
        JSON string with formatted results.
    """

    def _serialize_value(value):
        """Convert NaN/Inf to None for JSON serialization."""
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return value

    data = {
        "run_metadata": {
            "run_id": run_metadata.run_id,
            "parameters_hash": run_metadata.parameters_hash,
            "manifest_ref": run_metadata.manifest_ref,
            "start_time": run_metadata.start_time.isoformat(),
            "end_time": run_metadata.end_time.isoformat(),
            "total_candles_processed": run_metadata.total_candles_processed,
            "reproducibility_hash": run_metadata.reproducibility_hash,
        },
        "metrics": {
            "trade_count": metrics.trade_count,
            "win_count": metrics.win_count,
            "loss_count": metrics.loss_count,
            "win_rate": _serialize_value(metrics.win_rate),
            "avg_win_r": _serialize_value(metrics.avg_win_r),
            "avg_loss_r": _serialize_value(metrics.avg_loss_r),
            "avg_r": _serialize_value(metrics.avg_r),
            "expectancy": _serialize_value(metrics.expectancy),
            "sharpe_estimate": _serialize_value(metrics.sharpe_estimate),
            "profit_factor": _serialize_value(metrics.profit_factor),
            "max_drawdown_r": _serialize_value(metrics.max_drawdown_r),
            "latency_p95_ms": _serialize_value(metrics.latency_p95_ms),
            "latency_mean_ms": _serialize_value(metrics.latency_mean_ms),
        },
    }

    return json.dumps(data, indent=2)


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

    # Check if file is already in correct format by reading first line
    first_line = csv_path.read_text(encoding="utf-8").split("\n")[0].lower()
    if "timestamp" in first_line:
        logger.info("File already in correct format, skipping conversion")
        return csv_path

    # Read CSV (MetaTrader format: Date,Time,Open,High,Low,Close,Volume)
    df = pd.read_csv(
        csv_path,
        header=None,
        names=["date", "time", "open", "high", "low", "close", "volume"],
        dtype=str,  # Read all as strings to avoid mixed type issues
    )

    # Combine date and time into timestamp (both are now strings)
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
        required=False,  # Not required for --list-strategies or --register-strategy
        help="Path to CSV price data file (MetaTrader format or standard format)",
    )

    parser.add_argument(
        "--strategy",
        type=str,
        nargs="+",
        default=["trend-pullback"],
        help="Strategy name(s) to run (default: trend-pullback). Supports multiple: \
            --strategy strat1 strat2",
    )

    parser.add_argument(
        "--pair",
        type=str,
        nargs="+",
        default=["EURUSD"],
        help="Currency pair(s) to backtest (default: EURUSD). Supports multiple: \
            --pair EURUSD GBPUSD. When used without --data, auto-constructs path from \
            price_data/processed/<pair>/",
    )

    parser.add_argument(
        "--dataset",
        type=str,
        choices=["test", "validate"],
        default="test",
        help="Dataset to use when --data not specified (default: test). \
            Looks for price_data/processed/<pair>/<dataset>/<pair>_<dataset>.parquet",
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

    # Performance optimization flags (Phase 4: US2)
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Enable performance profiling with cProfile hotspot extraction (US2)",
    )

    parser.add_argument(
        "--benchmark-out",
        type=Path,
        help=(
            "Path to write benchmark JSON artifact "
            "(default: results/benchmarks/<timestamp>.json)"
        ),
    )

    # Parallel execution flags (Phase 7: T059)
    parser.add_argument(
        "--max-workers",
        type=int,
        help=(
            "Maximum number of parallel workers "
            "(default: auto-detect, capped to logical cores)"
        ),
    )

    # Partial dataset iteration flags (Phase 5: US3)
    parser.add_argument(
        "--data-frac",
        type=float,
        help=(
            "Fraction of dataset to process (0.0-1.0). "
            "Prompts interactively if omitted. Default: 1.0 (US3)"
        ),
    )

    parser.add_argument(
        "--portion",
        type=int,
        help=(
            "Which portion to select when using --data-frac < 1.0 "
            "(1-based index). Example: --data-frac 0.25 --portion 2 "
            "selects second quartile (US3)"
        ),
    )

    # Multi-strategy support (Phase 4: US2)
    parser.add_argument(
        "--list-strategies",
        action="store_true",
        help="List all registered strategies and exit (no backtest run)",
    )

    parser.add_argument(
        "--register-strategy",
        type=str,
        metavar="NAME",
        help="Register a new strategy by name (requires --strategy-module)",
    )

    parser.add_argument(
        "--strategy-module",
        type=str,
        help="Python module path for strategy (e.g., src.strategy.my_strategy)",
    )

    parser.add_argument(
        "--strategy-tags",
        type=str,
        nargs="*",
        default=[],
        help="Tags for strategy registration (space-separated)",
    )

    parser.add_argument(
        "--strategy-version",
        type=str,
        help="Version string for strategy registration (e.g., 1.0.0)",
    )

    # Multi-strategy selection (Phase 5: US3)
    parser.add_argument(
        "--strategies",
        type=str,
        nargs="+",
        help="Multiple strategy names for multi-strategy run \
(e.g., --strategies alpha beta gamma)",
    )

    parser.add_argument(
        "--weights",
        type=float,
        nargs="+",
        help="Strategy weights (must match --strategies order and sum to ~1.0, e.g., \
--weights 0.5 0.3 0.2)",
    )

    parser.add_argument(
        "--aggregate",
        action="store_true",
        help="Enable aggregated portfolio metrics output \
(default: True for multi-strategy)",
    )

    parser.add_argument(
        "--no-aggregate",
        action="store_true",
        help="Disable aggregation, produce only per-strategy outputs",
    )

    # Multi-symbol execution mode flags (Phase 6: US4)
    parser.add_argument(
        "--portfolio-mode",
        type=str,
        choices=["independent", "portfolio"],
        default="independent",
        help=(
            "Multi-symbol execution mode: 'independent' (isolated per-symbol "
            "backtests) or 'portfolio' (unified portfolio with shared capital, "
            "correlation tracking, and portfolio metrics). Default: independent (US4)"
        ),
    )

    parser.add_argument(
        "--disable-symbol",
        type=str,
        nargs="*",
        default=[],
        help=(
            "Symbol(s) to exclude from multi-symbol run "
            "(e.g., --disable-symbol GBPUSD USDJPY). Applies to both independent "
            "and portfolio modes (US4)"
        ),
    )

    parser.add_argument(
        "--correlation-threshold",
        type=float,
        help=(
            "Override default correlation threshold for portfolio mode "
            "(0.0-1.0). Controls correlation-based position sizing adjustments. "
            "Only applies when --portfolio-mode=portfolio (US4)"
        ),
    )

    parser.add_argument(
        "--snapshot-interval",
        type=int,
        help=(
            "Snapshot recording interval in bars for portfolio mode. "
            "Records portfolio state (allocations, correlations, diversification) "
            "every N bars. Only applies when --portfolio-mode=portfolio (US4)"
        ),
    )

    parser.add_argument(
        "--emit-perf-report",
        action="store_true",
        help=(
            "Emit PerformanceReport JSON after backtest completion. "
            "Captures scan/simulation timings, memory usage, signal/trade counts, "
            "and dataset provenance for benchmark tracking (Feature 010: T077)"
        ),
    )

    args = parser.parse_args()

    # Setup logging early for --list-strategies and --register-strategy
    setup_logging(level=args.log_level)

    # Handle --list-strategies (FR-017: List strategies without running backtest)
    if args.list_strategies:
        from ..strategy.registry import StrategyRegistry

        registry = StrategyRegistry()
        # Note: Persistent storage not yet implemented
        strategies = registry.list()

        if not strategies:
            print("No strategies registered.")
            print("\nUse --register-strategy to add a new strategy.")
        else:
            print(f"Registered Strategies ({len(strategies)}):")
            print("-" * 60)
            for strat in strategies:
                tags_str = ", ".join(strat.tags) if strat.tags else "none"
                version_str = strat.version or "unversioned"
                print(f"  {strat.name}")
                print(f"    Tags: {tags_str}")
                print(f"    Version: {version_str}")
                print()
        return 0

    # Handle --register-strategy (FR-001: Strategy registration)
    if args.register_strategy:
        if not args.strategy_module:
            print("Error: --strategy-module required for registration", file=sys.stderr)
            sys.exit(1)

        import importlib

        from ..strategy.registry import StrategyRegistry

        registry = StrategyRegistry()

        try:
            # Import strategy module
            module = importlib.import_module(args.strategy_module)

            # Look for strategy callable (convention: 'run' or 'execute')
            if hasattr(module, "run"):
                func = module.run
            elif hasattr(module, "execute"):
                func = module.execute
            else:
                print(
                    f"Error: Module '{args.strategy_module}' \
must expose 'run' or 'execute' function",
                    file=sys.stderr,
                )
                sys.exit(1)

            # Register strategy
            registry.register(
                name=args.register_strategy,
                func=func,
                tags=args.strategy_tags,
                version=args.strategy_version,
            )

            print(f"Successfully registered strategy: {args.register_strategy}")
            print(f"  Module: {args.strategy_module}")
            tags_str = ", ".join(args.strategy_tags) if args.strategy_tags else "none"
            print(f"  Tags: {tags_str}")
            print(f"  Version: {args.strategy_version or 'unversioned'}")
            print(
                "\nNote: Registration is in-memory only. \
Persistent storage not yet implemented."
            )

            return 0

        except ImportError as exc:
            print(
                f"Error: Failed to import module '{args.strategy_module}': {exc}",
                file=sys.stderr,
            )
            sys.exit(1)
        except ValueError as exc:
            print(f"Error: Registration failed: {exc}", file=sys.stderr)
            sys.exit(1)

    # Validate data file exists
    # (required for backtest runs, not for listing/registration)
    if args.data is None:
        # Data file required for backtest runs
        if not args.list_strategies and not args.register_strategy:
            # Auto-construct data path from pair and dataset
            # Try .parquet first, fallback to .csv
            pair_lower = args.pair[0].lower()
            base_path = (
                Path("price_data")
                / "processed"
                / pair_lower
                / args.dataset
            )
            filename_base = f"{pair_lower}_{args.dataset}"

            # Try .parquet first (faster)
            parquet_path = base_path / f"{filename_base}.parquet"
            csv_path = base_path / f"{filename_base}.csv"

            if parquet_path.exists():
                data_path = parquet_path
                logger.info(
                    "Auto-constructed data path from --pair %s and --dataset %s: %s",
                    args.pair[0],
                    args.dataset,
                    data_path,
                )
            elif csv_path.exists():
                data_path = csv_path
                logger.info(
                    "Auto-constructed data path from --pair %s and --dataset %s: %s "
                    "(Parquet not found, using CSV)",
                    args.pair[0],
                    args.dataset,
                    data_path,
                )
            else:
                print(
                    f"Error: No data file found for --pair {args.pair[0]} "
                    f"and --dataset {args.dataset}\n"
                    f"Searched:\n"
                    f"  - {parquet_path}\n"
                    f"  - {csv_path}\n"
                    f"Expected structure: price_data/processed/<pair>/<dataset>/"
                    f"<pair>_<dataset>.[parquet|csv]\n"
                    f"Use --data to specify a custom path.",
                    file=sys.stderr,
                )
                sys.exit(1)
            args.data = data_path
    elif not args.data.exists():
        print(f"Error: Data file not found: {args.data}", file=sys.stderr)
        sys.exit(1)

    logger.info("Starting directional backtest")
    logger.info("Direction: %s", args.direction)
    logger.info("Strategy: %s", ", ".join(args.strategy))
    # Optional pair inference if user did not explicitly override default
    # and data path suggests a different pair
    inferred_pair = None
    try:
        # Examine parts of path for 6-letter currency code (e.g., usdjpy)
        # reverse for specificity (file/parent dirs first)
        for part in args.data.parts[::-1]:
            part_lower = part.lower()
            if len(part_lower) == 6 and part_lower.isalpha():
                inferred_pair = part_lower.upper()
                break
        if (
            inferred_pair
            and len(args.pair) == 1
            and args.pair[0].upper() != inferred_pair
        ):
            logger.info(
                "Inferred pair '%s' from data path (overriding '%s'). "
                "Pass --pair to force a different symbol.",
                inferred_pair,
                args.pair[0].upper(),
            )
            args.pair[0] = inferred_pair  # mutate for subsequent usage
    except (AttributeError, IndexError, ValueError) as ex:
        logger.warning("Pair inference failed: %s", ex)

    logger.info("Pair(s): %s", ", ".join(args.pair))
    logger.info("Data: %s", args.data)
    logger.info("Dry-run: %s", args.dry_run)

    # Validate Phase 6 (US4) multi-symbol flags
    if args.correlation_threshold is not None:
        if not 0.0 <= args.correlation_threshold <= 1.0:
            print(
                "Error: --correlation-threshold must be between 0.0 and 1.0. "
                f"Got: {args.correlation_threshold}",
                file=sys.stderr,
            )
            sys.exit(1)
        if args.portfolio_mode != "portfolio":
            logger.warning(
                "--correlation-threshold only applies to portfolio mode, but "
                "--portfolio-mode=%s specified. Ignoring threshold.",
                args.portfolio_mode,
            )

    if args.snapshot_interval is not None:
        if args.snapshot_interval <= 0:
            print(
                "Error: --snapshot-interval must be positive. "
                f"Got: {args.snapshot_interval}",
                file=sys.stderr,
            )
            sys.exit(1)
        if args.portfolio_mode != "portfolio":
            logger.warning(
                "--snapshot-interval only applies to portfolio mode, but "
                "--portfolio-mode=%s specified. Ignoring interval.",
                args.portfolio_mode,
            )

    # Log portfolio mode settings
    if len(args.pair) > 1:
        logger.info("Portfolio mode: %s", args.portfolio_mode)
        if args.disable_symbol:
            logger.info("Disabled symbols: %s", ", ".join(args.disable_symbol))
        if (
            args.correlation_threshold is not None
            and args.portfolio_mode == "portfolio"
        ):
            logger.info(
                "Correlation threshold override: %.2f", args.correlation_threshold
            )
        if args.snapshot_interval is not None and args.portfolio_mode == "portfolio":
            logger.info("Snapshot interval: %d bars", args.snapshot_interval)

    # Fraction and portion validation/prompting (Phase 5: US3, FR-002, FR-012, FR-015)
    data_frac = args.data_frac
    portion = args.portion

    # Interactive prompt if --data-frac not provided
    if data_frac is None:
        prompt_attempt = 0
        max_attempts = 2
        while prompt_attempt < max_attempts:
            try:
                user_input = input(
                    "Enter dataset fraction to process "
                    "(0.0-1.0, press Enter for 1.0): "
                ).strip()
                if not user_input:
                    data_frac = 1.0
                    logger.info("Using default fraction: 1.0 (full dataset)")
                    break
                data_frac = float(user_input)
                if data_frac <= 0 or data_frac > 1.0:
                    print(
                        f"Invalid fraction: {data_frac}. "
                        "Must be between 0.0 (exclusive) and 1.0 (inclusive)."
                    )
                    prompt_attempt += 1
                    continue
                break
            except ValueError:
                print(
                    f"Invalid input: '{user_input}'. " "Please enter a numeric value."
                )
                prompt_attempt += 1

        if prompt_attempt >= max_attempts:
            print(
                f"Error: Failed to get valid fraction after "
                f"{max_attempts} attempts. Aborting.",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        # Validate command-line fraction
        if data_frac <= 0 or data_frac > 1.0:
            print(
                f"Error: --data-frac must be between 0.0 (exclusive) and "
                f"1.0 (inclusive). Got: {data_frac}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Portion validation and interactive prompt (if fraction < 1.0)
    if data_frac < 1.0 and portion is None:
        # Calculate max portions
        max_portions = int(1.0 / data_frac)
        try:
            user_input = input(
                f"Enter portion index (1-{max_portions}, press Enter for 1): "
            ).strip()
            if not user_input:
                portion = 1
                logger.info("Using default portion: 1 (first portion)")
            else:
                portion = int(user_input)
                if portion < 1 or portion > max_portions:
                    print(
                        f"Error: Portion must be between 1 and "
                        f"{max_portions}. Got: {portion}",
                        file=sys.stderr,
                    )
                    sys.exit(1)
        except ValueError:
            print(
                f"Error: Invalid portion input '{user_input}'. " "Must be an integer.",
                file=sys.stderr,
            )
            sys.exit(1)
    elif data_frac < 1.0 and portion is not None:
        # Validate command-line portion
        max_portions = int(1.0 / data_frac)
        if portion < 1 or portion > max_portions:
            print(
                f"Error: --portion must be between 1 and {max_portions} "
                f"for fraction {data_frac}. Got: {portion}",
                file=sys.stderr,
            )
            sys.exit(1)
    elif data_frac == 1.0:
        portion = 1  # Full dataset, single portion

    logger.info("Dataset fraction: %.2f", data_frac)
    if data_frac < 1.0:
        logger.info("Portion selected: %d", portion)

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Initialize profiler if profiling enabled
    profiler = None
    if args.profile:
        from ..backtest.profiling import ProfilingContext

        profiler = ProfilingContext()

    # Detect file type and preprocess if needed
    data_path = Path(args.data)

    if data_path.suffix.lower() == ".parquet":
        logger.info("Detected Parquet file, skipping CSV preprocessing")
        converted_csv = data_path
        use_arrow = True  # Force Arrow backend for Parquet
    elif data_path.suffix.lower() == ".csv":
        logger.info("Preprocessing CSV data")
        converted_csv = preprocess_metatrader_csv(args.data, args.output)
        use_arrow = False  # Use standard backend for CSV
    else:
        logger.warning(
            "Unknown file extension '%s', attempting to process as CSV",
            data_path.suffix
        )
        converted_csv = preprocess_metatrader_csv(args.data, args.output)
        use_arrow = False

    # Load strategy parameters (using defaults)
    parameters = StrategyParameters()
    logger.info(
        "Using strategy parameters: EMA(%d/%d), ATR mult: %.1f",
        parameters.ema_fast,
        parameters.ema_slow,
        parameters.atr_stop_mult,
    )

    # Execute backtest with optional profiling context
    profiling_ctx = profiler if profiler else nullcontext()
    with profiling_ctx:
        # Ingest candles with phase timing
        if profiler:
            profiler.start_phase("ingest")

        # Load strategy to get required indicators
        from ..strategy.trend_pullback.strategy import TREND_PULLBACK_STRATEGY

        strategy = TREND_PULLBACK_STRATEGY
        required_indicators = strategy.metadata.required_indicators

        logger.info(
            "Strategy: %s v%s",
            strategy.metadata.name,
            strategy.metadata.version,
        )
        logger.info("Required indicators: %s", required_indicators)

        logger.info("Ingesting candles from %s", converted_csv)

        # Stage 1: Core ingestion (OHLCV only)
        logger.info("Stage 1/3: Loading OHLCV data from CSV...")
        ingestion_result = ingest_ohlcv_data(
            path=converted_csv,
            timeframe_minutes=1,
            mode="columnar",
            downcast=False,
            use_arrow=use_arrow,
            strict_cadence=False,  # FX data has gaps (weekends/holidays)
            fill_gaps=False,  # Preserve gaps - don't create synthetic price data
        )
        logger.info(
            "✓ Ingested %d rows in %.2fs",
            len(ingestion_result.data),
            ingestion_result.metrics.runtime_seconds,
        )

        # Stage 2: Indicator enrichment
        logger.info("Stage 2/3: Computing technical indicators...")
        from ..indicators.enrich import enrich

        enrichment_result = enrich(
            core_ref=ingestion_result,
            indicators=required_indicators,
            strict=True,
        )
        logger.info(
            "✓ Applied %d indicators in %.2fs",
            len(enrichment_result.indicators_applied),
            enrichment_result.runtime_seconds,
        )

        # Store enriched DataFrame for potential optimized path use
        enriched_df = enrichment_result.enriched

        # Create orchestrator early to check for optimized path
        direction_mode = DirectionMode[args.direction]

        # Set default benchmark output path if profiling enabled
        benchmark_path = args.benchmark_out
        if args.profile and not benchmark_path:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            benchmark_path = Path("results/benchmarks") / f"benchmark_{timestamp}.json"

        orchestrator = BacktestOrchestrator(
            direction_mode=direction_mode,
            dry_run=args.dry_run,
            enable_profiling=args.profile,
        )

        # Attach profiler to orchestrator if profiling enabled
        if profiler:
            orchestrator.profiler = profiler

        # Check if optimized path is available (Feature 010)
        use_optimized_path = hasattr(orchestrator, "run_optimized_backtest")

        # Stage 3: Convert DataFrame to Candle objects (only for legacy path)
        if use_optimized_path:
            logger.info(
                "Stage 3/3: Skipping Candle conversion - using optimized DataFrame path"
            )
            candles = None  # Not needed for optimized path
        else:
            logger.info("Stage 3/3: Converting to Candle objects...")
            from ..models.core import Candle

            # Vectorized conversion using list comprehension with to_dict
            # Much faster than iterrows() for large datasets
            records = enriched_df.to_dict("records")

            candles = []
            for record in records:
                # Build indicators dict from indicator columns
                indicators_dict = {
                    name: record[name]
                    for name in required_indicators
                    if name in record
                }

                candles.append(
                    Candle(
                        timestamp_utc=record["timestamp_utc"],
                        open=record["open"],
                        high=record["high"],
                        low=record["low"],
                        close=record["close"],
                        volume=record.get("volume", 0.0),
                        indicators=indicators_dict,
                        is_gap=record.get("is_gap", False),
                    )
                )

            logger.info("✓ Created %d Candle objects", len(candles))

        if profiler:
            profiler.end_phase("ingest")
            profiler.end_phase("ingest")

        # Slice dataset if fraction < 1.0 (Phase 5: US3, FR-002, SC-003)
        if data_frac < 1.0:
            total_rows = len(enriched_df)
            logger.info(
                "Slicing dataset: fraction=%.2f, portion=%d, total_rows=%d",
                data_frac,
                portion,
                total_rows,
            )

            # Slice DataFrame for optimized path
            slice_count = int(total_rows * data_frac)
            enriched_df = enriched_df.iloc[:slice_count]

            # Also slice candles if legacy path
            if not use_optimized_path:
                from ..backtest.chunking import slice_dataset

                candles = slice_dataset(candles, fraction=data_frac, portion=portion)

            logger.info(
                "Sliced to %d rows (%.1f%%)",
                len(enriched_df),
                100 * len(enriched_df) / total_rows,
            )

        # Check if multi-symbol mode should be used
        is_multi_symbol = len(args.pair) > 1

        if is_multi_symbol:
            # Multi-symbol mode (Phase 4: US2, T020-T021 + Phase 6: US4, T041-T044)
            from ..backtest.portfolio.independent_runner import IndependentRunner
            from ..backtest.portfolio.validation import validate_symbol_list
            from ..models.portfolio import CurrencyPair, PortfolioConfig

            logger.info(
                "Multi-symbol mode: %d pairs requested, mode=%s",
                len(args.pair),
                args.portfolio_mode,
            )

            # Create CurrencyPair objects
            requested_pairs = [CurrencyPair(code=p.upper()) for p in args.pair]

            # Apply --disable-symbol filtering (Phase 6: US4, T042)
            if args.disable_symbol:
                disabled_codes = {code.upper() for code in args.disable_symbol}
                before_count = len(requested_pairs)
                requested_pairs = [
                    pair for pair in requested_pairs if pair.code not in disabled_codes
                ]
                after_count = len(requested_pairs)
                if after_count < before_count:
                    logger.info(
                        "Filtered out %d disabled symbol(s): %s",
                        before_count - after_count,
                        ", ".join(disabled_codes),
                    )

            if not requested_pairs:
                logger.error(
                    "No symbols remaining after --disable-symbol filter. Aborting."
                )
                sys.exit(1)

            # Validate symbols and skip missing ones with warnings (T021)
            data_dir = Path("price_data/processed")
            valid_pairs, errors = validate_symbol_list(requested_pairs, data_dir)

            if errors:
                logger.warning(
                    "Symbol validation found %d error(s), skipping invalid symbols:",
                    len(errors),
                )
                for error in errors:
                    logger.warning("  - %s", error)

            if not valid_pairs:
                logger.error("No valid symbols found. Aborting multi-symbol run.")
                sys.exit(1)

            logger.info(
                "Proceeding with %d valid symbol(s): %s",
                len(valid_pairs),
                ", ".join([p.code for p in valid_pairs]),
            )

            # Generate run ID
            run_id = (
                f"multi_{args.portfolio_mode}_{args.direction.lower()}_"
                f"{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
            )

            # Route to appropriate runner based on portfolio mode
            # (Phase 6: US4, T041)
            if args.portfolio_mode == "portfolio":
                # Portfolio mode: shared capital, correlation tracking
                # (T041, T043, T044)
                from ..backtest.portfolio.orchestrator import (
                    PortfolioOrchestrator,
                )

                logger.info(
                    "Running portfolio multi-symbol backtest with run_id=%s",
                    run_id,
                )

                # Create portfolio configuration
                portfolio_config = PortfolioConfig(
                    correlation_threshold=(
                        args.correlation_threshold
                        if args.correlation_threshold is not None
                        else 0.7  # Default from spec FR-010
                    ),
                    per_pair_thresholds={},  # No per-pair overrides from CLI yet
                )

                # Create portfolio orchestrator
                # pylint: disable=fixme
                portfolio_orch = PortfolioOrchestrator(
                    symbols=valid_pairs,
                    portfolio_config=portfolio_config,
                    initial_capital=10000.0,  # TODO: Make configurable
                    data_dir=data_dir,
                )

                # Run portfolio backtest
                # Note: PortfolioOrchestrator.run() raises NotImplementedError
                # This is expected for Phase 6 (primitives complete,
                # full execution pending)
                try:
                    # pylint: disable=assignment-from-no-return
                    results = portfolio_orch.run(
                        strategy_params=parameters,
                        mode=direction_mode,
                        output_dir=args.output,
                        snapshot_interval=args.snapshot_interval,
                    )
                    # Create result object for output formatting
                    result = type(
                        "PortfolioResult",
                        (),
                        {
                            "run_id": run_id,
                            "direction_mode": direction_mode,
                            "start_time": datetime.now(UTC),
                            "total_candles": 0,
                            "symbols": [p.code for p in valid_pairs],
                            "results": results,
                            "failures": portfolio_orch.get_failures(),
                            "metrics": None,
                            "is_multi_symbol": True,
                            "is_portfolio_mode": True,
                        },
                    )()
                except NotImplementedError as exc:
                    logger.error(
                        "Portfolio mode full execution not yet implemented: %s",
                        exc,
                    )
                    logger.info(
                        "Portfolio primitives (correlation, allocation, "
                        "snapshots) are complete. Full orchestration pending "
                        "future phase."
                    )
                    sys.exit(1)

            else:
                # Independent mode: isolated per-symbol execution (T041)
                runner = IndependentRunner(
                    symbols=valid_pairs,
                    data_dir=data_dir,
                )

                logger.info(
                    "Running independent multi-symbol backtest with run_id=%s",
                    run_id,
                )

                results = runner.run(
                    strategy_params=parameters,
                    mode=direction_mode,
                    output_dir=args.output,
                )

                # Create result object for output formatting
                result = type(
                    "MultiSymbolResult",
                    (),
                    {
                        "run_id": run_id,
                        "direction_mode": direction_mode,
                        "start_time": datetime.now(UTC),
                        "total_candles": 0,  # Sum from individual results
                        "symbols": [p.code for p in valid_pairs],
                        "results": results,
                        "failures": runner.get_failures(),
                        "metrics": None,  # No single metrics for multi-symbol
                        "is_multi_symbol": True,
                        "is_portfolio_mode": False,
                    },
                )()

                logger.info(
                    "Multi-symbol backtest complete: %d successful, %d failed",
                    len(results),
                    len(runner.get_failures()),
                )

        else:
            # Single-symbol mode (backward compatibility)
            # Future: multi-strategy support will loop over args.strategy
            # For now, use first strategy from list
            pair = args.pair[0]
            strategy = args.strategy[0]  # Currently only trend-pullback supported

            run_id = (
                f"{args.direction.lower()}_"
                f"{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
            )
            logger.info(
                "Running backtest with run_id=%s, pair=%s, strategy=%s",
                run_id,
                pair,
                strategy,
            )

            # Build signal parameters from strategy config
            signal_params = {
                "ema_fast": parameters.ema_fast,
                "ema_slow": parameters.ema_slow,
                "atr_stop_mult": parameters.atr_stop_mult,
                "target_r_mult": parameters.target_r_mult,
                "cooldown_candles": parameters.cooldown_candles,
                "rsi_length": parameters.rsi_length,
                "risk_per_trade_pct": parameters.risk_per_trade_pct,
            }

            # Feature 010: Use optimized path if available (BatchScan/BatchSimulation)
            if use_optimized_path:
                logger.info(
                    "Using optimized vectorized backtest path "
                    "(Feature 010: BatchScan/BatchSimulation)"
                )

                from ..strategy.trend_pullback.strategy import TREND_PULLBACK_STRATEGY

                result = orchestrator.run_optimized_backtest(
                    df=enriched_df,
                    pair=pair,
                    run_id=run_id,
                    strategy=TREND_PULLBACK_STRATEGY,
                    **signal_params,
                )

                logger.info("Optimized backtest complete: %s", result.run_id)
            else:
                # Fallback to legacy Candle-based path
                logger.info("Using legacy Candle-based backtest path")

                result = orchestrator.run_backtest(
                    candles=candles,
                    pair=pair,
                    run_id=run_id,
                    **signal_params,
                )

                logger.info("Backtest complete: %s", result.run_id)

        # Write benchmark artifact if profiling enabled
        if args.profile and benchmark_path:
            import tracemalloc

            from ..backtest.profiling import write_benchmark_record

            # Get phase times from orchestrator if available
            phase_times = {}
            hotspots = []
            if profiler:
                phase_times = profiler.get_phase_times()
                hotspots = profiler.get_hotspots(n=10)  # SC-008: ≥10 hotspots

            # Calculate metrics
            dataset_rows = len(candles)
            trades_simulated = 0
            if result.metrics:
                if hasattr(result.metrics, "combined"):
                    trades_simulated = result.metrics.combined.trade_count
                elif hasattr(result.metrics, "trade_count"):
                    trades_simulated = result.metrics.trade_count

            wall_clock_total = sum(phase_times.values()) if phase_times else 0.0

            # Memory metrics (approximate if tracemalloc not used)
            memory_peak_mb = 0.0
            memory_ratio = 1.0
            if tracemalloc.is_tracing():
                _, peak = tracemalloc.get_traced_memory()
                memory_peak_mb = peak / (1024 * 1024)
                # Estimate raw dataset size (rough approximation)
                raw_bytes = (
                    dataset_rows * 8 * 6
                )  # 8 bytes per float, 6 columns (OHLC+V+T)
                memory_ratio = peak / raw_bytes if raw_bytes > 0 else 1.0

            # Create benchmark directory
            benchmark_path.parent.mkdir(parents=True, exist_ok=True)

            write_benchmark_record(
                output_path=benchmark_path,
                dataset_rows=dataset_rows,
                trades_simulated=trades_simulated,
                phase_times=phase_times,
                wall_clock_total=wall_clock_total,
                memory_peak_mb=memory_peak_mb,
                memory_ratio=memory_ratio,
                hotspots=hotspots,  # Include cProfile hotspots
                fraction=data_frac,  # Phase 5: US3, FR-002
            )
            logger.info("Benchmark artifact written to %s", benchmark_path)

    # TODO(T045): Generate PerformanceReport after backtest completes
    # NOTE: Currently orchestrator doesn't expose ScanResult/SimulationResult
    # Full integration requires orchestrator refactoring to return:
    # - ScanResult: scan timing, candle count, signal count, progress overhead
    # - SimulationResult: simulation timing, trade count, memory stats
    # Once available, uncomment:
    # from ..backtest.report import create_report
    # perf_report = create_report(
    #     scan_result=scan_result,
    #     sim_result=sim_result,
    #     candle_count=len(candles),
    #     equivalence_verified=True,
    #     indicator_names=["ema_fast", "ema_slow", "atr", "rsi"],
    #     duplicate_timestamps=0,
    # )
    # report_writer = ReportWriter(output_dir=args.output)
    # report_path = report_writer.write_report(perf_report)
    # logger.info("Performance report written to %s", report_path)

    # Format output (outside profiling context)
    output_format = (
        OutputFormat.JSON if args.output_format == "json" else OutputFormat.TEXT
    )

    # Check if this is a multi-symbol result
    is_multi_symbol_result = (
        hasattr(result, "is_multi_symbol") and result.is_multi_symbol
    )

    if is_multi_symbol_result:
        # Multi-symbol formatting (T025)
        from ..io.formatters import (
            format_multi_symbol_json_output,
            format_multi_symbol_text_output,
        )

        if output_format == OutputFormat.JSON:
            output_content = format_multi_symbol_json_output(result)
        else:
            output_content = format_multi_symbol_text_output(result)
    else:
        # Single-symbol formatting
        if output_format == OutputFormat.JSON:
            output_content = format_json_output(result)
        else:
            output_content = format_text_output(result)

    # Generate output filename
    # Derive symbol tag for filename (FR-023)
    # Future multi-symbol logic will set 'multi'
    symbol_tag = None
    if hasattr(result, "pair") and result.pair:
        symbol_tag = result.pair.lower()
    if hasattr(result, "symbols") and result.symbols and len(result.symbols) > 1:
        symbol_tag = "multi"

    output_filename = generate_output_filename(
        direction=direction_mode,
        output_format=output_format,
        timestamp=result.start_time,
        symbol_tag=symbol_tag,
    )
    output_path = args.output / output_filename

    # Write output file
    output_path.write_text(output_content)
    logger.info("Results written to %s", output_path)

    # Emit PerformanceReport if requested (Feature 010: T077)
    if args.emit_perf_report and use_optimized_path:
        logger.info("Emitting PerformanceReport for optimized backtest")
        from ..backtest.report_writer import ReportWriter
        from ..models.performance_report import PerformanceReport

        # Extract metrics from result
        scan_duration = 0.0
        simulation_duration = 0.0
        signal_count = len(result.signals) if result.signals else 0
        trade_count = len(result.executions) if result.executions else 0

        # Try to extract timing from orchestrator phases if available
        if hasattr(orchestrator, "_phase_times"):
            scan_duration = orchestrator._phase_times.get("scan", 0.0)
            simulation_duration = orchestrator._phase_times.get("simulation", 0.0)

        # Create PerformanceReport
        # Note: Some fields use placeholder values pending full instrumentation
        perf_report = PerformanceReport(
            scan_duration_sec=scan_duration,
            simulation_duration_sec=simulation_duration,
            peak_memory_mb=0.0,  # TODO: Add memory tracking
            manifest_path="",  # TODO: Add manifest tracking
            manifest_sha256="0" * 64,  # Placeholder
            candle_count=result.total_candles,
            signal_count=signal_count,
            trade_count=trade_count,
            equivalence_verified=False,  # Not applicable for optimized-only run
            progress_emission_count=0,  # TODO: Track from progress dispatcher
            progress_overhead_pct=None,
            indicator_names=[],  # TODO: Extract from strategy metadata
            deterministic_mode=False,
            allocation_count_scan=None,
            allocation_reduction_pct=None,
            duplicate_timestamps_removed=0,
            duplicate_first_ts=None,
            duplicate_last_ts=None,
            created_at=datetime.now(UTC),
        )

        # Write report to JSON
        writer = ReportWriter(output_dir=str(args.output))
        report_path = writer.write_report(perf_report)
        logger.info("PerformanceReport written to %s", report_path)
        print(f"Performance report: {report_path}")
    elif args.emit_perf_report and not use_optimized_path:
        logger.warning(
            "PerformanceReport emission requested but optimized path not used. "
            "Skipping report emission."
        )

    # Print summary to console
    if output_format == OutputFormat.TEXT:
        print(output_content)
    else:
        print(f"Results saved to: {output_path}")
        if is_multi_symbol_result:
            # Multi-symbol summary
            print(f"Direction: {result.direction_mode}")
            print(f"Symbols: {', '.join(result.symbols)}")
            print(f"Successful: {len(result.results)}")
            print(f"Failed: {len(result.failures)}")
        else:
            # Single-symbol summary
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
