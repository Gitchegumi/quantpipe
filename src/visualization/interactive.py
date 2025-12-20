import logging
from pathlib import Path
from typing import Optional, Union, List, Any
import polars as pl
import pandas as pd
from lightweight_charts import Chart
from src.models.directional import BacktestResult

logger = logging.getLogger(__name__)


def _prepare_candle_data(data: pl.DataFrame) -> pd.DataFrame:
    """
    Convert Polars DataFrame to pandas DataFrame with OHLC columns expected by lightweight-charts.
    Handles missing data by forward filling or dropping/warning as appropriate.
    """
    required_cols = ["timestamp_utc", "open", "high", "low", "close"]

    # Validation: Check for missing columns
    missing = [c for c in required_cols if c not in data.columns]
    if missing:
        raise ValueError(f"Missing required columns for visualization: {missing}")

    # Select and rename to standard lower-case for uniformity (though input is likely already lower)
    df = data.select(required_cols).to_pandas()

    # Rename 'timestamp_utc' to 'time' or 'date' if needed by library,
    # but lightweight-charts typically accepts 'time' or 'date'.
    df = df.rename(columns={"timestamp_utc": "time"})

    # Drop rows with NaN in OHLC to prevent rendering issues
    initial_len = len(df)
    df = df.dropna(subset=["open", "high", "low", "close"])
    if len(df) < initial_len:
        logger.warning("Dropped %d rows with missing OHLC data", initial_len - len(df))

    return df


def _prepare_indicator_data(data: pl.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Extract indicator columns from DataFrame.
    Returns a dict mapping indicator name to its data series (pandas DataFrame with 'time' and 'value').
    """
    # Exclude OHLC and strict system columns
    exclude_cols = {
        "timestamp_utc",
        "open",
        "high",
        "low",
        "close",
        "date",
        "time",
        "symbol",
    }
    indicator_cols = [c for c in data.columns if c not in exclude_cols]

    indicators = {}
    if not indicator_cols:
        return indicators

    # Get base time series
    time_series = (
        data.select("timestamp_utc")
        .to_pandas()
        .rename(columns={"timestamp_utc": "time"})
    )

    for col in indicator_cols:
        # Extract column
        series = data.select(col).to_pandas()

        # Combine with time
        combined = pd.concat([time_series, series], axis=1)
        combined.columns = ["time", "value"]

        # Drop NaNs for line series (gaps are handled by not plotting points)
        combined = combined.dropna()

        if not combined.empty:
            indicators[col] = combined

    return indicators


def plot_backtest_results(
    data: pl.DataFrame,
    result: BacktestResult,
    pair: str,
    output_file: Optional[Union[str, Path]] = None,
    show_plot: bool = True,
) -> None:
    """
    Render interactive chart with backtest results.
    """
    logger.info("Preparing visualization for %s...", pair)

    # T005: Prepare Candle Data
    try:
        candles = _prepare_candle_data(data)
    except ValueError as e:
        logger.error("Failed to prepare candle data: %s", e)
        return

    # Initialize Chart
    chart = Chart(toolbox=True)
    chart.legend(visible=True)
    chart.topbar.textbox("pair", pair)

    # Set Candles
    # lightweight-charts-python expects a dataframe with time, open, high, low, close
    chart.set(candles)

    # T006: Add Indicators
    indicators = _prepare_indicator_data(data)
    for name, series in indicators.items():
        line = chart.create_line(name=name)
        line.set(series)

    # TODO: T010 Add Trades

    if show_plot:
        chart.show(block=True)
