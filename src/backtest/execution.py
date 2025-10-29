"""
Trade execution simulator for backtesting.

This module simulates realistic trade execution including entry fills, exit
fills, slippage, and the precedence rule for exit modes (fixed R target with
trailing stop timeout fallback per FR-026).
"""

import logging
from collections.abc import Sequence

from ..models.core import Candle, TradeExecution, TradeSignal
from ..models.exceptions import ExecutionSimulationError

logger = logging.getLogger(__name__)


def simulate_execution(
    signal: TradeSignal,
    candles: Sequence[Candle],
    slippage_pips: float = 0.5,
    spread_pips: float = 1.0,
    commission_per_lot: float = 7.0,
    trailing_stop_timeout_candles: int = 50,
) -> TradeExecution | None:
    """
    Simulate trade execution from signal to exit.

    Processes candles sequentially after signal timestamp to simulate:
    1. Entry fill at next candle open + slippage
    2. Exit via:
       - Stop-loss hit
       - Take-profit (fixed R target) hit
       - Trailing stop timeout (FR-026 fallback)

    Exit mode precedence (FR-026):
    - Primary: Fixed R target (take-profit)
    - Fallback: Trailing stop activated after timeout

    Args:
        signal: TradeSignal to execute.
        candles: Full candle sequence (must include candles after signal timestamp).
        slippage_pips: Entry/exit slippage in pips (default 0.5).
        spread_pips: Bid-ask spread in pips (default 1.0).
        commission_per_lot: Commission per lot (default 7.0).
        trailing_stop_timeout_candles: Candles before trailing stop activates (default 50).

    Returns:
        TradeExecution if trade completed, None if still open or invalid.

    Raises:
        ExecutionSimulationError: If execution simulation fails.

    Examples:
        >>> from datetime import datetime, timezone
        >>> from models.core import TradeSignal, Candle
        >>> signal = TradeSignal(...)
        >>> candles = [...]  # Candles after signal
        >>> execution = simulate_execution(signal, candles)
        >>> execution.exit_reason
        'TARGET'
        >>> execution.pnl_r
        2.0
    """
    if not candles:
        raise ExecutionSimulationError(
            "No candles provided for execution simulation",
            signal_id=signal.id,
        )

    # Find entry candle (first candle after signal timestamp)
    entry_candle_idx = None
    for i, candle in enumerate(candles):
        if candle.timestamp_utc > signal.timestamp_utc:
            entry_candle_idx = i
            break

    if entry_candle_idx is None:
        logger.debug(
            "No candles after signal timestamp %s", signal.timestamp_utc.isoformat()
        )
        return None

    entry_candle = candles[entry_candle_idx]

    # Simulate entry fill with slippage
    if signal.direction == "LONG":
        entry_fill_price = entry_candle.open + (slippage_pips / 10000)
    else:  # SHORT
        entry_fill_price = entry_candle.open - (slippage_pips / 10000)

    logger.debug(
        "Entry simulated: signal_id=%s..., timestamp=%s, fill=%.5f",
        signal.id[:16],
        entry_candle.timestamp_utc.isoformat(),
        entry_fill_price,
    )

    # Track trade through subsequent candles
    candles_in_trade = 0
    trailing_stop_active = False
    trailing_stop_price = signal.initial_stop_price

    # Calculate take-profit from initial stop (2R default)
    risk_distance = abs(entry_fill_price - signal.initial_stop_price)
    if signal.direction == "LONG":
        take_profit_price = entry_fill_price + (risk_distance * 2.0)
    else:  # SHORT
        take_profit_price = entry_fill_price - (risk_distance * 2.0)

    for i in range(entry_candle_idx + 1, len(candles)):
        candle = candles[i]
        candles_in_trade += 1

        # Check if trailing stop should activate (FR-026 timeout)
        if (
            candles_in_trade >= trailing_stop_timeout_candles
            and not trailing_stop_active
        ):
            trailing_stop_active = True
            trailing_stop_price = signal.initial_stop_price
            logger.debug(
                "Trailing stop activated after %d candles",
                trailing_stop_timeout_candles,
            )

        # Update trailing stop if active
        if trailing_stop_active:
            if signal.direction == "LONG":
                # Trail stop up as price rises
                potential_stop = candle.close - abs(
                    signal.entry_price - signal.initial_stop_price
                )
                if potential_stop > trailing_stop_price:
                    trailing_stop_price = potential_stop
            else:  # SHORT
                # Trail stop down as price falls
                potential_stop = candle.close + abs(
                    signal.entry_price - signal.initial_stop_price
                )
                if potential_stop < trailing_stop_price:
                    trailing_stop_price = potential_stop

        # Check for exit conditions
        exit_result = _check_exit_conditions(
            candle,
            signal,
            entry_fill_price,
            trailing_stop_price if trailing_stop_active else signal.initial_stop_price,
            take_profit_price,
            slippage_pips,
        )

        if exit_result:
            exit_fill_price, exit_reason = exit_result

            # Calculate PnL in R-multiples
            risk_distance = abs(entry_fill_price - signal.initial_stop_price)
            if signal.direction == "LONG":
                pnl_distance = exit_fill_price - entry_fill_price
            else:  # SHORT
                pnl_distance = entry_fill_price - exit_fill_price

            pnl_r = pnl_distance / risk_distance if risk_distance > 0 else 0.0

            # Calculate costs
            total_costs = (spread_pips / 10000) + (
                commission_per_lot * signal.calc_position_size / 100000
            )

            execution = TradeExecution(
                signal_id=signal.id,
                open_timestamp=entry_candle.timestamp_utc,
                entry_fill_price=entry_fill_price,
                close_timestamp=candle.timestamp_utc,
                exit_fill_price=exit_fill_price,
                exit_reason=exit_reason,
                pnl_r=pnl_r,
                slippage_entry_pips=slippage_pips,
                slippage_exit_pips=slippage_pips,
                costs_total=total_costs,
            )

            logger.info(
                "Trade closed: signal_id=%s..., exit_reason=%s, pnl_r=%.2fR, duration=%d candles",
                signal.id[:16],
                exit_reason,
                pnl_r,
                candles_in_trade,
            )

            return execution

    # Trade still open (not enough candles)
    logger.debug("Trade still open after %d candles", candles_in_trade)
    return None


def _check_exit_conditions(
    candle: Candle,
    signal: TradeSignal,
    entry_fill_price: float,
    current_stop_price: float,
    take_profit_price: float,
    slippage_pips: float,
) -> tuple[float, str] | None:
    """
    Check if any exit condition is met on this candle.

    Priority order:
    1. Stop-loss hit
    2. Take-profit hit
    3. Trailing stop hit (if active)

    Args:
        candle: Current candle.
        signal: Original trade signal.
        entry_fill_price: Actual entry fill price.
        current_stop_price: Current stop price (may be trailing).
        take_profit_price: Target profit price (calculated from risk distance).
        slippage_pips: Exit slippage in pips.

    Returns:
        Tuple of (exit_fill_price, exit_reason) if exit triggered, None otherwise.

    Examples:
        >>> from models.core import Candle, TradeSignal
        >>> candle = Candle(...)
        >>> signal = TradeSignal(...)
        >>> result = _check_exit_conditions(candle, signal, 1.10000, 1.09800, 0.5)
        >>> result
        (1.10400, 'TARGET')
    """
    if signal.direction == "LONG":
        # Check stop-loss
        if candle.low <= current_stop_price:
            exit_fill = current_stop_price - (slippage_pips / 10000)
            return (exit_fill, "STOP_LOSS")

        # Check take-profit
        if candle.high >= take_profit_price:
            exit_fill = take_profit_price - (slippage_pips / 10000)
            return (exit_fill, "TARGET")

    else:  # SHORT
        # Check stop-loss
        if candle.high >= current_stop_price:
            exit_fill = current_stop_price + (slippage_pips / 10000)
            return (exit_fill, "STOP_LOSS")

        # Check take-profit
        if candle.low <= take_profit_price:
            exit_fill = take_profit_price + (slippage_pips / 10000)
            return (exit_fill, "TARGET")

    return None


def calculate_max_adverse_excursion(
    execution: TradeExecution,
    candles: Sequence[Candle],
) -> float:
    """
    Calculate Maximum Adverse Excursion (MAE) for a trade.

    MAE is the worst price move against the position during the trade.

    Args:
        execution: Completed trade execution.
        candles: Candles covering the trade duration.

    Returns:
        MAE in R-multiples (negative value).

    Examples:
        >>> from models.core import TradeExecution
        >>> execution = TradeExecution(...)
        >>> candles = [...]
        >>> mae = calculate_max_adverse_excursion(execution, candles)
        >>> mae
        -0.5
    """
    # Find candles within trade duration
    trade_candles = [
        c
        for c in candles
        if execution.open_timestamp <= c.timestamp_utc <= execution.close_timestamp
    ]

    if not trade_candles:
        return 0.0

    # Determine direction from entry/exit prices
    direction = (
        "LONG" if execution.exit_fill_price > execution.entry_fill_price else "SHORT"
    )

    worst_price = execution.entry_fill_price
    if direction == "LONG":
        # Find lowest low during trade
        worst_price = min(c.low for c in trade_candles)
        mae_distance = worst_price - execution.entry_fill_price
    else:  # SHORT
        # Find highest high during trade
        worst_price = max(c.high for c in trade_candles)
        mae_distance = execution.entry_fill_price - worst_price

    # Convert to R-multiples
    # Assume stop distance from execution (not stored, so approximate)
    risk_distance = abs(execution.pnl_r) / max(
        abs(execution.exit_fill_price - execution.entry_fill_price), 0.0001
    )
    mae_r = mae_distance * risk_distance

    return mae_r


def calculate_max_favorable_excursion(
    execution: TradeExecution,
    candles: Sequence[Candle],
) -> float:
    """
    Calculate Maximum Favorable Excursion (MFE) for a trade.

    MFE is the best price move in favor of the position during the trade.

    Args:
        execution: Completed trade execution.
        candles: Candles covering the trade duration.

    Returns:
        MFE in R-multiples (positive value).

    Examples:
        >>> from models.core import TradeExecution
        >>> execution = TradeExecution(...)
        >>> candles = [...]
        >>> mfe = calculate_max_favorable_excursion(execution, candles)
        >>> mfe
        2.5
    """
    # Find candles within trade duration
    trade_candles = [
        c
        for c in candles
        if execution.open_timestamp <= c.timestamp_utc <= execution.close_timestamp
    ]

    if not trade_candles:
        return 0.0

    # Determine direction from entry/exit prices
    direction = (
        "LONG" if execution.exit_fill_price > execution.entry_fill_price else "SHORT"
    )

    best_price = execution.entry_fill_price
    if direction == "LONG":
        # Find highest high during trade
        best_price = max(c.high for c in trade_candles)
        mfe_distance = best_price - execution.entry_fill_price
    else:  # SHORT
        # Find lowest low during trade
        best_price = min(c.low for c in trade_candles)
        mfe_distance = execution.entry_fill_price - best_price

    # Convert to R-multiples
    risk_distance = abs(execution.pnl_r) / max(
        abs(execution.exit_fill_price - execution.entry_fill_price), 0.0001
    )
    mfe_r = mfe_distance * risk_distance

    return mfe_r
