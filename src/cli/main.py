import argparse
import sys
from typing import Optional

from .run_backtest import configure_backtest_parser, run_backtest_command
from .build_dataset import configure_ingest_parser, run_ingest_command
from .scaffold_strategy import configure_scaffold_parser, run_scaffold_command


def main(args: Optional[list[str]] = None) -> int:
    """
    Main entry point for the 'quantpipe' CLI.
    """
    parser = argparse.ArgumentParser(
        description="QuantPipe: Advanced Trading Strategy Backtesting & Analysis Framework"
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Subcommands"
    )

    # -------------------------------------------------------------------------
    # Subcommand: backtest
    # -------------------------------------------------------------------------
    backtest_parser = subparsers.add_parser(
        "backtest",
        help="Run a backtest simulation",
        description="Run a backtest simulation with configurable strategy, data, and risk parameters.",
    )
    configure_backtest_parser(backtest_parser)

    # -------------------------------------------------------------------------
    # Subcommand: ingest
    # -------------------------------------------------------------------------
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Build time series datasets",
        description="Build time series datasets with test/validation splits from raw CSV data.",
    )
    configure_ingest_parser(ingest_parser)

    # -------------------------------------------------------------------------
    # Subcommand: scaffold
    # -------------------------------------------------------------------------
    scaffold_parser = subparsers.add_parser(
        "scaffold",
        help="Create a new strategy from template",
        description="Generate a new strategy directory with boilerplate code.",
    )
    configure_scaffold_parser(scaffold_parser)

    # -------------------------------------------------------------------------
    # Parse & Execute
    # -------------------------------------------------------------------------
    parsed_args = parser.parse_args(args)

    if parsed_args.command == "backtest":
        return run_backtest_command(parsed_args)
    if parsed_args.command == "ingest":
        return run_ingest_command(parsed_args)
    if parsed_args.command == "scaffold":
        return run_scaffold_command(parsed_args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
