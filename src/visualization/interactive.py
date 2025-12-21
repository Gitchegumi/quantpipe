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
        combined.columns = ["time", col]

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
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Optional[Chart]:
    """
    Render interactive chart with backtest results.

    Args:
        start_date: ISO start date string (e.g. '2023-01-01').
        end_date: ISO end date string.
    """
    logger.info("Preparing visualization for %s...", pair)

    # T005: Prepare Candle Data
    try:
        candles = _prepare_candle_data(data)
        if candles.empty:
            logger.error("No candle data available for visualization.")
            return None
    except ValueError as e:
        logger.error("Failed to prepare candle data: %s", e)
        return None

    # Determine Time Window
    # Ensure 'time' column is datetime
    if not pd.api.types.is_datetime64_any_dtype(candles["time"]):
        candles["time"] = pd.to_datetime(candles["time"])

    # Default to last 3 months (approx 90 days) if no range specified
    if not start_date and not end_date:
        last_date = candles["time"].max()
        cutoff_date = last_date - pd.Timedelta(days=90)
        start_date_ts = cutoff_date
        end_date_ts = last_date
        logger.info(
            "No window specified. Defaulting to last 3 months (%s to %s)",
            cutoff_date.date(),
            last_date.date(),
        )
    else:
        # Parse user inputs
        start_date_ts = (
            pd.to_datetime(start_date).tz_localize(None)
            if start_date
            else candles["time"].min().tz_localize(None)
        )
        end_date_ts = (
            pd.to_datetime(end_date).tz_localize(None)
            if end_date
            else candles["time"].max().tz_localize(None)
        )

        # Handle timezone naive vs aware mismatch
        # Candles are likely aware (UTC). Arguments converted to naive or aware?
        # If candles are aware, localize user inputs to UTC?
        if candles["time"].dt.tz is not None:
            if start_date_ts.tzinfo is None:
                start_date_ts = start_date_ts.tz_localize("UTC")
            if end_date_ts.tzinfo is None:
                end_date_ts = end_date_ts.tz_localize("UTC")

    # Apply Filtering
    # Filter candles
    mask = (candles["time"] >= start_date_ts) & (candles["time"] <= end_date_ts)
    candles = candles.loc[mask]

    if candles.empty:
        logger.error(
            "No data found in specified range: %s to %s", start_date_ts, end_date_ts
        )
        return None

    # Max Size Safety Check
    MAX_CANDLES = (
        50_000  # Lowered to 50k to prevent System.OverflowException in pywebview
    )

    if len(candles) > MAX_CANDLES:
        logger.warning(
            "Selected range too large (%d rows). Truncating to first %d candles of selection.",
            len(candles),
            MAX_CANDLES,
        )
        candles = candles.head(MAX_CANDLES)

    start_time = candles.iloc[0]["time"]
    end_time = candles.iloc[-1]["time"]

    # Initialize Chart
    chart = Chart(toolbox=True)
    chart.legend(visible=True)
    chart.topbar.textbox("pair", pair)

    # T013/T014: Interactive Configuration
    chart.crosshair(mode="normal")

    # Set Candles
    chart.set(candles)

    # T006: Add Indicators
    indicators = _prepare_indicator_data(data)
    for name, series in indicators.items():
        # Match truncation
        if len(candles) < len(data):
            # Filter series >= start_time
            # Assuming 'time' column in series matches
            if not series.empty:
                series = series[
                    (series["time"] >= start_time) & (series["time"] <= end_time)
                ]

        logger.debug("Adding indicator series: %s", name)
        line = chart.create_line(name=name)
        line.set(series)

    # T010: Add Trades
    series_start_time = candles.iloc[0]["time"] if not candles.empty else None
    series_end_time = candles.iloc[-1]["time"] if not candles.empty else None
    _add_trade_markers(
        chart, result, min_time=series_start_time, max_time=series_end_time
    )

    if show_plot:
        chart.show(block=True)

    return chart


def _add_trade_markers(
    chart: Chart, result: BacktestResult, min_time: Any = None, max_time: Any = None
) -> None:
    """
    Extract executions from BacktestResult and add them as markers to the chart.
    """
    if not result.executions:
        logger.info("No executions found to visualize.")
        return

    markers = []
    for trade in result.executions:
        try:
            # Handle TradeExecution object
            if hasattr(trade, "open_timestamp"):
                ts = trade.open_timestamp
                side = trade.direction
                price = trade.entry_fill_price
            elif isinstance(trade, dict):
                # Fallback for legacy/dict structures
                ts = trade.get("timestamp")
                side = trade.get("side")
                price = trade.get("price")
            else:
                # Unknown type
                logger.warning("Unknown trade object type: %s", type(trade))
                continue

            if not ts:
                continue

            # T028: Filter out trades outside the visualized data range
            # Use strict type alignment (pd.Timestamp) and timezone synchronization
            if min_time is not None:
                t_comp = pd.to_datetime(ts)
                min_comp = pd.to_datetime(min_time)

                # Handle timezone naive vs aware mismatch (assume UTC if one is missing)
                if t_comp.tzinfo is not None and min_comp.tzinfo is None:
                    min_comp = min_comp.tz_localize("UTC")
                elif t_comp.tzinfo is None and min_comp.tzinfo is not None:
                    t_comp = t_comp.tz_localize("UTC")

                # REJECT if trade is strictly before start (or essentially equal, to avoid edge cases)
                # Adding 1 microsecond buffer to be safe against floating point equality issues in library
                if t_comp < min_comp:
                    continue

            if max_time is not None:
                t_comp = pd.to_datetime(ts)
                max_comp = pd.to_datetime(max_time)

                if t_comp.tzinfo is not None and max_comp.tzinfo is None:
                    max_comp = max_comp.tz_localize("UTC")
                elif t_comp.tzinfo is None and max_comp.tzinfo is not None:
                    t_comp = t_comp.tz_localize("UTC")

                # Strict check for max
                if t_comp > max_comp:
                    continue

            # Ensure side is normalized
            side = side.upper() if side else ""

            if side == "LONG" or side == "BUY":
                markers.append(
                    {
                        "time": ts,
                        "position": "belowBar",
                        "color": "#2196F3",  # Blue
                        "shape": "arrowUp",
                        "text": f"Buy @ {price}",
                    }
                )
            elif side == "SHORT" or side == "SELL":
                markers.append(
                    {
                        "time": ts,
                        "position": "aboveBar",
                        "color": "#E91E63",  # Pink
                        "shape": "arrowDown",
                        "text": f"Sell @ {price}",
                    }
                )
        except Exception as e:
            logger.warning("Failed to parse trade for visualization: %s", e)
            continue

    if markers:
        # Sort markers by time (required by library)
        markers.sort(key=lambda x: x["time"])
        try:
            chart.marker(markers)
        except Exception as e:
            logger.error("\nFailed to add markers: %s", e)
