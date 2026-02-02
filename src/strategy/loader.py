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

def load_private_strategies(registry: 'StrategyRegistry', private_dir: str = "private_strategies"):
    """
    Scan the private_strategies directory and register any found strategies.
    
    Expected structure:
    private_strategies/
        my_secret_strat/
            __init__.py
            strategy.py (must contain a class inheriting from Strategy or a 'run' function)
    """
    workspace_root = Path.cwd()
    private_path = workspace_root / private_dir
    
    if not private_path.exists():
        logger.info("Private strategies directory not found at %s. Skipping.", private_path)
        return

    logger.info("Scanning for private strategies in %s", private_path)
    
    # Iterate through items in private_strategies
    for item in private_path.iterdir():
        if item.name.startswith("__"):
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
            try:
                # Dynamic import
                spec = importlib.util.spec_from_file_location(
                    f"private_strategies.{strat_name}", 
                    strat_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Look for strategy instance or class
                # By convention, we look for a 'STRATEGY' instance or a 'run' function
                if hasattr(module, "STRATEGY"):
                    strategy = getattr(module, "STRATEGY")
                    registry.register(
                        name=strat_name,
                        func=getattr(strategy, "generate_signals", None) or getattr(module, "run"),
                        tags=getattr(strategy.metadata, "tags", ["private"]),
                        version=getattr(strategy.metadata, "version", "0.0.0")
                    )
                    logger.info("Successfully registered private strategy: %s", strat_name)
                elif hasattr(module, "run"):
                    registry.register(
                        name=strat_name,
                        func=getattr(module, "run"),
                        tags=["private", "legacy"],
                        version="0.0.0"
                    )
                    logger.info("Successfully registered legacy private strategy: %s", strat_name)
                    
            except Exception as e:
                logger.error("Failed to load private strategy %s: %s", strat_name, e)
