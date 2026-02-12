from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import argparse
import logging
import pandas as pd
from src.infrastructure.duckdb.vault import DuckDBVault

logger = logging.getLogger(__name__)


class ReplaySession:
    """
    Manages a stateful market replay session, providing candles one-by-one or in chunks.
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

    print(f"Loaded {len(df)} bars.")

    # Serve interactive dashboard using Panel + HoloViews
    try:
        import holoviews as hv
        import hvplot.pandas  # noqa: F401
        import panel as pn
        from bokeh.models import HoverTool

        hv.extension("bokeh")
        pn.extension()

        # Prepare DataFrame for plotting
        pdf = df.copy()
        if "timestamp" in pdf.columns:
            pdf = pdf.rename(columns={"timestamp": "timestamp_utc"})
            pdf["timestamp_utc"] = pd.to_datetime(pdf["timestamp_utc"])
            pdf = pdf.set_index("timestamp_utc").sort_index()
            pdf["time_str"] = pdf.index.strftime("%Y-%m-%d %H:%M:%S")
        else:
            # Assume index is already datetime
            pdf.index = pd.to_datetime(pdf.index)
            pdf["time_str"] = pdf.index.strftime("%Y-%m-%d %H:%M:%S")

        if len(pdf) > 0:
            xlim = (pdf.index[0], pdf.index[-1])
        else:
            xlim = None

        # Format prices to reasonable precision
        price_fmt = ".2f" if pdf["close"].mean() > 1 else ".5f"

        # Create OHLC chart
        tooltips = [
            ("Time", "@time_str"),
            ("Open", f"@open{{{price_fmt}}}"),
            ("High", f"@high{{{price_fmt}}}"),
            ("Low", f"@low{{{price_fmt}}}"),
            ("Close", f"@close{{{price_fmt}}}"),
            ("Volume", "@volume{0,0}"),
        ]
        chart = pdf.hvplot.ohlc(
            y=["open", "high", "low", "close"],
            xlabel="Time",
            ylabel="Price",
            width=1200,
            height=400,
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

        # Volume bar chart
        vol_chart = pdf.hvplot.bar(
            y="volume",
            color="gray",
            alpha=0.3,
            height=150,
            width=1200,
            xlim=xlim,
            ylabel="Volume",
        )

        # Dark theme CSS
        dark_css = """
        html { background-color: #1a1a2e; }
        body { color: #e0e0e0 !important; }
        """
        pn.config.raw_css.append(dark_css)

        # Build dashboard
        header = pn.pane.Markdown(
            f"# {symbol} Replay\n"
            f"**Timeframe:** {timeframe}  |  **Bars:** {len(df)}  |  **Range:** {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}",
            styles={"color": "#e0e0e0", "background": "#1a1a2e"},
        )
        layout = (chart + vol_chart).cols(1).opts(shared_axes=True)

        dashboard = pn.Column(
            header,
            pn.pane.HoloViews(layout, sizing_mode="stretch_width"),
            pn.pane.Markdown("Scroll to zoom. Drag to pan. Use toolbar to reset."),
            styles={"background": "#1a1a2e"},
        )

        print("\nStarting dashboard at http://localhost:5006/")
        print("Press Ctrl+C to stop.\n")

        pn.serve(dashboard, port=5006, show=False, title=f"{symbol} Replay - QuantPipe")

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
