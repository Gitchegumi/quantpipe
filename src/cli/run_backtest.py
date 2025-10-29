#!/usr/bin/env python3
"""
Unified backtest CLI with direction mode support and JSON output.

This CLI supports running backtests in three modes:
- LONG: Long-only signals (existing run_long_backtest.py functionality)
- SHORT: Short-only signals (using generate_short_signals)
- BOTH: Both long and short signals (future Phase 5 implementation)

Output Formats:
- text: Human-readable console output (default)
- json: Machine-readable JSON format for programmatic processing

Phase 4 Status: Demonstrates CLI interface structure. Full BOTH mode
implementation deferred to Phase 5 when dual-direction execution is needed.

Usage:
    python -m src.cli.run_backtest --direction LONG --data <csv_path>
    python -m src.cli.run_backtest --direction SHORT --data <csv_path>
    python -m src.cli.run_backtest --direction BOTH --data <csv_path>
    python -m src.cli.run_backtest --direction LONG --data <csv_path> --output-format json
"""

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from ..models.core import BacktestRun, MetricsSummary


def format_backtest_results_as_json(
    run_metadata: BacktestRun,
    metrics: MetricsSummary,
    additional_context: Dict[str, Any] = None,
) -> str:
    """
    Format backtest results as JSON string.

    Args:
        run_metadata: BacktestRun metadata object.
        metrics: MetricsSummary with performance statistics.
        additional_context: Optional dict with extra fields to include.

    Returns:
        JSON-formatted string with complete backtest results.

    Examples:
        >>> from datetime import datetime, timezone
        >>> from models.core import BacktestRun, MetricsSummary
        >>> import math
        >>> run = BacktestRun(
        ...     run_id="test_run",
        ...     parameters_hash="abc123",
        ...     manifest_ref="/data/test.csv",
        ...     start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ...     end_time=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        ...     total_candles_processed=1000,
        ...     reproducibility_hash="xyz789"
        ... )
        >>> metrics = MetricsSummary(
        ...     trade_count=10,
        ...     win_count=6,
        ...     loss_count=4,
        ...     win_rate=0.6,
        ...     avg_win_r=2.0,
        ...     avg_loss_r=1.0,
        ...     avg_r=0.8,
        ...     expectancy=0.8,
        ...     sharpe_estimate=1.2,
        ...     profit_factor=3.0,
        ...     max_drawdown_r=2.5,
        ...     latency_p95_ms=math.nan,
        ...     latency_mean_ms=math.nan
        ... )
        >>> json_output = format_backtest_results_as_json(run, metrics)
        >>> "run_id" in json_output
        True
    """
    # Convert dataclasses to dicts
    result = {
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
            "win_rate": metrics.win_rate,
            "avg_win_r": metrics.avg_win_r,
            "avg_loss_r": metrics.avg_loss_r,
            "avg_r": metrics.avg_r,
            "expectancy": metrics.expectancy,
            "sharpe_estimate": metrics.sharpe_estimate,
            "profit_factor": metrics.profit_factor,
            "max_drawdown_r": metrics.max_drawdown_r,
            "latency_p95_ms": metrics.latency_p95_ms,
            "latency_mean_ms": metrics.latency_mean_ms,
        },
    }

    if additional_context:
        result["additional_context"] = additional_context

    return json.dumps(result, indent=2, default=str)


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

    # Validate data file exists
    if not args.data.exists():
        print(f"Error: Data file not found: {args.data}", file=sys.stderr)
        sys.exit(1)

    # Determine output mode
    is_json_output = args.output_format == "json"

    # Route to appropriate implementation
    if args.direction == "LONG":
        if is_json_output:
            # Create sample JSON output structure (placeholder for real implementation)
            run_metadata = BacktestRun(
                run_id=f"long_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                parameters_hash="placeholder_hash",
                manifest_ref=str(args.data),
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                total_candles_processed=0,
                reproducibility_hash="placeholder_repro_hash",
            )
            # This would come from actual backtest execution
            import math
            metrics = MetricsSummary(
                trade_count=0,
                win_count=0,
                loss_count=0,
                win_rate=math.nan,
                avg_win_r=math.nan,
                avg_loss_r=math.nan,
                avg_r=math.nan,
                expectancy=math.nan,
                sharpe_estimate=math.nan,
                profit_factor=math.nan,
                max_drawdown_r=math.nan,
                latency_p95_ms=math.nan,
                latency_mean_ms=math.nan,
            )
            json_output = format_backtest_results_as_json(
                run_metadata,
                metrics,
                additional_context={"direction": "LONG", "status": "placeholder"},
            )
            print(json_output)
        else:
            print(f"Running LONG-only backtest on {args.data}")
            print("Delegating to run_long_backtest.py...")
            print("\nTo run: poetry run python -m src.cli.run_long_backtest \\")
            print(f"          --data {args.data} --log-level {args.log_level}")

    elif args.direction == "SHORT":
        if is_json_output:
            print(
                json.dumps(
                    {
                        "error": "SHORT mode JSON output not yet implemented",
                        "direction": "SHORT",
                        "status": "Phase 4 interface defined",
                    },
                    indent=2,
                )
            )
        else:
            print(f"Running SHORT-only backtest on {args.data}")
            print("\nSHORT mode implementation:")
            print("- Uses generate_short_signals() from signal_generator.py")
            print("- Executes with simulate_execution() (supports SHORT direction)")
            print("- Same metrics aggregation as LONG mode")
            print("\nFull implementation: Create run_short_backtest.py mirroring")
            print("run_long_backtest.py but calling generate_short_signals()")

    elif args.direction == "BOTH":
        if is_json_output:
            print(
                json.dumps(
                    {
                        "error": "BOTH mode not yet implemented",
                        "direction": "BOTH",
                        "status": "Phase 5 feature",
                    },
                    indent=2,
                )
            )
        else:
            print(f"Running BOTH directions backtest on {args.data}")
            print("\nBOTH mode (Phase 5 feature):")
            print("- Generates both LONG and SHORT signals")
            print("- Requires conflict resolution (avoid simultaneous positions)")
            print("- Enhanced metrics for combined performance")
            print("\nStatus: Interface defined, full implementation in Phase 5")

    return 0


if __name__ == "__main__":
    sys.exit(main())
