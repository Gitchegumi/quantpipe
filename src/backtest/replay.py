"""Market replay session and standalone replay CLI.

Provides:
- ReplaySession: Stateful candle-by-candle replay from DuckDB vault
- main(): CLI entry point (qp-replay) that loads vault data and serves
  an interactive Panel/HoloViews dashboard for visual exploration.
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

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
        """Fetch all data for the configured range from the vault.

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        df = self.vault.fetch_range(
            self.symbol,
            self.timeframe,
            self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            self.end_time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        return df

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
  # Replay last 3 months of EURUSD data
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
        help="Start date (YYYY-MM-DD). Default: 3 months ago.",
    )

    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="End date (YYYY-MM-DD). Default: today.",
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
        default="WARNING",
        help="Logging level (default: WARNING)",
    )

    return parser.parse_args()


def main():
    """CLI entry point for qp-replay.

    Loads data from DuckDB vault and serves an interactive
    Panel/HoloViews candlestick dashboard in the browser.
    """
    args = _parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Check vault exists
    vault_path = Path(args.vault_path)
    if not vault_path.exists():
        print(f"Error: DuckDB vault not found at {vault_path}")
        print("Run 'poetry run quantpipe ingest' to build the vault first.")
        return 1

    # If no symbol specified, list what's in the vault
    vault = DuckDBVault(db_path=str(vault_path))

    if args.symbol is None:
        try:
            symbols = vault.list_symbols()
            if not symbols:
                print("Vault is empty. Run 'poetry run quantpipe ingest' first.")
                vault.close()
                return 1
            print("Available symbols in vault:")
            for sym in symbols:
                print(f"  - {sym}")
            vault.close()
            print("\nUsage: qp-replay --symbol <SYMBOL>")
            return 0
        except Exception as e:
            print(f"Error reading vault: {e}")
            vault.close()
            return 1

    vault.close()

    # Parse dates
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=90)

    if args.end:
        try:
            end_dt = datetime.strptime(args.end, "%Y-%m-%d")
        except ValueError:
            print(f"Invalid end date format: {args.end}. Use YYYY-MM-DD.")
            return 1

    if args.start:
        try:
            start_dt = datetime.strptime(args.start, "%Y-%m-%d")
        except ValueError:
            print(f"Invalid start date format: {args.start}. Use YYYY-MM-DD.")
            return 1

    # Load data from vault
    symbol = args.symbol.lower()
    print(f"Loading {symbol.upper()} data from vault ({start_dt.date()} to {end_dt.date()})...")

    session = ReplaySession(
        symbol=symbol,
        timeframe=args.timeframe,
        start_time=start_dt,
        end_time=end_dt,
        vault_path=str(vault_path),
    )

    df = session.fetch_all()
    session.close()

    if df.empty:
        print(f"No data found for {symbol.upper()} in the specified date range.")
        return 1

    print(f"Loaded {len(df):,} candles. Launching dashboard...")

    # Serve interactive dashboard using Panel + HoloViews
    try:
        import holoviews as hv
        import hvplot.pandas  # noqa: F401
        import panel as pn
        from bokeh.models import HoverTool

        hv.extension("bokeh")
        hv.renderer("bokeh").theme = "dark_minimal"

        # Prepare DataFrame for plotting
        pdf = df.copy()
        if "timestamp" in pdf.columns:
            pdf = pdf.rename(columns={"timestamp": "timestamp_utc"})

        # Ensure timezone-naive for HoloViews
        pdf["timestamp_utc"] = pd.to_datetime(pdf["timestamp_utc"]).dt.tz_localize(None)
        pdf = pdf.set_index("timestamp_utc")
        pdf.index.name = "time"

        # Add formatted time string for tooltips
        pdf["time_str"] = pdf.index.strftime("%Y-%m-%d %H:%M")

        # Determine price format
        is_jpy = "jpy" in symbol.lower()
        price_fmt = "0.000" if is_jpy else "0.00000"

        # Initial zoom: last 60 candles
        zoom_count = 60
        if len(pdf) > zoom_count:
            xlim = (pdf.index[-zoom_count], pdf.index[-1])
        else:
            xlim = (pdf.index[0], pdf.index[-1])

        # Create OHLC chart
        tooltips = [
            ("Time", "@time_str"),
            ("Open", f"@open{{{price_fmt}}}"),
            ("High", f"@high{{{price_fmt}}}"),
            ("Low", f"@low{{{price_fmt}}}"),
            ("Close", f"@close{{{price_fmt}}}"),
        ]

        chart = pdf.hvplot.ohlc(
            y=["open", "high", "low", "close"],
            neg_color="red",
            pos_color="green",
            height=500,
            width=1200,
            title=f"{symbol.upper()} Replay ({args.timeframe})",
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
        html, body {
            background-color: #1a1a2e !important;
            color: #e0e0e0 !important;
        }
        .bk-root, .bk, .bk-Column, .bk-Row {
            background-color: #1a1a2e !important;
        }
        """
        pn.config.raw_css.append(dark_css)
        pn.extension()

        # Build dashboard
        header = pn.pane.Markdown(
            f"## 📊 {symbol.upper()} Replay — {start_dt.date()} to {end_dt.date()} ({len(df):,} candles)",
            styles={"color": "#e0e0e0", "background": "#1a1a2e"},
        )

        layout = hv.Layout([chart, vol_chart]).cols(1).opts(shared_axes=True)

        dashboard = pn.Column(
            header,
            pn.pane.HoloViews(layout, sizing_mode="stretch_width"),
            sizing_mode="stretch_width",
            styles={"background": "#1a1a2e"},
        )

        print("Dashboard running. Close the browser tab or press Ctrl+C to stop.")
        pn.serve(dashboard, show=True, title=f"QuantPipe Replay: {symbol.upper()}")

    except ImportError as e:
        print(f"Missing visualization dependency: {e}")
        print("Install with: poetry install")
        return 1
    except KeyboardInterrupt:
        print("\nReplay stopped.")
    except Exception as e:
        print(f"Error launching dashboard: {e}")
        logger.exception("Dashboard launch failed")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
