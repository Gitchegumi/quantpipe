"""Per-strategy state isolation for multi-strategy execution.

This module provides isolated state containers that prevent cross-contamination
between strategies during concurrent multi-strategy backtesting (FR-003).

Each StrategyState holds:
- Execution history (signals, fills)
- Running metrics (PnL, drawdown)
- Risk breach status
- Halt flag (local breach only)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class StrategyState:
    """
    Isolated state container for a single strategy instance.

    Prevents cross-contamination during multi-strategy execution per FR-003.
    Each strategy maintains independent execution history, metrics, and risk status.

    Attributes:
        strategy_name: Unique identifier matching registry entry.
        signals_generated: Count of signals generated.
        positions_opened: Count of positions entered.
        positions_closed: Count of positions exited.
        running_pnl: Cumulative profit/loss in base currency.
        peak_equity: Maximum equity reached (for drawdown calc).
        current_drawdown: Current drawdown from peak (0.0-1.0).
        max_drawdown: Maximum drawdown observed (0.0-1.0).
        is_halted: True if strategy halted due to local risk breach.
        halt_reason: Optional reason for halt.
        last_update: Timestamp of last state update.
        risk_breach_events: List of risk breach timestamps.

    Examples:
        >>> state = StrategyState(strategy_name="alpha")
        >>> state.running_pnl
        0.0
        >>> state.is_halted
        False
    """

    strategy_name: str
    signals_generated: int = 0
    positions_opened: int = 0
    positions_closed: int = 0
    running_pnl: float = 0.0
    peak_equity: float = 0.0
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    is_halted: bool = False
    halt_reason: str | None = None
    last_update: datetime | None = None
    risk_breach_events: list[datetime] = field(default_factory=list)

    def update_pnl(self, pnl_delta: float, timestamp: datetime) -> None:
        """
        Update running PnL and recalculate drawdown.

        Args:
            pnl_delta: Change in PnL (can be negative).
            timestamp: Timestamp of this update.
        """
        self.running_pnl += pnl_delta
        self.last_update = timestamp

        # Update peak and drawdown
        if self.running_pnl > self.peak_equity:
            self.peak_equity = self.running_pnl
            self.current_drawdown = 0.0
        elif self.peak_equity > 0:
            self.current_drawdown = (
                self.peak_equity - self.running_pnl
            ) / self.peak_equity

        if self.current_drawdown > self.max_drawdown:
            self.max_drawdown = self.current_drawdown

        logger.debug(
            "Strategy PnL updated: name=%s pnl=%.4f drawdown=%.4f",
            self.strategy_name,
            self.running_pnl,
            self.current_drawdown,
        )

    def record_signal(self) -> None:
        """Increment signal generation counter."""
        self.signals_generated += 1

    def record_position_opened(self) -> None:
        """Increment position opened counter."""
        self.positions_opened += 1

    def record_position_closed(self, pnl: float, timestamp: datetime) -> None:
        """
        Record position close and update metrics.

        Args:
            pnl: Realized PnL from this position.
            timestamp: Close timestamp.
        """
        self.positions_closed += 1
        self.update_pnl(pnl, timestamp)

    def halt(self, reason: str, timestamp: datetime) -> None:
        """
        Halt strategy due to risk breach.

        Args:
            reason: Human-readable reason for halt.
            timestamp: Timestamp when halt triggered.
        """
        self.is_halted = True
        self.halt_reason = reason
        self.last_update = timestamp
        self.risk_breach_events.append(timestamp)
        logger.warning(
            "Strategy halted: name=%s reason=%s",
            self.strategy_name,
            reason,
        )


class StateIsolationManager:
    """
    Manages isolated state containers for all active strategies.

    Provides factory methods to create and retrieve strategy-specific state.
    Ensures no cross-contamination between strategies (FR-003).

    Examples:
        >>> manager = StateIsolationManager()
        >>> state = manager.get_or_create("alpha")
        >>> state.strategy_name
        'alpha'
        >>> manager.get_or_create("alpha") is state
        True
    """

    def __init__(self):
        """Initialize empty state isolation manager."""
        self._states: dict[str, StrategyState] = {}
        logger.info("Initialized StateIsolationManager")

    def get_or_create(self, strategy_name: str) -> StrategyState:
        """
        Get existing state or create new isolated state for strategy.

        Args:
            strategy_name: Unique strategy identifier.

        Returns:
            StrategyState instance for this strategy.
        """
        if strategy_name not in self._states:
            self._states[strategy_name] = StrategyState(
                strategy_name=strategy_name
            )
            logger.debug("Created isolated state for strategy=%s", strategy_name)
        return self._states[strategy_name]

    def get_all_states(self) -> dict[str, StrategyState]:
        """
        Retrieve all strategy states.

        Returns:
            Dictionary mapping strategy name to StrategyState.
        """
        return self._states.copy()

    def reset(self) -> None:
        """Clear all strategy states (for testing)."""
        count = len(self._states)
        self._states.clear()
        logger.info("Reset StateIsolationManager: cleared %d states", count)


__all__ = ["StrategyState", "StateIsolationManager"]
