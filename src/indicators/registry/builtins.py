"""Built-in indicator registration.

This module registers all built-in indicators (EMA, ATR, StochRSI) with
the global indicator registry at module import time.
"""

import logging
from typing import Any

import pandas as pd

from src.indicators.builtin.atr import compute_atr
from src.indicators.builtin.ema import compute_ema
from src.indicators.builtin.stochrsi import compute_stoch_rsi
from src.indicators.registry.specs import IndicatorSpec
from src.indicators.registry.store import get_registry


logger = logging.getLogger(__name__)


def _ema_wrapper(df: pd.DataFrame, params: dict[str, Any]) -> dict[str, pd.Series]:
    """Wrapper for EMA computation to match IndicatorSpec signature.

    Args:
        df: DataFrame containing OHLCV data.
        params: Parameters including 'period' and optionally 'column'.

    Returns:
        Dict[str, pd.Series]: Computed EMA series.
    """
    period = params.get("period", 20)
    column = params.get("column", "close")
    return compute_ema(df, period=period, column=column)


def _atr_wrapper(df: pd.DataFrame, params: dict[str, Any]) -> dict[str, pd.Series]:
    """Wrapper for ATR computation to match IndicatorSpec signature.

    Args:
        df: DataFrame containing OHLCV data.
        params: Parameters including 'period'.

    Returns:
        Dict[str, pd.Series]: Computed ATR series.
    """
    period = params.get("period", 14)
    return compute_atr(df, period=period)


def _stoch_rsi_wrapper(
    df: pd.DataFrame, params: dict[str, Any]
) -> dict[str, pd.Series]:
    """Wrapper for StochRSI computation to match IndicatorSpec signature.

    Args:
        df: DataFrame containing OHLCV data.
        params: Parameters including 'rsi_period', 'stoch_period', 'column'.

    Returns:
        Dict[str, pd.Series]: Computed StochRSI series.
    """
    rsi_period = params.get("rsi_period", 14)
    stoch_period = params.get("stoch_period", 14)
    column = params.get("column", "close")
    return compute_stoch_rsi(
        df, rsi_period=rsi_period, stoch_period=stoch_period, column=column
    )


def register_builtins() -> None:
    """Register all built-in indicators with the global registry.

    Registers:
    - ema20: EMA with 20-period default
    - ema50: EMA with 50-period default
    - atr14: ATR with 14-period default
    - stoch_rsi: Stochastic RSI with default parameters

    This function is idempotent - calling multiple times is safe.
    """
    registry = get_registry()

    # Register EMA20
    try:
        ema20_spec = IndicatorSpec(
            name="ema20",
            requires=["close"],
            provides=["ema20"],
            compute=_ema_wrapper,
            version="1.0.0",
            params={"period": 20, "column": "close"},
        )
        registry.register(ema20_spec)
        logger.debug("Registered built-in indicator: ema20")
    except ValueError:
        logger.debug("Indicator ema20 already registered")

    # Register EMA50
    try:
        ema50_spec = IndicatorSpec(
            name="ema50",
            requires=["close"],
            provides=["ema50"],
            compute=_ema_wrapper,
            version="1.0.0",
            params={"period": 50, "column": "close"},
        )
        registry.register(ema50_spec)
        logger.debug("Registered built-in indicator: ema50")
    except ValueError:
        logger.debug("Indicator ema50 already registered")

    # Register ATR14
    try:
        atr14_spec = IndicatorSpec(
            name="atr14",
            requires=["high", "low", "close"],
            provides=["atr14"],
            compute=_atr_wrapper,
            version="1.0.0",
            params={"period": 14},
        )
        registry.register(atr14_spec)
        logger.debug("Registered built-in indicator: atr14")
    except ValueError:
        logger.debug("Indicator atr14 already registered")

    # Register StochRSI
    try:
        stoch_rsi_spec = IndicatorSpec(
            name="stoch_rsi",
            requires=["close"],
            provides=["stoch_rsi"],
            compute=_stoch_rsi_wrapper,
            version="1.0.0",
            params={"rsi_period": 14, "stoch_period": 14, "column": "close"},
        )
        registry.register(stoch_rsi_spec)
        logger.debug("Registered built-in indicator: stoch_rsi")
    except ValueError:
        logger.debug("Indicator stoch_rsi already registered")

    logger.info("Built-in indicators registered: ema20, ema50, atr14, stoch_rsi")


# Auto-register on module import
register_builtins()
