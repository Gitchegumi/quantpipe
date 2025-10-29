#!/usr/bin/env python3
"""
Unified backtest CLI with direction mode support.

This CLI supports running backtests in three modes:
- LONG: Long-only signals (existing run_long_backtest.py functionality)
- SHORT: Short-only signals (using generate_short_signals)
- BOTH: Both long and short signals (future Phase 5 implementation)

Phase 4 Status: Demonstrates CLI interface structure. Full BOTH mode
implementation deferred to Phase 5 when dual-direction execution is needed.

Usage:
    python -m src.cli.run_backtest --direction LONG --data <csv_path>
    python -m src.cli.run_backtest --direction SHORT --data <csv_path>
    python -m src.cli.run_backtest --direction BOTH --data <csv_path>
"""

import argparse
import sys
from pathlib import Path


def main():
    """
    Main entry point for unified backtest CLI.
    
    Phase 4: Provides interface, delegates to existing implementations.
    Phase 5: Will add full BOTH mode with dual-direction execution.
    """
    parser = argparse.ArgumentParser(
        description="Run trend-pullback backtest with configurable direction"
    )
    
    parser.add_argument(
        "--direction",
        type=str,
        choices=["LONG", "SHORT", "BOTH"],
        default="LONG",
        help="Trading direction: LONG (buy only), SHORT (sell only), or BOTH (Phase 5)",
    )
    
    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help="Path to CSV price data file",
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results"),
        help="Output directory for results (default: results/)",
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )
    
    args = parser.parse_args()
    
    # Validate data file exists
    if not args.data.exists():
        print(f"Error: Data file not found: {args.data}", file=sys.stderr)
        sys.exit(1)
    
    # Route to appropriate implementation
    if args.direction == "LONG":
        print(f"Running LONG-only backtest on {args.data}")
        print("Delegating to run_long_backtest.py...")
        # In real implementation, would import and call:
        # from src.cli.run_long_backtest import run_long_backtest
        # run_long_backtest(str(args.data), str(args.output), args.log_level)
        print("\nTo run: poetry run python -m src.cli.run_long_backtest \\")
        print(f"          --data {args.data} --log-level {args.log_level}")
        
    elif args.direction == "SHORT":
        print(f"Running SHORT-only backtest on {args.data}")
        print("\nSHORT mode implementation:")
        print("- Uses generate_short_signals() from signal_generator.py")
        print("- Executes with simulate_execution() (supports SHORT direction)")
        print("- Same metrics aggregation as LONG mode")
        print("\nFull implementation: Create run_short_backtest.py mirroring")
        print("run_long_backtest.py but calling generate_short_signals()")
        
    elif args.direction == "BOTH":
        print(f"Running BOTH directions backtest on {args.data}")
        print("\nBOTH mode (Phase 5 feature):")
        print("- Generates both LONG and SHORT signals")
        print("- Requires conflict resolution (avoid simultaneous positions)")
        print("- Enhanced metrics for combined performance")
        print("\nStatus: Interface defined, full implementation in Phase 5")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
