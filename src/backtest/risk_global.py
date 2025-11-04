"""Global portfolio-level risk evaluation for multi-strategy execution.

This module evaluates portfolio-wide risk conditions including:
- Global drawdown threshold monitoring
- Portfolio-level risk breach detection

Per FR-015, global risk limits are optional and distinct from per-strategy limits.
"""

import logging

logger = logging.getLogger(__name__)


def evaluate_portfolio_drawdown(
    current_portfolio_pnl: float,
    peak_portfolio_pnl: float,
    global_drawdown_limit: float | None,
) -> tuple[float, bool]:
    """
    Evaluate current portfolio drawdown and check against global limit.

    Args:
        current_portfolio_pnl: Current aggregated portfolio PnL.
        peak_portfolio_pnl: Peak aggregated portfolio PnL observed.
        global_drawdown_limit: Optional global drawdown threshold (0.0-1.0).

    Returns:
        Tuple of (current_drawdown_pct, is_breach).
        - current_drawdown_pct: Portfolio drawdown percentage (0.0-1.0)
        - is_breach: True if global limit exists and is breached

    Examples:
        >>> evaluate_portfolio_drawdown(880.0, 1000.0, 0.10)
        (0.12, True)
        >>> evaluate_portfolio_drawdown(920.0, 1000.0, 0.10)
        (0.08, False)
        >>> evaluate_portfolio_drawdown(500.0, 1000.0, None)
        (0.5, False)
    """
    # Calculate current drawdown
    if peak_portfolio_pnl <= 0:
        current_drawdown = 0.0
    else:
        current_drawdown = (
            peak_portfolio_pnl - current_portfolio_pnl
        ) / peak_portfolio_pnl

    # Check breach
    is_breach = False
    if global_drawdown_limit is not None:
        if current_drawdown > global_drawdown_limit:
            is_breach = True
            logger.warning(
                "Global drawdown breach: %.4f > limit %.4f",
                current_drawdown,
                global_drawdown_limit,
            )

    return (current_drawdown, is_breach)


def should_abort_portfolio(
    portfolio_drawdown: float,
    global_drawdown_limit: float | None,
    data_integrity_ok: bool = True,
) -> tuple[bool, str]:
    """
    Determine if portfolio execution should abort due to global conditions.

    Per FR-021, only two conditions trigger global abort:
    1. Portfolio drawdown exceeds global limit
    2. Data integrity failure (unrecoverable error)

    Args:
        portfolio_drawdown: Current portfolio drawdown (0.0-1.0).
        global_drawdown_limit: Global drawdown threshold (optional).
        data_integrity_ok: Whether data integrity checks passed.

    Returns:
        Tuple of (should_abort, reason).

    Examples:
        >>> should_abort_portfolio(0.12, 0.10)
        (True, 'global_drawdown_breach')
        >>> should_abort_portfolio(0.08, 0.10)
        (False, '')
        >>> should_abort_portfolio(0.05, None, data_integrity_ok=False)
        (True, 'data_integrity_failure')
    """
    # Check data integrity first (higher priority)
    if not data_integrity_ok:
        logger.error("Portfolio abort triggered: data integrity failure")
        return (True, "data_integrity_failure")

    # Check global drawdown
    if global_drawdown_limit is not None:
        if portfolio_drawdown > global_drawdown_limit:
            logger.warning(
                "Portfolio abort triggered: drawdown %.4f > limit %.4f",
                portfolio_drawdown,
                global_drawdown_limit,
            )
            return (True, "global_drawdown_breach")

    # No abort conditions met
    return (False, "")


__all__ = ["evaluate_portfolio_drawdown", "should_abort_portfolio"]
