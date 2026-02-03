import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

import pandas as pd
import polars as pl
import holoviews as hv
from holoviews.streams import Buffer
import panel as pn
import hvplot.pandas

from src.backtest.replay import ReplaySession
from src.models.events import CandleEvent, TradeEvent

logger = logging.getLogger(__name__)

class ReplayDashboard:
    """
    Real-time interactive dashboard for market replay.
    """
    def __init__(self, session: ReplaySession):
        self.session = session
        
        # HoloViews Buffer for real-time OHLC data
        # Define schema for the buffer
        self.ohlcv_buffer = Buffer(
            pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']),
            length=100 # Show last 100 candles
        )
        
        # Shared controls
        self.play_button = pn.widgets.Button(name='▶ Play', button_type='success', width=100)
        self.pause_button = pn.widgets.Button(name='⏸ Pause', button_type='warning', width=100)
        self.speed_slider = pn.widgets.FloatSlider(name='Speed (s)', start=0.1, end=2.0, step=0.1, value=0.5)
        
        self._callback = None
        self.play_button.on_click(self._start_replay)
        self.pause_button.on_click(self._stop_replay)

    def _update_replay(self):
        candle = self.session.next_candle()
        if candle is None:
            self._stop_replay()
            logger.info("Replay finished.")
            return
        
        # Update buffer
        # Candle is a dict from row.to_dict()
        df_row = pd.DataFrame([candle])
        self.ohlcv_buffer.send(df_row)

    def _start_replay(self, event=None):
        if self._callback is None:
            self._callback = pn.state.add_periodic_callback(
                self._update_replay, 
                period=int(self.speed_slider.value * 1000)
            )
            self.play_button.name = 'Running...'
            self.play_button.disabled = True

    def _stop_replay(self, event=None):
        if self._callback:
            self._callback.stop()
            self._callback = None
            self.play_button.name = '▶ Play'
            self.play_button.disabled = False

    def get_layout(self):
        """Builds and returns the dashboard layout."""
        # Use DynamicMap to link buffer to plot
        dmap = hv.DynamicMap(
            lambda data: hv.Curve(data, 'timestamp', 'close', label=f"{self.session.symbol} (Replay)"),
            streams=[self.ohlcv_buffer]
        ).opts(
            width=1000, height=400,
            active_tools=['wheel_zoom', 'pan'],
            title=f"Market Replay: {self.session.symbol}"
        )
        
        # Add a candlestick representation if possible (requires more complex logic for dynamic OHLC)
        # For now, start with a simple Curve to verify stream logic
        
        controls = pn.Row(
            self.play_button,
            self.pause_button,
            self.speed_slider
        )
        
        return pn.Column(
            "## 🌊 Market Replay Dashboard",
            dmap,
            controls
        )

    def show(self):
        pn.extension()
        layout = self.get_layout()
        pn.serve(layout, show=True, threaded=True)
