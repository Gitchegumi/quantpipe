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
    python -m src.cli.run_backtest --direction LONG --data <csv_path> \
        --strategy trend-pullback --pair EURUSD

    # Multiple pairs (future support)
    python -m src.cli.run_backtest --direction LONG --data <csv_path> \
        --pair EURUSD GBPUSD USDJPY

    # JSON output
    python -m src.cli.run_backtest --direction LONG --data <csv_path> \
        --output-format json

    # Dry-run (signals only)
    python -m src.cli.run_backtest --direction LONG --data <csv_path> --dry-run
"""

import io
import argparse
import json
import logging
import math
import sys
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ..backtest.metrics import MetricsSummary
from ..backtest.orchestrator import BacktestOrchestrator
from ..cli.logging_setup import setup_logging
from ..config.parameters import StrategyParameters
from ..data_io.formatters import (
    format_json_output,
    format_text_output,
    generate_output_filename,
)
from ..data_io.ingestion import ingest_ohlcv_data  # pylint: disable=no-name-in-module
from ..models.core import BacktestRun
from ..models.enums import DirectionMode, OutputFormat


logger = logging.getLogger(__name__)

# Default account balance for multi-symbol concurrent PnL calculation (FR-003)
DEFAULT_ACCOUNT_BALANCE: float = 2500.0


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

    parser.add_argument(
        "--use-polars-backend",
        action="store_true",
        help="Use Polars backend for data processing.",
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
            base_path = Path("price_data") / "processed" / pair_lower / args.dataset
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

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Initialize profiler if profiling enabled
    profiler = None
    if args.profile:
        from ..backtest.profiling import ProfilingContext

        profiler = ProfilingContext()

    # Use data path directly
    data_path = Path(args.data)
    converted_csv = data_path
    use_arrow = data_path.suffix.lower() == ".parquet"

    logger.info("Using data file: %s", converted_csv)

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

        # Stage 1: Core ingestion (OHLCV only) - Force Polars for vectorized path
        logger.info("Stage 1/2: Loading OHLCV data...")
        try:
            ingestion_result = ingest_ohlcv_data(
                path=converted_csv,
                timeframe_minutes=1,
                mode="columnar",
                downcast=False,
                use_arrow=use_arrow,
                strict_cadence=False,  # FX data has gaps (weekends/holidays)
                fill_gaps=False,  # Preserve gaps - don't create synthetic price data
                return_polars=True,  # Always use Polars for vectorized path
            )
        except (FileNotFoundError, ValueError, RuntimeError) as e:
            logger.error("Error during data ingestion: %s", e, exc_info=True)
            sys.exit(1)
        logger.info(
            "✓ Ingested %d rows in %.2fs",
            len(ingestion_result.data),
            ingestion_result.metrics.runtime_seconds,
        )

        # Stage 2: Vectorized indicator calculation
        logger.info("Stage 2/2: Computing technical indicators (vectorized)...")
        from ..indicators.dispatcher import calculate_indicators

        import polars as pl

        enriched_df = ingestion_result.data
        if isinstance(enriched_df, pd.DataFrame):
            enriched_df = pl.from_pandas(enriched_df)

        # Renaming 'timestamp' to 'timestamp_utc' if needed
        if "timestamp" in enriched_df.columns:
            enriched_df = enriched_df.rename({"timestamp": "timestamp_utc"})

        # Calculate indicators dynamically based on strategy requirements
        enriched_df = calculate_indicators(enriched_df, required_indicators)

        logger.info("✓ Computed indicators: %s", required_indicators)

        # Create orchestrator early to check for optimized path
        direction_mode = DirectionMode[args.direction]
        use_optimized_path = True  # Always use vectorized path as per refactor

        # Set default benchmark output path if profiling enabled
        benchmark_path = args.benchmark_out
        if args.profile and not benchmark_path:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            benchmark_path = Path("results/benchmarks") / f"benchmark_{timestamp}.json"

        show_progress = sys.stdout.isatty()

        orchestrator = BacktestOrchestrator(
            direction_mode=direction_mode,
            dry_run=args.dry_run,
            enable_profiling=args.profile,
            enable_progress=show_progress,
        )

        # Attach profiler to orchestrator if profiling enabled
        if profiler:
            orchestrator.profiler = profiler

        # Single-symbol mode uses vectorized path
        pair = args.pair[0]
        strategy_name = args.strategy[0]  # Currently only trend-pullback supported

        run_id = (
            f"{args.direction.lower()}_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )
        logger.info(
            "Running backtest with run_id=%s, pair=%s, strategy=%s",
            run_id,
            pair,
            strategy_name,
        )

        # Build signal parameters from strategy config
        # Build signal parameters from strategy config
        signal_params = parameters.model_dump()

        # Call vectorized backtest with Polars DataFrame
        logger.info("Using vectorized backtest path (Polars)")

        from ..strategy.trend_pullback.strategy import TREND_PULLBACK_STRATEGY

        result = orchestrator.run_backtest(
            candles=enriched_df,
            pair=pair,
            run_id=run_id,
            strategy=TREND_PULLBACK_STRATEGY,
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
            dataset_rows = len(enriched_df)
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
    is_multi_symbol_result = result.is_multi_symbol

    if is_multi_symbol_result:
        # Multi-symbol formatting (T025)
        from ..data_io.formatters import (
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
            created_at=datetime.now(timezone.utc),
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
    # Force UTF-8 encoding for stdout and stderr (only when run as script)
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    sys.exit(main())
