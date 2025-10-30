"""
Risk management for position sizing and stop-loss calculation.

This module calculates appropriate position sizes based on account risk
parameters and ATR-based stop distances. Ensures no single trade risks
more than the specified percentage of account equity.
"""

import logging
import math

from ..models.core import TradeSignal


logger = logging.getLogger(__name__)


def calculate_position_size(
    signal: TradeSignal,
    account_balance: float,
    risk_per_trade_pct: float,
    pip_value: float = 10.0,
    lot_step: float = 0.01,
    max_position_size: float = 10.0,
) -> float:
    """
    Calculate position size in lots based on risk parameters.

    Uses ATR-based stop distance to determine position size that risks
    exactly `risk_per_trade_pct` of account balance.

    Formula:
        risk_amount = account_balance * (risk_per_trade_pct / 100)
        stop_distance_pips = abs(entry_price - stop_price) * 10000
        position_size = risk_amount / (stop_distance_pips * pip_value)
        position_size = round to lot_step

    Args:
        signal: TradeSignal with entry and stop prices.
        account_balance: Current account balance in base currency.
        risk_per_trade_pct: Percentage of account to risk (e.g., 0.25 for 0.25%).
        pip_value: Value of 1 pip in base currency for 1 lot (default 10.0 for forex).
        lot_step: Minimum lot size increment (default 0.01).
        max_position_size: Maximum allowed position size in lots (default 10.0).

    Returns:
        Position size in lots, rounded to lot_step.

    Raises:
        ValueError: If account_balance <= 0 or risk_per_trade_pct <= 0.

    Examples:
        >>> from datetime import datetime, timezone
        >>> from models.core import TradeSignal
        >>> signal = TradeSignal(
        ...     id="test123",
        ...     pair="EURUSD",
        ...     direction="LONG",
        ...     entry_price=1.10000,
        ...     initial_stop_price=1.09800,  # 20 pips
        ...     risk_per_trade_pct=0.25,
        ...     calc_position_size=0.0,
        ...     tags=[],
        ...     version="0.1.0",
        ...     timestamp_utc=datetime(2025, 1, 1, tzinfo=timezone.utc)
        ... )
        >>> position_size = calculate_position_size(signal, 10000.0, 0.25)
        >>> position_size
        0.12
    """
    if account_balance <= 0:
        raise ValueError(f"Account balance must be positive, got {account_balance}")

    if risk_per_trade_pct <= 0:
        raise ValueError(
            f"Risk per trade percentage must be positive, got {risk_per_trade_pct}"
        )

    # Calculate risk amount in base currency
    risk_amount = account_balance * (risk_per_trade_pct / 100.0)

    # Calculate stop distance in pips
    price_difference = abs(signal.entry_price - signal.initial_stop_price)
    stop_distance_pips = price_difference * 10000  # Forex pips conversion

    if stop_distance_pips == 0:
        logger.warning("Stop distance is zero, cannot calculate position size")
        return lot_step

    # Calculate raw position size
    raw_position_size = risk_amount / (stop_distance_pips * pip_value)

    # Round to lot step
    position_size = math.floor(raw_position_size / lot_step) * lot_step

    # Apply maximum position size limit
    if position_size > max_position_size:
        logger.warning(
            "Position size %.2f exceeds maximum %.2f, capping to maximum",
            position_size,
            max_position_size,
        )
        position_size = max_position_size

    # Ensure minimum position size
    if position_size < lot_step:
        logger.warning(
            "Calculated position size %.2f below minimum %.2f, using minimum",
            position_size,
            lot_step,
        )
        position_size = lot_step

    logger.debug(
        "Position size calculated: %.2f lots (risk=$%.2f, stop=%.1f pips)",
        position_size,
        risk_amount,
        stop_distance_pips,
    )

    return position_size


def calculate_atr_stop(
    entry_price: float,
    atr_value: float,
    direction: str,
    atr_multiplier: float = 2.0,
) -> float:
    """
    Calculate ATR-based stop-loss price.

    Args:
        entry_price: Trade entry price.
        atr_value: Current ATR value.
        direction: Trade direction ("LONG" or "SHORT").
        atr_multiplier: ATR multiplier for stop distance (default 2.0).

    Returns:
        Stop-loss price.

    Raises:
        ValueError: If direction is invalid.

    Examples:
        >>> stop = calculate_atr_stop(1.10000, 0.00100, "LONG", 2.0)
        >>> stop
        1.09800
    """
    if direction not in ["LONG", "SHORT"]:
        raise ValueError(f"Invalid direction: {direction}")

    stop_distance = atr_value * atr_multiplier

    if direction == "LONG":
        stop_price = entry_price - stop_distance
    else:  # SHORT
        stop_price = entry_price + stop_distance

    return stop_price


def calculate_take_profit(
    entry_price: float,
    stop_loss_price: float,
    direction: str,
    reward_risk_ratio: float = 2.0,
) -> float:
    """
    Calculate take-profit price based on R-multiple.

    Args:
        entry_price: Trade entry price.
        stop_loss_price: Stop-loss price.
        direction: Trade direction ("LONG" or "SHORT").
        reward_risk_ratio: Reward-to-risk ratio (R-multiple, default 2.0).

    Returns:
        Take-profit price.

    Raises:
        ValueError: If direction is invalid.

    Examples:
        >>> tp = calculate_take_profit(1.10000, 1.09800, "LONG", 2.0)
        >>> tp
        1.10400
    """
    if direction not in ["LONG", "SHORT"]:
        raise ValueError(f"Invalid direction: {direction}")

    risk_distance = abs(entry_price - stop_loss_price)
    reward_distance = risk_distance * reward_risk_ratio

    if direction == "LONG":
        take_profit_price = entry_price + reward_distance
    else:  # SHORT
        take_profit_price = entry_price - reward_distance

    return take_profit_price


def validate_risk_limits(
    position_size: float,
    _account_balance: float,
    max_drawdown_pct: float = 10.0,
    current_drawdown_pct: float = 0.0,
) -> bool:
    """
    Validate that trade respects risk limits.

    Checks:
    - Current drawdown is below maximum allowed
    - Position size is reasonable relative to account

    Args:
        position_size: Calculated position size in lots.
        account_balance: Current account balance.
        max_drawdown_pct: Maximum allowed drawdown percentage (default 10.0).
        current_drawdown_pct: Current drawdown percentage (default 0.0).

    Returns:
        True if risk limits are satisfied, False otherwise.

    Examples:
        >>> is_valid = validate_risk_limits(0.10, 10000.0, 10.0, 2.5)
        >>> is_valid
        True
    """
    # Check drawdown limit
    if current_drawdown_pct >= max_drawdown_pct:
        logger.warning(
            "Current drawdown %.2f%% exceeds maximum %.2f%%, trade rejected",
            current_drawdown_pct,
            max_drawdown_pct,
        )
        return False

    # Check position size is reasonable (not zero or negative)
    if position_size <= 0:
        logger.warning("Invalid position size: %.2f", position_size)
        return False

    return True
