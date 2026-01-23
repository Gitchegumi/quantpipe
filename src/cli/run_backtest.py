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
import logging
import sys
from pathlib import Path

import polars as pl

from ..backtest.engine import (
    construct_data_paths,
    run_portfolio_backtest,
)
from ..backtest.portfolio.portfolio_simulator import PortfolioResult
from ..cli.logging_setup import setup_logging
from ..config.parameters import StrategyParameters
from ..data_io.formatters import (
    format_json_output,
    format_text_output,
    generate_output_filename,
    format_multi_symbol_text_output,
    format_multi_symbol_json_output,
    format_portfolio_text_output,
    format_portfolio_json_output,
)
from ..indicators.registry.builtins import register_builtins
from ..models.enums import DirectionMode, OutputFormat


# Ensure built-in indicators are registered early
register_builtins()

logger = logging.getLogger(__name__)

# Default account balance for multi-symbol concurrent PnL calculation (FR-003)
DEFAULT_ACCOUNT_BALANCE: float = 2500.0


def configure_backtest_parser(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Configure the argument parser for backtest arguments.
    Allows reuse by other CLI entry points (e.g., quantpipe backtest).
    """
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
        help="Risk percentage per trade (e.g., 0.25 for 0.25%%). Default: 0.25",
    )

    parser.add_argument(
        "--stop-policy",
        type=str,
        choices=[
            "ATR",
            "ATR_Trailing",
            "FixedPips",
            "FixedPips_Trailing",
            "MA_Trailing",
        ],
        default="ATR",
        help="Stop-loss policy type. Default: ATR",
    )

    parser.add_argument(
        "--atr-mult",
        type=float,
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
        "--ma-type",
        type=str,
        choices=["SMA", "EMA"],
        default="SMA",
        help="Moving average type for MA_Trailing policy. Default: SMA",
    )

    parser.add_argument(
        "--ma-period",
        type=int,
        default=50,
        help="Moving average period for MA_Trailing policy. Default: 50",
    )

    parser.add_argument(
        "--trail-trigger",
        type=float,
        default=1.0,
        help="R-multiple profit required to activate trailing stop. Default: 1.0",
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
        help="Reward-to-risk ratio for RiskMultiple TP policy. Default: 2.0",
    )

    parser.add_argument(
        "--max-position-size",
        type=float,
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
        "during specified sessions. Supports abbreviations: NY, EU (London), AS (Asia), SY (Sydney). "
        "Example: --sessions NY EU (trades only during NY and London hours).",
    )

    # CTI Prop Firm Arguments (Feature 027)
    parser.add_argument(
        "--cti-mode",
        type=str,
        choices=["1STEP", "2STEP", "INSTANT"],
        help="Enable CTI Prop Firm evaluation mode (Feature 027). "
        "Requires --starting-balance to match a valid CTI account size.",
    )

    parser.add_argument(
        "--disable-scaling",
        action="store_true",
        help="Disable CTI Scaling Plan simulation (defaults to enabled with --cti-mode). "
        "Checking this runs a standard single-challenge backtest.",
    )

    # Parameter Sweep Arguments (Feature 024: Parallel Indicator Parameter Sweep)
    parser.add_argument(
        "--test-range",
        action="store_true",
        help="Enable interactive parameter sweep mode. Prompts for indicator "
        "parameter ranges and runs backtests across all combinations. "
        "See specs/024-parallel-param-sweep for details.",
    )

    parser.add_argument(
        "--export",
        type=Path,
        help="Export sweep results to CSV file (only with --test-range).",
    )

    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run parameter sweep sequentially for debugging (only with --test-range).",
    )

    return parser


def run_backtest_command(args: argparse.Namespace) -> int:
    """
    Execute the backtest logic with the provided arguments.
    """
    # Setup logging early for --list-strategies and --register-strategy
    setup_logging(level=args.log_level)

    # -------------------------------------------------------------------------
    # Parameter Resolution (CLI > Config > Defaults)
    # -------------------------------------------------------------------------
    param_overrides = {}

    # Load from config file if present
    if args.config and args.config.exists():
        import yaml

        try:
            with open(args.config, encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}
                # Assuming config structure matches StrategyParameters flat fields
                param_overrides.update(config_data)
            logger.info("Loaded config from %s", args.config)

            # Legacy: Apply config defaults for non-strategy args
            # Check if user explicitly passed --timeframe (not using default)
            cli_timeframe_default = "1m"
            if args.timeframe == cli_timeframe_default and "timeframe" in config_data:
                args.timeframe = config_data["timeframe"]
                logger.info("Using timeframe from config: %s", args.timeframe)

            # Apply other config defaults
            if "direction" in config_data and args.direction == "LONG":
                args.direction = config_data["direction"]
            if "dataset" in config_data and args.dataset == "test":
                args.dataset = config_data["dataset"]

        except Exception as e:  # pylint: disable=broad-except
            logger.error("Failed to load config file: %s", e)
    elif args.config:
        logger.warning("Config file not found: %s", args.config)

    # Override with CLI args if explicitly provided (not None)
    if args.risk_pct is not None:
        param_overrides["risk_per_trade_pct"] = args.risk_pct
    if args.atr_mult is not None:
        param_overrides["atr_stop_mult"] = args.atr_mult
    if args.rr_ratio is not None:
        param_overrides["target_r_mult"] = args.rr_ratio
    if args.starting_balance is not None:
        param_overrides["account_balance"] = args.starting_balance
    if args.max_position_size is not None:
        param_overrides["max_position_size"] = args.max_position_size

    # Instantiate StrategyParameters (Validation + Defaults)
    parameters = StrategyParameters(**param_overrides)

    # Log active risk parameters (FR-006)
    logger.info("Active Risk Parameters:")
    logger.info("  Risk %%: %.2f", parameters.risk_per_trade_pct)
    logger.info("  Stop Multiplier (ATR): %.2f", parameters.atr_stop_mult)
    logger.info("  R:R Ratio: %.2f", parameters.target_r_mult)
    logger.info("  Max Position Size: %.2f", parameters.max_position_size)
    logger.info("  Account Balance: %.2f", parameters.account_balance)

    # -------------------------------------------------------------------------
    # End Parameter Resolution
    # -------------------------------------------------------------------------

    # Construct RiskConfig from CLI args or --risk-config file (T021: FR-004)
    risk_config = None
    if hasattr(args, "risk_config") and args.risk_config:
        import json

        from ..risk.config import RiskConfig

        if args.risk_config.exists():
            with open(args.risk_config, encoding="utf-8") as f:
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
            multiplier=parameters.atr_stop_mult,  # Use resolved parameter
            period=args.atr_period,
            pips=args.fixed_pips,
            ma_type=args.ma_type,
            ma_period=args.ma_period,
            trail_trigger_r=args.trail_trigger,
        )

        tp_policy = TakeProfitPolicyConfig(
            type=args.tp_policy,
            rr_ratio=parameters.target_r_mult,  # Use resolved parameter
        )

        risk_config = RiskConfig(
            risk_pct=parameters.risk_per_trade_pct,  # Use resolved parameter
            stop_policy=stop_policy,
            take_profit_policy=tp_policy,
            max_position_size=parameters.max_position_size,  # Use resolved parameter
        )
        logger.info(
            "Constructed risk config from CLI: stop=%s (mult=%.1f), tp=%s (rr=%.1f)",
            args.stop_policy,
            parameters.atr_stop_mult,
            args.tp_policy,
            parameters.target_r_mult,
        )

    # Handle --list-strategies (FR-017: List strategies without running backtest)
    if args.list_strategies:
        from ..strategy.registry import StrategyRegistry

        registry = StrategyRegistry()
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
        from ..backtest.sweep import (
            display_results_table,
            export_results_to_csv,
            filter_invalid_combinations,
            generate_combinations,
            run_sweep,
        )
        from .prompts.range_input import collect_all_ranges, confirm_sweep
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
            max_workers=args.max_workers,
            sequential=args.sequential,
        )

        display_results_table(sweep_result.results, top_n=10)

        # Export results (Phase 6)
        if args.export:
            export_results_to_csv(sweep_result, args.export)
            print(f"\n[INFO] Sweep results exported to: {args.export}")

        return 0

    # Validate data file exists
    # (required for backtest runs, not for listing/registration)
    if not args.list_strategies and not args.register_strategy:
        # Determine data paths
        if args.data:
            pair_name = args.pair[0] if args.pair else "CUSTOM"
            pair_paths = [(pair_name, args.data)]
        else:
            # Use new construct_data_paths() for multi-pair support (T008-T011)
            pair_paths = construct_data_paths(args.pair, args.dataset)

        # Unified backtest path: always use run_portfolio_backtest (1 or N symbols)
        logger.info(
            "Backtest: %d symbol(s), $%.2f starting balance",
            len(pair_paths),
            parameters.account_balance,  # Use resolved parameter
        )

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

            # Defaults if flags active but not configured
            news_cfg = None
            if args.blackout_news:
                news_cfg = NewsBlackoutConfig(enabled=True)

            session_cfg = None
            if args.blackout_sessions:
                session_cfg = SessionBlackoutConfig(enabled=True)

            whitelist_cfg = None
            if args.sessions:
                # Map shorthand to full names if needed, or rely on config parsing
                whitelist_cfg = SessionOnlyConfig(enabled=True, sessions=args.sessions)

            blackout_config = BlackoutConfig(
                enabled=True,
                session_blackout=session_cfg,
                news_event=news_cfg,
                session_filter=whitelist_cfg,
            )
            logger.info("Blackout filtering enabled: %s", blackout_config)

        # ---------------------------------------------------------------------
        # Execution (Unified - Independent or Portfolio Mode)
        # ---------------------------------------------------------------------
        # Calls execute independent backtests per symbol using run_portfolio_backtest

        result, symbol_data = run_portfolio_backtest(
            pair_paths=pair_paths,
            direction_mode=direction_mode,
            strategy_params=parameters,
            starting_equity=parameters.account_balance,
            dry_run=args.dry_run,
            show_progress=show_progress,
            timeframe=args.timeframe,
            blackout_config=blackout_config,
            risk_config=risk_config,
            # indicator_overrides=None, # Explicitly using defaults
        )

        # Logic to display output
        out_fmt = OutputFormat(args.output_format)

        # For now, we only handle PortfolioResult as implicit strict return type of run_portfolio_backtest
        # (Legacy single-symbol BacktestResult not returned by this function)
        if hasattr(result, "equity_curve"):  # Duck typing for PortfolioResult
            if out_fmt == OutputFormat.TEXT:
                print(format_portfolio_text_output(result, "trend-pullback"))
            else:
                print(format_portfolio_json_output(result))

        # Legacy BacktestResult support (only check if NOT a PortfolioResult)
        elif hasattr(result, "is_multi_symbol") and result.is_multi_symbol:
            if out_fmt == OutputFormat.TEXT:
                print(format_multi_symbol_text_output(result, "trend-pullback"))
            else:
                print(format_multi_symbol_json_output(result))
        else:
            if out_fmt == OutputFormat.TEXT:
                print(format_text_output(result, "trend-pullback"))
            else:
                print(format_json_output(result))

        # Save to file
        # Check if args.output is directory or file
        output_path = args.output
        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)

        filename = generate_output_filename(
            direction=direction_mode,
            output_format=out_fmt,
            timestamp=result.start_time,
            symbol_tag=(
                result.symbols[0]
                if hasattr(result, "symbols") and result.symbols
                else getattr(result, "pair", "multi")
            ),
            timeframe_tag=args.timeframe,
        )

        full_path = output_path / filename
        with open(full_path, "w", encoding="utf-8") as f:
            if hasattr(result, "equity_curve"):  # PortfolioResult
                if out_fmt == OutputFormat.TEXT:
                    f.write(format_portfolio_text_output(result, "trend-pullback"))
                else:
                    f.write(format_portfolio_json_output(result))
            elif hasattr(result, "is_multi_symbol") and result.is_multi_symbol:
                if out_fmt == OutputFormat.TEXT:
                    f.write(format_multi_symbol_text_output(result, "trend-pullback"))
                else:
                    f.write(format_multi_symbol_json_output(result))
            else:
                if out_fmt == OutputFormat.TEXT:
                    f.write(format_text_output(result, "trend-pullback"))
                else:
                    f.write(format_json_output(result))

        logger.info("Results saved to %s", full_path)

        # Visualization
        if args.visualize:
            from ..visualization.datashader_viz import plot_backtest_results

            logger.info("Opening visualization...")

            # Prepare data for visualization
            # If multi-symbol, concat
            if len(symbol_data) > 1:
                # Concat all frames
                dfs = []
                for sym, df in symbol_data.items():
                    # Add symbol col if not present
                    if "symbol" not in df.columns:
                        df = df.with_columns(pl.lit(sym).alias("symbol"))
                    dfs.append(df)

                viz_data = pl.concat(dfs)
                pair_label = "PORTFOLIO"
            else:
                pair_label = list(symbol_data.keys())[0]
                viz_data = symbol_data[pair_label]

            plot_backtest_results(
                data=viz_data,
                result=result,
                pair=pair_label,
                show_plot=True,
                initial_balance=parameters.account_balance,
                timeframe=args.timeframe,
                # date ranges and other configs ignored for now
            )

    return 0
