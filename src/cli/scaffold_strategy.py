"""CLI command for scaffolding new trading strategies.

This module provides a command-line interface for generating new
strategy directories from templates.

Usage:
    poetry run python -m src.cli.scaffold_strategy <name> [options]

Arguments:
    name: Strategy name (valid Python identifier)

Options:
    --output: Output directory (default: src/strategy/<name>/)
    --description: Strategy description
    --tags: Comma-separated list of tags
    --register: Auto-register strategy after creation (default: True)

Example:
    poetry run python -m src.cli.scaffold_strategy my_momentum --tags trend,momentum

Exit codes:
    0: Success
    1: Invalid strategy name
    2: Directory already exists
    3: Template rendering error
"""

import argparse
import sys
from pathlib import Path

from src.strategy.scaffold.generator import ScaffoldGenerator


def main() -> int:
    """Main entry point for scaffold command.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = argparse.ArgumentParser(
        description="Scaffold a new trading strategy from template.",
        prog="python -m src.cli.scaffold_strategy",
    )
    parser.add_argument(
        "name",
        type=str,
        help="Strategy name (valid Python identifier, e.g., my_strategy)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory (default: src/strategy/<name>/)",
    )
    parser.add_argument(
        "--description",
        type=str,
        default="",
        help="Strategy description",
    )
    parser.add_argument(
        "--tags",
        type=str,
        default="",
        help="Comma-separated list of tags (e.g., trend,momentum)",
    )
    parser.add_argument(
        "--no-register",
        action="store_true",
        help="Skip auto-registration in strategy registry",
    )

    args = parser.parse_args()

    # Parse tags
    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []

    # Generate strategy
    generator = ScaffoldGenerator()
    result = generator.generate(
        name=args.name,
        output_dir=args.output,
        description=args.description,
        tags=tags,
    )

    if not result.success:
        print(f"Error: {result.error}", file=sys.stderr)
        if "Invalid strategy name" in (result.error or ""):
            return 1
        if "already exists" in (result.error or ""):
            return 2
        return 3

    print(f"✓ Strategy '{args.name}' created successfully!")
    print(f"  Directory: {result.strategy_dir}")
    print("  Files created:")
    for file_path in result.created_files:
        print(f"    - {file_path.name}")

    # Auto-register if requested (default behavior)
    if not args.no_register:
        _print_registration_instructions(args.name)

    print("\nNext steps:")
    print("  1. Edit strategy.py to implement your signal logic")
    print("  2. Update required_indicators in metadata")
    print("  3. Run a backtest to test your strategy")
    print(f"\n  poetry run python -m src.cli.run_backtest --strategy {args.name}")

    return 0


def _print_registration_instructions(name: str) -> None:
    """Print instructions for registering the strategy."""
    print("\n  To use in backtest, import and register your strategy:")
    print(f"    from src.strategy.{name} import {name.upper()}_STRATEGY")


if __name__ == "__main__":
    sys.exit(main())
