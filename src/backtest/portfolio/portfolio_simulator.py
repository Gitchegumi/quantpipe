"""Portfolio simulator for time-synchronized multi-symbol backtesting.

This module implements portfolio-mode simulation where all symbols trade
against a shared running balance. Trades execute chronologically across
all symbols, with wins/losses affecting capital available for subsequent trades.

Key features:
- Time-synchronized execution across all symbols
- Shared portfolio equity that updates after each trade closes
- Position sizing at 0.25% of current equity
- Maximum one open position per symbol at a time
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
import polars as pl

from src.models.core import TradeSignal


logger = logging.getLogger(__name__)


@dataclass
class OpenPosition:
    """Tracks an open position for a symbol.

    Attributes:
        symbol: Currency pair
        signal_id: Original signal ID
        entry_timestamp: When position was opened
        entry_bar_idx: Index of entry bar
        entry_price: Entry fill price
        stop_price: Current stop loss price
        target_price: Take profit price
        direction: 'LONG' or 'SHORT'
        position_size: Position size in lots
        risk_amount: Dollar amount at risk
    """

    symbol: str
    signal_id: str
    entry_timestamp: datetime
    entry_bar_idx: int
    entry_price: float
    stop_price: float
    target_price: float
    direction: str
    position_size: float
    risk_amount: float


@dataclass
class ClosedTrade:
    """Record of a closed trade.

    Attributes:
        symbol: Currency pair
        signal_id: Original signal ID
        direction: 'LONG' or 'SHORT'
        entry_timestamp: Entry time
        exit_timestamp: Exit time
        entry_price: Entry fill price
        exit_price: Exit fill price
        exit_reason: 'stop_loss', 'take_profit', or 'end_of_data'
        pnl_dollars: Profit/loss in dollars
        pnl_r: Profit/loss as R-multiple
        risk_amount: Original risk amount
    """

    symbol: str
    signal_id: str
    direction: str
    entry_timestamp: datetime
    exit_timestamp: datetime
    entry_price: float
    exit_price: float
    exit_reason: str
    pnl_dollars: float
    pnl_r: float
    risk_amount: float


@dataclass
class PortfolioResult:
    """Result from portfolio-mode multi-symbol backtest.

    Attributes:
        run_id: Unique run identifier
        direction_mode: Direction mode (LONG/SHORT/BOTH)
        starting_equity: Initial capital
        final_equity: Ending capital
        equity_curve: List of (timestamp, equity) tuples
        closed_trades: All closed trades
        total_trades: Total trades across all symbols
        total_pnl: Total P&L in dollars
        per_symbol_trades: Breakdown by symbol
        symbols: List of symbols traded
    """

    run_id: str
    direction_mode: str
    start_time: datetime
    end_time: datetime
    starting_equity: float
    final_equity: float
    equity_curve: list[tuple[datetime, float]] = field(default_factory=list)
    closed_trades: list[ClosedTrade] = field(default_factory=list)
    total_trades: int = 0
    total_pnl: float = 0.0
    per_symbol_trades: dict = field(default_factory=dict)
    symbols: list[str] = field(default_factory=list)
    data_start_date: Optional[datetime] = None
    data_end_date: Optional[datetime] = None


class PortfolioSimulator:
    """Time-synchronized portfolio simulation with shared equity.

    Processes signals from all symbols chronologically, maintaining
    a shared running balance that updates after each trade closes.

    Attributes:
        starting_equity: Initial portfolio capital ($2,500)
        risk_per_trade: Position sizing as fraction of equity (0.0025 = 0.25%)
        max_positions_per_symbol: Maximum concurrent positions per symbol (1)

    Example:
        >>> simulator = PortfolioSimulator(starting_equity=2500.0)
        >>> result = simulator.simulate(symbol_data, symbol_signals)
        >>> print(f"Final equity: ${result.final_equity:.2f}")
    """

    def __init__(
        self,
        starting_equity: float = 2500.0,
        risk_per_trade: float = 0.0025,  # 0.25%
        max_positions_per_symbol: int = 1,
        target_r_mult: float = 2.0,  # Default 2:1 reward/risk
    ):
        """Initialize portfolio simulator.

        Args:
            starting_equity: Initial portfolio capital
            risk_per_trade: Position sizing as fraction of equity (0.0025 = 0.25%)
            max_positions_per_symbol: Maximum concurrent positions per symbol
            target_r_mult: Target R-multiple for take profit
        """
        self.starting_equity = starting_equity
        self.risk_per_trade = risk_per_trade
        self.max_positions_per_symbol = max_positions_per_symbol
        self.target_r_mult = target_r_mult
        self.current_equity = starting_equity
        self.open_positions: dict[str, OpenPosition] = {}  # symbol -> position
        self.closed_trades: list[ClosedTrade] = []
        self.equity_curve: list[tuple[datetime, float]] = []

    def simulate(
        self,
        symbol_data: dict[str, pl.DataFrame],
        symbol_signals: dict[str, list],  # symbol -> list of signal dicts
        direction_mode: str = "BOTH",
        run_id: str = "portfolio_run",
    ) -> PortfolioResult:
        """Run time-synchronized simulation across all symbols.

        Args:
            symbol_data: Dict mapping symbol to enriched Polars DataFrame
            symbol_signals: Dict mapping symbol to list of signal dicts
            direction_mode: Direction mode (LONG/SHORT/BOTH)
            run_id: Unique run identifier

        Returns:
            PortfolioResult with equity curve and trade breakdown
        """
        start_time = datetime.now()
        logger.info(
            "Starting portfolio simulation: %d symbols, $%.2f starting equity",
            len(symbol_data),
            self.starting_equity,
        )

        # Reset state
        self.current_equity = self.starting_equity
        self.open_positions = {}
        self.closed_trades = []
        self.equity_curve = []

        # Merge all timestamps across symbols
        all_timestamps = self._merge_timestamps(symbol_data)
        logger.info("Processing %d unique timestamps", len(all_timestamps))

        # Index signals by timestamp for each symbol
        signals_by_ts = self._index_signals_by_timestamp(symbol_signals)

        # Get data bounds
        data_start = all_timestamps[0] if all_timestamps else start_time
        data_end = all_timestamps[-1] if all_timestamps else start_time

        # Record initial equity
        self.equity_curve.append((data_start, self.current_equity))

        # Process each timestamp chronologically
        for ts in all_timestamps:
            self._process_bar(ts, symbol_data, signals_by_ts)

        # Close any remaining open positions at end
        self._close_all_positions_at_end(symbol_data)

        # Record final equity
        self.equity_curve.append((data_end, self.current_equity))

        end_time = datetime.now()

        # Build per-symbol breakdown
        per_symbol_trades = self._build_per_symbol_breakdown()

        result = PortfolioResult(
            run_id=run_id,
            direction_mode=direction_mode,
            start_time=start_time,
            end_time=end_time,
            starting_equity=self.starting_equity,
            final_equity=self.current_equity,
            equity_curve=self.equity_curve.copy(),
            closed_trades=self.closed_trades.copy(),
            total_trades=len(self.closed_trades),
            total_pnl=self.current_equity - self.starting_equity,
            per_symbol_trades=per_symbol_trades,
            symbols=list(symbol_data.keys()),
            data_start_date=data_start,
            data_end_date=data_end,
        )

        logger.info(
            "Portfolio simulation complete: %d trades, final equity: $%.2f (%.2f%%)",
            result.total_trades,
            result.final_equity,
            (result.final_equity / self.starting_equity - 1) * 100,
        )

        return result

    def _merge_timestamps(self, symbol_data: dict[str, pl.DataFrame]) -> list[datetime]:
        """Merge all timestamps across symbols into single sorted list."""
        all_ts = set()
        for df in symbol_data.values():
            ts_col = "timestamp_utc" if "timestamp_utc" in df.columns else "timestamp"
            if ts_col in df.columns:
                timestamps = df[ts_col].to_list()
                all_ts.update(timestamps)
        return sorted(all_ts)

    def _index_signals_by_timestamp(
        self, symbol_signals: dict[str, list]
    ) -> dict[datetime, list[tuple[str, dict]]]:
        """Index all signals by their timestamp.

        Returns:
            Dict mapping timestamp -> list of (symbol, signal) tuples
        """
        signals_by_ts: dict[datetime, list[tuple[str, dict]]] = {}

        for symbol, signals in symbol_signals.items():
            for signal in signals:
                # Handle both dict and object signals
                if hasattr(signal, "timestamp_utc"):
                    ts = signal.timestamp_utc
                elif isinstance(signal, dict):
                    ts = signal.get("timestamp_utc") or signal.get("timestamp")
                else:
                    continue

                if ts not in signals_by_ts:
                    signals_by_ts[ts] = []
                signals_by_ts[ts].append((symbol, signal))

        return signals_by_ts

    def _process_bar(
        self,
        timestamp: datetime,
        symbol_data: dict[str, pl.DataFrame],
        signals_by_ts: dict[datetime, list[tuple[str, dict]]],
    ):
        """Process one bar across all symbols.

        1. Check SL/TP for all open positions
        2. Open new positions for signals at this timestamp
        """
        # Check open positions for SL/TP hits
        for symbol in list(self.open_positions.keys()):
            self._check_position_exit(symbol, timestamp, symbol_data[symbol])

        # Check for new signals at this timestamp
        if timestamp in signals_by_ts:
            for symbol, signal in signals_by_ts[timestamp]:
                self._try_open_position(symbol, signal, timestamp, symbol_data[symbol])

    def _check_position_exit(self, symbol: str, timestamp: datetime, df: pl.DataFrame):
        """Check if open position should be closed at this bar."""
        if symbol not in self.open_positions:
            return

        pos = self.open_positions[symbol]

        # Get bar data at this timestamp
        ts_col = "timestamp_utc" if "timestamp_utc" in df.columns else "timestamp"
        bar = df.filter(pl.col(ts_col) == timestamp)
        if bar.is_empty():
            return

        high = bar["high"][0]
        low = bar["low"][0]
        close = bar["close"][0]

        exit_price = None
        exit_reason = None

        if pos.direction == "LONG":
            # Check stop loss (low touches stop)
            if low <= pos.stop_price:
                exit_price = pos.stop_price
                exit_reason = "stop_loss"
            # Check take profit (high touches target)
            elif high >= pos.target_price:
                exit_price = pos.target_price
                exit_reason = "take_profit"
        else:  # SHORT
            # Check stop loss (high touches stop)
            if high >= pos.stop_price:
                exit_price = pos.stop_price
                exit_reason = "stop_loss"
            # Check take profit (low touches target)
            elif low <= pos.target_price:
                exit_price = pos.target_price
                exit_reason = "take_profit"

        if exit_price is not None:
            self._close_position(symbol, timestamp, exit_price, exit_reason)

    def _try_open_position(
        self,
        symbol: str,
        signal: dict,
        timestamp: datetime,
        df: pl.DataFrame,
    ):
        """Try to open a new position for a signal."""
        # Check if position already open for this symbol
        if symbol in self.open_positions:
            logger.debug("Skipping signal for %s - position already open", symbol)
            return

        # Get signal details
        if hasattr(signal, "entry_price"):
            entry_price = signal.entry_price
            stop_price = signal.initial_stop_price
            direction = signal.direction
            signal_id = signal.id
        else:
            entry_price = signal.get("entry_price")
            stop_price = signal.get("initial_stop_price") or signal.get("stop_price")
            direction = signal.get("direction")
            signal_id = signal.get("id", f"{symbol}_{timestamp}")

        if entry_price is None or stop_price is None:
            return

        # Calculate position size based on current equity
        risk_amount = self.current_equity * self.risk_per_trade
        stop_distance = abs(entry_price - stop_price)

        if stop_distance == 0:
            return

        # Calculate target price (using R-multiple)
        if direction == "LONG":
            target_price = entry_price + (stop_distance * self.target_r_mult)
        else:
            target_price = entry_price - (stop_distance * self.target_r_mult)

        # Get bar index
        ts_col = "timestamp_utc" if "timestamp_utc" in df.columns else "timestamp"
        bar_idx_result = df.with_row_index().filter(pl.col(ts_col) == timestamp)
        bar_idx = bar_idx_result["index"][0] if not bar_idx_result.is_empty() else 0

        position = OpenPosition(
            symbol=symbol,
            signal_id=signal_id,
            entry_timestamp=timestamp,
            entry_bar_idx=bar_idx,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            direction=direction,
            position_size=risk_amount / stop_distance,
            risk_amount=risk_amount,
        )

        self.open_positions[symbol] = position
        logger.debug(
            "Opened %s position on %s at %.5f, stop=%.5f, target=%.5f, risk=$%.2f",
            direction,
            symbol,
            entry_price,
            stop_price,
            target_price,
            risk_amount,
        )

    def _close_position(
        self,
        symbol: str,
        timestamp: datetime,
        exit_price: float,
        exit_reason: str,
    ):
        """Close a position and update equity."""
        pos = self.open_positions.pop(symbol)

        # Calculate P&L
        if pos.direction == "LONG":
            pnl_pips = exit_price - pos.entry_price
        else:
            pnl_pips = pos.entry_price - exit_price

        # Calculate R-multiple
        stop_distance = abs(pos.entry_price - pos.stop_price)
        pnl_r = pnl_pips / stop_distance if stop_distance > 0 else 0.0

        # Calculate dollar P&L
        pnl_dollars = pnl_r * pos.risk_amount

        # Update equity
        old_equity = self.current_equity
        self.current_equity += pnl_dollars

        # Record trade
        trade = ClosedTrade(
            symbol=symbol,
            signal_id=pos.signal_id,
            direction=pos.direction,
            entry_timestamp=pos.entry_timestamp,
            exit_timestamp=timestamp,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            exit_reason=exit_reason,
            pnl_dollars=pnl_dollars,
            pnl_r=pnl_r,
            risk_amount=pos.risk_amount,
        )
        self.closed_trades.append(trade)

        # Record equity curve point
        self.equity_curve.append((timestamp, self.current_equity))

        logger.debug(
            "Closed %s %s at %.5f (%s): %.2fR, $%.2f | Equity: $%.2f -> $%.2f",
            symbol,
            pos.direction,
            exit_price,
            exit_reason,
            pnl_r,
            pnl_dollars,
            old_equity,
            self.current_equity,
        )

    def _close_all_positions_at_end(self, symbol_data: dict[str, pl.DataFrame]):
        """Close all remaining positions at end of data."""
        for symbol in list(self.open_positions.keys()):
            df = symbol_data[symbol]
            ts_col = "timestamp_utc" if "timestamp_utc" in df.columns else "timestamp"

            last_row = df.tail(1)
            if last_row.is_empty():
                continue

            close_price = last_row["close"][0]
            last_ts = last_row[ts_col][0]

            self._close_position(symbol, last_ts, close_price, "end_of_data")

    def _build_per_symbol_breakdown(self) -> dict:
        """Build per-symbol trade breakdown."""
        breakdown = {}

        for trade in self.closed_trades:
            if trade.symbol not in breakdown:
                breakdown[trade.symbol] = {
                    "trade_count": 0,
                    "win_count": 0,
                    "loss_count": 0,
                    "total_pnl": 0.0,
                    "total_r": 0.0,
                }

            breakdown[trade.symbol]["trade_count"] += 1
            breakdown[trade.symbol]["total_pnl"] += trade.pnl_dollars
            breakdown[trade.symbol]["total_r"] += trade.pnl_r

            if trade.pnl_r > 0:
                breakdown[trade.symbol]["win_count"] += 1
            else:
                breakdown[trade.symbol]["loss_count"] += 1

        # Calculate derived metrics
        for symbol, stats in breakdown.items():
            tc = stats["trade_count"]
            stats["win_rate"] = stats["win_count"] / tc if tc > 0 else 0.0
            stats["avg_r"] = stats["total_r"] / tc if tc > 0 else 0.0

        return breakdown
