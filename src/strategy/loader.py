"""
Dynamic loader for private/proprietary strategies.
"""

import importlib.util
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .registry import StrategyRegistry

logger = logging.getLogger(__name__)


def load_private_strategies(
    registry: "StrategyRegistry", private_dir: str = "private_strategies"
):
    """
    Scan the private_strategies directory and register any found strategies.

    Expected structure:
    private_strategies/
        my_secret_strat/
            __init__.py
            strategy.py (must contain a class inheriting from Strategy or
                        a 'run' function)
    """
    workspace_root = Path.cwd()
    private_path = workspace_root / private_dir

    if not private_path.exists():
        logger.info(
            "Private strategies directory not found at %s. Skipping.", private_path
        )
    else:
        _scan_and_register(
            registry, private_path, is_private=True, prefix="private_strategies"
        )

    # Also scan src/strategy for public strategies
    public_path = workspace_root / "src" / "strategy"
    if public_path.exists():
        _scan_and_register(
            registry, public_path, is_private=False, prefix="src.strategy"
        )


def _scan_and_register(
    registry: "StrategyRegistry",
    path: Path,
    is_private: bool = False,
    prefix: str = "private_strategies",
):
    """Helper to scan a directory and register strategies."""
    logger.info("Scanning for strategies in %s", path)

    # Framework files to exclude from scanning
    excluded_files = {
        "base.py",
        "config_override.py",
        "id_factory.py",
        "indicator_registry.py",
        "loader.py",
        "registry.py",
        "validator.py",
        "weights.py",
        "__init__.py",
    }

    seen_strategies = set()

    # Iterate through items in path
    for item in path.iterdir():
        if item.name.startswith("__") or item.name in excluded_files:
            continue

        strat_file = None
        strat_name = None

        if item.is_dir():
            strat_file = item / "strategy.py"
            strat_name = item.name
        elif item.suffix == ".py":
            strat_file = item
            strat_name = item.stem

        if strat_file and strat_file.exists():
            if strat_name in seen_strategies:
                continue
            seen_strategies.add(strat_name)

            try:
                # Dynamic import
                module_name = f"{prefix}.{strat_name}"
                spec = importlib.util.spec_from_file_location(
                    module_name, str(strat_file)
                )
                if spec is None or spec.loader is None:
                    logger.warning("Could not load spec for %s", strat_name)
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Look for strategy instance or class
                # By convention, we look for a 'STRATEGY' instance or a 'run' function
                # Look for strategy instance or class
                # By convention, we look for a 'STRATEGY' instance or a 'run' function
                strategy = getattr(module, "STRATEGY", None)

                # If not found, look for variables ending in _STRATEGY (e.g. SIMPLE_MOMENTUM_STRATEGY)
                if strategy is None:
                    for var_name, var_val in vars(module).items():
                        if var_name.endswith("_STRATEGY") and hasattr(
                            var_val, "metadata"
                        ):
                            strategy = var_val
                            break

                if strategy:
                    # Safely get metadata
                    metadata = getattr(strategy, "metadata", None)
                    tags = ["private"] if is_private else ["public"]
                    version = "0.0.0"

                    if metadata:
                        tags = getattr(metadata, "tags", tags)
                        version = getattr(metadata, "version", version)

                    registry.register(
                        name=strat_name,
                        func=getattr(strategy, "generate_signals", None)
                        or getattr(module, "run"),
                        tags=tags,
                        version=version,
                    )
                    logger.info("Successfully registered strategy: %s", strat_name)
                elif hasattr(module, "run"):
                    registry.register(
                        name=strat_name,
                        func=getattr(module, "run"),
                        tags=(
                            ["private", "legacy"]
                            if is_private
                            else ["public", "legacy"]
                        ),
                        version="0.0.0",
                    )
                    logger.info(
                        "Successfully registered legacy strategy: %s", strat_name
                    )

            except Exception as e:
                logger.error("Failed to load strategy %s: %s", strat_name, e)
