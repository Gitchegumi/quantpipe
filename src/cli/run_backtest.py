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
import sys
import re  # Import re for regex in _prompt
from datetime import UTC, datetime
from pathlib import Path

import questionary  # <<< Added for interactive prompts
import polars as pl
from rich.console import Console

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

# --- Initialize Rich Console for cleaner output ---
console = Console()

# Ensure built-in indicators are registered early
register_builtins()

logger = logging.getLogger(__name__)

# Default account balance for multi-symbol concurrent PnL calculation (FR-003)
DEFAULT_ACCOUNT_BALANCE: float = 2500.0


def _is_interactive() -> bool:
    """Check if the current session is interactive (attached to a TTY)."""
    return sys.stdin.isatty() and sys.stdout.isatty()


# --- Interactive Prompt Utilities using Questionary ---


def _prompt(msg: str, default=None, coerce=str, choices=None):
    """
    Interactively prompt user for input using questionary arrow-key menus.
    Handles default values, coercion, and choices for menu selection.
    """
    # Extract default value from message using regex if present (e.g., "[default_value]")
    default_match = re.search(r"\[([^\]]+)\]", msg)
    if (
        default is None and default_match
    ):  # Use default from message if not provided via arg
        default = default_match.group(1)

    # Clean message for questionary (remove placeholders like [choices] and trailing colon)
    message = re.sub(r"\s*\[[^\]]+\]\s*:?\s*$", "", msg).strip()
    message = message.lstrip("? ").strip()  # Remove leading '?' and space

    if choices:
        # Use questionary.select for menu interaction
        cleaned_choices = [str(c) for c in choices if isinstance(c, (str, int, float))]

        # Find default choice index if default is in cleaned_choices
        default_choice_str = str(default) if default is not None else None

        try:
            choice = questionary.select(
                message,
                choices=cleaned_choices,
                default=(
                    default_choice_str
                    if default_choice_str in cleaned_choices
                    else None
                ),
                use_shortcuts=True,  # Enable keyboard shortcuts like '?' for help
                qmark="?",  # Retain the question mark prefix
            ).ask()

            if choice is None:  # User cancelled (Ctrl+C)
                print("\nOperation cancelled.")
                sys.exit(1)

            return coerce(choice)

        except Exception as e:
            print(f"\nError during selection prompt: {e}")
            # Fallback to manual input or default if possible
            if default is not None:
                try:
                    val = coerce(default)
                    print(f"Falling back to default value: {default}")
                    return val
                except ValueError:
                    pass  # If default also fails coercion, proceed to manual input
            print("Please enter value manually:")
            return coerce(input(f"{message} "))  # Manual input fallback

    else:
        # Use questionary.text for free-form input
        try:
            text_input = questionary.text(
                message,
                default=str(default) if default is not None else "",
                # Allow empty input unless coerced value is invalid
                validate=lambda x: coerce(x) is not None if x else True,
                qmark="?",
            ).ask()

            if text_input is None:  # User cancelled
                print("\nOperation cancelled.")
                sys.exit(1)

            # If input is empty and a default exists, use the default
            if text_input == "" and default is not None:
                return coerce(default)

            # Attempt coercion
            val = coerce(text_input)

            return val

        except Exception as e:  # Catch potential errors during prompt execution
            print(f"\nError during text prompt: {e}")
            return (
                coerce(default) if default is not None else None
            )  # Fallback to default


def _multi_select_prompt(msg: str, default=None, coerce=str, choices=None):
    """
    Interactively prompt user for multiple inputs using questionary.checkbox.
    Handles default values, coercion, and user cancellation.
    Assumes choices are presented as a list.
    """
    message = msg.replace("? ", "").strip()  # Clean message for questionary

    if choices:
        # Ensure choices are strings for questionary compatibility
        string_choices = [str(c) for c in choices if isinstance(c, (str, int, float))]

        # Format default selections for questionary
        default_selections = []
        if default is not None:
            # Ensure default is treated as a list for consistent processing
            default_list = default if isinstance(default, list) else [default]
            # Filter defaults to only include those present in the actual choices
            default_selections = [
                str(d) for d in default_list if str(d) in string_choices
            ]

        try:
            selected_choices = questionary.checkbox(
                message, choices=string_choices, default=default_selections, qmark="?"
            ).ask()

            if selected_choices is None:  # User cancelled
                print("\nOperation cancelled.")
                sys.exit(1)

            # Coerce selected choices and return the list
            coerced_results = [coerce(choice) for choice in selected_choices]

            # Basic validation can be added here if needed beyond simple coercion
            # For now, assume successful coercion is sufficient validation

            return coerced_results

        except Exception as e:  # Catch potential errors during prompt execution
            print(f"\nError during checkbox prompt: {e}")
            # Return empty list on error, or potentially prompt again
            return []

    else:
        # Handle case where choices are not provided (should ideally not happen for multi-select)
        print("Error: _multi_select_prompt was called without providing choices.")
        return []


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
        default=None,
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
        default=None,
        help="Strategy name(s) to run (e.g., trend-pullback). Supports multiple: \
            --strategy strat1 strat2",
    )

    parser.add_argument(
        "--pair",
        type=str,
        nargs="+",
        default=None,
        help="Currency pair(s) to backtest (e.g., EURUSD). Supports multiple: \
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
        default=None,
        help="Timeframe for backtesting (default: 1m). Resamples 1-minute data to "
        "target timeframe. Supports: Xm (minutes), Xh (hours), Xd (days). "
        "Examples: 1m, 5m, 15m, 1h, 4h, 1d, 7m, 90m",
    )

    parser.add_argument(
        "--simulation-type",
        type=str,
        choices=["Personal Capital", "City Traders Imperium (CTI)"],
        default=None,
        help="Simulation type: 'Personal Capital' or 'City Traders Imperium (CTI)'",
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
        help="Starting account balance / Challenge Level (default: $2500). "
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

    # GPU Acceleration flags (Feature 023-GPU)
    parser.add_argument(
        "--gpu",
        "--cuda",
        "--gpu-accel",
        action="store_true",
        help="Enable GPU acceleration for indicators and scanning using CuPy/CUDA.",
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
        dest="risk_percent",  # Corrected dest name
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
        default=None,
        help="Stop-loss policy type. Default: ATR",
    )

    parser.add_argument(
        "--atr-mult",
        type=float,
        help="ATR multiplier for stop distance. Default: 2.0",
        dest="atr_multiplier",  # Corrected dest name
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
        default=None,
        help="Take-profit policy type. Default: RiskMultiple",
        dest="take_profit_policy",  # Corrected dest name
    )

    parser.add_argument(
        "--rr-ratio",
        type=float,
        help="Reward-to-risk ratio for RiskMultiple TP policy. Default: 2.0",
        dest="reward_risk_ratio",  # Corrected dest name
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
        "NY close \u2192 Asian open transition (low liquidity period). "
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

    parser.add_argument(
        "--limit-sessions",
        action="store_true",
        help="Limit trading to specific sessions (requires --sessions).",
    )

    parser.add_argument(
        "--sessions-force-close",
        action="store_true",
        help="Force close open trades at the end of the specified session(s).",
        dest="force_session_close",  # Corrected dest name
    )

    parser.add_argument(
        "--sessions-window",
        type=int,
        help="Buffer window in minutes before session end to stop new entries (if force-close enabled).",
        dest="session_buffer",  # Corrected dest name
    )

    parser.add_argument(
        "--news-force-close",
        action="store_true",
        help="Force close open trades before high-impact news events.",
        dest="force_news_close",  # Corrected dest name
    )

    parser.add_argument(
        "--news-window-before",
        type=int,
        help="Minutes before news event to start blackout / force close.",
        dest="minutes_before_news",  # Corrected dest name
    )

    parser.add_argument(
        "--news-window-after",
        type=int,
        help="Minutes after news event to end blackout.",
        dest="minutes_after_news",  # Corrected dest name
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
        "--buyback-strategy",
        type=str,
        choices=["1STEP", "2STEP", "INSTANT"],
        help="Strategy for handling account buybacks after Attempt 1 (defaults to --cti-mode).",
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

    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Bypass interactive prompts and use defaults on missing flags.",
    )

    return parser


def run_backtest_command(args: argparse.Namespace) -> int:
    """
    Execute the backtest logic with the provided arguments.
    """
    if args.profile:
        import cProfile
        import pstats
        import io

        pr = cProfile.Profile()
        pr.enable()

    # Setup logging early for --list-strategies and --register-strategy
    setup_logging(level=args.log_level)

    # --- Imports for parameter sweep moved here to prevent UnboundLocalError ---
    # These imports are only needed if the parameter sweep mode is activated.
    # Moved here to avoid potential circular dependencies or unnecessary imports in standard runs.
    from ..backtest.sweep import (
        display_results_table,
        export_results_to_csv,
        filter_invalid_combinations,
        generate_combinations,
        run_sweep,
    )
    from .prompts.range_input import (
        collect_all_ranges,
        confirm_sweep,
    )  # Assuming these exist
    from ..strategy.registry import (
        StrategyRegistry,
    )  # Used for dynamic strategy listing

    # --- Early Exit for Strategy Listing ---
    if args.list_strategies:
        registry = StrategyRegistry()
        strategies = registry.list()

        console.print("\n[bold cyan]Available Strategies:[/bold cyan]")
        table = pl.DataFrame(
            {
                "Name": [s.name for s in strategies],
                "Tags": [", ".join(s.tags) for s in strategies],
                "Version": [s.version for s in strategies],
            }
        )
        console.print(table)
        return 0

    # --- Define Choices for Prompts ---
    direction_choices = ["LONG", "SHORT", "BOTH"]
    simulation_choices = ["Personal Capital", "City Traders Imperium (CTI)"]
    cti_mode_choices = ["1STEP", "2STEP", "INSTANT"]
    stop_policy_choices = [
        "ATR",
        "ATR_Trailing",
        "FixedPips",
        "FixedPips_Trailing",
        "MA_Trailing",
    ]
    take_profit_choices = ["RiskMultiple", "None"]
    yes_no_choices = ["y", "n"]
    session_choices = ["NY", "EU", "AS", "SY"]  # Common session abbreviations

    # --- Interactive Prompts for Missing Flags (Feature 026) ---
    is_interactive = _is_interactive() and not args.non_interactive
    run_param_sweep = False  # Initialize sweep flag

    # Only prompt if not in non-interactive mode and certain flags are missing
    if not args.list_strategies and not args.register_strategy:
        # Check for missing required flags that need user input
        # We'll refine this logic below to prompt only when truly needed.

        # 1. Strategy Prompt
        if args.strategy is None:
            if not is_interactive:
                args.strategy = ["trend-pullback"]  # Default for non-interactive
            else:
                try:
                    registry = StrategyRegistry()
                    available_strategies = [strat.name for strat in registry.list()]

                    # Filter strategies if a partial match is provided
                    strategy_input = _prompt(
                        "? Strategy [trend-pullback] ",
                        default=(
                            "trend-pullback"
                            if "trend-pullback" in available_strategies
                            else (
                                available_strategies[0]
                                if available_strategies
                                else None
                            )
                        ),
                        choices=available_strategies,
                    )
                    args.strategy = (
                        [strategy_input] if strategy_input else ["trend-pullback"]
                    )
                except Exception as e:
                    logger.error(f"Could not list strategies: {e}. Using default.")
                    args.strategy = ["trend-pullback"]

        # 2. Pair Prompt (only if --data is not specified)
        if args.pair is None and not args.data:
            if not is_interactive:
                args.pair = ["EURUSD"]  # Default for non-interactive
            else:
                # Dynamically get available pairs from price_data/processed/
                import os

                PRICE_DATA_DIR = Path("price_data/processed")

                # Attempt to resolve PRICE_DATA_DIR relative to common locations
                if not PRICE_DATA_DIR.exists():
                    pass

                available_pairs = []
                if PRICE_DATA_DIR.exists():
                    # Scan for .parquet files
                    for item in PRICE_DATA_DIR.glob("*.parquet"):
                        # Filename format: PAIR_TIMEFRAME.parquet or similar?
                        # Assuming filename starts with PAIR
                        # But actually user said "processed" directory.
                        # Usually files are like EURUSD_1h.parquet or similar.
                        # Or just straight PAIR names if it's a directory structure?
                        # Let's assume files are named per pair.
                        # Common pattern: BTCUSDT.parquet or BTCUSDT_1h.parquet
                        parts = item.stem.split("_")
                        if parts:
                            available_pairs.append(parts[0])

                available_pairs = sorted(list(set(available_pairs)))  # Unique pairs

                if not available_pairs:
                    logger.warning("No price data found in %s.", PRICE_DATA_DIR)
                    logger.warning("Please run 'quantpipe ingest' to download data.")
                    # Provide a dummy choice or exit?
                    # Prompt shouldn't crash.
                    available_pairs = ["NO_DATA_FOUND"]

                pair_choices = available_pairs
                default_pair = (
                    "EURUSD" if "EURUSD" in available_pairs else available_pairs[0]
                )

                args.pair = _prompt(
                    "? Pair(s) to trade ",
                    default=default_pair,
                    choices=pair_choices,
                )
                if args.pair == "NO_DATA_FOUND":
                    logger.error("No data found. Exiting.")
                    return 1

                # Support multiple selection? The prompt returns a string if choices is list of strings?
                # questionary.checkbox returns list. questionary.select returns string.
                # _prompt uses select (single choice). The arg is 'pair' (singular/list?).
                # If the user wants multiple, they probably need a different prompt type or split string.
                # Argument parser says nargs='*'.
                # But here we are setting args.pair to a single string from prompt.
                # We should wrap it in list.
                args.pair = [args.pair]

        # 3. Direction Prompt
        if args.direction is None:
            if not is_interactive:
                args.direction = "LONG"  # Default for non-interactive
            else:
                d = _prompt("? Direction ", default="LONG", choices=direction_choices)
                args.direction = d if d else "LONG"

        # 4. Timeframe Prompt
        if args.timeframe is None:
            if not is_interactive:
                args.timeframe = "1m"  # Default for non-interactive
            else:
                t = _prompt("? Timeframe (e.g., 1m, 5m, 1h) ", default="1m")
                args.timeframe = t if t else "1m"

        # 5. Simulation Type (FR-027 / Issue #83 Refactor)
        if args.simulation_type is None:  # Assuming this arg exists or should be added
            if not is_interactive:
                args.simulation_type = "Personal Capital"  # Default for non-interactive
            else:
                sim_type = _prompt(
                    "? What simulation are you running? ",
                    default="Personal Capital",
                    choices=simulation_choices,
                )
                args.simulation_type = sim_type if sim_type else "Personal Capital"

        # Conditional prompts based on simulation type
        if args.simulation_type == "City Traders Imperium (CTI)":
            console.print("\n[CTI Prop Firm Settings]")

            # 1. CTI Mode
            if args.cti_mode is None:
                if not is_interactive:
                    args.cti_mode = "2STEP"  # Default for non-interactive
                else:
                    mode = _prompt(
                        "? CTI Mode ", default="2STEP", choices=cti_mode_choices
                    )
                    args.cti_mode = mode if mode else "2STEP"

            # 2. Buy-back Strategy (defaults to selected CTI mode)
            if args.buyback_strategy is None:
                if not is_interactive:
                    args.buyback_strategy = (
                        args.cti_mode
                    )  # Default to selected CTI mode
                else:
                    bb_mode = _prompt(
                        f"? Buy-back Strategy ",
                        default=args.cti_mode,
                        choices=cti_mode_choices,
                    )
                    args.buyback_strategy = bb_mode if bb_mode else args.cti_mode

            # 3. Challenge Level (dynamically populated)
            if args.starting_balance is None:
                challenge_choices = []
                PRESETS_DIR = Path("src/config/presets/cti")
                filename_map = {
                    "1STEP": "cti_1_step_challenge.json",
                    "2STEP": "cti_2_step_challenge.json",
                    "INSTANT": "cti_instant_funding.json",
                }

                # Resolve file path relative to script or CWD
                file_path_str = filename_map.get(
                    args.cti_mode, "cti_2_step_challenge.json"
                )
                possible_paths = [
                    PRESETS_DIR / file_path_str,
                    Path("src/config/presets/cti")
                    / file_path_str,  # Relative to workspace root
                    Path(__file__).parent
                    / "src/config/presets/cti"
                    / file_path_str,  # Relative to current script file
                ]

                resolved_path = None
                for p in possible_paths:
                    if p.exists():
                        resolved_path = p.resolve()
                        break

                if resolved_path:
                    try:
                        with open(resolved_path, encoding="utf-8") as f:
                            data = json.load(f)

                            if args.cti_mode == "INSTANT" and "programs" in data:
                                program_list = data.get("programs", {}).get(
                                    "STANDARD", []
                                )
                                challenge_choices = [
                                    str(float(item.get("tier_name")))
                                    for item in program_list
                                    if "tier_name" in item
                                ]
                            elif "starting_account_sizes" in data:
                                challenge_choices = [
                                    str(float(item.get("account_size")))
                                    for item in data["starting_account_sizes"]
                                    if "account_size" in item
                                ]

                            if not challenge_choices:
                                raise ValueError("No challenge levels found in file.")

                    except Exception as e:
                        logger.exception(
                            f"Failed to load CTI challenge levels for mode '{args.cti_mode}' from {resolved_path}: {e}"
                        )
                        # Fallback to hardcoded values if dynamic load fails
                        challenge_choices = [
                            str(float(c))
                            for c in [
                                2500.0,
                                5000.0,
                                10000.0,
                                25000.0,
                                50000.0,
                                100000.0,
                            ]
                        ]
                else:  # If file_path does not exist, use hardcoded defaults
                    challenge_choices = [
                        str(float(c))
                        for c in [2500.0, 5000.0, 10000.0, 25000.0, 50000.0, 100000.0]
                    ]

                default_challenge = "25000.0"
                if challenge_choices:
                    if default_challenge not in challenge_choices:
                        # Try to pick a sensible default if 25000 is not available
                        if "100000.0" in challenge_choices:
                            default_challenge = "100000.0"
                        elif "50000.0" in challenge_choices:
                            default_challenge = "50000.0"
                        elif challenge_choices:
                            default_challenge = challenge_choices[0]

                b = _prompt(
                    "? Challenge Level (USD) ",
                    default=default_challenge,
                    coerce=float,
                    choices=challenge_choices,
                )
                args.starting_balance = b if b else float(default_challenge)

            else:  # Personal Capital Settings
                console.print("\n[Personal Capital Settings]")
                if args.starting_balance is None:
                    if not is_interactive:
                        args.starting_balance = DEFAULT_ACCOUNT_BALANCE
                    else:
                        b = _prompt(
                            "? Starting Capital (USD) ",
                            default=str(
                                DEFAULT_ACCOUNT_BALANCE
                            ),  # Use default constant
                            coerce=float,
                        )
                        args.starting_balance = b if b else DEFAULT_ACCOUNT_BALANCE

            # 6. Risk Parameters
            console.print("\n[Risk Management]")

            # Risk % per trade
            if args.risk_percent is None:
                if not is_interactive:
                    args.risk_percent = 0.25
                else:
                    rp = _prompt("? Risk % per trade ", default="0.25", coerce=float)
                    args.risk_percent = rp if rp else 0.25

            # Stop Policy
            if args.stop_policy is None:
                if not is_interactive:
                    args.stop_policy = "ATR"
                else:
                    sp = _prompt(
                        "? Stop Policy ", default="ATR", choices=stop_policy_choices
                    )
                    args.stop_policy = sp if sp else "ATR"

            # Take Profit Policy
            if args.take_profit_policy is None:
                if not is_interactive:
                    args.take_profit_policy = "RiskMultiple"
                else:
                    tp = _prompt(
                        "? Take Profit Policy ",
                        default="RiskMultiple",
                        choices=take_profit_choices,
                    )
                    args.take_profit_policy = tp if tp else "RiskMultiple"

            # Reward-to-Risk Ratio
            if args.reward_risk_ratio is None:
                if not is_interactive:
                    args.reward_risk_ratio = 2.0
                else:
                    rrr = _prompt(
                        "? Reward-to-Risk Ratio ", default="2.0", coerce=float
                    )
                    args.reward_risk_ratio = rrr if rrr else 2.0

            # ATR Multiplier (only if ATR or ATR_Trailing is selected)
            if (
                args.stop_policy in ["ATR", "ATR_Trailing"]
                and args.atr_multiplier is None
            ):
                if not is_interactive:
                    args.atr_multiplier = 2.0
                else:
                    atm = _prompt("? ATR Multiplier ", default="2.0", coerce=float)
                    args.atr_multiplier = atm if atm else 2.0

            # ATR Period (only if ATR or ATR_Trailing is selected)
            if args.stop_policy in ["ATR", "ATR_Trailing"] and args.atr_period is None:
                if not is_interactive:
                    args.atr_period = 14
                else:
                    atp = _prompt("? ATR Period ", default="14", coerce=int)
                    args.atr_period = atp if atp else 14

            # 7. Session Management
            console.print("\n[Session Management]")

            # Limit trading to specific sessions?
            if args.limit_sessions is None:
                if not is_interactive:
                    args.limit_sessions = False
                else:
                    yn = _prompt(
                        "? Limit trading to specific sessions? ",
                        default="n",
                        choices=yes_no_choices,
                    )
                    args.limit_sessions = yn == "y"

            if args.limit_sessions and args.sessions is None:
                selected_sessions = _multi_select_prompt(
                    "? Sessions (space-separated, e.g., NY EU AS SY) ",
                    default=["NY"],  # Default to NY if not specified
                    choices=session_choices,
                )
                args.sessions = selected_sessions if selected_sessions else ["NY"]
            elif not args.limit_sessions and args.sessions is None:
                args.sessions = []  # Explicitly empty if not limiting

            # Enable forced close for sessions?
            if args.force_session_close is None:
                if not is_interactive:
                    args.force_session_close = False
                else:
                    yn = _prompt(
                        "? Enable forced close for sessions? ",
                        default="n",
                        choices=yes_no_choices,
                    )
                    args.force_session_close = yn == "y"

            # Session buffer window
            if args.session_buffer is None:
                if not is_interactive:
                    args.session_buffer = 15
                else:
                    sb = _prompt(
                        "? Session buffer window (minutes) ", default="15", coerce=int
                    )
                    args.session_buffer = sb if sb else 15

            # 8. News Event Filtering
            console.print("\n[News Event Filtering]")

            # Enable news event blackout filtering?
            if args.news_event_blackout is None:
                if not is_interactive:
                    args.news_event_blackout = False
                else:
                    yn = _prompt(
                        "? Enable news event blackout filtering? ",
                        default="n",
                        choices=yes_no_choices,
                    )
                    args.news_event_blackout = yn == "y"

            # Enable forced close for news?
            if args.force_news_close is None:
                if not is_interactive:
                    args.force_news_close = False
                else:
                    yn = _prompt(
                        "? Enable forced close for news? ",
                        default="n",
                        choices=yes_no_choices,
                    )
                    args.force_news_close = yn == "y"

            # Minutes before/after news
            if args.minutes_before_news is None:
                if not is_interactive:
                    args.minutes_before_news = 10
                else:
                    mbn = _prompt("? Minutes before news ", default="10", coerce=int)
                    args.minutes_before_news = mbn if mbn else 10

            if args.minutes_after_news is None:
                if not is_interactive:
                    args.minutes_after_news = 30
                else:
                    man = _prompt("? Minutes after news ", default="30", coerce=int)
                    args.minutes_after_news = man if man else 30

            # 9. Parameter Sweep Mode Prompt
            # Only prompt if --test-range wasn't explicitly set via CLI
            if not args.test_range:
                if not is_interactive:
                    run_param_sweep = (
                        False  # Default to not running sweep if non-interactive
                    )
                else:
                    yn = _prompt(
                        "? Would you like to test a range of indicator values? ",
                        default="n",
                        choices=yes_no_choices,
                    )
                    if yn == "y":
                        run_param_sweep = True
                        args.test_range = True  # Set flag to trigger sweep logic
            elif args.test_range:  # If --test-range was explicitly set on CLI
                run_param_sweep = True

        # --- End of Interactive Prompts ---

    # If running in interactive mode and a parameter sweep was indicated,
    # load the necessary sweep-related imports.
    if run_param_sweep or args.test_range:
        # These imports were moved outside the interactive block earlier,
        # ensuring they are available if sweep mode is activated.
        pass  # Imports are already handled above

    # --- Execute Backtest ---

    # If strategy is empty after prompts (user cancelled or no strategy found)
    if not args.strategy:
        logger.error("No strategy selected or found. Exiting.")
        sys.exit(1)

    # Handle parameter sweep mode
    if args.test_range:
        logger.info("Starting parameter sweep mode.")

        # Collect ranges for indicators (e.g., ATR period, ATR multiplier, RRR)
        # This function should prompt the user for ranges if not provided via CLI args
        try:
            indicator_ranges = collect_all_ranges(
                args
            )  # Pass args to reuse values if already set
        except Exception as e:
            logger.error(f"Failed to collect indicator ranges: {e}")
            return 1

        # Generate combinations of parameters
        try:
            combinations = list(generate_combinations(indicator_ranges))
        except Exception as e:
            logger.error(f"Failed to generate parameter combinations: {e}")
            return 1

        # Filter out invalid combinations (e.g., if a parameter depends on another)
        try:
            valid_combinations, skipped = filter_invalid_combinations(combinations)
        except Exception as e:
            logger.error(f"Failed to filter invalid parameter combinations: {e}")
            return 1

        if not confirm_sweep(indicator_ranges, len(valid_combinations), skipped):
            logger.info("Parameter sweep cancelled by user.")
            return 1  # Indicate cancellation

        # Run the sweep
        try:
            results = run_sweep(args, valid_combinations)
        except Exception as e:
            logger.error(f"Error during parameter sweep execution: {e}")
            return 1

        # Display and export results
        display_results_table(results)

        if args.csv:  # Assuming --csv argument exists for export path
            try:
                export_results_to_csv(results, args.csv)
                logger.info(f"Results exported to {args.csv}")
            except Exception as e:
                logger.error(f"Failed to export results to CSV: {e}")

        logger.info("Parameter sweep finished.")
        return 0  # Success

    # --- Standard Backtest Execution ---

    # If no arguments were passed, and we are not in interactive mode,
    # it means the user is running `opentrades run backtest` without flags.
    # We should prompt them if they want to enter interactive mode.
    if not any(vars(args).values()) and not is_interactive and not args.non_interactive:
        yn = _prompt(
            "No arguments provided. Enter interactive mode? ",
            default="y",
            choices=["y", "n"],
        )
        if yn == "y":
            # Rerun the function to trigger interactive prompts
            # Need to simulate new args object with all None values to force interactive mode
            import argparse

            new_args = argparse.Namespace()
            # Populate with None for all expected args
            for arg_name in vars(args):
                setattr(new_args, arg_name, None)
            return run_backtest_command(new_args)  # Recursive call to re-enter prompts
        else:
            logger.info("Exiting without running backtest.")
            return 1

    # Placeholder: In a real implementation, this is where the backtest execution logic would go.
    # For now, we'll just print the arguments to show they were processed.
    print("\n--- Backtest Configuration ---")
    print(f"Strategy: {args.strategy}")
    print(f"Pair(s): {args.pair}")
    print(f"Direction: {args.direction}")
    print(f"Timeframe: {args.timeframe}")
    print(f"Simulation Type: {args.simulation_type}")
    if args.simulation_type == "City Traders Imperium (CTI)":
        print(f"CTI Mode: {args.cti_mode}")
        print(f"Buy-back Strategy: {args.buyback_strategy}")
        print(f"Challenge Level (USD): {args.starting_balance}")
    else:
        print(f"Starting Capital (USD): {args.starting_balance}")
    print(f"Risk % per trade: {args.risk_percent}")
    print(f"Stop Policy: {args.stop_policy}")
    if args.stop_policy in ["ATR", "ATR_Trailing"]:
        print(f"ATR Multiplier: {args.atr_multiplier}")
        print(f"ATR Period: {args.atr_period}")
    print(f"Take Profit Policy: {args.take_profit_policy}")
    print(f"Reward-to-Risk Ratio: {args.reward_risk_ratio}")
    print(
        f"Limit trading to specific sessions?: {'Yes' if args.limit_sessions else 'No'}"
    )
    if args.limit_sessions:
        print(f"Sessions: {args.sessions}")
    print(f"Force session close?: {'Yes' if args.force_session_close else 'No'}")
    print(f"Session buffer window (minutes): {args.session_buffer}")
    print(
        f"News event blackout filtering?: {'Yes' if args.news_event_blackout else 'No'}"
    )
    print(f"Force news close?: {'Yes' if args.force_news_close else 'No'}")
    if args.news_event_blackout or args.force_news_close:
        print(f"Minutes before news: {args.minutes_before_news}")
        print(f"Minutes after news: {args.minutes_after_news}")

    print("----------------------------")

    # Placeholder: In a real implementation, this is where the backtest execution logic would go.
    # For now, we simulate successful completion.
    logger.info("Backtest configuration processed successfully.")

    return 0  # Indicate success


# --- Placeholder for Argument Parser Setup ---
# This part would typically be handled by the main cli script that calls this function.
# Example:
# parser = argparse.ArgumentParser(description="Run backtests.")
# # Add arguments here...
# args = parser.parse_args()
# sys.exit(run_backtest_command(args))
