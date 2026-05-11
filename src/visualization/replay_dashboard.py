"""Interactive Market Replay Dashboard.

Real-time step-through visualization that replays market data candle-by-candle
using HoloViews Buffer streams for dynamic updating. Integrates with the existing
datashader visualization components (candlesticks, trade overlays, indicator panels,
portfolio curve, metrics) while adding replay-specific controls.

Controls:
- Play/Pause/Stop: Continuous replay at configured speed
- Speed slider: 0.1x to 5x playback multiplier
- Step forward: Advance one candle at a time
- Time display: Current candle timestamp
- Trade counter: Number of trades triggered during replay
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import pandas as pd

try:
    import holoviews as hv
    import hvplot.pandas  # noqa: F401 - Required for hvplot extension
    import panel as pn
    from holoviews.streams import Buffer
    from bokeh.models import CrosshairTool, HoverTool

    HAS_DATASHADER = True
except ImportError:
    HAS_DATASHADER = False

from src.backtest.replay import ReplaySession, ReplayConfig
from src.models.events import CandleEvent, TradeEvent

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)

# Dark theme CSS
DARK_CSS = """
:root {
    --bg-color: #1a1a2e;
    --text-color: #e0e0e0;
}
html, body {
    background-color: var(--bg-color) !important;
    color: var(--text-color) !important;
    margin: 0;
    padding: 0;
}
"""

# Maximum candles to show in the rolling chart window
MAX_CHART_CANDLES = 300
# Maximum candles in the full replay buffer before dropping oldest
MAX_REPLAY_BUFFER = 10_000


class ReplayDashboard:
    """
    Real-time interactive dashboard for market replay.

    Streams candle data through HoloViews Buffer streams, updating candlestick
    charts, trade overlays, and portfolio curves as the replay progresses.

    Supports three playback modes:
    - Step: Manual single-candle advancement via step_forward()
    - Play: Continuous playback at the configured speed multiplier
    - Stop: Halts playback and resets replay state

    The dashboard integrates with the existing datashader visualization system,
    rendering the same chart components (OHLC, trade markers, indicators,
    oscillators, portfolio curve) in a live-updating context.

    Examples:
        >>> session = ReplaySession(data, config)
        >>> dashboard = ReplayDashboard(session)
        >>> dashboard.show()  # Blocks; serves Panel app in a thread
    """

    def __init__(
        self,
        session: ReplaySession,
        initial_balance: float = 2_500.0,
        risk_per_trade: float = 6.25,
        output_file: Optional[Path] = None,
    ) -> None:
        """
        Initialize the replay dashboard.

        Args:
            session: ReplaySession providing candles and trade events.
            initial_balance: Starting portfolio balance in dollars.
            risk_per_trade: Dollar risk per 1R per trade.
            output_file: Optional path to save the dashboard as HTML on close.
        """
        if not HAS_DATASHADER:
            raise ImportError(
                "ReplayDashboard requires: holoviews, hvplot, panel, bokeh. "
                "Install with: poetry add holoviews hvplot panel bokeh"
            )

        self.session = session
        self.initial_balance = initial_balance
        self.risk_per_trade = risk_per_trade
        self.output_file = output_file

        # --- Buffer streams for dynamic HoloViews updates ---
        # OHLC buffer: accumulates candles as replay advances
        self._ohlc_buffer = Buffer(
            pd.DataFrame(
                columns=[
                    "timestamp_utc",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ]
            ),
            length=MAX_CHART_CANDLES,
        )

        # Portfolio buffer: accumulates portfolio value at each trade
        self._portfolio_buffer = Buffer(
            pd.DataFrame(columns=["timestamp_utc", "portfolio_value"]),
            length=MAX_CHART_CANDLES,
        )

        # Trade marker buffer: entry/exit annotations
        self._trade_buffer = Buffer(
            pd.DataFrame(
                columns=[
                    "timestamp_utc",
                    "price",
                    "pnl_r",
                    "action",
                    "side",
                ]
            ),
            length=500,
        )

        # Portfolio tracking
        self._portfolio_value = initial_balance

        # --- Playback state ---
        self._callback = None
        self._speed = 0.5  # seconds per candle
        self._running = False

        # --- Build Panel widgets ---
        self._build_controls()
        self._build_status_bar()

        # --- Build HoloViews layout ---
        self._build_layout()

        # Apply dark theme
        pn.config.raw_css.append(DARK_CSS)
        pn.extension()

        logger.info("ReplayDashboard initialized for %s", session.symbol)

    # ------------------------------------------------------------------
    # Widget construction
    # ------------------------------------------------------------------

    def _build_controls(self) -> None:
        """Build replay control widgets."""
        self._play_btn = pn.widgets.Button(
            name="▶ Play",
            button_type="success",
            width=100,
        )
        self._pause_btn = pn.widgets.Button(
            name="⏸ Pause",
            button_type="warning",
            width=100,
            disabled=True,
        )
        self._stop_btn = pn.widgets.Button(
            name="⏹ Stop",
            button_type="danger",
            width=100,
        )
        self._step_btn = pn.widgets.Button(
            name="→| Step",
            button_type="primary",
            width=100,
        )
        self._reset_btn = pn.widgets.Button(
            name="↺ Reset",
            button_type="default",
            width=100,
        )

        self._speed_slider = pn.widgets.FloatSlider(
            name="Speed (s/candle)",
            start=0.1,
            end=5.0,
            step=0.1,
            value=0.5,
            format="0.0s",
            width=200,
        )
        self._speed_slider.param.watch(self._on_speed_change, "value")

        self._play_btn.on_click(self._start_replay)
        self._pause_btn.on_click(self._pause_replay)
        self._stop_btn.on_click(self._stop_replay)
        self._step_btn.on_click(self._on_step)
        self._reset_btn.on_click(self._on_reset)

    def _build_status_bar(self) -> None:
        """Build status display widgets."""
        self._time_display = pn.pane.Markdown(
            "**Time:** `--`",
            width=220,
            styles={"color": "#e0e0e0"},
        )
        self._position_display = pn.pane.Markdown(
            "**Candle:** 0 / 0",
            width=150,
            styles={"color": "#e0e0e0"},
        )
        self._trade_display = pn.pane.Markdown(
            "**Trades:** 0",
            width=120,
            styles={"color": "#e0e0e0"},
        )
        self._portfolio_display = pn.pane.Markdown(
            f"**Balance:** ${self.initial_balance:,.2f}",
            width=160,
            styles={"color": "#00e5e5"},
        )

    def _build_layout(self) -> None:
        """Build the HoloViews chart layout."""
        hv.extension("bokeh")
        hv.renderer("bokeh").theme = "dark_minimal"

        # Candlestick chart (OHLC)
        self._ohlc_plot = hv.DynamicMap(
            self._ohlcv_callback,
            streams=[self._ohlc_buffer],
        ).opts(
            title=self.session.symbol,
            height=400,
            active_tools=["wheel_zoom", "pan"],
            tools=["pan", "wheel_zoom", "box_zoom", "reset"],
        )

        # Portfolio curve
        self._portfolio_plot = hv.DynamicMap(
            self._portfolio_callback,
            streams=[self._portfolio_buffer],
        ).opts(
            title="Portfolio",
            height=180,
            active_tools=["wheel_zoom"],
            tools=["pan", "wheel_zoom", "box_zoom", "reset"],
            ylabel="Balance ($)",
        )

        # Trade markers overlay
        self._trade_plot = hv.DynamicMap(
            self._trade_callback,
            streams=[self._trade_buffer],
        )

        # Combined layout: price + portfolio, stacked vertically
        combined = self._ohlc_plot * self._trade_plot
        self._layout = hv.Layout([combined, self._portfolio_plot]).cols(1)
        self._layout = self._layout.opts(
            shared_axes=True,
            title=f"Market Replay: {self.session.symbol}",
        )

    # ------------------------------------------------------------------
    # HoloViews callbacks
    # ------------------------------------------------------------------

    def _ohlcv_callback(self, data: pd.DataFrame) -> hv.Overlay:
        """Render the OHLC chart from the buffer."""
        if data is None or data.empty:
            return hv.Curve([], "time", "close").opts(
                height=400, title=self.session.symbol
            )

        df = data.copy()

        # Ensure timestamp is naive datetime for plotting
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
        if df["timestamp_utc"].dt.tz is not None:
            df["timestamp_utc"] = df["timestamp_utc"].dt.tz_localize(None)
        df = df.set_index("timestamp_utc")
        df.index.name = "time"

        if "time_str" not in df.columns and len(df) > 0:
            df["time_str"] = df.index.strftime("%Y-%m-%d %H:%M")

        is_jpy = "JPY" in self.session.symbol.upper()
        price_fmt = "0.000" if is_jpy else "0.00000"

        tooltips = [
            ("Time", "@time_str"),
            ("O", f"@open{{{price_fmt}}}"),
            ("H", f"@high{{{price_fmt}}}"),
            ("L", f"@low{{{price_fmt}}}"),
            ("C", f"@close{{{price_fmt}}}"),
        ]

        chart = df.hvplot.ohlc(
            y=["open", "high", "low", "close"],
            neg_color="red",
            pos_color="green",
            height=400,
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

        return chart

    def _portfolio_callback(self, data: pd.DataFrame) -> hv.Curve:
        """Render the portfolio balance curve from the buffer."""
        if data is None or data.empty:
            return hv.Curve([], "time", "balance").opts(height=180, title="Portfolio")

        df = data.copy()
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
        if df["timestamp_utc"].dt.tz is not None:
            df["timestamp_utc"] = df["timestamp_utc"].dt.tz_localize(None)
        df = df.set_index("timestamp_utc")
        df.index.name = "time"

        tooltips = [("Time", "@time_str"), ("Balance", "$@{portfolio_value}{0,0.00}")]
        if "time_str" not in df.columns:
            df["time_str"] = df.index.strftime("%Y-%m-%d %H:%M")

        curve = df.hvplot.line(
            y="portfolio_value",
            color="cyan",
            height=180,
            hover_cols=["time_str", "portfolio_value"],
        ).opts(
            ylabel="Balance ($)",
            tools=[
                "pan",
                "wheel_zoom",
                "reset",
                HoverTool(tooltips=tooltips, mode="vline"),
            ],
        )

        return curve

    def _trade_callback(self, data: pd.DataFrame) -> Optional[hv.Element]:
        """Render trade entry/exit markers from the buffer."""
        if data is None or data.empty:
            return None

        df = data.copy()
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
        if df["timestamp_utc"].dt.tz is not None:
            df["timestamp_utc"] = df["timestamp_utc"].dt.tz_localize(None)

        longs = df[df["side"] == "LONG"]
        shorts = df[df["side"] == "SHORT"]

        markers = None
        if not longs.empty:
            long_markers = longs.hvplot.scatter(
                x="timestamp_utc",
                y="price",
                color="green",
                marker="triangle",
                size=80,
                alpha=0.9,
                label="Long",
            )
            markers = long_markers

        if not shorts.empty:
            short_markers = shorts.hvplot.scatter(
                x="timestamp_utc",
                y="price",
                color="red",
                marker="inverted_triangle",
                size=80,
                alpha=0.9,
                label="Short",
            )
            markers = markers * short_markers if markers else short_markers

        return markers

    # ------------------------------------------------------------------
    # Playback control
    # ------------------------------------------------------------------

    def _on_speed_change(self, event: Any) -> None:
        """Handle speed slider change."""
        self._speed = float(event.new)
        if self._callback and self._running:
            self._callback.period = int(self._speed * 1000)

    def _advance(self) -> None:
        """Emit the next candle and update all buffers."""
        candle = self.session.next_candle()
        if candle is None:
            self._stop_replay()
            logger.info("Replay exhausted.")
            return

        # Convert CandleEvent to DataFrame row for OHLC buffer
        row_dict = candle.to_dict()
        ts = row_dict["timestamp_utc"]
        if not isinstance(ts, pd.Timestamp):
            ts = pd.Timestamp(ts)
        if ts.tzinfo is not None:
            ts = ts.tz_localize(None)

        ohlc_row = pd.DataFrame([{
            "timestamp_utc": ts,
            "open": row_dict["open"],
            "high": row_dict["high"],
            "low": row_dict["low"],
            "close": row_dict["close"],
            "volume": row_dict["volume"],
        }])
        self._ohlc_buffer.send(ohlc_row)

        # Update status displays
        self._update_status(candle)

    def _update_status(self, candle: CandleEvent) -> None:
        """Update status bar displays."""
        ts_str = candle.timestamp.strftime("%Y-%m-%d %H:%M")
        self._time_display.object = f"**Time:** `{ts_str}`"
        self._position_display.object = (
            f"**Candle:** {self.session.position - 1} / {self.session.total_candles}"
        )
        self._trade_display.object = f"**Trades:** {self.session.trade_count}"
        self._portfolio_display.object = (
            f"**Balance:** ${self._portfolio_value:,.2f}"
        )

    def _start_replay(self, event: Optional[Any] = None) -> None:
        """Start continuous playback."""
        if self.session.is_exhausted:
            self._on_reset()

        self._running = True
        self._play_btn.disabled = True
        self._pause_btn.disabled = False

        period_ms = int(self._speed * 1000)
        self._callback = pn.state.add_periodic_callback(
            self._advance,
            period=period_ms,
        )
        logger.info("Replay started at %.1fs/candle", self._speed)

    def _pause_replay(self, event: Optional[Any] = None) -> None:
        """Pause continuous playback without stopping."""
        if self._callback:
            self._callback.stop()
            self._callback = None
        self._running = False
        self._play_btn.disabled = False
        self._pause_btn.disabled = True
        logger.info("Replay paused at position %d", self.session.position)

    def _stop_replay(self, event: Optional[Any] = None) -> None:
        """Stop playback and cancel the periodic callback."""
        if self._callback:
            self._callback.stop()
            self._callback = None
        self._running = False
        self._play_btn.disabled = False
        self._pause_btn.disabled = True
        logger.info("Replay stopped.")

    def _on_step(self, event: Optional[Any] = None) -> None:
        """Advance exactly one candle."""
        if self.session.is_exhausted:
            return
        candle = self.session.next_candle()
        if candle is None:
            self._update_status(candle)  # type: ignore
            return

        ts = candle.timestamp
        if not isinstance(ts, pd.Timestamp):
            ts = pd.Timestamp(ts)
        if ts.tzinfo is not None:
            ts = ts.tz_localize(None)

        ohlc_row = pd.DataFrame([{
            "timestamp_utc": ts,
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
        }])
        self._ohlc_buffer.send(ohlc_row)
        self._update_status(candle)

    def _on_reset(self, event: Optional[Any] = None) -> None:
        """Reset the session and clear all buffers."""
        self._stop_replay()
        self.session.reset()
        self._portfolio_value = self.initial_balance

        # Clear buffers
        empty_ohlc = pd.DataFrame(
            columns=["timestamp_utc", "open", "high", "low", "close", "volume"]
        )
        empty_portfolio = pd.DataFrame(columns=["timestamp_utc", "portfolio_value"])
        empty_trades = pd.DataFrame(
            columns=["timestamp_utc", "price", "pnl_r", "action", "side"]
        )
        self._ohlc_buffer.send(empty_ohlc)
        self._portfolio_buffer.send(empty_portfolio)
        self._trade_buffer.send(empty_trades)

        self._time_display.object = "**Time:** `--`"
        self._position_display.object = (
            f"**Candle:** 0 / {self.session.total_candles}"
        )
        self._trade_display.object = "**Trades:** 0"
        self._portfolio_display.object = (
            f"**Balance:** ${self.initial_balance:,.2f}"
        )
        logger.info("ReplayDashboard reset.")

    def _on_trade(
        self,
        action: str,
        price: float,
        side: str,
        pnl_r: Optional[float] = None,
    ) -> None:
        """Record a trade event and update the portfolio buffer."""
        trade = self.session.emit_trade(action=action, price=price, side=side, pnl_r=pnl_r)

        # Update portfolio value
        if pnl_r is not None:
            self._portfolio_value += pnl_r * self.risk_per_trade

        # Update trade marker buffer
        ts = trade.timestamp
        if not isinstance(ts, pd.Timestamp):
            ts = pd.Timestamp(ts)
        if ts.tzinfo is not None:
            ts = ts.tz_localize(None)

        trade_row = pd.DataFrame([{
            "timestamp_utc": ts,
            "price": price,
            "pnl_r": pnl_r or 0.0,
            "action": action,
            "side": side,
        }])
        self._trade_buffer.send(trade_row)

        # Update portfolio buffer
        portfolio_row = pd.DataFrame([{
            "timestamp_utc": ts,
            "portfolio_value": self._portfolio_value,
        }])
        self._portfolio_buffer.send(portfolio_row)

    # ------------------------------------------------------------------
    # Layout and display
    # ------------------------------------------------------------------

    def get_layout(self) -> pn.Column:
        """
        Build and return the complete Panel dashboard layout.

        Returns:
            Panel Column containing controls, status bar, and chart.
        """
        # Header
        header = pn.pane.Markdown(
            f"## 🌊 Market Replay: {self.session.symbol} ({self.session.timeframe})",
            styles={"color": "#e0e0e0", "background": "#1a1a2e", "padding": "8px"},
        )

        # Control row
        control_row = pn.row(
            self._play_btn,
            self._pause_btn,
            self._stop_btn,
            self._step_btn,
            self._reset_btn,
            self._speed_slider,
            sizing_mode="stretch_width",
        )

        # Status row
        status_row = pn.row(
            self._time_display,
            self._position_display,
            self._trade_display,
            self._portfolio_display,
            spacing=10,
        )

        # HoloViews chart pane
        chart_pane = pn.pane.HoloViews(
            self._layout,
            sizing_mode="stretch_width",
            height=620,
        )

        dashboard = pn.Column(
            header,
            control_row,
            status_row,
            chart_pane,
            sizing_mode="stretch_width",
            styles={"background": "#1a1a2e"},
        )

        return dashboard

    def show(self, threaded: bool = True) -> None:
        """
        Serve the dashboard and open in a browser.

        Args:
            threaded: If True, serve in a background thread (non-blocking).
                      If False, block the calling thread.
        """
        layout = self.get_layout()

        if self.output_file:
            try:
                hv.save(
                    layout,
                    str(self.output_file),
                    backend="bokeh",
                )
                logger.info("Dashboard saved to %s", self.output_file)
            except Exception as exc:
                logger.warning("Failed to save dashboard HTML: %s", exc)

        pn.serve(layout, show=True, threaded=threaded)
        logger.info("ReplayDashboard server started.")
