"""Portfolio simulator for time-synchronized multi-symbol backtesting.

This module implements portfolio-mode simulation where all symbols trade
against a shared running balance. Uses vectorized simulation per symbol
then merges results chronologically for equity tracking.

Key features:
- Vectorized simulation per symbol (fast)
- Shared portfolio equity updated after each trade closes (chronologically)
- Position sizing at 0.25% of current equity
- Maximum one open position per symbol at a time
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import polars as pl


logger = logging.getLogger(__name__)


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
    timeframe: str = "1m"
    data_start_date: Optional[datetime] = None
    data_end_date: Optional[datetime] = None


class PortfolioSimulator:
    """Time-synchronized portfolio simulation with shared equity.

    Uses vectorized simulation per symbol (fast), then merges trade
    results chronologically to update shared equity.

    Attributes:
        starting_equity: Initial portfolio capital ($2,500)
        risk_per_trade: Position sizing as fraction of equity (0.0025 = 0.25%)

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
        self.closed_trades: list[ClosedTrade] = []
        self.equity_curve: list[tuple[datetime, float]] = []

    def simulate(
        self,
        symbol_data: dict[str, pl.DataFrame],
        symbol_signals: dict[str, list],  # symbol -> list of signal dicts
        direction_mode: str = "BOTH",
        run_id: str = "portfolio_run",
        timeframe: str = "1m",
    ) -> PortfolioResult:
        """Run vectorized simulation per symbol, then merge chronologically.

        Args:
            symbol_data: Dict mapping symbol to enriched Polars DataFrame
            symbol_signals: Dict mapping symbol to list of signal dicts
            direction_mode: Direction mode (LONG/SHORT/BOTH)
            run_id: Unique run identifier
            timeframe: The timeframe of the data (e.g., "1m", "5m")

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
        self.closed_trades = []
        self.equity_curve = []

        # Collect all trades from all symbols
        all_trades: list[ClosedTrade] = []

        # Phase 1: Run vectorized simulation for each symbol
        for symbol, signals in symbol_signals.items():
            if symbol not in symbol_data:
                continue

            df = symbol_data[symbol]
            symbol_trades = self._simulate_symbol_vectorized(symbol, df, signals)
            all_trades.extend(symbol_trades)
            logger.info("Simulated %s: %d trades", symbol, len(symbol_trades))

        # Phase 2: Sort all trades by exit timestamp
        all_trades.sort(key=lambda t: t.exit_timestamp)
        logger.info("Processing %d trades chronologically", len(all_trades))

        # Get data bounds
        data_start = None
        data_end = None
        for df in symbol_data.values():
            ts_col = "timestamp_utc" if "timestamp_utc" in df.columns else "timestamp"
            if ts_col in df.columns:
                starts = df[ts_col].min()
                ends = df[ts_col].max()
                if data_start is None or starts < data_start:
                    data_start = starts
                if data_end is None or ends > data_end:
                    data_end = ends

        if data_start is None:
            data_start = start_time
        if data_end is None:
            data_end = datetime.now()

        # Record initial equity
        self.equity_curve.append((data_start, self.current_equity))

        # Phase 3: Update equity chronologically
        for trade in all_trades:
            # Recalculate P&L based on current equity at trade entry time
            # For now, use fixed R-multiple from signal
            pnl_dollars = trade.pnl_r * (self.current_equity * self.risk_per_trade)
            trade.pnl_dollars = pnl_dollars
            trade.risk_amount = self.current_equity * self.risk_per_trade

            self.current_equity += pnl_dollars
            self.closed_trades.append(trade)
            self.equity_curve.append((trade.exit_timestamp, self.current_equity))

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
            timeframe=timeframe,
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

    def _simulate_symbol_vectorized(
        self,
        symbol: str,
        df: pl.DataFrame,
        signals: list,
    ) -> list[ClosedTrade]:
        """Run vectorized simulation using shared batch engine for consistency.

        Delegates to src.backtest.trade_sim_batch.simulate_trades_batch to ensure
        portfolio mode yields identical trade outcomes to independent mode.
        """
        if not signals:
            return []

        # Import shared engine
        try:
            from src.backtest.trade_sim_batch import simulate_trades_batch
        except ImportError as e:
            logger.error("Failed to import batch engine: %s", e)
            return []

        # 1. Prepare Price Data (Pandas/Numpy required for batch engine)
        # Assuming df has 'high', 'low', 'close', 'timestamp_utc'
        # Select minimum columns to reduce overhead
        cols = ["high", "low", "close", "timestamp_utc"]
        data_pd = df.select([c for c in cols if c in df.columns]).to_pandas()

        # Ensure timestamp column exists for mapping
        ts_col = "timestamp_utc" if "timestamp_utc" in data_pd.columns else "timestamp"
        if ts_col not in data_pd.columns:
            logger.error("Missing timestamp column in data for %s", symbol)
            return []

        # create map for O(1) index lookup
        ts_map = {ts: i for i, ts in enumerate(data_pd[ts_col])}

        # 2. Prepare Entries
        entries = []
        for signal in signals:
            # Handle both object and dict signals
            if hasattr(signal, "timestamp_utc"):
                sig_ts = signal.timestamp_utc
                sig_entry = signal.entry_price
                sig_stop = signal.initial_stop_price
                # sig_target is implicit 2R usually? Or handled by logic?
                # orchestrator calc: target_pct = (risk * target_r_mult) / entry
                # We need to replicate this logic or rely on defaults?
                # simulate_trades_batch accepts 'take_profit_pct' in entry dict.

                # We interpret signal directly
                direction = signal.direction
                signal_id = getattr(signal, "id", f"{symbol}_{sig_ts}")
            else:
                sig_ts = signal.get("timestamp_utc") or signal.get("timestamp")
                sig_entry = signal.get("entry_price")
                sig_stop = signal.get("initial_stop_price")
                direction = signal.get("direction")
                signal_id = signal.get("id", f"{symbol}_{sig_ts}")

            # Lookup index
            idx = ts_map.get(sig_ts)
            if idx is None or sig_entry is None or sig_stop is None:
                continue

            # Calculate percentages
            risk_dist = abs(sig_entry - sig_stop)
            if sig_entry == 0:
                continue

            sl_pct = risk_dist / sig_entry
            tp_pct = (risk_dist * self.target_r_mult) / sig_entry

            entries.append(
                {
                    "signal_id": signal_id,
                    "direction": direction,
                    "entry_index": idx,
                    "entry_price": sig_entry,
                    "side": direction,
                    "stop_loss_pct": sl_pct,
                    "take_profit_pct": tp_pct,
                    "original_signal": signal,  # Keep ref if needed
                }
            )

        if not entries:
            return []

        # 3. Run Shared Batch Simulation
        results = simulate_trades_batch(entries, data_pd)

        # 4. Convert Results to ClosedTrade
        closed_trades = []
        timestamps = data_pd[ts_col].values  # numpy array for fast access

        for res, entry in zip(results, entries, strict=False):
            if res["exit_index"] is None:
                continue

            # Skip if invalid
            if res.get("exit_reason") == "INVALID_ENTRY":
                continue

            entry_idx = res["entry_index"]
            exit_idx = res["exit_index"]

            # Recalculate PnL in R (engine returns 'pnl' as percentage)
            # pnl_r = pnl_pct / stop_loss_pct
            sl_pct = entry["stop_loss_pct"]
            pnl_r = res["pnl"] / sl_pct if sl_pct > 0 else 0.0

            # Exit Reason Map
            reason_map = {
                "STOP_LOSS": "stop_loss",
                "TAKE_PROFIT": "take_profit",
                "TIMEOUT": "end_of_data",  # Map TIMEOUT to EOD for now
                "END_OF_DATA": "end_of_data",
            }
            exit_reason = reason_map.get(res["exit_reason"], "end_of_data")

            trade = ClosedTrade(
                symbol=symbol,
                signal_id=entry["signal_id"],
                direction=entry["direction"],
                entry_timestamp=timestamps[entry_idx],
                exit_timestamp=timestamps[exit_idx],
                entry_price=res.get("entry_price", entry["entry_price"]),
                exit_price=res["exit_price"],
                exit_reason=exit_reason,
                pnl_dollars=0.0,  # Calculated later
                pnl_r=pnl_r,
                risk_amount=0.0,
            )
            closed_trades.append(trade)

        return closed_trades

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
        for stats in breakdown.values():
            tc = stats["trade_count"]
            stats["win_rate"] = stats["win_count"] / tc if tc > 0 else 0.0
            stats["avg_r"] = stats["total_r"] / tc if tc > 0 else 0.0

        return breakdown
