"""Tests for ReplayDashboard (widget creation, layout structure)."""
from __future__ import annotations

import pytest

from src.backtest.replay import ReplayConfig, ReplaySession


try:
    import panel as pn
    import holoviews as hv
    HAS_PANEL = True
except ImportError:
    HAS_PANEL = False

pytestmark = pytest.mark.skipif(
    not HAS_PANEL,
    reason="Requires panel and holoviews (optional viz stack)",
)


@pytest.fixture
def sample_data():
    """Build a 20-candle Polars DataFrame for testing."""
    import polars as pl
    from datetime import datetime, timezone

    n = 20
    timestamps = [
        datetime(2025, 1, 1, 12, i, tzinfo=timezone.utc) for i in range(n)
    ]
    df = pl.DataFrame(
        {
            "timestamp_utc": timestamps,
            "open": [1.1000 + i * 0.0001 for i in range(n)],
            "high": [1.1001 + i * 0.0001 for i in range(n)],
            "low": [1.0999 + i * 0.0001 for i in range(n)],
            "close": [1.1000 + i * 0.0001 + 0.00005 for i in range(n)],
            "volume": [1000.0 + i * 10 for i in range(n)],
        }
    )
    return df


@pytest.fixture
def replay_session(sample_data):
    """Create a default ReplaySession for testing."""
    config = ReplayConfig(symbol="EURUSD", timeframe="1m", buffer_size=5)
    return ReplaySession(sample_data, config)


class TestReplayDashboardInit:
    """Tests for ReplayDashboard initialization."""

    def test_init_without_panel(self, replay_session):
        """Dashboard initializes with all expected attributes."""
        from src.visualization.replay_dashboard import ReplayDashboard

        dashboard = ReplayDashboard(replay_session)
        assert dashboard.session is replay_session
        assert dashboard.initial_balance == 2500.0
        assert dashboard.risk_per_trade == 6.25
        assert dashboard._speed == 0.5
        assert not dashboard._running

    def test_init_custom_balance(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(
            replay_session,
            initial_balance=5000.0,
            risk_per_trade=10.0,
        )
        assert dashboard.initial_balance == 5000.0
        assert dashboard.risk_per_trade == 10.0

    def test_speed_slider_initialized(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(replay_session)
        assert dashboard._speed_slider.value == 0.5
        assert dashboard._speed_slider.start == 0.1
        assert dashboard._speed_slider.end == 5.0


class TestReplayDashboardControls:
    """Tests for ReplayDashboard control widgets."""

    def test_play_button_exists(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(replay_session)
        assert dashboard._play_btn is not None
        assert dashboard._play_btn.name == "▶ Play"

    def test_pause_button_exists(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(replay_session)
        assert dashboard._pause_btn is not None
        assert dashboard._pause_btn.name == "⏸ Pause"

    def test_stop_button_exists(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(replay_session)
        assert dashboard._stop_btn is not None

    def test_step_button_exists(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(replay_session)
        assert dashboard._step_btn is not None
        assert dashboard._step_btn.name == "→| Step"

    def test_speed_slider_range(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(replay_session)
        assert dashboard._speed_slider.start == 0.1
        assert dashboard._speed_slider.end == 5.0

    def test_status_displays_exist(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(replay_session)
        assert dashboard._time_display is not None
        assert dashboard._position_display is not None
        assert dashboard._trade_display is not None
        assert dashboard._portfolio_display is not None


class TestReplayDashboardBuffer:
    """Tests for ReplayDashboard buffer streams."""

    def test_ohlc_buffer_exists(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(replay_session)
        assert dashboard._ohlc_buffer is not None
        # Buffer should be empty at start
        assert dashboard._ohlc_buffer.data.empty

    def test_portfolio_buffer_exists(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(replay_session)
        assert dashboard._portfolio_buffer is not None
        assert dashboard._portfolio_buffer.data.empty

    def test_trade_buffer_exists(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(replay_session)
        assert dashboard._trade_buffer is not None


class TestReplayDashboardLayout:
    """Tests for ReplayDashboard layout structure."""

    def test_get_layout_returns_column(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(replay_session)
        layout = dashboard.get_layout()
        assert isinstance(layout, pn.Column)

    def test_layout_contains_header(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(replay_session)
        layout = dashboard.get_layout()
        # First item should be the markdown header
        assert len(layout) >= 4  # header, controls, status, chart

    def test_layout_contains_control_row(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(replay_session)
        layout = dashboard.get_layout()
        # Should have control row (Row widget) as second item
        assert hasattr(layout, "__iter__")
        items = list(layout)
        assert len(items) >= 3

    def test_holoviews_layout_built(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(replay_session)
        assert dashboard._layout is not None
        assert isinstance(dashboard._layout, hv.Layout)


class TestReplayDashboardStatusUpdate:
    """Tests for status display updates."""

    def test_status_start_state(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(replay_session)
        # Should show initial state
        assert "--" in dashboard._time_display.object
        assert "0" in dashboard._position_display.object
        assert "0" in dashboard._trade_display.object

    def test_status_after_step(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(replay_session)
        dashboard._on_step()
        # Time should now be set (not --)
        assert "--" not in dashboard._time_display.object


class TestReplayDashboardReset:
    """Tests for reset functionality."""

    def test_reset_clears_buffers(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(replay_session)
        # Advance a few candles
        dashboard._on_step()
        dashboard._on_step()
        dashboard._on_reset()
        # Buffers should be empty after reset
        assert dashboard._ohlc_buffer.data.empty
        assert dashboard._portfolio_buffer.data.empty

    def test_reset_clears_trade_count(self, replay_session):
        from src.visualization.replay_dashboard import ReplayDashboard
        dashboard = ReplayDashboard(replay_session)
        dashboard._on_step()
        dashboard._on_trade("OPEN", 1.1005, "LONG")
        assert dashboard.session.trade_count == 1
        dashboard._on_reset()
        assert dashboard.session.trade_count == 0
