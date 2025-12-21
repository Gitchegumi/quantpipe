"""
Datashader-based backtest visualization.

Uses HoloViews + Datashader for efficient rendering of large datasets (millions of points).
Designed for backtest analysis where 1-minute precision is required without downsampling.

Features:
- Candlestick charts with datashading
- Trade boxes with TP/SL zones
- Indicator overlays
- Multi-symbol support
- Dollar-based portfolio value curve
- HTML export to /results/dashboards/
"""

import logging
import warnings
from pathlib import Path
from typing import Optional, Union, Any, Dict, List

import polars as pl
import pandas as pd
import numpy as np

try:
    import holoviews as hv
    import hvplot.pandas  # noqa: F401 - Required for hvplot extension
    import panel as pn
    from bokeh.models import HoverTool

    # Suppress Bokeh integer precision warnings (from nanosecond timestamps)
    warnings.filterwarnings(
        "ignore", message="out of range integer", category=UserWarning
    )

    HAS_DATASHADER = True
except ImportError:
    HAS_DATASHADER = False

from src.models.directional import BacktestResult

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_INITIAL_BALANCE = 2_500.0
DEFAULT_RISK_PER_TRADE = 6.25  # $6.25 per 1R (0.25% of $2,500)


def _to_naive_datetime(ts) -> pd.Timestamp:
    """Convert any timestamp to timezone-naive datetime64[ns].

    This ensures all plotted timestamps have the same dtype,
    preventing UFuncTypeError in HoloViews overlay comparisons.
    """
    ts = pd.to_datetime(ts)
    if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
        ts = ts.tz_localize(None)
    return ts


def plot_backtest_results(
    data: pl.DataFrame,
    result: BacktestResult,
    pair: str,
    output_file: Optional[Union[str, Path]] = None,
    show_plot: bool = True,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    initial_balance: float = DEFAULT_INITIAL_BALANCE,
    risk_per_trade: float = DEFAULT_RISK_PER_TRADE,
    timeframe: str = "1m",
) -> Optional[Any]:
    """
    Render interactive backtest visualization using Datashader.

    Args:
        data: Polars DataFrame with OHLC data and indicators.
        result: BacktestResult containing trade executions.
        pair: Trading pair symbol.
        output_file: Optional path to save as HTML.
        show_plot: Whether to display interactive plot.
        start_date: Optional start date filter (YYYY-MM-DD).
        end_date: Optional end date filter (YYYY-MM-DD).
        initial_balance: Starting portfolio balance in dollars.
        risk_per_trade: Dollar amount risked per 1R.
        timeframe: Timeframe of the data (e.g., '15m', '1h').

    Returns:
        HoloViews layout object, or None if dependencies missing.
    """
    if not HAS_DATASHADER:
        logger.error(
            "Datashader visualization requires: holoviews, hvplot, panel. "
            "Install with: poetry add holoviews hvplot panel"
        )
        return None

    logger.info("Preparing Datashader visualization for %s...", pair)

    # Initialize HoloViews with Bokeh backend
    hv.extension("bokeh")

    # Handle multi-symbol results
    if result.is_multi_symbol and result.results:
        return _create_multi_symbol_layout(
            data,
            result,
            start_date,
            end_date,
            initial_balance,
            risk_per_trade,
            show_plot,
            output_file,
            timeframe,
        )

    # Single symbol visualization
    return _create_single_symbol_layout(
        data,
        result,
        pair,
        start_date,
        end_date,
        initial_balance,
        risk_per_trade,
        show_plot,
        output_file,
        timeframe,
    )


def _create_single_symbol_layout(
    data: pl.DataFrame,
    result: BacktestResult,
    pair: str,
    start_date: Optional[str],
    end_date: Optional[str],
    initial_balance: float,
    risk_per_trade: float,
    show_plot: bool,
    output_file: Optional[Union[str, Path]],
    timeframe: str = "1m",
) -> Optional[Any]:
    """Create visualization for a single symbol."""
    # Prepare data
    df = _prepare_data(data, start_date, end_date)
    if df is None or df.is_empty():
        logger.error("No data available for visualization.")
        return None

    logger.info("Visualizing %d candles for %s.", len(df), pair)
    pdf = df.to_pandas()

    # Create components
    price_chart, xlim = _create_candlestick_chart(pdf, pair)
    trade_boxes = _create_trade_boxes(result, pdf)
    indicator_overlays, oscillator_panel = _create_indicator_overlays(pdf, pair, xlim)
    portfolio_curve = _create_portfolio_curve(result, initial_balance, risk_per_trade)

    # Combine price chart with trade boxes and indicator overlays
    combined = price_chart
    if trade_boxes:
        combined = combined * trade_boxes
    if indicator_overlays:
        combined = combined * indicator_overlays

    # Stack charts vertically: price (with overlays) + oscillators + portfolio
    charts = [combined]
    if oscillator_panel:
        charts.append(oscillator_panel)
    if portfolio_curve:
        charts.append(portfolio_curve)

    if len(charts) > 1:
        # shared_axes=True links x-axis for synchronized panning
        layout = hv.Layout(charts).cols(1).opts(shared_axes=True)
    else:
        layout = combined

    # Title includes pair and timeframe (e.g., "Backtest: EURUSD (15m)")
    title = (
        f"Backtest: {pair}" if timeframe == "1m" else f"Backtest: {pair} ({timeframe})"
    )
    layout = layout.opts(title=title)

    # Save and show
    _save_and_show(layout, result.run_id, output_file, show_plot, result)

    return layout


def _create_multi_symbol_layout(
    data: pl.DataFrame,
    result: BacktestResult,
    start_date: Optional[str],
    end_date: Optional[str],
    initial_balance: float,
    risk_per_trade: float,
    show_plot: bool,
    output_file: Optional[Union[str, Path]],
    timeframe: str = "1m",
) -> Optional[Any]:
    """Create visualization with separate chart per symbol."""
    charts = []

    for symbol, symbol_result in result.results.items():
        # Filter data for this symbol
        symbol_data = (
            data.filter(pl.col("symbol") == symbol)
            if "symbol" in data.columns
            else data
        )

        df = _prepare_data(symbol_data, start_date, end_date)
        if df is None or df.is_empty():
            logger.warning("No data for symbol %s, skipping.", symbol)
            continue

        pdf = df.to_pandas()

        price_chart = _create_candlestick_chart(pdf, symbol)
        trade_boxes = _create_trade_boxes(symbol_result, pdf)
        indicators = _create_indicator_overlays(pdf)

        combined = price_chart
        if trade_boxes:
            combined = combined * trade_boxes
        if indicators:
            combined = combined * indicators

        charts.append(combined)

    if not charts:
        logger.error("No charts created.")
        return None

    # Aggregate portfolio curve across all symbols
    portfolio_curve = _create_portfolio_curve(result, initial_balance, risk_per_trade)

    # Stack charts vertically
    layout = hv.Layout(charts).cols(1)
    if portfolio_curve:
        layout = layout + portfolio_curve

    # Title includes timeframe (e.g., "Multi-Symbol Backtest (15m)")
    title = (
        "Multi-Symbol Backtest"
        if timeframe == "1m"
        else f"Multi-Symbol Backtest ({timeframe})"
    )
    layout = layout.opts(title=title, shared_axes=False)

    _save_and_show(layout, result.run_id, output_file, show_plot)

    return layout


def _prepare_data(
    data: pl.DataFrame,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Optional[pl.DataFrame]:
    """Filter and prepare data for visualization."""
    # Maximum candles OHLC chart can handle efficiently
    MAX_CANDLES = 500_000

    required_cols = ["timestamp_utc", "open", "high", "low", "close"]
    missing = [c for c in required_cols if c not in data.columns]
    if missing:
        logger.error("Missing required columns: %s", missing)
        return None

    df = data.clone()

    if start_date:
        df = df.filter(pl.col("timestamp_utc") >= pl.lit(start_date).str.to_datetime())
    if end_date:
        df = df.filter(pl.col("timestamp_utc") <= pl.lit(end_date).str.to_datetime())

    df = df.sort("timestamp_utc")

    # Limit data size for performance
    if len(df) > MAX_CANDLES:
        df = df.tail(MAX_CANDLES)
        logger.info(
            "Limited to last %d candles for performance. Use --viz-start/--viz-end to view specific range.",
            MAX_CANDLES,
        )

    return df


def _create_candlestick_chart(pdf: pd.DataFrame, pair: str) -> Any:
    """Create candlestick chart using hvplot."""
    # Prepare data
    if "timestamp_utc" in pdf.columns:
        pdf = pdf.set_index("timestamp_utc")

    pdf.index.name = "time"

    # Enforce consistent datetime64[ns] naive dtype on index
    pdf.index = pd.to_datetime(pdf.index).tz_localize(None)

    pdf = pdf.dropna(subset=["open", "high", "low", "close"])

    # Add pre-formatted time string column for tooltip display
    # This avoids issues with Bokeh's datetime formatter and epoch milliseconds
    pdf = pdf.copy()
    pdf["time_str"] = pdf.index.strftime("%Y-%m-%d %H:%M")

    # Set initial zoom to last 60 candles (works for any timeframe)
    INITIAL_CANDLE_COUNT = 60

    last_time = pdf.index[-1]
    if len(pdf) > INITIAL_CANDLE_COUNT:
        initial_start = pdf.index[-INITIAL_CANDLE_COUNT]
    else:
        initial_start = pdf.index[0]

    xlim = (initial_start, last_time)

    # Calculate y-axis range from visible data only
    visible_pdf = pdf.loc[initial_start:last_time]
    if len(visible_pdf) > 0:
        ylim = _calculate_price_range(visible_pdf, pair)
    else:
        ylim = _calculate_price_range(pdf, pair)

    # Determine decimal places based on pair type
    is_jpy_pair = "JPY" in pair.upper()
    price_format = "0.000" if is_jpy_pair else "0.00000"

    # Create custom tooltips for OHLC chart
    tooltips = [
        ("Time", "@time_str"),
        ("Open", f"@open{{{price_format}}}"),
        ("High", f"@high{{{price_format}}}"),
        ("Low", f"@low{{{price_format}}}"),
        ("Close", f"@close{{{price_format}}}"),
    ]

    chart = pdf.hvplot.ohlc(
        y=["open", "high", "low", "close"],
        neg_color="red",
        pos_color="green",
        height=400,
        width=1200,
        title=pair,
        ylim=ylim,
        xlim=xlim,
        hover_cols=["time_str", "open", "high", "low", "close"],
    ).opts(
        tools=[
            "pan",
            "wheel_zoom",
            "box_zoom",
            "reset",
            HoverTool(tooltips=tooltips, mode="vline"),
        ],
        active_tools=["pan", "wheel_zoom"],
    )

    return chart, xlim


def _calculate_price_range(pdf: pd.DataFrame, pair: str) -> tuple:
    """Calculate sensible y-axis range with outlier removal."""
    # Determine max reasonable price based on pair type
    is_jpy_pair = "JPY" in pair.upper()
    max_reasonable = 200.0 if is_jpy_pair else 2.0

    # Filter out outliers
    high_prices = pdf["high"]
    low_prices = pdf["low"]

    valid_high = high_prices[high_prices <= max_reasonable]
    valid_low = low_prices[low_prices <= max_reasonable]

    if valid_high.empty or valid_low.empty:
        # Fallback to unfiltered if all data would be removed
        valid_high = high_prices
        valid_low = low_prices

    # Use percentiles to remove extreme outliers
    price_max = valid_high.quantile(0.999)  # 99.9th percentile
    price_min = valid_low.quantile(0.001)  # 0.1th percentile

    # Add 2% padding
    padding = (price_max - price_min) * 0.02

    return (price_min - padding, price_max + padding)


def _create_trade_boxes(result: BacktestResult, pdf: pd.DataFrame) -> Optional[Any]:
    """Create trade entry/exit markers with connecting lines."""
    if not result.executions:
        return None

    # Get the time range of the visible data (using consistent dtype)
    if "timestamp_utc" in pdf.columns:
        data_min_time = _to_naive_datetime(pdf["timestamp_utc"].min())
        data_max_time = _to_naive_datetime(pdf["timestamp_utc"].max())
    else:
        data_min_time = _to_naive_datetime(pdf.index.min())
        data_max_time = _to_naive_datetime(pdf.index.max())

    entries = []
    exits = []

    for trade in result.executions:
        if not hasattr(trade, "open_timestamp"):
            continue

        # Use helper for consistent datetime dtype
        entry_time = _to_naive_datetime(trade.open_timestamp)
        exit_time = _to_naive_datetime(trade.close_timestamp)

        # Only include trades within the visible data range
        if entry_time < data_min_time or entry_time > data_max_time:
            continue

        entry_price = trade.entry_fill_price
        exit_price = trade.exit_fill_price
        pnl_r = trade.pnl_r
        direction = trade.direction.upper() if trade.direction else "LONG"

        # Calculate TP and SL levels (2R target, 1R stop)
        risk = abs(exit_price - entry_price) / max(abs(pnl_r), 0.01)
        if direction == "LONG":
            tp_price = entry_price + 2 * risk
            sl_price = entry_price - risk
        else:
            tp_price = entry_price - 2 * risk
            sl_price = entry_price + risk

        entries.append(
            {
                "time": entry_time,
                "exit_time": exit_time,
                "price": entry_price,
                "tp_price": tp_price,
                "sl_price": sl_price,
                "direction": direction,
                "pnl_r": pnl_r,
            }
        )

        exits.append(
            {
                "time": exit_time,
                "price": exit_price,
                "pnl_r": pnl_r,
            }
        )

    if not entries:
        logger.info("No trades in visible time range.")
        return None

    # Create DataFrames
    entries_df = pd.DataFrame(entries)
    exits_df = pd.DataFrame(exits)

    # Entry markers: Green triangles for long, Red inverted triangles for short
    longs = entries_df[entries_df["direction"] == "LONG"]
    shorts = entries_df[entries_df["direction"] == "SHORT"]

    markers = None

    if not longs.empty:
        long_markers = longs.hvplot.scatter(
            x="time",
            y="price",
            color="green",
            marker="triangle",
            size=80,
            alpha=0.9,
            label="Long Entry",
        )
        markers = long_markers

    if not shorts.empty:
        short_markers = shorts.hvplot.scatter(
            x="time",
            y="price",
            color="red",
            marker="inverted_triangle",
            size=80,
            alpha=0.9,
            label="Short Entry",
        )
        markers = markers * short_markers if markers else short_markers

    # Exit markers: Cyan diamonds for winners, Orange for losers
    if not exits_df.empty:
        winners = exits_df[exits_df["pnl_r"] > 0]
        losers = exits_df[exits_df["pnl_r"] <= 0]

        if not winners.empty:
            winner_markers = winners.hvplot.scatter(
                x="time",
                y="price",
                color="cyan",
                marker="diamond",
                size=100,
                alpha=1.0,
                label="Win Exit",
            )
            markers = markers * winner_markers if markers else winner_markers

        if not losers.empty:
            loser_markers = losers.hvplot.scatter(
                x="time",
                y="price",
                color="orange",
                marker="diamond",
                size=100,
                alpha=1.0,
                label="Loss Exit",
            )
            markers = markers * loser_markers if markers else loser_markers

    # Add connecting lines between entry and exit (limited for performance)
    MAX_LINES = 100
    num_trades = min(len(entries), MAX_LINES)

    if num_trades > 0:
        # Use last N trades (most recent)
        recent_entries = entries[-num_trades:]
        recent_exits = exits[-num_trades:]

        # Create entry-exit connecting lines, TP lines, and SL lines
        lines = None
        for entry, exit_pt in zip(recent_entries, recent_exits):
            entry_time = entry["time"]
            exit_time = entry.get("exit_time", exit_pt["time"])

            # Entry to exit connecting line (gray dashed)
            line_df = pd.DataFrame(
                [
                    {"time": entry_time, "price": entry["price"]},
                    {"time": exit_time, "price": exit_pt["price"]},
                ]
            )
            line = line_df.hvplot.line(
                x="time",
                y="price",
                color="gray",
                alpha=0.4,
                line_width=1,
                line_dash="dashed",
            )
            lines = lines * line if lines else line

            # TP level line (green dashed)
            tp_df = pd.DataFrame(
                [
                    {"time": entry_time, "price": entry["tp_price"]},
                    {"time": exit_time, "price": entry["tp_price"]},
                ]
            )
            tp_line = tp_df.hvplot.line(
                x="time",
                y="price",
                color="green",
                alpha=0.5,
                line_width=1,
                line_dash="dotted",
            )
            lines = lines * tp_line

            # SL level line (red dashed)
            sl_df = pd.DataFrame(
                [
                    {"time": entry_time, "price": entry["sl_price"]},
                    {"time": exit_time, "price": entry["sl_price"]},
                ]
            )
            sl_line = sl_df.hvplot.line(
                x="time",
                y="price",
                color="red",
                alpha=0.5,
                line_width=1,
                line_dash="dotted",
            )
            lines = lines * sl_line

        if lines:
            markers = markers * lines if markers else lines
            logger.info("Added %d trade lines (entry-exit + TP/SL).", num_trades)

    logger.info("Created %d trade markers.", len(entries))

    return markers


def _create_indicator_overlays(
    pdf: pd.DataFrame, pair: str, xlim: tuple = None
) -> tuple:
    """Create indicator overlays and oscillator panels.

    Returns tuple of (price_overlays, oscillator_panel).
    - price_overlays: EMAs, etc. to overlay on price chart
    - oscillator_panel: RSI, StochRSI, etc. to show below price chart
    """
    # Identify indicator columns (non-OHLC)
    exclude = {
        "time_str",
        "timestamp_utc",
        "open",
        "high",
        "low",
        "close",
        "time",
        "symbol",
        "date",
        "volume",
    }
    indicator_cols = [c for c in pdf.columns if c.lower() not in exclude]

    if not indicator_cols:
        return None, None

    # Separate price-scale indicators from oscillators
    oscillator_patterns = ["rsi", "stoch"]
    price_indicator_patterns = ["ema", "sma", "ma", "atr"]

    price_indicators = []
    oscillators = []

    for col in indicator_cols:
        col_lower = col.lower()
        if any(p in col_lower for p in oscillator_patterns):
            oscillators.append(col)
        elif any(p in col_lower for p in price_indicator_patterns):
            price_indicators.append(col)

    # Always build 'time' from real timestamps (NOT the RangeIndex)
    ind_df = pdf.copy()

    if "timestamp_utc" in ind_df.columns:
        ind_df["time"] = pd.to_datetime(ind_df["timestamp_utc"]).dt.tz_localize(None)
    elif ind_df.index.name == "time":
        ind_df = ind_df.reset_index()
        ind_df["time"] = pd.to_datetime(ind_df["time"]).dt.tz_localize(None)
    else:
        # Last resort: try index, but this is usually wrong for your workflow
        ind_df["time"] = pd.to_datetime(ind_df.index).tz_localize(None)

    # Create price overlays (EMAs, etc.) using time column
    overlays = None
    ema_colors = {"ema20": "yellow", "ema50": "cyan", "ema200": "magenta"}

    for col in price_indicators[:3]:  # Limit to 3 for clarity
        if col in ind_df.columns:
            # Filter out NaN values for clean line rendering
            ema_df = ind_df[["time", col]].dropna()
            if ema_df.empty:
                continue

            color = ema_colors.get(col.lower(), "white")
            line = ema_df.hvplot.line(
                x="time",
                y=col,
                label=col,
                line_width=1.5,
                color=color,
                alpha=0.9,
                xlim=xlim,
            )
            overlays = overlays * line if overlays else line
            logger.debug(
                "EMA %s has %d points, range: %.5f - %.5f",
                col,
                len(ema_df),
                ema_df[col].min(),
                ema_df[col].max(),
            )

    if price_indicators:
        logger.info(
            "Added %d price indicator overlays: %s",
            len(price_indicators[:3]),
            price_indicators[:3],
        )

    # Create oscillator panel (RSI, StochRSI) using time column
    oscillator_panel = None
    osc_colors = {
        "rsi14": "yellow",
        "stoch_rsi": "cyan",
        "stoch_rsi_k": "cyan",
        "stoch_rsi_d": "magenta",
    }

    for col in oscillators[:2]:  # Limit to 2 oscillators
        if col in ind_df.columns:
            # Filter out NaN values for clean line rendering
            osc_df = ind_df[["time", col]].dropna()
            if osc_df.empty:
                continue

            color = osc_colors.get(col.lower(), "white")
            line = osc_df.hvplot.line(
                x="time",
                y=col,
                label=col,
                line_width=1,
                color=color,
                alpha=0.8,
                height=150,
                width=1200,
                xlim=xlim,
            )
            oscillator_panel = oscillator_panel * line if oscillator_panel else line

    # Apply xlim and fixed ylim (-0.01 to 1.01) to oscillator panel with center line
    if oscillator_panel:
        # Add horizontal center line at 0.5 across entire dataset
        data_start = ind_df["time"].min()
        data_end = ind_df["time"].max()
        center_line_df = pd.DataFrame(
            [
                {"time": data_start, "value": 0.5},
                {"time": data_end, "value": 0.5},
            ]
        )
        center_line = center_line_df.hvplot.line(
            x="time",
            y="value",
            color="gray",
            line_width=1,
            line_dash="dashed",
            alpha=0.5,
        )
        oscillator_panel = oscillator_panel * center_line

        opts_dict = {"ylabel": "Stoch RSI", "ylim": (-0.01, 1.01)}
        if xlim:
            opts_dict["xlim"] = xlim
        oscillator_panel = oscillator_panel.opts(**opts_dict)
        logger.info("Added oscillator panel with: %s", oscillators[:2])

    return overlays, oscillator_panel


def _create_portfolio_curve(
    result: BacktestResult,
    initial_balance: float,
    risk_per_trade: float,
) -> Optional[Any]:
    """Create portfolio value curve in dollars."""
    executions = result.executions
    if not executions:
        return None

    # Collect all executions (including from multi-symbol)
    all_trades = []
    if result.is_multi_symbol and result.results:
        for sym_result in result.results.values():
            if sym_result.executions:
                all_trades.extend(sym_result.executions)
    else:
        all_trades = list(executions)

    if not all_trades:
        return None

    # Sort by close timestamp (using consistent dtype)
    trade_data = []
    for trade in all_trades:
        if hasattr(trade, "close_timestamp") and hasattr(trade, "pnl_r"):
            ts = _to_naive_datetime(trade.close_timestamp)
            trade_data.append({"timestamp": ts, "pnl_r": trade.pnl_r})

    if not trade_data:
        return None

    trade_df = pd.DataFrame(trade_data).sort_values("timestamp")
    trade_df = trade_df.set_index("timestamp")

    # Calculate cumulative portfolio value
    trade_df["pnl_dollars"] = trade_df["pnl_r"] * risk_per_trade
    trade_df["portfolio_value"] = initial_balance + trade_df["pnl_dollars"].cumsum()

    # Create line chart using datetime x-axis
    curve = trade_df.hvplot.line(
        y="portfolio_value",
        label="Portfolio Value ($)",
        color="cyan",
        height=200,
        width=1200,
    ).opts(
        ylabel="Portfolio Value ($)",
        tools=["pan", "wheel_zoom", "reset"],
    )

    logger.info("Created portfolio curve with %d trade events.", len(trade_df))

    return curve


def _create_metrics_panel(result: BacktestResult) -> Any:
    """Create a Panel pane with backtest metrics."""
    metrics = result.metrics
    if not metrics:
        return pn.pane.Markdown("*No metrics available*")

    # Build metrics markdown (double newlines for line breaks)
    lines = ["## Backtest Metrics\n"]

    # Check if combined metrics exist (BOTH mode)
    if hasattr(metrics, "combined") and metrics.combined:
        m = metrics.combined
        lines.append("### Combined\n")
        lines.append(f"#### Trades: {m.trade_count}\n")
        lines.append(f"#### Win Rate: {m.win_rate:.1%}\n")
        lines.append(f"#### Expectancy: {m.expectancy:.2f}R\n")
        lines.append(f"#### Profit Factor: {m.profit_factor:.2f}\n")
        lines.append(f"#### Max DD: ${m.max_drawdown_r:.0f}R\n\n")

    # Long metrics
    if hasattr(metrics, "long") and metrics.long:
        m = metrics.long
        lines.append("### Long\n")
        lines.append(f"#### Trades: {m.trade_count}\n")
        lines.append(f"#### Win Rate: {m.win_rate:.1%}\n")
        lines.append(f"#### Expectancy: {m.expectancy:.2f}R\n\n")

    # Short metrics
    if hasattr(metrics, "short") and metrics.short:
        m = metrics.short
        lines.append("### Short\n")
        lines.append(f"#### Trades: {m.trade_count}\n")
        lines.append(f"#### Win Rate: {m.win_rate:.1%}\n")
        lines.append(f"#### Expectancy: {m.expectancy:.2f}R\n\n")

    # Fallback for single direction mode
    if not hasattr(metrics, "combined"):
        if hasattr(metrics, "trade_count"):
            lines.append(f"#### Trades: {metrics.trade_count}\n")
            lines.append(f"#### Win Rate: {metrics.win_rate:.1%}\n")
            lines.append(f"#### Expectancy: {metrics.expectancy:.2f}R\n")
            lines.append(f"#### Profit Factor: {metrics.profit_factor:.2f}\n")

    return pn.pane.Markdown("".join(lines), width=250)


def _save_and_show(
    layout: Any,
    run_id: str,
    output_file: Optional[Union[str, Path]],
    show_plot: bool,
    result: Optional[BacktestResult] = None,
) -> None:
    """Display dashboard in browser."""
    # Note: HTML save is currently disabled due to datetime/float serialization issues
    # TODO: Re-enable once HoloViews datetime handling is fixed

    # Show in browser
    if show_plot:
        pn.extension()

        # Create layout with chart (75% width) and metrics panel on the right
        chart_panel = pn.pane.HoloViews(layout, sizing_mode="stretch_width")

        if result:
            metrics_panel = _create_metrics_panel(result)
            # Row layout: chart takes 75%, metrics takes remaining
            dashboard = pn.Row(chart_panel, metrics_panel, sizing_mode="stretch_width")
        else:
            dashboard = chart_panel

        pn.serve(dashboard, show=True, threaded=True)
        logger.info("Visualization server started. Close browser tab to continue.")
