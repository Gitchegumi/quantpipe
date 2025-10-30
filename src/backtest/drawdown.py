"""
Drawdown computation for backtest analysis.

This module provides utilities for calculating and analyzing drawdown curves
from trade execution sequences. It supports both cumulative and rolling
drawdown analysis, essential for risk assessment and strategy validation.

All functions handle empty sequences gracefully and return appropriate defaults.
"""

import logging
from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from ..models.core import TradeExecution


logger = logging.getLogger(__name__)


def compute_drawdown_curve(executions: Sequence[TradeExecution]) -> NDArray[np.float64]:
    """
    Compute the drawdown curve from a sequence of trade executions.

    The drawdown at each point is the difference between the cumulative
    equity and the running maximum (peak). All values are ≤ 0.

    Args:
        executions: Sequence of TradeExecution objects with pnl_r values.

    Returns:
        NumPy array of drawdown values in R multiples (all ≤ 0).
        Returns empty array if no executions provided.

    Examples:
        >>> from datetime import datetime, timezone
        >>> from models.core import TradeExecution
        >>> executions = [
        ...     TradeExecution(
        ...         signal_id="sig1",
        ...         open_timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        ...         close_timestamp=datetime(2025, 1, 1, 18, 0, tzinfo=timezone.utc),
        ...         fill_entry_price=1.10000,
        ...         fill_stop_price=1.09800,
        ...         fill_exit_price=1.10400,
        ...         exit_reason="TARGET",
        ...         pnl_r=2.0,
        ...         slippage_pips=0.5,
        ...         execution_costs_pct=0.001
        ...     ),
        ...     TradeExecution(
        ...         signal_id="sig2",
        ...         open_timestamp=datetime(2025, 1, 2, 12, 0, tzinfo=timezone.utc),
        ...         close_timestamp=datetime(2025, 1, 2, 14, 0, tzinfo=timezone.utc),
        ...         fill_entry_price=1.10500,
        ...         fill_stop_price=1.10300,
        ...         fill_exit_price=1.10300,
        ...         exit_reason="STOP",
        ...         pnl_r=-1.5,
        ...         slippage_pips=0.3,
        ...         execution_costs_pct=0.001
        ...     )
        ... ]
        >>> dd_curve = compute_drawdown_curve(executions)
        >>> dd_curve
        array([ 0. , -1.5])
    """
    if not executions:
        logger.debug("No executions provided for drawdown computation")
        return np.array([], dtype=np.float64)

    # Extract PnL values
    pnl_r_values = np.array([ex.pnl_r for ex in executions], dtype=np.float64)

    # Compute cumulative equity curve
    cumulative_equity = np.cumsum(pnl_r_values)

    # Track running maximum (peak equity)
    running_max = np.maximum.accumulate(cumulative_equity)

    # Drawdown is current equity minus peak
    drawdown_curve = cumulative_equity - running_max

    logger.debug(
        "Computed drawdown curve: %d points, max_dd=%.2fR",
        len(drawdown_curve),
        np.min(drawdown_curve),
    )

    return drawdown_curve


def compute_max_drawdown(executions: Sequence[TradeExecution]) -> float:
    """
    Compute the maximum drawdown from a sequence of trade executions.

    Maximum drawdown is the largest peak-to-trough decline in cumulative
    equity, measured in R multiples. Returns 0.0 if no executions or no
    drawdown occurred.

    Args:
        executions: Sequence of TradeExecution objects with pnl_r values.

    Returns:
        Maximum drawdown in R multiples (≤ 0).

    Examples:
        >>> from datetime import datetime, timezone
        >>> from models.core import TradeExecution
        >>> executions = [
        ...     TradeExecution(
        ...         signal_id="sig1",
        ...         open_timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        ...         close_timestamp=datetime(2025, 1, 1, 18, 0, tzinfo=timezone.utc),
        ...         fill_entry_price=1.10000,
        ...         fill_stop_price=1.09800,
        ...         fill_exit_price=1.10400,
        ...         exit_reason="TARGET",
        ...         pnl_r=1.0,
        ...         slippage_pips=0.5,
        ...         execution_costs_pct=0.001
        ...     ),
        ...     TradeExecution(
        ...         signal_id="sig2",
        ...         open_timestamp=datetime(2025, 1, 2, 12, 0, tzinfo=timezone.utc),
        ...         close_timestamp=datetime(2025, 1, 2, 14, 0, tzinfo=timezone.utc),
        ...         fill_entry_price=1.10500,
        ...         fill_stop_price=1.10300,
        ...         fill_exit_price=1.10300,
        ...         exit_reason="STOP",
        ...         pnl_r=-3.0,
        ...         slippage_pips=0.3,
        ...         execution_costs_pct=0.001
        ...     ),
        ...     TradeExecution(
        ...         signal_id="sig3",
        ...         open_timestamp=datetime(2025, 1, 3, 12, 0, tzinfo=timezone.utc),
        ...         close_timestamp=datetime(2025, 1, 3, 18, 0, tzinfo=timezone.utc),
        ...         fill_entry_price=1.10200,
        ...         fill_stop_price=1.10000,
        ...         fill_exit_price=1.10600,
        ...         exit_reason="TARGET",
        ...         pnl_r=2.0,
        ...         slippage_pips=0.4,
        ...         execution_costs_pct=0.001
        ...     )
        ... ]
        >>> max_dd = compute_max_drawdown(executions)
        >>> max_dd
        -2.0
    """
    if not executions:
        logger.debug("No executions provided for max drawdown computation")
        return 0.0

    drawdown_curve = compute_drawdown_curve(executions)

    if len(drawdown_curve) == 0:
        return 0.0

    max_dd = float(np.min(drawdown_curve))

    logger.info("Maximum drawdown: %.2fR from %d trades", max_dd, len(executions))

    return max_dd


def find_drawdown_periods(
    executions: Sequence[TradeExecution],
) -> list[tuple[int, int, float]]:
    """
    Identify all distinct drawdown periods in the execution sequence.

    A drawdown period starts when equity falls below its previous peak
    and ends when equity reaches a new peak. Returns list of tuples
    containing (start_index, end_index, drawdown_magnitude).

    Args:
        executions: Sequence of TradeExecution objects with pnl_r values.

    Returns:
        List of drawdown periods as (start_idx, end_idx, magnitude) tuples.
        Empty list if no executions or no drawdowns occurred.

    Examples:
        >>> from datetime import datetime, timezone
        >>> from models.core import TradeExecution
        >>> executions = [
        ...     TradeExecution(
        ...         signal_id="sig1",
        ...         open_timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        ...         close_timestamp=datetime(2025, 1, 1, 18, 0, tzinfo=timezone.utc),
        ...         fill_entry_price=1.10000,
        ...         fill_stop_price=1.09800,
        ...         fill_exit_price=1.10400,
        ...         exit_reason="TARGET",
        ...         pnl_r=2.0,
        ...         slippage_pips=0.5,
        ...         execution_costs_pct=0.001
        ...     ),
        ...     TradeExecution(
        ...         signal_id="sig2",
        ...         open_timestamp=datetime(2025, 1, 2, 12, 0, tzinfo=timezone.utc),
        ...         close_timestamp=datetime(2025, 1, 2, 14, 0, tzinfo=timezone.utc),
        ...         fill_entry_price=1.10500,
        ...         fill_stop_price=1.10300,
        ...         fill_exit_price=1.10300,
        ...         exit_reason="STOP",
        ...         pnl_r=-1.0,
        ...         slippage_pips=0.3,
        ...         execution_costs_pct=0.001
        ...     ),
        ...     TradeExecution(
        ...         signal_id="sig3",
        ...         open_timestamp=datetime(2025, 1, 3, 12, 0, tzinfo=timezone.utc),
        ...         close_timestamp=datetime(2025, 1, 3, 18, 0, tzinfo=timezone.utc),
        ...         fill_entry_price=1.10200,
        ...         fill_stop_price=1.10000,
        ...         fill_exit_price=1.10600,
        ...         exit_reason="TARGET",
        ...         pnl_r=1.5,
        ...         slippage_pips=0.4,
        ...         execution_costs_pct=0.001
        ...     )
        ... ]
        >>> periods = find_drawdown_periods(executions)
        >>> len(periods)
        1
        >>> periods[0]
        (1, 1, -1.0)
    """
    if not executions:
        logger.debug("No executions provided for drawdown period analysis")
        return []

    pnl_r_values = np.array([ex.pnl_r for ex in executions], dtype=np.float64)
    cumulative_equity = np.cumsum(pnl_r_values)
    running_max = np.maximum.accumulate(cumulative_equity)
    drawdown_curve = cumulative_equity - running_max

    periods: list[tuple[int, int, float]] = []
    in_drawdown = False
    start_idx = 0
    dd_magnitude = 0.0

    for i, dd in enumerate(drawdown_curve):
        if dd < 0 and not in_drawdown:
            # Start of new drawdown period
            in_drawdown = True
            start_idx = i
            dd_magnitude = dd
        elif dd < 0 and in_drawdown:
            # Update magnitude if deeper
            dd_magnitude = min(dd_magnitude, dd)
        elif dd == 0 and in_drawdown:
            # End of drawdown period (new peak reached)
            periods.append((start_idx, i - 1, dd_magnitude))
            in_drawdown = False
            dd_magnitude = 0.0

    # Handle case where drawdown extends to end of sequence
    if in_drawdown:
        periods.append((start_idx, len(drawdown_curve) - 1, dd_magnitude))

    logger.debug("Found %d drawdown period(s)", len(periods))

    return periods


def compute_recovery_time(
    executions: Sequence[TradeExecution], drawdown_start_idx: int, drawdown_end_idx: int
) -> int:
    """
    Compute the number of trades required to recover from a drawdown.

    Recovery is defined as returning to the peak equity level that existed
    before the drawdown began.

    Args:
        executions: Sequence of TradeExecution objects.
        drawdown_start_idx: Index where drawdown began.
        drawdown_end_idx: Index where drawdown reached its deepest point.

    Returns:
        Number of trades from drawdown start to recovery (new peak).
        Returns 0 if recovery never occurred.

    Examples:
        >>> from datetime import datetime, timezone
        >>> from models.core import TradeExecution
        >>> executions = [
        ...     TradeExecution(
        ...         signal_id="sig1",
        ...         open_timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        ...         close_timestamp=datetime(2025, 1, 1, 18, 0, tzinfo=timezone.utc),
        ...         fill_entry_price=1.10000,
        ...         fill_stop_price=1.09800,
        ...         fill_exit_price=1.10400,
        ...         exit_reason="TARGET",
        ...         pnl_r=2.0,
        ...         slippage_pips=0.5,
        ...         execution_costs_pct=0.001
        ...     ),
        ...     TradeExecution(
        ...         signal_id="sig2",
        ...         open_timestamp=datetime(2025, 1, 2, 12, 0, tzinfo=timezone.utc),
        ...         close_timestamp=datetime(2025, 1, 2, 14, 0, tzinfo=timezone.utc),
        ...         fill_entry_price=1.10500,
        ...         fill_stop_price=1.10300,
        ...         fill_exit_price=1.10300,
        ...         exit_reason="STOP",
        ...         pnl_r=-1.5,
        ...         slippage_pips=0.3,
        ...         execution_costs_pct=0.001
        ...     ),
        ...     TradeExecution(
        ...         signal_id="sig3",
        ...         open_timestamp=datetime(2025, 1, 3, 12, 0, tzinfo=timezone.utc),
        ...         close_timestamp=datetime(2025, 1, 3, 18, 0, tzinfo=timezone.utc),
        ...         fill_entry_price=1.10200,
        ...         fill_stop_price=1.10000,
        ...         fill_exit_price=1.10600,
        ...         exit_reason="TARGET",
        ...         pnl_r=2.0,
        ...         slippage_pips=0.4,
        ...         execution_costs_pct=0.001
        ...     )
        ... ]
        >>> recovery = compute_recovery_time(executions, 1, 1)
        >>> recovery
        2
    """
    if not executions or drawdown_start_idx >= len(executions):
        logger.warning("Invalid drawdown indices for recovery calculation")
        return 0

    pnl_r_values = np.array([ex.pnl_r for ex in executions], dtype=np.float64)
    cumulative_equity = np.cumsum(pnl_r_values)

    # Peak equity before drawdown
    if drawdown_start_idx == 0:
        peak_before = 0.0
    else:
        peak_before = cumulative_equity[drawdown_start_idx - 1]

    # Find when we recover to peak
    for i in range(drawdown_start_idx, len(cumulative_equity)):
        if cumulative_equity[i] >= peak_before:
            recovery_trades = i - drawdown_start_idx + 1
            logger.debug(
                "Recovery from drawdown at %d: %d trades",
                drawdown_start_idx,
                recovery_trades,
            )
            return recovery_trades

    # No recovery occurred
    logger.debug("No recovery from drawdown starting at %d", drawdown_start_idx)
    return 0
