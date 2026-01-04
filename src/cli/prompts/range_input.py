"""Interactive range input prompts for parameter sweep configuration.

This module provides Rich-based interactive prompting for collecting
indicator parameter ranges from users during parameter sweep testing.
"""

import logging
from typing import Any

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from src.backtest.sweep import ParameterRange, SweepConfig, parse_range_input
from src.indicators.registry.store import get_registry
from src.strategy.base import Strategy


logger = logging.getLogger(__name__)
console = Console()


def prompt_for_indicator_params(
    indicator_name: str,
    params: dict[str, Any],
) -> list[ParameterRange]:
    """Prompt user for each configurable parameter of an indicator.

    Args:
        indicator_name: Semantic indicator name (e.g., "fast_ema").
        params: Default parameters from indicator registry.

    Returns:
        List of ParameterRange objects for this indicator.
    """
    ranges = []

    console.print(f"\n[bold cyan]--- {indicator_name} ---[/bold cyan]")

    for param_name, default_value in sorted(params.items()):
        # Skip non-numeric parameters (like 'column')
        if not isinstance(default_value, int | float):
            continue

        param_type = type(default_value)
        prompt_text = f"Enter {indicator_name} {param_name} ({default_value})"

        while True:
            try:
                user_input = Prompt.ask(prompt_text, default="")
                values, is_range = parse_range_input(
                    user_input, default_value, param_type
                )
                ranges.append(
                    ParameterRange(
                        indicator_name=indicator_name,
                        param_name=param_name,
                        values=values,
                        is_range=is_range,
                        default=default_value,
                    )
                )
                break
            except ValueError as e:
                console.print(f"[red]Error: {e}[/red]")
                console.print("[dim]Try again or press Enter for default[/dim]")

    return ranges


def collect_all_ranges(strategy: Strategy) -> SweepConfig | None:
    """Collect parameter ranges for all indicators required by a strategy.

    Args:
        strategy: Strategy instance with metadata.

    Returns:
        SweepConfig with all collected ranges, or None if cancelled.
    """
    registry = get_registry()
    metadata = strategy.metadata
    required_indicators = metadata.required_indicators

    console.print(
        "\n[bold green]=== Indicator Parameter Sweep Configuration ===[/bold green]"
    )
    console.print(
        "[dim]Press Enter to accept default, or specify value/range (e.g., '10-30 step 5')[/dim]\n"
    )

    all_ranges: list[ParameterRange] = []

    for indicator_name in required_indicators:
        spec = registry.get(indicator_name)
        if spec is None:
            console.print(
                f"[yellow]Warning: Indicator '{indicator_name}' not found in registry[/yellow]"
            )
            continue

        if not spec.params:
            console.print(f"[dim]{indicator_name}: No configurable parameters[/dim]")
            continue

        indicator_ranges = prompt_for_indicator_params(indicator_name, spec.params)
        all_ranges.extend(indicator_ranges)

    if not all_ranges:
        console.print(
            "[yellow]No configurable parameters found for this strategy[/yellow]"
        )
        return None

    return SweepConfig(
        strategy_name=metadata.name,
        ranges=all_ranges,
    )


def confirm_sweep(config: SweepConfig, valid_count: int, skipped_count: int) -> bool:
    """Prompt user to confirm sweep execution.

    Args:
        config: Sweep configuration.
        valid_count: Number of valid combinations.
        skipped_count: Number of filtered combinations.

    Returns:
        True if user confirms, False otherwise.
    """
    # Calculate total combinations
    total = 1
    for r in config.ranges:
        total *= len(r.values)

    console.print()

    # Show parameter summary table
    table = Table(title="Parameter Sweep Summary")
    table.add_column("Indicator", style="cyan")
    table.add_column("Parameter", style="green")
    table.add_column("Values", style="yellow")

    for r in config.ranges:
        if len(r.values) > 5:
            values_str = f"{r.values[0]} ... {r.values[-1]} ({len(r.values)} values)"
        else:
            values_str = ", ".join(str(v) for v in r.values)
        table.add_row(r.indicator_name, r.param_name, values_str)

    console.print(table)
    console.print()

    console.print(f"[bold]Total combinations:[/bold] {total}")
    if skipped_count > 0:
        console.print(
            f"[yellow]Skipped (constraint violations):[/yellow] {skipped_count}"
        )
    console.print(f"[bold green]Valid combinations to test:[/bold green] {valid_count}")

    # Require confirmation for large sweeps (>500 per FR-018)
    if valid_count > 500:
        console.print(
            "\n[bold yellow]⚠️ Large sweep detected![/bold yellow] "
            "This may take a significant amount of time."
        )

    response = Prompt.ask(
        f"\nProceed with {valid_count} combination(s)?",
        choices=["y", "n"],
        default="y",
    )

    return response.lower() == "y"
