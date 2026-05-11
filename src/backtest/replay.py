"""Market replay session for step-through backtest visualization.

This module provides a stateful ReplaySession that reads candles from a
Polars DataFrame (loaded via the standard ingestion pipeline) and streams
them one-by-one or in configurable windows. Designed for real-time replay
dashboard visualization.

Key differences from batch backtest:
- ReplaySession is stateful, maintaining current position across calls
- Supports variable-speed playback (0.1x to 5x)
- Emits CandleEvent and TradeEvent for each step
- Integrates with ReplayDashboard for HoloViews visualization
"""
from __future__ import annotations

import logging
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import polars as pl

from src.models.events import CandleEvent, TradeEvent

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


@dataclass
class ReplayConfig:
    """Configuration for a replay session.

    Attributes:
        symbol: Trading pair symbol (e.g., 'EURUSD').
        timeframe: Candle timeframe string (e.g., '1m', '15m').
        buffer_size: Number of candles to hold in the rolling window.
        start_idx: Starting candle index (0-indexed).
        end_idx: Ending candle index (inclusive, None = end of data).
    """

    symbol: str
    timeframe: str = "1m"
    buffer_size: int = 1000
    start_idx: int = 0
    end_idx: Optional[int] = None


class ReplaySession:
    """
    Manages a stateful market replay session, streaming candles one-by-one.

    Replaces the DuckDB-backed ReplaySession with one that reads directly
    from a Polars DataFrame via the standard ingestion pipeline, enabling
    replay against any dataset (CSV/Parquet) without a vault dependency.

    The session maintains a rolling buffer of the last N candles for
    visualization and exposes a step interface for replay control.

    Examples:
        >>> import polars as pl
        >>> from src.data_io.ingestion import ingest_ohlcv_data
        >>> result = ingest_ohlcv_data("price_data/eurusd/test.csv", 1, return_polars=True)
        >>> session = ReplaySession(result.data, ReplayConfig(symbol="EURUSD"))
        >>> candle = session.next_candle()
        >>> candle.symbol
        'EURUSD'
        >>> session.step_forward()
        >>> session.position
        2
        >>> session.reset()
        >>> session.position
        1
    """

    def __init__(
        self,
        data: pl.DataFrame,
        config: ReplayConfig,
    ) -> None:
        """
        Initialize a replay session from a Polars DataFrame.

        Args:
            data: Polars DataFrame with columns: timestamp_utc, open, high, low,
                close, volume, plus optional indicator columns.
            config: ReplayConfig with symbol, timeframe, buffer_size, etc.
        """
        self._data = data
        self._config = config
        self._total = len(data)

        # Validate required columns
        required = {"timestamp_utc", "open", "high", "low", "close"}
        missing = required - set(data.columns)
        if missing:
            raise ValueError(f"ReplaySession missing columns: {missing}")

        # Clamp indices to data bounds
        start_idx = max(0, config.start_idx)
        end_idx = config.end_idx if config.end_idx is not None else self._total
        end_idx = min(end_idx, self._total)
        # Ensure start never exceeds end
        if start_idx > end_idx:
            start_idx = end_idx

        self._start_idx = start_idx
        self._end_idx = end_idx

        # Current position (1-indexed to match human-readable candle numbers)
        self._position = start_idx + 1

        # Rolling buffer of last N candles (DataFrame for efficient slicing)
        self._buffer: list[pl.DataFrame] = []
        self._buffer_max = max(1, config.buffer_size)

        # Trade event tracking
        self._trade_count = 0
        self._trades: list[TradeEvent] = []

        # Pre-load initial buffer
        self._refill_buffer()

        logger.info(
            "ReplaySession initialized: %s %s, %d candles (%d:%d), buffer=%d",
            config.symbol,
            config.timeframe,
            self._total,
            self._start_idx,
            self._end_idx,
            self._buffer_max,
        )

    @property
    def symbol(self) -> str:
        """Trading pair symbol."""
        return self._config.symbol

    @property
    def timeframe(self) -> str:
        """Candle timeframe string."""
        return self._config.timeframe

    @property
    def position(self) -> int:
        """Current candle position (1-indexed)."""
        return self._position

    @property
    def total_candles(self) -> int:
        """Total number of candles in the dataset."""
        return self._end_idx - self._start_idx

    @property
    def is_exhausted(self) -> bool:
        """True if the session has consumed all candles."""
        return self._position > self._end_idx

    @property
    def current_timestamp(self) -> Optional[datetime]:
        """Timestamp of the current candle, or None if exhausted."""
        if self.is_exhausted or not self._buffer:
            return None
        row = self._buffer[-1]
        ts = row["timestamp_utc"][0]
        if isinstance(ts, datetime):
            return ts
        # Polars may return pl.Datetime
        return ts

    @property
    def trade_count(self) -> int:
        """Total number of trade events emitted."""
        return self._trade_count

    @property
    def trades(self) -> Sequence[TradeEvent]:
        """Sequence of trade events emitted so far."""
        return self._trades

    def _refill_buffer(self) -> None:
        """Refill the rolling buffer with up to buffer_max candles ending at current position."""
        # Current position maps to row at index (position - 1) in the slice
        end_row = min(self._position, self._end_idx)
        start_row = max(self._start_idx, end_row - self._buffer_max)

        if end_row <= start_row:
            self._buffer = []
            return

        slice_df = self._data.slice(start_row, end_row - start_row)
        self._buffer = [slice_df]

    def _buffer_as_df(self) -> pl.DataFrame:
        """Return the current buffer as a single Polars DataFrame."""
        if not self._buffer:
            return self._data.slice(0, 0)
        return pl.concat(self._buffer)

    def next_candle(self) -> Optional[CandleEvent]:
        """
        Return the next CandleEvent in the sequence.

        Advances the position by one. Returns None when the session is exhausted.

        Returns:
            CandleEvent for the next candle, or None if no more candles.
        """
        if self.is_exhausted:
            return None

        row_idx = self._position - 1  # 0-indexed
        if row_idx < self._start_idx or row_idx >= self._end_idx:
            self._position = self._end_idx + 1
            return None

        row = self._data.slice(row_idx, 1)
        ts = row["timestamp_utc"][0]

        # Convert Polars Datetime to native datetime
        if not isinstance(ts, datetime):
            if hasattr(ts, "to_pydatetime"):
                ts = ts.to_pydatetime()
            else:
                ts = datetime.fromisoformat(str(ts))

        event = CandleEvent(
            timestamp=ts,
            symbol=self._config.symbol,
            open=float(row["open"][0]),
            high=float(row["high"][0]),
            low=float(row["low"][0]),
            close=float(row["close"][0]),
            volume=float(row["volume"][0]),
        )

        self._position += 1
        self._refill_buffer()

        return event

    def step_forward(self, steps: int = 1) -> Optional[CandleEvent]:
        """
        Advance by a fixed number of candles.

        Args:
            steps: Number of candles to advance. Default 1.

        Returns:
            CandleEvent for the candle after stepping, or None if exhausted.
        """
        for _ in range(steps):
            self.next_candle()
        if self.is_exhausted:
            return None
        if self._position <= self._start_idx + 1:
            return None
        buf = self._buffer_as_df()
        if buf.is_empty():
            return None
        last_row = buf.tail(1)
        ts = last_row["timestamp_utc"][0]
        if not isinstance(ts, datetime):
            if hasattr(ts, "to_pydatetime"):
                ts = ts.to_pydatetime()
            else:
                ts = datetime.fromisoformat(str(ts))
        return CandleEvent(
            timestamp=ts,
            symbol=self._config.symbol,
            open=float(last_row["open"][0]),
            high=float(last_row["high"][0]),
            low=float(last_row["low"][0]),
            close=float(last_row["close"][0]),
            volume=float(last_row["volume"][0]),
        )

    def current_candle(self) -> Optional[CandleEvent]:
        """
        Return the most recently emitted CandleEvent without advancing.

        Returns:
            Last CandleEvent, or None if no candles have been emitted yet.
        """
        if self._position <= self._start_idx + 1:
            return None
        buf = self._buffer_as_df()
        if buf.is_empty():
            return None
        # Last row of buffer
        last_row = buf.tail(1)
        ts = last_row["timestamp_utc"][0]
        if not isinstance(ts, datetime):
            if hasattr(ts, "to_pydatetime"):
                ts = ts.to_pydatetime()
            else:
                ts = datetime.fromisoformat(str(ts))
        return CandleEvent(
            timestamp=ts,
            symbol=self._config.symbol,
            open=float(last_row["open"][0]),
            high=float(last_row["high"][0]),
            low=float(last_row["low"][0]),
            close=float(last_row["close"][0]),
            volume=float(last_row["volume"][0]),
        )

    def buffer_df(self) -> pl.DataFrame:
        """
        Return the current rolling buffer as a DataFrame.

        The buffer contains at most buffer_size candles ending at the current position,
        suitable for passing to the visualization pipeline.

        Returns:
            Polars DataFrame with the rolling candle window.
        """
        return self._buffer_as_df()

    def emit_trade(
        self,
        action: str,
        price: float,
        side: str,
        pnl_r: Optional[float] = None,
    ) -> TradeEvent:
        """
        Emit and record a trade event at the current position.

        Args:
            action: "OPEN" or "CLOSE".
            price: Fill price.
            side: "LONG" or "SHORT".
            pnl_r: Realized PnL in R-multiples (for CLOSE events).

        Returns:
            The emitted TradeEvent.
        """
        ts = self.current_timestamp or datetime.now()
        event = TradeEvent(
            timestamp=ts,
            symbol=self._config.symbol,
            action=action,
            price=price,
            side=side,
            pnl_r=pnl_r,
        )
        self._trades.append(event)
        self._trade_count += 1
        return event

    def reset(self) -> None:
        """Reset the session to its starting position, clearing trades."""
        self._position = self._start_idx + 1
        self._trade_count = 0
        self._trades = []
        self._refill_buffer()
        logger.info("ReplaySession reset to position %d", self._position)

    def iterate(self) -> Iterator[CandleEvent]:
        """
        Yield CandleEvents from the current position to exhaustion.

        Yields:
            CandleEvent for each candle in sequence.

        Examples:
            >>> session = ReplaySession(data, config)
            >>> for event in session.iterate():
            ...     print(event.timestamp, event.close)
        """
        while True:
            candle = self.next_candle()
            if candle is None:
                break
            yield candle
