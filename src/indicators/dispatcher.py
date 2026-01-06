"""
Indicator dispatcher for Polars-based vectorized indicators.

Parses indicator definitions (e.g., "ema20", "zscore(20)") and dispatches
to the appropriate calculation functions, preserving Polars performance.
"""

import re
import logging
from typing import Callable, Any
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
    "fast_ema": calculate_ema,
    "slow_ema": calculate_ema,
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

    # Fallback: handle semantic names without periods
    if indicator_str == "fast_ema":
        return "ema", {"period": 20, "output_col": "fast_ema"}
    if indicator_str == "slow_ema":
        return "ema", {"period": 50, "output_col": "slow_ema"}
    if indicator_str == "atr":
        return "atr", {"period": 14, "output_col": "atr"}
    if indicator_str == "rsi":
        return "rsi", {"period": 14, "output_col": "rsi"}
    if indicator_str == "stoch_rsi":
        return "stoch_rsi", {"period": 14, "output_col": "stoch_rsi"}

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


def calculate_indicators(
    df: pl.DataFrame,
    indicators: list[str],
    overrides: dict[str, dict[str, Any]] | None = None,
) -> pl.DataFrame:
    """
    Calculate a list of indicators and append them to the DataFrame.

    Args:
        df: Input Polars DataFrame.
        indicators: List of indicator definition strings (e.g. ["ema20", "atr14"]).
        overrides: Optional dict mapping indicator strings to parameter overrides.
                   e.g. {"fast_ema": {"period": 10}}

    Returns:
        DataFrame with all calculated indicator columns.
    """
    if not indicators:
        return df

    if overrides is None:
        overrides = {}

    for ind_str in indicators:
        try:
            name, kwargs = parse_indicator_string(ind_str)

            # Apply overrides if present
            # Apply overrides if present
            # matching either the full string (rare) or the parsed name
            if ind_str in overrides:
                kwargs.update(overrides[ind_str])
            elif name in overrides:
                kwargs.update(overrides[name])

            logger.info(
                "Parsing indicator: %s -> name=%s, kwargs=%s", ind_str, name, kwargs
            )

            if name not in REGISTRY:
                logger.warning(
                    "Unknown indicator '%s' (parsed from '%s'). Registry: %s",
                    name,
                    ind_str,
                    list(REGISTRY.keys()),
                )
                continue

            func = REGISTRY[name]
            # Pass the original indicator string as output_col to preserve naming
            # (e.g., rsi14 instead of just rsi)
            if "output_col" not in kwargs:
                kwargs["output_col"] = ind_str

            # Special handling for stoch_rsi
            if name in ("stoch_rsi", "stochrsi"):
                # Map stoch_period -> period for the stoch calculation
                if "stoch_period" in kwargs:
                    kwargs["period"] = kwargs.pop("stoch_period")

                # Handle rsi_period for base RSI calculation
                # We pop it so it's not passed to calculate_stoch_rsi
                rsi_period = kwargs.pop("rsi_period", 14)

                if "rsi_col" not in kwargs:
                    # Look for existing RSI column with matching period
                    # Heuristic: try "rsi" or "rsi{rsi_period}"
                    candidates = ["rsi", f"rsi{rsi_period}"]
                    found_col = next((c for c in candidates if c in df.columns), None)

                    if not found_col:
                        # Fallback: check any column starting with "rsi"
                        rsi_cols = [col for col in df.columns if col.startswith("rsi")]
                        if rsi_cols:
                            found_col = rsi_cols[0]

                    if not found_col:
                        # Calculate base RSI
                        # We MUST output to "rsi" column because generate_signals_vectorized
                        # expects "rsi" to exist.
                        logger.info(
                            "Calculating base RSI for stoch_rsi with period %s",
                            rsi_period,
                        )
                        rsi_out_col = "rsi"
                        df = REGISTRY["rsi"](
                            df, period=rsi_period, output_col=rsi_out_col
                        )
                        kwargs["rsi_col"] = rsi_out_col
                    else:
                        kwargs["rsi_col"] = found_col

            df = func(df, **kwargs)

        except (ValueError, TypeError, pl.exceptions.PolarsError) as e:
            logger.error("Failed to calculate indicator '%s': %s", ind_str, e)
            continue

    return df
