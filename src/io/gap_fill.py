"""Gap filling synthesizer with vectorized operations.

This module provides utilities for filling gaps in candle data using
vectorized forward-fill operations and marking synthetic rows.

**Important**: Gap filling creates synthetic price data and should be used
sparingly. The primary use case is during **timeframe resampling** (e.g., 
1-minute → 5-minute → 1-hour candles), not during raw data ingestion. 
During ingestion, gaps should be preserved as they represent actual market 
closures (weekends, holidays, illiquid periods). Future specification will 
implement proper resampling with appropriate gap handling.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def synthesize_gap_values(df: pd.DataFrame) -> pd.DataFrame:
    """Fill gap rows with synthesized OHLCV values.

    Gap filling rules:
    - open, high, low: Forward-fill from previous close
    - close: Forward-fill from previous close
    - volume: Set to 0.0
    - is_gap: Set to True for synthetic rows

    Args:
        df: DataFrame with gaps (NaN values).

    Returns:
        pd.DataFrame: DataFrame with gaps filled.
    """
    # Create is_gap column to mark synthetic rows
    df["is_gap"] = df["close"].isna()

    # Forward-fill close values
    df["close"] = df["close"].ffill()

    # For gap rows, set open/high/low equal to the forward-filled close
    # (representing no price movement in synthetic intervals)
    gap_mask = df["is_gap"]

    df.loc[gap_mask, "open"] = df.loc[gap_mask, "close"]
    df.loc[gap_mask, "high"] = df.loc[gap_mask, "close"]
    df.loc[gap_mask, "low"] = df.loc[gap_mask, "close"]
    df.loc[gap_mask, "volume"] = 0.0

    # Ensure non-gap rows have is_gap=False
    df.loc[~gap_mask, "is_gap"] = False

    gaps_filled = gap_mask.sum()
    logger.info("Filled %d gap rows with synthetic values", gaps_filled)

    return df


def fill_gaps_vectorized(
    df: pd.DataFrame, timeframe_minutes: int
) -> tuple[pd.DataFrame, int]:
    """Fill gaps in candle data using vectorized operations.

    This function combines reindexing and gap value synthesis in a
    vectorized manner without per-row loops.

    Args:
        df: DataFrame with 'timestamp_utc' and OHLCV columns.
        timeframe_minutes: Expected cadence in minutes.

    Returns:
        tuple: (filled_df, count_gaps)
    """
    from .gaps import reindex_with_gaps

    # Reindex to create gap placeholders
    reindexed_df, count_gaps = reindex_with_gaps(df, timeframe_minutes)

    # Synthesize gap values
    filled_df = synthesize_gap_values(reindexed_df)

    # Reset index to make timestamp_utc a column again
    filled_df = filled_df.reset_index(names=["timestamp_utc"])

    return filled_df, count_gaps
