"""CLI command for building time series datasets with test/validation splits.

Feature: 004-timeseries-dataset
Tasks: T016, T017
"""

import argparse
import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from ..io.dataset_builder import build_symbol_dataset, build_all_symbols

logger = logging.getLogger(__name__)
console = Console()


def main() -> int:
    """Build dataset CLI entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Build time series datasets with test/validation splits",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build dataset for a specific symbol
  poetry run python -m src.cli.build_dataset --symbol eurusd

  # Build datasets for all symbols
  poetry run python -m src.cli.build_dataset --all

  # Force rebuild even if output exists
  poetry run python -m src.cli.build_dataset --all --force

  # Specify custom paths
  poetry run python -m src.cli.build_dataset --symbol eurusd \\
    --raw-path custom/raw --output-path custom/processed
        """,
    )

    parser.add_argument(
        "--symbol",
        type=str,
        help="Build dataset for specific symbol (e.g., eurusd)",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Build datasets for all discovered symbols",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild even if processed output exists (future enhancement)",
    )

    parser.add_argument(
        "--raw-path",
        type=str,
        default="price_data/raw",
        help="Path to raw data directory (default: price_data/raw)",
    )

    parser.add_argument(
        "--output-path",
        type=str,
        default="price_data/processed",
        help="Path to processed output directory (default: price_data/processed)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Validate arguments
    if not args.symbol and not args.all:
        console.print("[red]Error: Must specify either --symbol or --all[/red]")
        parser.print_help()
        return 1

    if args.symbol and args.all:
        console.print("[red]Error: Cannot specify both --symbol and --all[/red]")
        return 1

    # Verify raw path exists
    raw_path = Path(args.raw_path)
    if not raw_path.exists():
        console.print(
            f"[red]Error: Raw data path does not exist: {args.raw_path}[/red]"
        )
        return 1

    try:
        if args.symbol:
            # Single symbol build
            console.print(
                f"\n[cyan]Building dataset for symbol: {args.symbol}[/cyan]\n"
            )
            result = build_symbol_dataset(args.symbol, args.raw_path, args.output_path)

            if result["success"]:
                metadata = result["metadata"]
                _display_symbol_result(args.symbol, metadata)
                console.print("\n[green]✓ Dataset build successful[/green]")
                return 0
            else:
                console.print(f"\n[red]✗ Build failed for {args.symbol}[/red]")
                console.print(f"Reason: {result['skip_reason']}")
                console.print(f"Details: {result['error']}")
                return 1

        else:
            # Multi-symbol build
            console.print(f"\n[cyan]Building datasets for all symbols[/cyan]")
            console.print(f"Raw path: {args.raw_path}")
            console.print(f"Output path: {args.output_path}\n")

            summary = build_all_symbols(args.raw_path, args.output_path, args.force)

            _display_build_summary(summary)

            if summary.symbols_skipped:
                console.print(
                    f"\n[yellow]⚠ {len(summary.symbols_skipped)} symbol(s) skipped[/yellow]"
                )
                return 0  # Still exit 0 if some succeeded
            else:
                console.print("\n[green]✓ All symbols processed successfully[/green]")
                return 0

    except Exception as e:
        console.print(f"\n[red]✗ Unexpected error: {e}[/red]")
        logger.error("Build failed with exception", exc_info=True)
        return 1


def _display_symbol_result(symbol: str, metadata) -> None:
    """Display single symbol build results in a table.

    Args:
        symbol: Symbol identifier
        metadata: MetadataRecord instance
    """
    table = Table(title=f"Dataset: {symbol}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Rows", f"{metadata.total_rows:,}")
    table.add_row(
        "Test Rows",
        f"{metadata.test_rows:,} ({metadata.test_rows/metadata.total_rows*100:.1f}%)",
    )
    table.add_row(
        "Validation Rows",
        f"{metadata.validation_rows:,} ({metadata.validation_rows/metadata.total_rows*100:.1f}%)",
    )
    table.add_row("Time Span", f"{metadata.start_timestamp} → {metadata.end_timestamp}")
    table.add_row("Validation Start", str(metadata.validation_start_timestamp))
    table.add_row("Gap Count", str(metadata.gap_count))
    table.add_row("Overlap Count", str(metadata.overlap_count))
    table.add_row("Source Files", str(len(metadata.source_files)))

    console.print(table)


def _display_build_summary(summary) -> None:
    """Display multi-symbol build summary.

    Args:
        summary: BuildSummary instance
    """
    # Overall stats
    stats_table = Table(title="Build Summary")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="green")

    stats_table.add_row("Duration", f"{summary.duration_seconds:.2f} seconds")
    stats_table.add_row("Symbols Processed", str(len(summary.symbols_processed)))
    stats_table.add_row("Symbols Skipped", str(len(summary.symbols_skipped)))
    stats_table.add_row("Total Rows", f"{summary.total_rows_processed:,}")
    stats_table.add_row("Test Rows", f"{summary.total_test_rows:,}")
    stats_table.add_row("Validation Rows", f"{summary.total_validation_rows:,}")

    console.print(stats_table)

    # Processed symbols
    if summary.symbols_processed:
        console.print("\n[green]Processed Symbols:[/green]")
        for symbol in summary.symbols_processed:
            console.print(f"  ✓ {symbol}")

    # Skipped symbols
    if summary.symbols_skipped:
        skip_table = Table(title="Skipped Symbols")
        skip_table.add_column("Symbol", style="yellow")
        skip_table.add_column("Reason", style="red")
        skip_table.add_column("Details")

        for skipped in summary.symbols_skipped:
            skip_table.add_row(skipped.symbol, skipped.reason.value, skipped.details)

        console.print("\n")
        console.print(skip_table)


if __name__ == "__main__":
    sys.exit(main())
