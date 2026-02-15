from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import argparse
import logging
import pandas as pd
from pathlib import Path
from src.infrastructure.duckdb.vault import DuckDBVault
import numpy as np

logger = logging.getLogger(__name__)


class ReplaySession:
    """
    Manages a stateful market replay session, providing candles one-by-one or in chunks.
    Legacy non-streaming mode for compatibility.
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        vault_path: str = "data/vault.duckdb",
        buffer_size: int = 1000,
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.start_time = start_time
        self.end_time = end_time
        self.vault_path = vault_path
        self.buffer_size = buffer_size

        self.current_time = start_time
        self.vault = DuckDBVault(db_path=vault_path)

        # Pre-load initial buffer
        self._buffer = pd.DataFrame()
        self._buffer_idx = 0
        self._load_next_buffer()

    def _load_next_buffer(self):
        """Loads the next chunk of data from the vault into the memory buffer."""
        fetch_end = self.current_time + timedelta(days=1)
        if fetch_end > self.end_time:
            fetch_end = self.end_time

        self._buffer = self.vault.fetch_range(
            self.symbol,
            self.timeframe,
            self.current_time.strftime("%Y-%m-%d %H:%M:%S"),
            fetch_end.strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._buffer_idx = 0

        if not self._buffer.empty:
            logger.debug("Replay buffer refilled: %s bars.", len(self._buffer))

    def next_candle(self) -> Optional[Dict[str, Any]]:
        """Returns the next candle in the sequence."""
        if self._buffer_idx >= len(self._buffer):
            if self.current_time >= self.end_time:
                return None
            self._load_next_buffer()
            if self._buffer.empty:
                return None

        row = self._buffer.iloc[self._buffer_idx]
        self._buffer_idx += 1
        self.current_time = row["timestamp"]

        return row.to_dict()

    def fetch_all(self) -> pd.DataFrame:
        """Fetches all candles for the session's time range as a DataFrame."""
        # Query vault directly for the full range
        df = self.vault.fetch_range(
            self.symbol,
            self.timeframe,
            self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            self.end_time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        return df

    def get_data_range(self) -> tuple[datetime, datetime]:
        """
        Get the actual timestamp range available in the vault for this symbol/timeframe.

        Returns:
            Tuple of (min_timestamp, max_timestamp) or (None, None) if error/empty
        """
        try:
            query = """
                SELECT
                    MIN(timestamp) as min_ts,
                    MAX(timestamp) as max_ts
                FROM ohlcv
                WHERE symbol = ? AND timeframe = ?
            """
            result = self.vault.conn.execute(query, [self.symbol, self.timeframe]).fetchone()
            if result and result[0] and result[1]:
                return pd.to_datetime(result[0]).to_pydatetime(), pd.to_datetime(result[1]).to_pydatetime()
            return None, None
        except Exception as e:
            logger.warning("Failed to get data range: %s", e)
            return None, None

    def reset(self):
        """Resets the session to the start time."""
        self.current_time = self.start_time
        self._load_next_buffer()

    def close(self):
        self.vault.close()


class StreamingReplaySession:
    """
    Manages a streaming replay with a bounded display window.
    Fetches data in chunks and updates Bokeh ColumnDataSource via streaming.
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        vault_path: str = "data/vault.duckdb",
        max_candles: int = 5000,
        buffer_size: int = 1000,
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.start_time = start_time
        self.end_time = end_time
        self.vault_path = vault_path
        self.max_candles = max_candles
        self.buffer_size = buffer_size

        self.vault = DuckDBVault(db_path=vault_path)

        # State
        self.current_time = start_time
        self._buffer = pd.DataFrame()
        self._buffer_idx = 0
        self._prefetch_queue = []
        self._is_playing = False
        self._replay_speed = 1.0

        # Load initial buffer
        self._load_next_buffer()

        # Build initial view (first max_candles or all if less)
        self._view_df = self._buffer.head(self.max_candles).copy() if not self._buffer.empty else pd.DataFrame()
        if not self._view_df.empty:
            self._advance_to_end_of_view()

    def _load_next_buffer(self):
        """Loads the next chunk of data from the vault into the memory buffer."""
        fetch_end = self.current_time + timedelta(days=1)
        if fetch_end > self.end_time:
            fetch_end = self.end_time

        self._buffer = self.vault.fetch_range(
            self.symbol,
            self.timeframe,
            self.current_time.strftime("%Y-%m-%d %H:%M:%S"),
            fetch_end.strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._buffer_idx = 0

        if not self._buffer.empty:
            logger.debug("Replay buffer refilled: %s bars.", len(self._buffer))

    def _advance_to_end_of_view(self):
        """Advances current_time to the last candle currently in the view."""
        if not self._view_df.empty:
            last_ts = self._view_df.index.max() if self._view_df.index.name == "timestamp_utc" else self._view_df["timestamp"].iloc[-1]
            self.current_time = pd.to_datetime(last_ts).to_pydatetime()

    def get_view_data(self) -> pd.DataFrame:
        """Returns the current view DataFrame (bounded to max_candles)."""
        return self._view_df.copy()

    def stream_next_batch(self, batch_size: int = 1) -> pd.DataFrame:
        """
        Streams the next batch of candles into the view.
        Returns the new rows that were added (for Bokeh streaming).
        The returned DataFrame uses the original datetime index (timestamp_utc) for x-axis.
        """
        if self._buffer.empty:
            # Try to load more
            self._load_next_buffer()
            if self._buffer.empty:
                return pd.DataFrame()

        # Take next batch from buffer
        available = len(self._buffer) - self._buffer_idx
        n = min(batch_size, available)
        new_rows = self._buffer.iloc[self._buffer_idx:self._buffer_idx + n].copy()

        # Append to view
        if self._view_df.empty:
            self._view_df = new_rows
        else:
            self._view_df = pd.concat([self._view_df, new_rows])

        # Maintain bounded window (by timestamp, not integer position)
        if len(self._view_df) > self.max_candles:
            # Keep the most recent max_candles rows
            self._view_df = self._view_df.iloc[-self.max_candles:]

        # Advance buffer pointer and current_time
        self._buffer_idx += n
        self.current_time = new_rows.iloc[-1]["timestamp"]

        # Refill buffer if we've consumed it
        if self._buffer_idx >= len(self._buffer):
            self._load_next_buffer()

        return new_rows

    def is_finished(self) -> bool:
        """Checks if replay has reached the end."""
        return self._buffer.empty and self._buffer_idx >= len(self._buffer) and self.current_time >= self.end_time

    def get_progress(self) -> float:
        """Returns progress percentage through the time range."""
        if self.start_time == self.end_time:
            return 0.0
        total_seconds = (self.end_time - self.start_time).total_seconds()
        elapsed = (self.current_time - self.start_time).total_seconds()
        return min(100.0, max(0.0, (elapsed / total_seconds) * 100))

    def reset(self):
        """Resets the session to the start time."""
        self.current_time = self.start_time
        self._buffer_idx = 0
        self._load_next_buffer()
        self._view_df = self._buffer.head(self.max_candles).copy() if not self._buffer.empty else pd.DataFrame()
        if not self._view_df.empty:
            self._advance_to_end_of_view()

    def close(self):
        self.vault.close()


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the replay command."""
    parser = argparse.ArgumentParser(
        description="Interactive market data replay viewer (DuckDB vault)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Replay entire dataset for EURUSD (default range from vault)
  qp-replay --symbol EURUSD

  # Replay specific date range
  qp-replay --symbol EURUSD --start 2024-06-01 --end 2024-12-31

  # Use custom vault path
  qp-replay --symbol EURUSD --vault-path /path/to/vault.duckdb

  # Fast replay with streaming window (max 5000 candles visible)
  qp-replay --symbol EURUSD --replay-speed 10 --max-candles 5000

  # Disable streaming for small ranges (loads all at once)
  qp-replay --symbol EURUSD --no-streaming
        """,
    )

    parser.add_argument(
        "--symbol",
        type=str,
        default=None,
        help="Symbol to replay (e.g., EURUSD). If omitted, lists available symbols.",
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default="1m",
        help="Timeframe (default: 1m)",
    )
    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help="Start date (YYYY-MM-DD). Default: earliest available.",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="End date (YYYY-MM-DD). Default: latest available.",
    )
    parser.add_argument(
        "--vault-path",
        type=str,
        default="data/vault.duckdb",
        help="Path to DuckDB vault (default: data/vault.duckdb)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--overlay-indicators",
        action="store_true",
        help="Overlay strategy indicator columns from test partition (if available)",
    )
    parser.add_argument(
        "--max-candles",
        type=int,
        default=5000,
        help="Maximum number of candles to display at once (default: 5000)",
    )
    parser.add_argument(
        "--replay-speed",
        type=float,
        default=1.0,
        help="Replay speed multiplier (1.0 = real-time, 10.0 = 10x faster)",
    )
    parser.add_argument(
        "--no-streaming",
        action="store_true",
        help="Disable streaming replay (load all data, use with caution for large ranges)",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point for the replay CLI."""
    args = _parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    vault_path = args.vault_path
    vault = DuckDBVault(db_path=vault_path)

    # If no symbol specified, list what's in the vault
    if args.symbol is None:
        try:
            symbols = vault.list_symbols()
            if not symbols:
                print("No symbols found in vault. Run 'poetry run quantpipe ingest' to build the vault first.")
                return 1
            print("\nAvailable symbols:")
            for sym in symbols:
                print(f"  {sym}")
            print("\nUsage: qp-replay --symbol <SYMBOL>")
            return 0
        except Exception as e:
            print(f"Error connecting to vault: {e}")
            print(f"Vault path: {vault_path}")
            print("Ensure vault exists. Run 'poetry run quantpipe ingest' to build the vault first.")
            return 1

    symbol = args.symbol.upper()
    timeframe = args.timeframe

    # Determine date range
    min_ts, max_ts = None, None
    try:
        min_ts, max_ts = vault.get_data_range(symbol, timeframe)
    except Exception as e:
        logger.warning("Could not query vault for date range: %s", e)

    if min_ts is None or max_ts is None:
        print(f"No data found for {symbol} {timeframe} in vault.")
        print(f"Vault path: {vault_path}")
        return 1

    start_dt = min_ts if not args.start else datetime.strptime(args.start, "%Y-%m-%d")
    end_dt = max_ts if not args.end else datetime.strptime(args.end, "%Y-%m-%d")

    # Clamp to available data bounds and ensure start <= end
    adjusted = False
    if start_dt < min_ts:
        start_dt = min_ts
        adjusted = True
    if end_dt > max_ts:
        end_dt = max_ts
        adjusted = True
    if start_dt > end_dt:
        # If start is after end (e.g., default 90-day start beyond max_ts), set start to end
        start_dt = end_dt
        adjusted = True

    if adjusted:
        print(f"Date range adjusted to: {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}")

    print(f"Loading {symbol.upper()} {timeframe} from {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}...")
    print(f"Vault: {vault_path}")

    # Choose session type based on args
    if args.no_streaming:
        # Legacy mode: load all at once
        session = ReplaySession(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_dt,
            end_time=end_dt,
            vault_path=vault_path,
        )
        df = session.fetch_all()
        session.close()

        if df.empty:
            print(f"No data in selected range.")
            return 1

        print(f"Loaded {len(df)} bars (non-streaming mode).")
    else:
        # Streaming mode with bounded window
        session = StreamingReplaySession(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_dt,
            end_time=end_dt,
            vault_path=vault_path,
            max_candles=args.max_candles,
        )
        df = session.get_view_data()
        print(f"Streaming mode: max {args.max_candles} candles visible. Buffering for smooth replay.")

    if df.empty:
        print(f"No data in selected range.")
        return 1

    # Serve interactive dashboard using Panel + HoloViews
    try:
        import holoviews as hv
        import hvplot.pandas  # noqa: F401
        import panel as pn
        from bokeh.models import HoverTool, ColumnDataSource, Button, Div
        from bokeh.plotting import figure
        from bokeh.layouts import column, row
        from bokeh.palettes import Category10
        from bokeh.models import Span, Label
        from bokeh.events import ButtonClick
        import asyncio
        from threading import Thread, Event
        import time

        hv.extension("bokeh")
        pn.extension()

        # Prepare main DataFrame for plotting
        pdf = df.copy()

        # Normalize timestamp column to datetime and set as index (with duplicate protection)
        if "timestamp" in pdf.columns and "timestamp_utc" not in pdf.columns:
            pdf = pdf.rename(columns={"timestamp": "timestamp_utc"})
        elif "timestamp_utc" not in pdf.columns:
            # If neither exists, assume index is timestamp
            pdf = pdf.reset_index()
            if "timestamp" not in pdf.columns and pdf.columns[0] != "timestamp_utc":
                pdf = pdf.rename(columns={pdf.columns[0]: "timestamp_utc"})

        if "timestamp_utc" in pdf.columns:
            pdf["timestamp_utc"] = pd.to_datetime(pdf["timestamp_utc"])
            pdf = pdf.set_index("timestamp_utc").sort_index()
        else:
            # Fallback: ensure index is datetime
            pdf.index = pd.to_datetime(pdf.index)
            pdf = pdf.sort_index()

        # Human-readable time string for hover (guard against duplicates)
        if "time_str" not in pdf.columns:
            pdf["time_str"] = pdf.index.strftime("%Y-%m-%d %H:%M:%S")

        # Load indicator overlay from test partition if requested (for static initial view)
        indicator_dfs = []
        if args.overlay_indicators:
            test_parquet = Path(f"price_data/processed/{symbol.lower()}/test/{symbol.lower()}_test.parquet")
            if test_parquet.exists():
                try:
                    test_df = pd.read_parquet(test_parquet)
                    # Align index to pdf's index (timestamp)
                    if "timestamp" in test_df.columns:
                        test_df = test_df.rename(columns={"timestamp": "timestamp_utc"})
                        test_df["timestamp_utc"] = pd.to_datetime(test_df["timestamp_utc"])
                        test_df = test_df.set_index("timestamp_utc").sort_index()
                    # Intersection of indices with current view
                    common_idx = pdf.index.intersection(test_df.index)
                    if len(common_idx) > 0:
                        test_df = test_df.loc[common_idx]
                        indicator_dfs.append(test_df)
                        print(f"Overlayed {len(test_df.columns)} indicator(s) from test partition.")
                except Exception as e:
                    print(f"Warning: failed to load indicators from {test_parquet}: {e}")
            else:
                print(f"Note: test parquet not found at {test_parquet}; indicators not overlaid.")

        # Prepare time-sorted data for streaming (with duplicate-safe guards)
        if pdf.index.name != "timestamp_utc":
            if "timestamp_utc" in pdf.columns:
                pdf = pdf.set_index("timestamp_utc").sort_index()
            else:
                pdf.index = pd.to_datetime(pdf.index)
                pdf = pdf.sort_index()

        # Add derived columns for candlestick rendering BEFORE creating source (guard against duplicates)
        if "direction" not in pdf.columns:
            pdf["direction"] = ["up" if c > o else "down" for c, o in zip(pdf["close"], pdf["open"])]
        if "center" not in pdf.columns:
            pdf["center"] = (pdf["open"] + pdf["close"]) / 2
        if "height" not in pdf.columns:
            pdf["height"] = abs(pdf["close"] - pdf["open"])

        # Ensure timestamp_utc is available as a column for glyphs (datetime) - safe fallback
        if "timestamp_utc" not in pdf.columns:
            pdf["timestamp_utc"] = pdf.index

        # Ensure index (milliseconds) is available for Bokeh datetime axis - safe fallback
        if "index" not in pdf.columns:
            pdf["index"] = pdf.index.view('int64')

        # Ensure time_str is present for hover tool - safe fallback (may have been added earlier)
        if "time_str" not in pdf.columns:
            pdf["time_str"] = pdf.index.strftime("%Y-%m-%d %H:%M:%S")

        # Create Bokeh ColumnDataSource with all columns including derived and index
        source = ColumnDataSource(pdf)

        # Determine price format
        price_fmt = ".2f" if pdf["close"].mean() > 1 else ".5f"

        # Create main price chart (Bokeh figure)
        p = figure(
            x_axis_type="datetime",
            title=f"{symbol} {timeframe} Replay (Streaming: {args.max_candles} max candles)",
            width=1200,
            height=500,
            tools="pan,wheel_zoom,box_zoom,reset,save",
            active_drag="pan",
            active_scroll="wheel_zoom",
        )

        # Add candlestick glyphs - bound to ColumnDataSource for streaming updates
        up_color = "#00FF00"
        down_color = "#FF0000"
        body_width = 60 * 1000  # 1 minute in milliseconds for 1m data

        # Wicks (high-low lines) - use segment with source
        p.segment(
            x0="index", y0="high", x1="index", y1="low",
            source=source, color="#888888", line_width=1
        )

        # Compute candle width from timeframe (e.g., "15m" -> 15 minutes in milliseconds)
        def _timeframe_to_ms(tf: str) -> int:
            import re
            m = re.match(r"(\d+)([mhdw])", tf.lower())
            if not m:
                return 60 * 1000  # default 1m
            qty = int(m.group(1))
            unit = m.group(2)
            if unit == "m":
                return qty * 60 * 1000
            elif unit == "h":
                return qty * 60 * 60 * 1000
            elif unit == "d":
                return qty * 24 * 60 * 60 * 1000
            elif unit == "w":
                return qty * 7 * 24 * 60 * 60 * 1000
            return 60 * 1000

        body_width = _timeframe_to_ms(args.timeframe)

        # Candle bodies - use rect with source, color-mapped by direction
        from bokeh.core.properties import value
        from bokeh.transform import factor_cmap
        
        p.rect(
            x="index", y="center", width=value(body_width), height="height",
            source=source,
            fill_color=factor_cmap("direction", palette=[down_color, up_color], factors=["down", "up"]),
            line_color=factor_cmap("direction", palette=[down_color, up_color], factors=["down", "up"]),
            line_width=1,
        )

        # HoverTool
        hover = HoverTool(
            tooltips=[
                ("Time", "@time_str"),
                ("Open", f"@open{{{price_fmt}}}"),
                ("High", f"@high{{{price_fmt}}}"),
                ("Low", f"@low{{{price_fmt}}}"),
                ("Close", f"@close{{{price_fmt}}}"),
            ],
            mode="vline",
        )
        p.add_tools(hover)

        # Volume panel: REMOVED entirely per requirement (FX has no meaningful volume)

        # Indicator panes
        indicator_figs = []
        for ind_df in indicator_dfs:
            ind_fig = figure(
                x_axis_type="datetime",
                width=1200,
                height=150,
                x_range=p.x_range,
                tools="",
                toolbar_location=None,
            )
            for col in ind_df.columns:
                if col.endswith("_color"):
                    continue
                color = "lime"
                if "ema" in col:
                    color = "orange"
                elif "rsi" in col:
                    color = "cyan"
                ind_fig.line(ind_df.index, ind_df[col], line_width=1, color=color, legend_label=col)
            ind_fig.legend.location = "top_left"
            ind_fig.legend.orientation = "horizontal"
            indicator_figs.append(ind_fig)

        # Control panel
        status_div = Div(text=f"<b>Status:</b> Ready | Progress: 0% | View: {len(pdf)} candles", width=500)
        speed_div = Div(text=f"<b>Speed:</b> {args.replay_speed}x", width=150)

        play_button = Button(label="▶ Play", width=80, button_type="success")
        pause_button = Button(label="⏸ Pause", width=80, button_type="warning")
        reset_button = Button(label="⏮ Reset", width=80, button_type="primary")

        # Streaming state
        streaming_state = {
            "running": False,
            "session": session,
            "replay_speed": args.replay_speed,
            "timer_id": None,
        }

        def update_chart():
            """Periodic callback that advances the replay by one candle and streams it.
            Only streams data values - does not modify source schema/columns."""
            state = streaming_state
            if not state["running"]:
                return

            new_rows = state["session"].stream_next_batch(batch_size=1)
            if new_rows.empty or state["session"].is_finished():
                state["running"] = False
                play_button.disabled = False
                pause_button.disabled = True
                status_div.text = f"<b>Status:</b> Finished | Progress: 100% | View: {len(state['session']._view_df)}"
                return

            # Prepare data for streaming - ONLY use columns that already exist in source
            # Do NOT add new columns here; they were defined during initialization
            new_data = {}
            for col in source.column_names:
                if col in new_rows.columns:
                    val = new_rows[col]
                    # Convert to list appropriately
                    if hasattr(val, 'tolist'):
                        new_data[col] = val.tolist()
                    else:
                        new_data[col] = [val]
                elif col == "index":
                    # Convert datetime index to int64 milliseconds for Bokeh
                    new_data["index"] = new_rows.index.view('int64').tolist()

            # Calculate derived column values ONLY if they exist in source (for streaming)
            # These are required data values, not schema modifications
            if "direction" in source.column_names and "direction" not in new_data:
                new_data["direction"] = ["up" if c > o else "down" for c, o in zip(new_rows["close"], new_rows["open"])]
            if "center" in source.column_names and "center" not in new_data:
                new_data["center"] = ((new_rows["open"] + new_rows["close"]) / 2).tolist()
            if "height" in source.column_names and "height" not in new_data:
                new_data["height"] = abs(new_rows["close"] - new_rows["open"]).tolist()
            if "timestamp_utc" in source.column_names and "timestamp_utc" not in new_data:
                new_data["timestamp_utc"] = [new_rows.index[0]] if not new_rows.empty else []
            if "time_str" in source.column_names and "time_str" not in new_data:
                new_data["time_str"] = [new_rows.index[0].strftime("%Y-%m-%d %H:%M:%S")] if not new_rows.empty else []

            # Stream with rollover
            source.stream(new_data, rollover=args.max_candles)

            # Update status
            progress = state["session"].get_progress()
            status_div.text = f"<b>Status:</b> Playing | Progress: {progress:.1f}% | View: {len(state['session']._view_df)}"

        def on_play():
            state = streaming_state
            state["running"] = True
            play_button.disabled = True
            pause_button.disabled = False
            if state["timer_id"] is None:
                # Create periodic callback once and store the callback object
                interval_ms = int(60000 / state["replay_speed"])
                state["timer_id"] = pn.state.add_periodic_callback(update_chart, interval_ms)
            else:
                state["timer_id"].start()

        def on_pause():
            state = streaming_state
            state["running"] = False
            play_button.disabled = False
            pause_button.disabled = True
            if state["timer_id"] is not None:
                state["timer_id"].stop()

        def on_reset():
            """Reset the replay session and rebuild the data source.
            Uses existing source schema - only replaces data values, never adds columns."""
            state = streaming_state
            state["running"] = False
            if state["timer_id"] is not None:
                state["timer_id"].stop()
            state["session"].reset()
            initial_df = state["session"].get_view_data()

            # Prepare initial_df with all required columns that exist in source schema
            # This ensures consistency without duplicating columns
            if not initial_df.empty:
                # Add derived columns to initial_df ONLY if missing and needed by source
                if "direction" in source.column_names and "direction" not in initial_df.columns:
                    initial_df["direction"] = [
                        "up" if c > o else "down"
                        for c, o in zip(initial_df["close"], initial_df["open"])
                    ]
                if "center" in source.column_names and "center" not in initial_df.columns:
                    initial_df["center"] = (initial_df["open"] + initial_df["close"]) / 2
                if "height" in source.column_names and "height" not in initial_df.columns:
                    initial_df["height"] = abs(initial_df["close"] - initial_df["open"])
                if "timestamp_utc" in source.column_names and "timestamp_utc" not in initial_df.columns:
                    initial_df["timestamp_utc"] = initial_df.index
                if "index" in source.column_names and "index" not in initial_df.columns:
                    initial_df["index"] = initial_df.index.view('int64')
                if "time_str" in source.column_names and "time_str" not in initial_df.columns:
                    initial_df["time_str"] = initial_df.index.strftime("%Y-%m-%d %H:%M:%S")

            # Rebuild source data using ONLY existing columns from source.column_names
            # Never add new columns here - only populate existing schema with data
            new_source_data = {}
            for col in source.column_names:
                if col in initial_df.columns and not initial_df.empty:
                    val = initial_df[col]
                    if hasattr(val, 'tolist'):
                        new_source_data[col] = val.tolist()
                    else:
                        new_source_data[col] = [val]
                elif col == "index" and not initial_df.empty:
                    new_source_data["index"] = initial_df.index.view('int64').tolist()
                else:
                    # Empty list for missing columns (schema preserved, data cleared)
                    new_source_data[col] = []

            # Replace entire data dictionary atomically (no schema changes)
            source.data = new_source_data
            progress = state["session"].get_progress()
            status_div.text = f"<b>Status:</b> Reset | Progress: {progress:.1f}% | View: {len(initial_df)}"
            play_button.disabled = False
            pause_button.disabled = True

        play_button.on_click(on_play)
        pause_button.on_click(on_pause)
        reset_button.on_click(on_reset)

        # Layout
        controls = row(play_button, pause_button, reset_button, speed_div, status_div)
        layout = column(controls, p)
        # Volume panel intentionally removed; only indicators below price if present
        for ind_fig in indicator_figs:
            layout = column(layout, ind_fig)

        # Dark theme
        dark_css = """
        html { background-color: #1a1a2e; }
        body { color: #e0e0e0 !important; }
        .bk-root .bk-widget { color: #e0e0e0; }
        """
        pn.config.raw_css.append(dark_css)

        print("\nStarting dashboard at http://localhost:5006/")
        print(f"Controls: Play/Pause/Reset. Replay speed: {args.replay_speed}x (1x = real-time)")
        print("Press Ctrl+C to stop.\n")

        pn.serve(layout, port=5006, show=False, title=f"{symbol} Replay - QuantPipe")

    except ImportError as e:
        print(f"\nDashboard dependencies missing: {e}")
        print("Install with: poetry install")
        return 1
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
        return 0
    except Exception as e:
        print(f"\nFailed to start dashboard: {e}")
        print("Ensure Panel and HoloViews are installed correctly.")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
