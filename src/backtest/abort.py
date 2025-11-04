"""Abort criteria evaluation for multi-strategy backtesting.

This module provides functions to evaluate global abort conditions during
multi-strategy execution per FR-021:
- Global portfolio drawdown breach
- Unrecoverable system error (data corruption, integrity failure)

Single strategy exceptions do NOT trigger global abort—they halt only that
strategy while others continue.
"""

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class AbortReason(Enum):
    """Enumeration of global abort reasons."""

    GLOBAL_DRAWDOWN_BREACH = "global_drawdown_breach"
    UNRECOVERABLE_ERROR = "unrecoverable_error"
    NO_ABORT = "no_abort"


def evaluate_global_abort(
    current_portfolio_drawdown: float,
    global_drawdown_limit: float | None,
    data_integrity_ok: bool = True,
) -> tuple[bool, AbortReason]:
    """
    Evaluate whether global abort conditions are met.

    Per FR-021, only two conditions trigger global abort:
    1. Global portfolio drawdown exceeds configured threshold
    2. Unrecoverable system error detected (data corruption, etc.)

    Args:
        current_portfolio_drawdown: Current portfolio-level drawdown (0.0-1.0).
        global_drawdown_limit: Configured global drawdown threshold (optional).
        data_integrity_ok: Whether data integrity checks passed.

    Returns:
        Tuple of (should_abort: bool, reason: AbortReason).

    Examples:
        >>> evaluate_global_abort(0.12, 0.10)
        (True, <AbortReason.GLOBAL_DRAWDOWN_BREACH: 'global_drawdown_breach'>)
        >>> evaluate_global_abort(0.08, 0.10)
        (False, <AbortReason.NO_ABORT: 'no_abort'>)
        >>> evaluate_global_abort(0.05, None)
        (False, <AbortReason.NO_ABORT: 'no_abort'>)
        >>> evaluate_global_abort(0.05, 0.10, data_integrity_ok=False)
        (True, <AbortReason.UNRECOVERABLE_ERROR: 'unrecoverable_error'>)
    """
    # Check data integrity (unrecoverable error condition)
    if not data_integrity_ok:
        logger.error("Global abort triggered: unrecoverable data integrity failure")
        return (True, AbortReason.UNRECOVERABLE_ERROR)

    # Check global drawdown limit (if configured)
    if global_drawdown_limit is not None:
        if current_portfolio_drawdown > global_drawdown_limit:
            logger.warning(
                "Global abort triggered: portfolio drawdown %.4f exceeds limit %.4f",
                current_portfolio_drawdown,
                global_drawdown_limit,
            )
            return (True, AbortReason.GLOBAL_DRAWDOWN_BREACH)

    # No abort conditions met
    return (False, AbortReason.NO_ABORT)


def should_halt_strategy(
    strategy_name: str,
    current_drawdown: float,
    per_strategy_limit: float,
) -> bool:
    """
    Evaluate whether a single strategy should halt due to local risk breach.

    This does NOT trigger global abort—only halts the individual strategy
    per FR-021 (local breaches are isolated).

    Args:
        strategy_name: Name of the strategy being evaluated.
        current_drawdown: Current drawdown for this strategy (0.0-1.0).
        per_strategy_limit: Per-strategy drawdown limit.

    Returns:
        True if strategy should halt, False otherwise.

    Examples:
        >>> should_halt_strategy("alpha", 0.12, 0.10)
        True
        >>> should_halt_strategy("beta", 0.08, 0.10)
        False
    """
    if current_drawdown > per_strategy_limit:
        logger.warning(
            "Strategy halt: name=%s drawdown=%.4f exceeds limit=%.4f",
            strategy_name,
            current_drawdown,
            per_strategy_limit,
        )
        return True
    return False


__all__ = ["evaluate_global_abort", "should_halt_strategy", "AbortReason"]
