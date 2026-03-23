"""CLI command for building time series datasets with test/validation splits.

Feature: 004-timeseries-dataset
Tasks: T016, T017
"""

# pylint: disable=line-too-long f-string-without-interpolation broad-exception-caught

import argparse
import json
import logging
import re
import sys
from pathlib import Path

import questionary
from rich.console import Console
from rich.table import Table

from ..data_io.dataset_builder import build_symbol_dataset, build_all_symbols, discover_symbols

logger = logging.getLogger(__name__)
console = Console()


def _is_interactive() -> bool:
    """Check if the current session is interactive (attached to a TTY)."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def _prompt(msg: str, default=None, coerce=str, choices=None):
    """Interactive prompt using questionary."""
    default_match = re.search(r"\[([^\]]+)\]", msg)
    if default is None and default_match:
        default = default_match.group(1)
    message = re.sub(r"\s*\[[^\]]+\]\s*:?\s*$", "", msg).strip()
    message = message.lstrip("? ").strip()

    if choices:
        cleaned_choices = [str(c) for c in choices if isinstance(c, (str, int, float))]
        default_choice_str = str(default) if default is not None else None
        try:
            choice = questionary.select(
                message,
                choices=cleaned_choices,
                default=default_choice_str if default_choice_str in cleaned_choices else None,
                use_shortcuts=True,
                qmark="?",
            ).ask()
            if choice is None:
                print("\nOperation cancelled.")
                sys.exit(1)
            return coerce(choice)
        except Exception as e:
            print(f"\nError during selection prompt: {e}")
            if default is not None:
                try:
                    val = coerce(default)
                    print(f"Falling back to default: {default}")
                    return val
                except ValueError:
                    pass
            print("Please enter value manually:")
            return coerce(input(f"{message} "))
    else:
        try:
            text_input = questionary.text(
                message,
                default=str(default) if default is not None else "",
                validate=lambda x: coerce(x) is not None if x else True,
                qmark="?",
            ).ask()
            if text_input is None:
                print("\nOperation cancelled.")
                sys.exit(1)
            if text_input == "" and default is not None:
                return coerce(default)
            return coerce(text_input)
        except Exception as e:
            print(f"\nError during text prompt: {e}")
            return coerce(default) if default is not None else None


def _multi_select_prompt(msg: str, default=None, coerce=str, choices=None):
    """Interactive multi-select prompt using questionary.checkbox."""
    message = msg.replace("? ", "").strip()
    if choices:
        string_choices = [str(c) for c in choices if isinstance(c, (str, int, float))]
        try:
            selected = questionary.checkbox(
                message,
                choices=string_choices,
            ).ask()
            if selected is None:
                print("\nOperation cancelled.")
                sys.exit(1)
            return [coerce(c) for c in selected]
        except Exception as e:
            print(f"\nError during multi-select prompt: {e}")
            if default:
                print(f"Falling back to default: {default}")
                return [coerce(c) for c in default]
            return []
    return []


def configure_ingest_parser(parser: argparse.ArgumentParser) -> None:
    """Configure the argument parser for the 'ingest' command."""
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
        "--save-to-vault",
        action="store_true",
        default=True,
        help="Save processed data to DuckDB vault (default: True)",
    )

    parser.add_argument(
        "--no-vault",
        action="store_false",
        dest="save_to_vault",
        help="Disable saving to DuckDB vault",
    )

    parser.add_argument(
        "--vault-path",
        type=str,
        default="data/vault.duckdb",
        help="Path to DuckDB vault file (default: data/vault.duckdb)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )


def run_ingest_command(args: argparse.Namespace) -> int:
    """Execute the 'ingest' command."""
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Verify raw path exists (early)
    raw_path = Path(args.raw_path)
    if not raw_path.exists():
        console.print(
            f"[red]Error: Raw data path does not exist: {args.raw_path}[/red]"
        )
        return 1

    # Interactive prompt for symbol selection if neither --symbol nor --all provided
    if not args.symbol and not args.all:
        is_interactive = _is_interactive()
        if not is_interactive:
            console.print("[red]Error: Must specify either --symbol or --all[/red]")
            return 1
        else:
            # Discover available symbols from raw directory
            available_symbols = discover_symbols(str(raw_path))
            if not available_symbols:
                console.print("[red]No symbols found in raw data directory.[/red]")
                return 1

            # Present choices: list symbols + "All symbols"
            choices = available_symbols + ["All symbols"]
            selected = _multi_select_prompt(
                "? Select symbols to process (space to select, Enter to confirm) ",
                default=[],
                choices=choices,
            )
            if not selected:
                console.print("[yellow]No selection made. Exiting.[/yellow]")
                return 0
            if "All symbols" in selected:
                args.all = True
            else:
                args.symbol = selected

    # Validate mutually exclusive flags after potential interactive filling
    if args.symbol and args.all:
        console.print("[red]Error: Cannot specify both --symbol and --all[/red]")
        return 1

    try:
        if args.symbol:
            # Single symbol build
            console.print(
                f"\n[cyan]Building dataset for symbol: {args.symbol}[/cyan]\n"
            )
            result = build_symbol_dataset(
                args.symbol,
                args.raw_path,
                args.output_path,
                save_to_vault=args.save_to_vault,
                vault_path=args.vault_path
            )

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

            summary = build_all_symbols(
                args.raw_path,
                args.output_path,
                args.force,
                save_to_vault=args.save_to_vault,
                vault_path=args.vault_path
            )

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

    configure_ingest_parser(parser)
    args = parser.parse_args()
    return run_ingest_command(args)


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
