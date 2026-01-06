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
import logging
import sys
from contextlib import nullcontext
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import polars as pl

from ..backtest.orchestrator import BacktestOrchestrator
from ..backtest.portfolio.portfolio_simulator import PortfolioSimulator
from ..cli.logging_setup import setup_logging
from ..config.parameters import StrategyParameters
from ..data_io.formatters import (
    format_json_output,
    format_text_output,
    generate_output_filename,
)
from ..data_io.ingestion import ingest_ohlcv_data  # pylint: disable=no-name-in-module
from ..data_io.resample import resample_ohlcv
from ..data_io.resample_cache import resample_with_cache
from ..data_io.timeframe import parse_timeframe
from ..indicators.dispatcher import calculate_indicators
from ..indicators.registry.builtins import register_builtins
from ..models.core import TradeExecution
from ..models.directional import BacktestResult
from ..models.enums import DirectionMode, OutputFormat
from ..strategy.trend_pullback.signal_generator_vectorized import (
    generate_signals_vectorized,
)
from ..strategy.trend_pullback.strategy import TREND_PULLBACK_STRATEGY
from ..backtest.engine import (
    construct_data_paths,
    run_portfolio_backtest,
    run_multi_symbol_backtest,
)


# Ensure built-in indicators are registered early
register_builtins()

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
        "--timeframe",
        type=str,
        default="1m",
        help="Timeframe for backtesting (default: 1m). Resamples 1-minute data to "
        "target timeframe. Supports: Xm (minutes), Xh (hours), Xd (days). "
        "Examples: 1m, 5m, 15m, 1h, 4h, 1d, 7m, 90m",
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

    # Account balance for position sizing (unified architecture)
    parser.add_argument(
        "--starting-balance",
        type=float,
        default=2500.0,
        help="Starting account balance for position sizing (default: $2500). "
        "All symbols trade against this shared balance.",
    )

    parser.add_argument(
        "--no-aggregate",
        action="store_true",
        help="Disable aggregation, produce only per-strategy outputs",
    )

    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Open interactive chart with results (requires GUI environment)",
    )

    parser.add_argument(
        "--viz-start",
        type=str,
        help="Start date for visualization (YYYY-MM-DD). If omitted, defaults to last 3 months.",
    )

    parser.add_argument(
        "--viz-end",
        type=str,
        help="End date for visualization (YYYY-MM-DD).",
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

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to YAML config file for default values. "
        "CLI arguments take precedence over config values. "
        "Example: --config backtest_config.yaml",
    )

    # Risk Management Arguments (Feature 021: FR-004 - Runtime policy selection)
    parser.add_argument(
        "--risk-config",
        type=Path,
        help="Path to JSON risk configuration file. "
        "Overrides individual --risk-* arguments if specified. "
        "See specs/021-decouple-risk-management/quickstart.md for format.",
    )

    parser.add_argument(
        "--risk-pct",
        type=float,
        default=0.25,
        help="Risk percentage per trade (e.g., 0.25 for 0.25%%). Default: 0.25",
    )

    parser.add_argument(
        "--stop-policy",
        type=str,
        choices=["ATR", "ATR_Trailing", "FixedPips"],
        default="ATR",
        help="Stop-loss policy type. Default: ATR",
    )

    parser.add_argument(
        "--atr-mult",
        type=float,
        default=2.0,
        help="ATR multiplier for stop distance. Default: 2.0",
    )

    parser.add_argument(
        "--atr-period",
        type=int,
        default=14,
        help="ATR calculation period. Default: 14",
    )

    parser.add_argument(
        "--fixed-pips",
        type=float,
        help="Fixed pip distance for FixedPips stop policy (required if --stop-policy=FixedPips)",
    )

    parser.add_argument(
        "--tp-policy",
        type=str,
        choices=["RiskMultiple", "None"],
        default="RiskMultiple",
        help="Take-profit policy type. Default: RiskMultiple",
    )

    parser.add_argument(
        "--rr-ratio",
        type=float,
        default=2.0,
        help="Reward-to-risk ratio for RiskMultiple TP policy. Default: 2.0",
    )

    parser.add_argument(
        "--max-position-size",
        type=float,
        default=10.0,
        help="Maximum position size in lots. Default: 10.0",
    )

    # Blackout Filtering Arguments (Feature 023: Session Blackouts)
    parser.add_argument(
        "--blackout-sessions",
        action="store_true",
        help="Enable session-gap blackout filtering. Blocks new entries during "
        "NY close → Asian open transition (low liquidity period). "
        "See specs/023-session-blackouts for details.",
    )

    parser.add_argument(
        "--blackout-news",
        action="store_true",
        help="Enable news-event blackout filtering. Blocks new entries during "
        "high-impact news releases (NFP, IJC). Default windows: 10min before "
        "to 30min after event. See specs/023-session-blackouts for details.",
    )

    parser.add_argument(
        "--sessions",
        type=str,
        nargs="+",
        help="Enable session-only trading (whitelist approach). Only allow trades "
        "during specified sessions. Valid values: NY, LONDON, ASIA, SYDNEY. "
        "Example: --sessions NY LONDON (trades only during NY and London hours).",
    )

    # Parameter Sweep Arguments (Feature 024: Parallel Indicator Parameter Sweep)
    parser.add_argument(
        "--test_range",
        action="store_true",
        help="Enable interactive parameter sweep mode. Prompts for indicator "
        "parameter ranges and runs backtests across all combinations. "
        "See specs/024-parallel-param-sweep for details.",
    )

    parser.add_argument(
        "--export",
        type=Path,
        help="Export sweep results to CSV file (only with --test_range).",
    )

    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run parameter sweep sequentially for debugging (only with --test_range).",
    )

    args = parser.parse_args()

    # Setup logging early for --list-strategies and --register-strategy
    setup_logging(level=args.log_level)

    # Load config file if specified (T020: Config file support)
    if args.config:
        import yaml

        if args.config.exists():
            with open(args.config, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            logger.info("Loaded config from %s", args.config)

            # Apply config values only if CLI didn't override (T021: CLI precedence)
            # Check if user explicitly passed --timeframe (not using default)
            cli_timeframe_default = "1m"
            if args.timeframe == cli_timeframe_default and "timeframe" in config:
                args.timeframe = config["timeframe"]
                logger.info("Using timeframe from config: %s", args.timeframe)

            # Apply other config defaults
            if "direction" in config and args.direction == "LONG":
                args.direction = config["direction"]
            if "dataset" in config and args.dataset == "test":
                args.dataset = config["dataset"]
        else:
            logger.warning("Config file not found: %s", args.config)

    # Construct RiskConfig from CLI args or --risk-config file (T021: FR-004)
    risk_config = None
    if hasattr(args, "risk_config") and args.risk_config:
        import json

        from ..risk.config import RiskConfig

        if args.risk_config.exists():
            with open(args.risk_config, "r", encoding="utf-8") as f:
                risk_dict = json.load(f)
            risk_config = RiskConfig.from_dict(risk_dict)
            logger.info(
                "Loaded risk config from %s: %s",
                args.risk_config,
                risk_config.stop_policy.type,
            )
        else:
            logger.warning("Risk config file not found: %s", args.risk_config)
    elif hasattr(args, "stop_policy"):
        # Construct from individual CLI args
        from ..risk.config import (
            RiskConfig,
            StopPolicyConfig,
            TakeProfitPolicyConfig,
        )

        stop_policy = StopPolicyConfig(
            type=args.stop_policy,
            multiplier=args.atr_mult,
            period=args.atr_period,
            pips=args.fixed_pips,
        )

        tp_policy = TakeProfitPolicyConfig(
            type=args.tp_policy,
            rr_ratio=args.rr_ratio,
        )

        risk_config = RiskConfig(
            risk_pct=args.risk_pct,
            stop_policy=stop_policy,
            take_profit_policy=tp_policy,
            max_position_size=args.max_position_size,
        )
        logger.info(
            "Constructed risk config from CLI: stop=%s (mult=%.1f), tp=%s (rr=%.1f)",
            args.stop_policy,
            args.atr_mult,
            args.tp_policy,
            args.rr_ratio,
        )

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

    # Handle --test_range (Feature 024: Parameter Sweep Mode)
    if args.test_range:
        from .prompts.range_input import collect_all_ranges, confirm_sweep
        from ..backtest.sweep import (
            filter_invalid_combinations,
            generate_combinations,
            run_sweep,
            display_results_table,
        )
        from ..strategy.trend_pullback.strategy import TrendPullbackStrategy

        logger.info("Entering parameter sweep mode...")

        # Load strategy (currently only trend_pullback supported)
        strategy = TrendPullbackStrategy()

        # Collect parameter ranges from user
        sweep_config = collect_all_ranges(strategy)
        if sweep_config is None:
            print("No parameters to sweep. Exiting.")
            return 0

        # Generate combinations
        all_combinations = generate_combinations(sweep_config.ranges)
        sweep_config.total_combinations = len(all_combinations)

        # Filter invalid combinations
        valid_combinations, skipped = filter_invalid_combinations(all_combinations)
        sweep_config.valid_combinations = len(valid_combinations)
        sweep_config.skipped_count = skipped

        if not valid_combinations:
            print("No valid combinations after filtering. Exiting.")
            return 0

        # Confirm with user
        if not confirm_sweep(sweep_config, len(valid_combinations), skipped):
            print("Sweep cancelled by user.")
            return 0

        # Execute sweep
        print(
            f"\n[INFO] Starting sweep execution with {len(valid_combinations)} combinations..."
        )

        sweep_result = run_sweep(
            combinations=valid_combinations,
            pairs=args.pair,
            dataset=args.dataset,
            direction=args.direction,
        )

        display_results_table(sweep_result.results, top_n=10)
        return 0

    # Validate data file exists
    # (required for backtest runs, not for listing/registration)
    if args.data is None:
        # Data file required for backtest runs
        if not args.list_strategies and not args.register_strategy:
            # Use new construct_data_paths() for multi-pair support (T008-T011)
            pair_paths = construct_data_paths(args.pair, args.dataset)

            # Unified backtest path: always use run_portfolio_backtest (1 or N symbols)
            logger.info(
                "Backtest: %d symbol(s), $%.2f starting balance",
                len(pair_paths),
                args.starting_balance,
            )

            # Load strategy parameters
            parameters = StrategyParameters()
            direction_mode = DirectionMode[args.direction]
            show_progress = sys.stdout.isatty()

            # Build blackout config from CLI args (Feature 023)
            blackout_config = None
            if args.blackout_sessions or args.blackout_news or args.sessions:
                from ..risk.blackout.config import (
                    BlackoutConfig,
                    NewsBlackoutConfig,
                    SessionBlackoutConfig,
                    SessionOnlyConfig,
                )

                # Normalize session names to uppercase
                allowed_sessions = (
                    [s.upper() for s in args.sessions] if args.sessions else []
                )

                blackout_config = BlackoutConfig(
                    news=NewsBlackoutConfig(enabled=args.blackout_news),
                    sessions=SessionBlackoutConfig(enabled=args.blackout_sessions),
                    session_only=SessionOnlyConfig(
                        enabled=bool(args.sessions),
                        allowed_sessions=allowed_sessions,
                    ),
                )
                logger.info(
                    "Blackout filtering enabled: news=%s, sessions=%s, session_only=%s",
                    args.blackout_news,
                    args.blackout_sessions,
                    allowed_sessions if args.sessions else False,
                )

            result, enriched_data = run_portfolio_backtest(
                pair_paths=pair_paths,
                direction_mode=direction_mode,
                strategy_params=parameters,
                starting_equity=args.starting_balance,
                dry_run=args.dry_run,
                show_progress=show_progress,
                timeframe=args.timeframe,
                blackout_config=blackout_config,
            )

            # Format and output portfolio results
            from ..data_io.formatters import (
                format_portfolio_json_output,
                format_portfolio_text_output,
            )

            output_format = (
                OutputFormat.JSON if args.output_format == "json" else OutputFormat.TEXT
            )

            if output_format == OutputFormat.JSON:
                output_content = format_portfolio_json_output(result)
            else:
                output_content = format_portfolio_text_output(result)

            # Generate output filename
            output_filename = generate_output_filename(
                direction=direction_mode,
                output_format=output_format,
                timestamp=result.start_time,
                symbol_tag="portfolio",
                timeframe_tag=(args.timeframe if args.timeframe != "1m" else None),
            )

            # Write results to file
            output_path = args.output / output_filename
            args.output.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output_content)
            logger.info("Results written to %s", output_path)
            if args.visualize:
                try:
                    from ..visualization.datashader_viz import (
                        plot_backtest_results,
                    )
                    from rich.console import Console

                    console = Console()

                    # Show spinner while preparing data
                    with console.status(
                        "[bold green]Preparing visualization data...[/bold green]"
                    ):
                        # Combine enriched data (with indicators) for visualization
                        symbol_dfs = []
                        for symbol, df in enriched_data.items():
                            # Add symbol column if not present
                            if "symbol" not in df.columns:
                                df = df.with_columns(pl.lit(symbol).alias("symbol"))
                            symbol_dfs.append(df)
                        all_symbol_data = pl.concat(symbol_dfs)
                        # Convert PortfolioResult to BacktestResult-like structure
                        # For visualization compatibility

                        # Group executions by symbol
                        symbol_executions: dict[str, list[TradeExecution]] = {}

                        # Pre-initialize lists for all symbols loaded
                        unique_symbols = all_symbol_data["symbol"].unique().to_list()
                        for symbol in unique_symbols:
                            symbol_executions[symbol] = []

                        for trade in result.closed_trades:
                            symbol = trade.symbol
                            if symbol not in symbol_executions:
                                symbol_executions[symbol] = []

                            exec_obj = TradeExecution(
                                signal_id=trade.signal_id,
                                direction=trade.direction,
                                open_timestamp=trade.entry_timestamp,
                                entry_fill_price=trade.entry_price,
                                close_timestamp=trade.exit_timestamp,
                                exit_fill_price=trade.exit_price,
                                exit_reason=trade.exit_reason,
                                pnl_r=trade.pnl_r,
                                slippage_entry_pips=0.0,
                                slippage_exit_pips=0.0,
                                costs_total=0.0,
                                stop_price=0.0,
                                target_price=0.0,
                                portfolio_balance_at_exit=trade.portfolio_balance_at_exit,
                                risk_percent=trade.risk_percent,
                                risk_amount=trade.risk_amount,
                            )
                            symbol_executions[symbol].append(exec_obj)

                        # Create per-symbol results
                        results_dict = {}
                        for symbol, execs in symbol_executions.items():
                            results_dict[symbol] = BacktestResult(
                                run_id=f"{result.run_id}_{symbol}",
                                direction_mode=result.direction_mode,
                                start_time=result.start_time,
                                end_time=result.end_time,
                                data_start_date=result.data_start_date,
                                data_end_date=result.data_end_date,
                                total_candles=0,
                                signals=[],
                                executions=execs,
                                metrics=None,
                                pair=symbol,
                                timeframe=result.timeframe,
                            )

                        # Populate executions field with flat list of all trades
                        executions = [
                            trade
                            for symbol_execs in symbol_executions.values()
                            for trade in symbol_execs
                        ]

                        viz_result = BacktestResult(
                            run_id=result.run_id,
                            direction_mode=result.direction_mode,
                            start_time=result.start_time,
                            end_time=result.end_time,
                            data_start_date=result.data_start_date,
                            data_end_date=result.data_end_date,
                            total_candles=0,
                            signals=[],
                            executions=executions,
                            metrics=None,
                            results=results_dict,
                            pair="Multi-Symbol",
                            symbols=list(results_dict.keys()),
                            timeframe=result.timeframe,
                        )

                    # Spinner ends here, then call plot which logs cleanly
                    plot_backtest_results(
                        data=all_symbol_data,
                        result=viz_result,
                        pair="Portfolio",
                        show_plot=True,
                        start_date=args.viz_start,
                        end_date=args.viz_end,
                        timeframe=args.timeframe,
                    )
                except ImportError as e:
                    logger.error(
                        "Visualization module not found or dependency missing: %s",
                        e,
                    )
                except (RuntimeError, TypeError, ValueError, KeyError) as e:
                    logger.error(
                        "Failed to generate visualization: %s",
                        e,
                        exc_info=True,
                    )

            return 0  # Exit after backtest completes
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

        # Parse and validate timeframe (T013)
        try:
            timeframe = parse_timeframe(args.timeframe)
            timeframe_minutes = timeframe.period_minutes
            logger.info("Timeframe: %s (%d minutes)", args.timeframe, timeframe_minutes)
        except ValueError as e:
            logger.error("Invalid timeframe: %s", e)
            sys.exit(1)

        # Stage 1.5: Resample to target timeframe if not 1m (T014)

        enriched_df = ingestion_result.data
        if isinstance(enriched_df, pd.DataFrame):
            enriched_df = pl.from_pandas(enriched_df)

        # Renaming 'timestamp' to 'timestamp_utc' if needed
        if "timestamp" in enriched_df.columns:
            enriched_df = enriched_df.rename({"timestamp": "timestamp_utc"})

        if timeframe_minutes > 1:
            logger.info(
                "Stage 1.5: Resampling to %dm timeframe...",
                timeframe_minutes,
            )
            original_rows = len(enriched_df)

            # Use caching for resampled data (T027)
            pair = args.pair[0] if args.pair else "UNKNOWN"
            enriched_df = resample_with_cache(
                df=enriched_df,
                instrument=pair,
                tf_minutes=timeframe_minutes,
                resample_fn=resample_ohlcv,
            )

            logger.info(
                "✓ Resampled %d → %d bars (%dm)",
                original_rows,
                len(enriched_df),
                timeframe_minutes,
            )

            # Check for incomplete bar warning (FR-015, T030)
            if "bar_complete" in enriched_df.columns:
                incomplete_count = enriched_df.filter(
                    pl.col("bar_complete") == False  # noqa: E712
                ).height
                total_bars = len(enriched_df)
                if total_bars > 0:
                    incomplete_pct = (incomplete_count / total_bars) * 100
                    if incomplete_pct > 10.0:
                        logger.warning(
                            "%.1f%% of bars are incomplete (threshold: 10%%). "
                            "This indicates data gaps in the source data.",
                            incomplete_pct,
                        )

        # Stage 2: Vectorized indicator calculation
        logger.info("Stage 2/2: Computing technical indicators (vectorized)...")

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
        signal_params = parameters.model_dump()

        # Call vectorized backtest with Polars DataFrame
        logger.info("Using vectorized backtest path (Polars)")

        # Debug: Verify all required indicators are present
        logger.info("DataFrame columns before backtest: %s", enriched_df.columns)
        missing = [col for col in required_indicators if col not in enriched_df.columns]
        if missing:
            logger.error("Missing required indicators: %s", missing)

        result = orchestrator.run_backtest(
            candles=enriched_df,
            pair=pair,
            run_id=run_id,
            strategy=TREND_PULLBACK_STRATEGY,
            **signal_params,
        )

        # Add timeframe to result for output formatting (FR-015)
        result = replace(result, timeframe=args.timeframe)

        logger.info("Backtest complete: %s", result.run_id)

        # Calculate metrics (Moved up for availability)
        dataset_rows = len(enriched_df)
        trades_simulated = 0
        if result.metrics:
            if hasattr(result.metrics, "combined"):
                trades_simulated = result.metrics.combined.trade_count
            elif hasattr(result.metrics, "trade_count"):
                trades_simulated = result.metrics.trade_count

        # Write benchmark artifact if profiling enabled
        phase_times = {}
        if args.profile and benchmark_path:
            import tracemalloc

            from ..backtest.profiling import write_benchmark_record

            # Get phase times from orchestrator if available
            hotspots = []
            if profiler:
                phase_times = profiler.get_phase_times()
                hotspots = profiler.get_hotspots(n=10)  # SC-008: ≥10 hotspots

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

            wall_clock_total = sum(phase_times.values()) if phase_times else 0.0

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

        # T011 Integration: Interactive Visualization
        if args.visualize:
            try:
                from ..visualization.datashader_viz import plot_backtest_results
                from rich.console import Console

                console = Console()
                logger.info("Generating Datashader visualization...")

                with console.status(
                    "[bold green]Preparing visualization (Datashader)...[/bold green]"
                ):
                    plot_backtest_results(
                        data=enriched_df,
                        result=result,
                        pair=pair,
                        show_plot=True,
                        start_date=args.viz_start,
                        end_date=args.viz_end,
                        timeframe=args.timeframe,
                        viz_config=strategy.get_visualization_config(),
                    )

            except ImportError as e:
                logger.error(
                    "Visualization module not found or dependency missing: %s",
                    e,
                )
            except (RuntimeError, TypeError, ValueError, KeyError) as e:
                logger.error("Failed to generate visualization: %s", e, exc_info=True)

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
        timeframe_tag=args.timeframe if args.timeframe != "1m" else None,
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
