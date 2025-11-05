"""
Basic technical indicators for trading strategy.

This module implements core technical indicators using numpy for vectorized
computation. All indicators follow standard definitions to ensure
interpretability and alignment with industry conventions.

Indicators:
- EMA (Exponential Moving Average): Trend identification
- ATR (Average True Range): Volatility measurement
- RSI (Relative Strength Index): Momentum oscillator
"""

import numpy as np
from numpy.typing import NDArray


def ema(prices: NDArray[np.float64], period: int) -> NDArray[np.float64]:
    """
    Calculate Exponential Moving Average using standard smoothing factor.

    The EMA gives more weight to recent prices and responds faster to price
    changes than a simple moving average. Uses the standard smoothing factor
    alpha = 2 / (period + 1).

    Args:
        prices: Array of price values (typically close prices).
        period: Number of periods for the EMA calculation.

    Returns:
        Array of EMA values with same length as input. Initial values
        before sufficient data are NaN.

    Raises:
        ValueError: If period < 1 or prices array is empty.

    Examples:
        >>> import numpy as np
        >>> prices = np.array([1.10, 1.11, 1.12, 1.11, 1.13])
        >>> result = ema(prices, period=3)
        >>> len(result) == len(prices)
        True
    """
    if period < 1:
        raise ValueError(f"Period must be >= 1, got {period}")
    if len(prices) == 0:
        raise ValueError("Prices array cannot be empty")

    alpha = 2.0 / (period + 1)
    ema_values = np.full_like(prices, np.nan, dtype=np.float64)

    # Start EMA at first valid price
    ema_values[0] = prices[0]

    # Calculate EMA iteratively
    for i in range(1, len(prices)):
        ema_values[i] = alpha * prices[i] + (1 - alpha) * ema_values[i - 1]

    # First 'period' values should be NaN (insufficient data)
    ema_values[: period - 1] = np.nan

    return ema_values


def atr(
    high: NDArray[np.float64],
    low: NDArray[np.float64],
    close: NDArray[np.float64],
    period: int = 14,
) -> NDArray[np.float64]:
    """
    Calculate Average True Range for volatility measurement.

    ATR measures market volatility by decomposing the entire range of price
    movement for a period. True Range is the maximum of:
    - Current high minus current low
    - Absolute value of current high minus previous close
    - Absolute value of current low minus previous close

    Args:
        high: Array of high prices.
        low: Array of low prices.
        close: Array of close prices.
        period: Number of periods for ATR smoothing (default: 14).

    Returns:
        Array of ATR values with same length as input. Initial values
        before sufficient data are NaN.

    Raises:
        ValueError: If arrays have different lengths, period < 1,
            or arrays are empty.

    Examples:
        >>> import numpy as np
        >>> high = np.array([1.12, 1.13, 1.14, 1.13, 1.15])
        >>> low = np.array([1.10, 1.11, 1.12, 1.11, 1.13])
        >>> close = np.array([1.11, 1.12, 1.13, 1.12, 1.14])
        >>> result = atr(high, low, close, period=3)
        >>> len(result) == len(high)
        True
    """
    if len(high) != len(low) or len(high) != len(close):
        raise ValueError("High, low, and close arrays must have the same length")
    if period < 1:
        raise ValueError(f"Period must be >= 1, got {period}")
    if len(high) == 0:
        raise ValueError("Price arrays cannot be empty")

    # Calculate True Range
    tr = np.full(len(high), np.nan, dtype=np.float64)

    # First TR is just high - low
    tr[0] = high[0] - low[0]

    # Subsequent TRs use the formula
    for i in range(1, len(high)):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr[i] = max(hl, hc, lc)

    # Calculate ATR as EMA of True Range
    atr_values = ema(tr, period)

    return atr_values


def rsi(prices: NDArray[np.float64], period: int = 14) -> NDArray[np.float64]:
    """
    Calculate Relative Strength Index momentum oscillator.

    RSI measures the magnitude of recent price changes to evaluate
    overbought or oversold conditions. Output ranges from 0 to 100.

    Traditional interpretation:
    - RSI > 70: Overbought condition
    - RSI < 30: Oversold condition

    Args:
        prices: Array of price values (typically close prices).
        period: Number of periods for RSI calculation (default: 14).

    Returns:
        Array of RSI values (0-100) with same length as input. Initial values
        before sufficient data are NaN.

    Raises:
        ValueError: If period < 1 or prices array is empty.

    Examples:
        >>> import numpy as np
        >>> prices = np.array([1.10, 1.11, 1.12, 1.11, 1.13, 1.14, 1.13])
        >>> result = rsi(prices, period=6)
        >>> len(result) == len(prices)
        True
        >>> np.all((result[~np.isnan(result)] >= 0) & (result[~np.isnan(result)] <= 100))
        True
    """
    if period < 1:
        raise ValueError(f"Period must be >= 1, got {period}")
    if len(prices) == 0:
        raise ValueError("Prices array cannot be empty")
    if len(prices) < 2:
        return np.full_like(prices, np.nan, dtype=np.float64)

    # Calculate price changes
    deltas = np.diff(prices)

    # Separate gains and losses
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # Calculate average gains and losses using EMA
    # Pad with initial zero to match original array length
    gains_padded = np.concatenate([[0.0], gains])
    losses_padded = np.concatenate([[0.0], losses])

    avg_gains = ema(gains_padded, period)
    avg_losses = ema(losses_padded, period)

    # Calculate RS and RSI
    rsi_values = np.full_like(prices, np.nan, dtype=np.float64)

    # Avoid division by zero - suppress the warning since we handle it with np.where
    valid_mask = avg_losses != 0
    with np.errstate(divide='ignore', invalid='ignore'):
        rs = np.where(valid_mask, avg_gains / avg_losses, 100.0)

    # RSI = 100 - (100 / (1 + RS))
    rsi_values = 100.0 - (100.0 / (1.0 + rs))

    # Handle case where avg_loss is zero (all gains)
    rsi_values[~valid_mask & (avg_gains > 0)] = 100.0
    rsi_values[~valid_mask & (avg_gains == 0)] = 50.0

    # First 'period' values should be NaN (insufficient data)
    rsi_values[:period] = np.nan

    return rsi_values


def validate_indicator_inputs(
    prices: NDArray[np.float64], period: int, min_length: int = 2
) -> None:
    """
    Validate common indicator input parameters.

    Args:
        prices: Price array to validate.
        period: Period parameter to validate.
        min_length: Minimum required array length.

    Raises:
        ValueError: If validation fails.

    Examples:
        >>> import numpy as np
        >>> prices = np.array([1.0, 2.0, 3.0])
        >>> validate_indicator_inputs(prices, period=2, min_length=2)
    """
    if len(prices) < min_length:
        raise ValueError(
            f"Prices array must have at least {min_length} elements, "
            f"got {len(prices)}"
        )
    if period < 1:
        raise ValueError(f"Period must be >= 1, got {period}")
    if np.any(np.isnan(prices)):
        raise ValueError("Prices array contains NaN values")
    if np.any(np.isinf(prices)):
        raise ValueError("Prices array contains infinite values")
