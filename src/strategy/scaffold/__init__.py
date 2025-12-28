"""Strategy scaffold module for generating new strategy templates.

This module provides utilities to scaffold new trading strategies
using Jinja2 templates, enabling users to quickly create new strategies
that conform to the Strategy Protocol.

Example:
    from src.strategy.scaffold import ScaffoldGenerator

    generator = ScaffoldGenerator()
    generator.generate("my_strategy")  # Creates src/strategy/my_strategy/
"""

from src.strategy.scaffold.generator import ScaffoldGenerator


__all__ = ["ScaffoldGenerator"]
