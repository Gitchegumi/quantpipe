"""Stochastic RSI indicator implementation.

Stochastic RSI combines RSI with stochastic oscillator mathematics to create
a more sensitive momentum indicator that oscillates between 0 and 1.

Formula:
1. Calculate RSI over N periods
2. Apply stochastic formula to RSI values:
   StochRSI = (RSI - RSI_Low) / (RSI_High - RSI_Low)
   where RSI_High and RSI_Low are highest/lowest RSI over lookback window

Optional enhancement for trend-pullback strategy to improve reversal detection.
"""

from typing import List

import numpy as np


def compute_stoch_rsi(
    rsi_values: List[float],
    lookback: int = 14,
) -> List[float]:
    """Compute Stochastic RSI from RSI values.

    Args:
        rsi_values: List of RSI values (typically 0-100 range)
        lookback: Window size for stochastic calculation (default 14)

    Returns:
        List of Stochastic RSI values (0.0 to 1.0 range)
        Returns empty list if insufficient data

    Note:
        First (lookback - 1) values will be NaN due to insufficient window.
    """
    if len(rsi_values) < lookback:
        return []

    rsi_arr = np.array(rsi_values)
    stoch_rsi = []

    for i in range(len(rsi_arr)):
        if i < lookback - 1:
            stoch_rsi.append(np.nan)
            continue

        window = rsi_arr[i - lookback + 1 : i + 1]
        rsi_high = np.max(window)
        rsi_low = np.min(window)

        if rsi_high == rsi_low:
            # Avoid division by zero - flat RSI yields 0.5
            stoch_rsi.append(0.5)
        else:
            current_rsi = rsi_arr[i]
            stoch = (current_rsi - rsi_low) / (rsi_high - rsi_low)
            stoch_rsi.append(stoch)

    return stoch_rsi


def compute_stoch_rsi_k_d(
    rsi_values: List[float],
    lookback: int = 14,
    k_smooth: int = 3,
    d_smooth: int = 3,
) -> tuple[List[float], List[float]]:
    """Compute smoothed Stochastic RSI %K and %D lines.

    %K = SMA of Stochastic RSI over k_smooth periods
    %D = SMA of %K over d_smooth periods

    Args:
        rsi_values: List of RSI values
        lookback: Window for stochastic calculation (default 14)
        k_smooth: Smoothing period for %K line (default 3)
        d_smooth: Smoothing period for %D line (default 3)

    Returns:
        Tuple of (%K values, %D values)
        Both lists same length as input, with NaN for insufficient data

    Note:
        Crossovers of %K and %D can signal momentum shifts.
        %K > %D with both rising = bullish momentum
        %K < %D with both falling = bearish momentum
    """
    stoch_rsi = compute_stoch_rsi(rsi_values, lookback=lookback)
    if len(stoch_rsi) == 0:
        return [], []

    stoch_arr = np.array(stoch_rsi)

    # Compute %K (SMA of StochRSI)
    k_values = []
    for i in range(len(stoch_arr)):
        if i < k_smooth - 1:
            k_values.append(np.nan)
            continue
        if np.isnan(stoch_arr[i]):
            k_values.append(np.nan)
            continue

        window = stoch_arr[i - k_smooth + 1 : i + 1]
        if np.any(np.isnan(window)):
            k_values.append(np.nan)
        else:
            k_values.append(np.mean(window))

    k_arr = np.array(k_values)

    # Compute %D (SMA of %K)
    d_values = []
    for i in range(len(k_arr)):
        if i < d_smooth - 1:
            d_values.append(np.nan)
            continue
        if np.isnan(k_arr[i]):
            d_values.append(np.nan)
            continue

        window = k_arr[i - d_smooth + 1 : i + 1]
        if np.any(np.isnan(window)):
            d_values.append(np.nan)
        else:
            d_values.append(np.mean(window))

    return k_values, d_values


def detect_stoch_rsi_oversold(
    k_values: List[float],
    threshold: float = 0.2,
) -> bool:
    """Detect if Stochastic RSI is in oversold territory.

    Args:
        k_values: List of %K values
        threshold: Oversold threshold (default 0.2 = 20%)

    Returns:
        True if current %K < threshold, False otherwise

    Note:
        Can be used to confirm pullback depth in trend-pullback strategy.
    """
    if len(k_values) == 0:
        return False

    current_k = k_values[-1]
    if np.isnan(current_k):
        return False

    return current_k < threshold


def detect_stoch_rsi_overbought(
    k_values: List[float],
    threshold: float = 0.8,
) -> bool:
    """Detect if Stochastic RSI is in overbought territory.

    Args:
        k_values: List of %K values
        threshold: Overbought threshold (default 0.8 = 80%)

    Returns:
        True if current %K > threshold, False otherwise

    Note:
        Can be used to confirm pullback depth (inverse for short trades).
    """
    if len(k_values) == 0:
        return False

    current_k = k_values[-1]
    if np.isnan(current_k):
        return False

    return current_k > threshold


def detect_bullish_crossover(
    k_values: List[float],
    d_values: List[float],
) -> bool:
    """Detect bullish crossover (%K crosses above %D).

    Args:
        k_values: List of %K values
        d_values: List of %D values

    Returns:
        True if %K just crossed above %D, False otherwise

    Note:
        Can be used as additional reversal confirmation in pullback strategy.
    """
    if len(k_values) < 2 or len(d_values) < 2:
        return False

    k_current = k_values[-1]
    k_previous = k_values[-2]
    d_current = d_values[-1]
    d_previous = d_values[-2]

    if np.isnan(k_current) or np.isnan(k_previous):
        return False
    if np.isnan(d_current) or np.isnan(d_previous):
        return False

    # Crossover: previous K <= previous D, current K > current D
    return k_previous <= d_previous and k_current > d_current


def detect_bearish_crossover(
    k_values: List[float],
    d_values: List[float],
) -> bool:
    """Detect bearish crossover (%K crosses below %D).

    Args:
        k_values: List of %K values
        d_values: List of %D values

    Returns:
        True if %K just crossed below %D, False otherwise

    Note:
        Can be used as additional reversal confirmation for short pullback trades.
    """
    if len(k_values) < 2 or len(d_values) < 2:
        return False

    k_current = k_values[-1]
    k_previous = k_values[-2]
    d_current = d_values[-1]
    d_previous = d_values[-2]

    if np.isnan(k_current) or np.isnan(k_previous):
        return False
    if np.isnan(d_current) or np.isnan(d_previous):
        return False

    # Crossover: previous K >= previous D, current K < current D
    return k_previous >= d_previous and k_current < d_current
