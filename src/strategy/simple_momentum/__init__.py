"""Simple momentum strategy module.

This module exports the SimpleMomentumStrategy as a reference implementation
demonstrating the Strategy Protocol pattern. Use this as a template for
creating your own strategies.

Example:
    from src.strategy.simple_momentum import SIMPLE_MOMENTUM_STRATEGY

    # Use the global instance for backtesting
    signals = SIMPLE_MOMENTUM_STRATEGY.generate_signals(candles, parameters)

    # Or import the class to create custom instances
    from src.strategy.simple_momentum import SimpleMomentumStrategy
    strategy = SimpleMomentumStrategy()
"""

from src.strategy.simple_momentum.strategy import (
    SimpleMomentumStrategy,
    SIMPLE_MOMENTUM_STRATEGY,
)


__all__ = ["SimpleMomentumStrategy", "SIMPLE_MOMENTUM_STRATEGY"]
