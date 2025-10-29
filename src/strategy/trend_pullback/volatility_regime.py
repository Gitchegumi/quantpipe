"""
Volatility regime classification for adaptive strategy behavior.

This module classifies market conditions into LOW, NORMAL, or HIGH volatility
regimes based on ATR (Average True Range) analysis. Volatility regimes can be
used to adjust position sizing, risk parameters, or signal filtering.

The classifier uses a rolling window approach to establish baseline volatility
and percentile-based thresholds for regime classification.
"""

import logging
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from ...models.core import Candle

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VolatilityRegime:
    """
    Represents the current volatility regime classification.

    Attributes:
        regime: Current volatility state - 'LOW', 'NORMAL', or 'HIGH'.
        current_atr: Current ATR value.
        baseline_atr: Rolling average ATR over lookback period.
        percentile_rank: Current ATR's percentile rank (0-100) in lookback window.
        lookback_period: Number of candles used for regime calculation.

    Examples:
        >>> from datetime import datetime, timezone
        >>> regime = VolatilityRegime(
        ...     regime='NORMAL',
        ...     current_atr=0.0015,
        ...     baseline_atr=0.0014,
        ...     percentile_rank=52.3,
        ...     lookback_period=100
        ... )
        >>> regime.regime
        'NORMAL'
    """

    regime: str  # Literal['LOW', 'NORMAL', 'HIGH']
    current_atr: float
    baseline_atr: float
    percentile_rank: float
    lookback_period: int


def classify_volatility_regime(
    candles: Sequence[Candle],
    lookback_period: int = 100,
    low_threshold_percentile: float = 30.0,
    high_threshold_percentile: float = 70.0,
) -> VolatilityRegime:
    """
    Classify the current volatility regime based on recent ATR history.

    Uses percentile ranking of current ATR relative to a lookback window
    to determine whether the market is in LOW, NORMAL, or HIGH volatility.

    Args:
        candles: Sequence of Candle objects with ATR values. Must have at
            least `lookback_period` candles for valid classification.
        lookback_period: Number of recent candles to analyze for baseline.
            Default is 100 candles.
        low_threshold_percentile: ATR percentile below which regime is 'LOW'.
            Default is 30.0 (bottom 30%).
        high_threshold_percentile: ATR percentile above which regime is 'HIGH'.
            Default is 70.0 (top 30%).

    Returns:
        VolatilityRegime object with classification and statistics.

    Raises:
        ValueError: If insufficient candles provided or invalid percentiles.

    Examples:
        >>> from datetime import datetime, timezone, timedelta
        >>> from models.core import Candle
        >>> base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        >>> candles = [
        ...     Candle(
        ...         timestamp_utc=base_time + timedelta(minutes=i),
        ...         open=1.1000, high=1.1010, low=1.0990, close=1.1005,
        ...         volume=1000.0, ema20=1.1000, ema50=1.0995,
        ...         atr=0.0015, rsi=50.0
        ...     )
        ...     for i in range(150)
        ... ]
        >>> # Modify last candle to have higher ATR
        >>> candles[-1] = Candle(
        ...     timestamp_utc=base_time + timedelta(minutes=149),
        ...     open=1.1000, high=1.1030, low=1.0970, close=1.1010,
        ...     volume=1000.0, ema20=1.1000, ema50=1.0995,
        ...     atr=0.0035, rsi=50.0
        ... )
        >>> regime = classify_volatility_regime(candles)
        >>> regime.regime
        'HIGH'
    """
    if len(candles) < lookback_period:
        raise ValueError(
            f"Insufficient candles for volatility classification: "
            f"{len(candles)} provided, {lookback_period} required"
        )

    if not (0 <= low_threshold_percentile < high_threshold_percentile <= 100):
        raise ValueError(
            f"Invalid percentile thresholds: low={low_threshold_percentile}, "
            f"high={high_threshold_percentile}"
        )

    # Extract ATR values from recent candles
    atr_values = np.array([c.atr for c in candles[-lookback_period:]], dtype=np.float64)

    # Current ATR is the most recent value
    current_atr = float(atr_values[-1])

    # Baseline ATR is the mean over lookback period
    baseline_atr = float(np.mean(atr_values))

    # Calculate percentile rank of current ATR
    percentile_rank = float(
        (np.sum(atr_values <= current_atr) / len(atr_values)) * 100
    )

    # Classify regime based on percentile thresholds
    if percentile_rank < low_threshold_percentile:
        regime = "LOW"
    elif percentile_rank > high_threshold_percentile:
        regime = "HIGH"
    else:
        regime = "NORMAL"

    logger.debug(
        f"Volatility regime: {regime} | "
        f"Current ATR: {current_atr:.6f} | "
        f"Baseline ATR: {baseline_atr:.6f} | "
        f"Percentile: {percentile_rank:.1f}%"
    )

    return VolatilityRegime(
        regime=regime,
        current_atr=current_atr,
        baseline_atr=baseline_atr,
        percentile_rank=percentile_rank,
        lookback_period=lookback_period,
    )


def get_adaptive_risk_multiplier(regime: VolatilityRegime) -> float:
    """
    Get a risk multiplier based on the current volatility regime.

    Returns a multiplier that can be applied to position sizing to reduce
    risk in high volatility environments and potentially increase in low
    volatility (optional based on risk appetite).

    Args:
        regime: VolatilityRegime object from classify_volatility_regime().

    Returns:
        Risk multiplier float:
            - HIGH volatility: 0.5 (reduce position size by 50%)
            - NORMAL volatility: 1.0 (standard position size)
            - LOW volatility: 1.0 (standard position size, conservative)

    Examples:
        >>> from volatility_regime import VolatilityRegime
        >>> regime = VolatilityRegime(
        ...     regime='HIGH',
        ...     current_atr=0.0035,
        ...     baseline_atr=0.0015,
        ...     percentile_rank=85.0,
        ...     lookback_period=100
        ... )
        >>> multiplier = get_adaptive_risk_multiplier(regime)
        >>> multiplier
        0.5
    """
    multipliers = {
        "LOW": 1.0,  # Conservative: keep standard size
        "NORMAL": 1.0,  # Standard size
        "HIGH": 0.5,  # Reduce risk in high volatility
    }

    multiplier = multipliers.get(regime.regime, 1.0)

    logger.debug(
        f"Risk multiplier for {regime.regime} volatility: {multiplier:.2f}x"
    )

    return multiplier


def detect_volatility_expansion(
    candles: Sequence[Candle], window_size: int = 20, expansion_threshold: float = 1.5
) -> bool:
    """
    Detect if volatility is rapidly expanding (potential trend start).

    Compares recent ATR to historical ATR to identify significant volatility
    increases that may signal the start of a new trending period.

    Args:
        candles: Sequence of Candle objects with ATR values.
        window_size: Number of recent candles to compare. Default is 20.
        expansion_threshold: Ratio threshold for expansion detection.
            Default is 1.5 (50% increase).

    Returns:
        True if volatility is expanding above threshold, False otherwise.

    Examples:
        >>> from datetime import datetime, timezone, timedelta
        >>> from models.core import Candle
        >>> base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        >>> # Create candles with increasing ATR
        >>> candles = [
        ...     Candle(
        ...         timestamp_utc=base_time + timedelta(minutes=i),
        ...         open=1.1000, high=1.1010, low=1.0990, close=1.1005,
        ...         volume=1000.0, ema20=1.1000, ema50=1.0995,
        ...         atr=0.0010 if i < 30 else 0.0020,
        ...         rsi=50.0
        ...     )
        ...     for i in range(50)
        ... ]
        >>> expanding = detect_volatility_expansion(candles)
        >>> expanding
        True
    """
    if len(candles) < window_size * 2:
        logger.warning(
            f"Insufficient candles for expansion detection: "
            f"{len(candles)} provided, {window_size * 2} recommended"
        )
        return False

    # Get ATR values
    atr_values = np.array([c.atr for c in candles], dtype=np.float64)

    # Recent ATR (average of last window_size candles)
    recent_atr = float(np.mean(atr_values[-window_size:]))

    # Historical ATR (average of previous window_size candles)
    historical_atr = float(
        np.mean(atr_values[-2 * window_size : -window_size])
    )

    # Avoid division by zero
    if historical_atr == 0:
        logger.warning("Historical ATR is zero, cannot compute expansion ratio")
        return False

    # Compute expansion ratio
    expansion_ratio = recent_atr / historical_atr

    is_expanding = expansion_ratio >= expansion_threshold

    logger.debug(
        f"Volatility expansion check: ratio={expansion_ratio:.2f}, "
        f"threshold={expansion_threshold:.2f}, expanding={is_expanding}"
    )

    return is_expanding


def detect_volatility_contraction(
    candles: Sequence[Candle],
    window_size: int = 20,
    contraction_threshold: float = 0.7,
) -> bool:
    """
    Detect if volatility is contracting (potential consolidation/range).

    Compares recent ATR to historical ATR to identify significant volatility
    decreases that may signal a consolidation phase or ranging market.

    Args:
        candles: Sequence of Candle objects with ATR values.
        window_size: Number of recent candles to compare. Default is 20.
        contraction_threshold: Ratio threshold for contraction detection.
            Default is 0.7 (30% decrease).

    Returns:
        True if volatility is contracting below threshold, False otherwise.

    Examples:
        >>> from datetime import datetime, timezone, timedelta
        >>> from models.core import Candle
        >>> base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        >>> # Create candles with decreasing ATR
        >>> candles = [
        ...     Candle(
        ...         timestamp_utc=base_time + timedelta(minutes=i),
        ...         open=1.1000, high=1.1010, low=1.0990, close=1.1005,
        ...         volume=1000.0, ema20=1.1000, ema50=1.0995,
        ...         atr=0.0020 if i < 30 else 0.0012,
        ...         rsi=50.0
        ...     )
        ...     for i in range(50)
        ... ]
        >>> contracting = detect_volatility_contraction(candles)
        >>> contracting
        True
    """
    if len(candles) < window_size * 2:
        logger.warning(
            f"Insufficient candles for contraction detection: "
            f"{len(candles)} provided, {window_size * 2} recommended"
        )
        return False

    # Get ATR values
    atr_values = np.array([c.atr for c in candles], dtype=np.float64)

    # Recent ATR (average of last window_size candles)
    recent_atr = float(np.mean(atr_values[-window_size:]))

    # Historical ATR (average of previous window_size candles)
    historical_atr = float(
        np.mean(atr_values[-2 * window_size : -window_size])
    )

    # Avoid division by zero
    if historical_atr == 0:
        logger.warning("Historical ATR is zero, cannot compute contraction ratio")
        return False

    # Compute contraction ratio
    contraction_ratio = recent_atr / historical_atr

    is_contracting = contraction_ratio <= contraction_threshold

    logger.debug(
        f"Volatility contraction check: ratio={contraction_ratio:.2f}, "
        f"threshold={contraction_threshold:.2f}, contracting={is_contracting}"
    )

    return is_contracting
