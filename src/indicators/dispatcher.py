"""
Indicator dispatcher for Polars-based vectorized indicators.

Parses indicator definitions (e.g., "ema20", "zscore(20)") and dispatches
to the appropriate calculation functions, preserving Polars performance.
"""

import re
import logging
from typing import Callable
import polars as pl

from src.backtest.vectorized_rolling_window import (
    calculate_ema,
    calculate_atr,
    calculate_rsi,
    calculate_stoch_rsi,
)
from src.indicators.stats import (
    calculate_zscore,
    calculate_rolling_mean,
    calculate_rolling_std,
)

logger = logging.getLogger(__name__)

# Type definition for indicator functions
# Func(df, period, [column, output_col, ...]) -> pl.DataFrame
IndicatorFunc = Callable[..., pl.DataFrame]

REGISTRY: dict[str, IndicatorFunc] = {
    # Standard indicators
    "ema": calculate_ema,
    "atr": calculate_atr,
    "rsi": calculate_rsi,
    "stoch_rsi": calculate_stoch_rsi,
    "stochrsi": calculate_stoch_rsi,
    # Statistical indicators
    "zscore": calculate_zscore,
    "mean": calculate_rolling_mean,
    "std": calculate_rolling_std,
}


def parse_indicator_string(indicator_str: str) -> tuple[str, dict]:
    """
    Parse an indicator string into name and arguments.

    Supports two formats:
    1. Legacy shorthand: "ema20" -> name="ema", args={"period": 20}
    2. Functional: "zscore(20)" -> name="zscore", args={"period": 20}
       "zscore(period=20, column='close')" -> name="zscore", args={...}

    Args:
        indicator_str: Indicator definition string.

    Returns:
        Tuple of (indicator_name, arguments_dict).
    """
    indicator_str = indicator_str.lower().strip()

    # Regex for functional format: name(args)
    # e.g., zscore(20) or ema(period=20)
    func_match = re.match(r"^([a-z_]+)\((.*)\)$", indicator_str)
    if func_match:
        name = func_match.group(1)
        args_str = func_match.group(2).strip()
        args = {}

        if args_str:
            # Simple parsing of comma-separated args
            # This is a basic parser; for complex cases, ast.literal_eval
            # might be safer/better
            parts = [p.strip() for p in args_str.split(",")]
            for i, part in enumerate(parts):
                if "=" in part:
                    key, value = part.split("=", 1)
                    args[key.strip()] = _parse_value(value.strip())
                else:
                    # Positional arg - assume first is always 'period' if integer
                    if i == 0:
                        args["period"] = _parse_value(part)
                    else:
                        logger.warning(
                            "Implicit positional argument index %d in '%s' might be ambiguous",  # pylint: disable=line-too-long
                            i,
                            indicator_str,
                        )
        return name, args

    # Regex for legacy format: name + digits
    # e.g., ema20, atr14
    legacy_match = re.match(r"^([a-z_]+)(\d+)$", indicator_str)
    if legacy_match:
        name = legacy_match.group(1)
        period = int(legacy_match.group(2))
        return name, {"period": period}

    # Fallback: just name (maybe defined with defaults?)
    return indicator_str, {}


def _parse_value(val_str: str) -> int | float | str:
    """Helper to parse definitions strings into types."""
    # Remove quotes
    if (val_str.startswith("'") and val_str.endswith("'")) or (
        val_str.startswith('"') and val_str.endswith('"')
    ):
        return val_str[1:-1]

    try:
        if "." in val_str:
            return float(val_str)
        return int(val_str)
    except ValueError:
        return val_str


def calculate_indicators(df: pl.DataFrame, indicators: list[str]) -> pl.DataFrame:
    """
    Calculate a list of indicators and append them to the DataFrame.

    Args:
        df: Input Polars DataFrame.
        indicators: List of indicator definition strings (e.g. ["ema20", "atr14"]).

    Returns:
        DataFrame with all calculated indicator columns.
    """
    if not indicators:
        return df

    for ind_str in indicators:
        try:
            name, kwargs = parse_indicator_string(ind_str)

            if name not in REGISTRY:
                logger.warning(
                    "Unknown indicator '%s' (parsed from '%s')", name, ind_str
                )
                continue

            func = REGISTRY[name]
            # Pass the original indicator string as output_col to preserve naming
            # (e.g., rsi14 instead of just rsi)
            if "output_col" not in kwargs:
                kwargs["output_col"] = ind_str
            df = func(df, **kwargs)

        except (ValueError, TypeError, pl.exceptions.PolarsError) as e:
            logger.error("Failed to calculate indicator '%s': %s", ind_str, e)
            continue

    return df
