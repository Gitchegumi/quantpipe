"""Tests for ReplaySession (buffer management, time progression, reset)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.backtest.replay import ReplayConfig, ReplaySession


@pytest.fixture
def sample_data():
    """Build a 20-candle Polars DataFrame for testing."""
    import polars as pl

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
def session(sample_data):
    """Create a default ReplaySession for testing."""
    config = ReplayConfig(symbol="EURUSD", timeframe="1m", buffer_size=5)
    return ReplaySession(sample_data, config)


class TestReplayConfig:
    """Tests for ReplayConfig dataclass."""

    def test_defaults(self):
        config = ReplayConfig(symbol="EURUSD")
        assert config.symbol == "EURUSD"
        assert config.timeframe == "1m"
        assert config.buffer_size == 1000
        assert config.start_idx == 0
        assert config.end_idx is None

    def test_custom_values(self):
        config = ReplayConfig(symbol="GBPUSD", timeframe="15m", buffer_size=200, start_idx=5, end_idx=15)
        assert config.symbol == "GBPUSD"
        assert config.timeframe == "15m"
        assert config.buffer_size == 200
        assert config.start_idx == 5
        assert config.end_idx == 15


class TestReplaySession:
    """Tests for ReplaySession core API."""

    def test_initialization(self, sample_data):
        config = ReplayConfig(symbol="EURUSD", timeframe="1m", buffer_size=10)
        session = ReplaySession(sample_data, config)
        assert session.symbol == "EURUSD"
        assert session.timeframe == "1m"
        assert session.total_candles == 20
        assert session.position == 1
        assert not session.is_exhausted

    def test_initialization_missing_column(self, sample_data):
        import polars as pl
        bad_df = sample_data.drop("high")
        config = ReplayConfig(symbol="EURUSD")
        with pytest.raises(ValueError, match="missing columns"):
            ReplaySession(bad_df, config)

    def test_initialization_index_clamping(self, sample_data):
        # start_idx beyond data -> clamped to end (0 candles)
        config = ReplayConfig(symbol="EURUSD", start_idx=999, end_idx=9999)
        session = ReplaySession(sample_data, config)
        assert session.total_candles == 0  # start clamped to end, range is empty

    def test_next_candle_basic(self, session):
        candle = session.next_candle()
        assert candle is not None
        assert candle.symbol == "EURUSD"
        assert candle.open == 1.1000
        assert candle.high == 1.1001
        assert candle.low == 1.0999
        assert candle.close == pytest.approx(1.10005)
        assert session.position == 2

    def test_next_candle_exhaustion(self, sample_data):
        config = ReplayConfig(symbol="EURUSD", buffer_size=5, start_idx=0, end_idx=3)
        session = ReplaySession(sample_data, config)
        assert session.total_candles == 3

        for i in range(3):
            candle = session.next_candle()
            assert candle is not None, f"Failed at iteration {i}"

        # One more should be None (exhausted)
        assert session.next_candle() is None
        assert session.is_exhausted

    def test_step_forward(self, sample_data):
        config = ReplayConfig(symbol="EURUSD", buffer_size=5)
        session = ReplaySession(sample_data, config)
        session.step_forward(3)
        assert session.position == 4  # Started at 1, stepped 3 -> position 4
        assert not session.is_exhausted

    def test_step_forward_exhausted(self, sample_data):
        config = ReplayConfig(symbol="EURUSD", buffer_size=5, start_idx=0, end_idx=1)
        session = ReplaySession(sample_data, config)
        session.next_candle()  # consume the only candle
        result = session.step_forward(1)
        assert result is None
        assert session.is_exhausted

    def test_current_candle(self, sample_data):
        config = ReplayConfig(symbol="EURUSD", buffer_size=5)
        session = ReplaySession(sample_data, config)
        assert session.current_candle() is None  # No candles consumed yet
        session.next_candle()
        curr = session.current_candle()
        assert curr is not None
        assert curr.open == 1.1000

    def test_reset(self, sample_data):
        config = ReplayConfig(symbol="EURUSD", buffer_size=5)
        session = ReplaySession(sample_data, config)
        session.next_candle()
        session.next_candle()
        session.next_candle()
        assert session.position == 4
        session.reset()
        assert session.position == 1
        assert not session.is_exhausted
        assert session.trade_count == 0

    def test_reset_clears_trades(self, sample_data):
        config = ReplayConfig(symbol="EURUSD", buffer_size=5)
        session = ReplaySession(sample_data, config)
        session.next_candle()
        session.emit_trade("OPEN", 1.1000, "LONG")
        session.emit_trade("CLOSE", 1.1010, "LONG", pnl_r=2.0)
        assert session.trade_count == 2
        session.reset()
        assert session.trade_count == 0
        assert len(session.trades) == 0

    def test_buffer_df(self, sample_data):
        config = ReplayConfig(symbol="EURUSD", buffer_size=5)
        session = ReplaySession(sample_data, config)
        session.step_forward(3)
        buf = session.buffer_df()
        assert len(buf) <= 5
        assert "timestamp_utc" in buf.columns
        assert "close" in buf.columns

    def test_emit_trade(self, session):
        session.next_candle()
        trade = session.emit_trade("OPEN", 1.1005, "LONG")
        assert trade.symbol == "EURUSD"
        assert trade.action == "OPEN"
        assert trade.side == "LONG"
        assert session.trade_count == 1

        trade2 = session.emit_trade("CLOSE", 1.1015, "LONG", pnl_r=1.5)
        assert trade2.pnl_r == 1.5
        assert session.trade_count == 2

    def test_iterate(self, sample_data):
        config = ReplayConfig(symbol="EURUSD", buffer_size=5, start_idx=0, end_idx=3)
        session = ReplaySession(sample_data, config)
        candles = list(session.iterate())
        assert len(candles) == 3
        assert all(c.symbol == "EURUSD" for c in candles)

    def test_current_timestamp(self, sample_data):
        config = ReplayConfig(symbol="EURUSD", buffer_size=5)
        session = ReplaySession(sample_data, config)
        assert session.current_timestamp is None
        session.next_candle()
        ts = session.current_timestamp
        assert ts is not None
        assert ts.year == 2025
        assert ts.month == 1

    def test_position_1_indexed(self, sample_data):
        config = ReplayConfig(symbol="EURUSD", buffer_size=5)
        session = ReplaySession(sample_data, config)
        assert session.position == 1  # 1-indexed at start
        session.next_candle()
        assert session.position == 2
        session.next_candle()
        assert session.position == 3

    def test_trades_sequence(self, session):
        session.next_candle()
        session.emit_trade("OPEN", 1.1005, "LONG")
        session.emit_trade("CLOSE", 1.1015, "LONG", pnl_r=1.0)
        trades = session.trades
        assert len(trades) == 2
        assert trades[0].action == "OPEN"
        assert trades[1].action == "CLOSE"
        assert trades[1].pnl_r == 1.0
