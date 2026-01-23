import argparse
import sys
from typing import Optional

from .run_backtest import configure_backtest_parser, run_backtest_command


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
    # Parse & Execute
    # -------------------------------------------------------------------------
    parsed_args = parser.parse_args(args)

    if parsed_args.command == "backtest":
        return run_backtest_command(parsed_args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
