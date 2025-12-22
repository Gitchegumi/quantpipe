"""Batch simulation module for efficient trade processing.

This module implements vectorized batch simulation to process large numbers of
trades efficiently while maintaining execution semantics equivalence with baseline.
Coordinates position state tracking, SL/TP evaluation, and trade outcome generation.

Performance target: ≤480s for ~84,938 trades (FR-001, User Story 3).
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

from src.backtest.progress import ProgressDispatcher
from src.backtest.sim_eval import (
    apply_slippage_vectorized,
    calculate_pnl_vectorized,
    evaluate_exit_priority,
    evaluate_stops_vectorized,
    evaluate_targets_vectorized,
)


logger = logging.getLogger(__name__)


@dataclass
class SimulationResult:
    """Result of batch simulation operation.

    Attributes:
        trade_count: Total number of trades simulated
        long_count: Number of long trades
        short_count: Number of short trades
        winners_count: Number of winning trades
        losers_count: Number of losing trades
        total_pnl: Total profit/loss in base currency
        total_pnl_r: Total profit/loss in R multiples
        simulation_duration_sec: Wall-clock time for simulation
        progress_overhead_pct: Percentage of time spent on progress updates
        entry_indices: Array of entry candle indices
        exit_indices: Array of exit candle indices
        entry_prices: Array of entry prices (after slippage)
        exit_prices: Array of exit prices (after slippage)
        stop_prices: Array of stop loss prices
        target_prices: Array of take profit prices
        pnl_currency: Array of PnL values in base currency
        pnl_r: Array of PnL values in R multiples
        directions: Array of trade directions (1=LONG, -1=SHORT)
        exit_reasons: Array of exit reason codes
    """

    trade_count: int
    long_count: int
    short_count: int
    winners_count: int
    losers_count: int
    total_pnl: float
    total_pnl_r: float
    simulation_duration_sec: float
    progress_overhead_pct: float
    # Trade detail arrays
    entry_indices: np.ndarray
    exit_indices: np.ndarray
    entry_prices: np.ndarray
    exit_prices: np.ndarray
    stop_prices: np.ndarray
    target_prices: np.ndarray
    pnl_currency: np.ndarray
    pnl_r: np.ndarray
    directions: np.ndarray
    exit_reasons: np.ndarray


@dataclass
class PositionState:
    """State tracking for open positions during simulation.

    Attributes:
        entry_indices: NumPy array of entry candle indices
        exit_indices: NumPy array of exit candle indices (-1 if still open)
        entry_prices: NumPy array of entry fill prices
        stop_prices: NumPy array of stop-loss prices
        target_prices: NumPy array of take-profit prices
        directions: NumPy array of directions (1=LONG, -1=SHORT)
        position_sizes: NumPy array of position sizes
        is_open: Boolean mask of currently open positions
    """

    entry_indices: np.ndarray
    exit_indices: np.ndarray
    entry_prices: np.ndarray
    stop_prices: np.ndarray
    target_prices: np.ndarray
    directions: np.ndarray
    position_sizes: np.ndarray
    is_open: np.ndarray


class BatchSimulation:
    """Batch simulator for efficient trade processing.

    Implements FR-001 (simulation performance ≤480s for ~84,938 trades) using
    vectorized position state tracking and batch SL/TP evaluation.

    Example:
        >>> simulator = BatchSimulation(risk_per_trade=0.01)
        >>> result = simulator.simulate(signal_indices, price_arrays, risk_params)
        >>> print(result.trade_count)
    """

    def __init__(
        self,
        risk_per_trade: float = 0.01,
        enable_progress: bool = True,
        max_concurrent_positions: int | None = 1,
    ):
        """Initialize batch simulator.

        Args:
            risk_per_trade: Risk per trade as fraction of account (default: 0.01)
            enable_progress: Whether to emit progress updates (default: True)
            max_concurrent_positions: Maximum concurrent positions (default: 1).
                Set to None for unlimited positions.
        """
        self.risk_per_trade = risk_per_trade
        self.enable_progress = enable_progress
        self.max_concurrent_positions = max_concurrent_positions

    def simulate(
        self,
        signal_indices: np.ndarray,
        timestamps: np.ndarray,
        ohlc_arrays: tuple[np.ndarray, ...],
    ) -> SimulationResult:
        """Execute batch simulation on signal indices.

        Args:
            signal_indices: Array of candle indices where signals were generated
            timestamps: Array of all timestamps
            ohlc_arrays: Tuple of (timestamps, open, high, low, close) arrays

        Returns:
            SimulationResult with trade outcomes and performance metrics

        Raises:
            ValueError: If input arrays invalid or misaligned
        """
        import time

        sim_start = time.perf_counter()

        # Validate inputs
        self._validate_inputs(signal_indices, timestamps, ohlc_arrays)

        n_signals = len(signal_indices)
        logger.info("Starting batch simulation for %d signals", n_signals)

        # Handle zero signals edge case
        if n_signals == 0:
            sim_duration = time.perf_counter() - sim_start
            logger.info("Zero signals - simulation complete in %.3fs", sim_duration)
            return self._create_zero_result(sim_duration)

        # Initialize progress tracking
        progress: Optional[ProgressDispatcher] = None
        if self.enable_progress:
            progress = ProgressDispatcher(
                total_items=n_signals,
                show_progress=self.enable_progress,
            )
            progress.start()

        # Apply position filtering BEFORE initializing positions (FR-001)
        logger.info(
            "Position filter check: max_concurrent=%s, n_signals=%d",
            self.max_concurrent_positions,
            n_signals,
        )
        if (
            self.max_concurrent_positions is not None
            and self.max_concurrent_positions > 0
        ):
            original_count = len(signal_indices)
            signal_indices = self._filter_signals_vectorized(
                signal_indices, ohlc_arrays
            )
            n_signals = len(signal_indices)
            logger.info(
                "Position filter applied: %d -> %d signals (removed %d)",
                original_count,
                n_signals,
                original_count - n_signals,
            )
            if n_signals == 0:
                if progress is not None:
                    progress.finish()
                sim_duration = time.perf_counter() - sim_start
                logger.info("All signals filtered by position limit - no trades")
                return self._create_zero_result(sim_duration)

        # Initialize position state arrays
        position_state = self._initialize_positions(
            signal_indices, timestamps, ohlc_arrays
        )

        # Simulate trades (placeholder implementation)
        trade_outcomes = self._simulate_trades(
            position_state, timestamps, ohlc_arrays, progress
        )

        # Step 6: Finalize progress tracking
        progress_overhead_pct = 0.0
        if progress is not None:
            result = progress.finish()
            progress_overhead_pct = result["progress_overhead_pct"]
            logger.info("Progress overhead: %.2f%%", progress_overhead_pct)

        sim_duration = time.perf_counter() - sim_start

        # Aggregate results
        result = self._aggregate_results(
            position_state, trade_outcomes, sim_duration, progress_overhead_pct
        )

        logger.info(
            "Batch simulation complete: %d trades in %.2fs (%.1f trades/sec)",
            result.trade_count,
            sim_duration,
            result.trade_count / sim_duration if sim_duration > 0 else 0,
        )

        return result

    def _validate_inputs(
        self,
        signal_indices: np.ndarray,
        timestamps: np.ndarray,
        ohlc_arrays: tuple[np.ndarray, ...],
    ) -> None:
        """Validate input arrays for simulation.

        Args:
            signal_indices: Array of signal indices
            timestamps: Array of timestamps
            ohlc_arrays: OHLC price arrays

        Raises:
            ValueError: If inputs invalid
        """
        if not isinstance(signal_indices, np.ndarray):
            msg = "signal_indices must be NumPy array"
            logger.error(msg)
            raise ValueError(msg)

        if not isinstance(timestamps, np.ndarray):
            msg = "timestamps must be NumPy array"
            logger.error(msg)
            raise ValueError(msg)

        if len(ohlc_arrays) != 5:
            msg = "ohlc_arrays must contain 5 arrays (timestamps, O, H, L, C)"
            logger.error(msg)
            raise ValueError(msg)

        # Check signal indices are within bounds
        if len(signal_indices) > 0:
            if np.any(signal_indices < 0) or np.any(signal_indices >= len(timestamps)):
                msg = "signal_indices contain out-of-bounds values"
                logger.error(msg)
                raise ValueError(msg)

        logger.debug("Input validation passed")

    def _create_zero_result(self, duration: float) -> SimulationResult:
        """Create result for zero signals edge case.

        Args:
            duration: Simulation duration in seconds

        Returns:
            SimulationResult with all counts set to zero
        """
        return SimulationResult(
            trade_count=0,
            long_count=0,
            short_count=0,
            winners_count=0,
            losers_count=0,
            total_pnl=0.0,
            total_pnl_r=0.0,
            simulation_duration_sec=duration,
            progress_overhead_pct=0.0,
            # Empty arrays for zero trades
            entry_indices=np.array([], dtype=np.int64),
            exit_indices=np.array([], dtype=np.int64),
            entry_prices=np.array([]),
            exit_prices=np.array([]),
            stop_prices=np.array([]),
            target_prices=np.array([]),
            pnl_currency=np.array([]),
            pnl_r=np.array([]),
            directions=np.array([], dtype=np.int8),
            exit_reasons=np.array([], dtype=np.int8),
        )

    def _filter_signals_sequential(
        self,
        signal_indices: np.ndarray,
        ohlc_arrays: tuple[np.ndarray, ...],
    ) -> np.ndarray:
        """Filter signals to enforce one-trade-at-a-time (FR-001).

        Simulates a quick forward scan for each signal to estimate when
        the trade would exit, then only keeps signals that don't overlap.

        Args:
            signal_indices: Original signal indices
            ohlc_arrays: OHLC price arrays for exit estimation

        Returns:
            Filtered signal indices respecting max_concurrent_positions
        """
        if len(signal_indices) == 0:
            return signal_indices

        n_candles = len(ohlc_arrays[0])
        _, open_prices, high_prices, low_prices, _ = ohlc_arrays

        kept_signals = []
        current_exit_idx = -1  # Track when current position exits

        for i, signal_idx in enumerate(signal_indices):
            # Skip if this signal occurs before current position exits
            if signal_idx <= current_exit_idx:
                if i < 10:  # Log first 10 rejections for debugging
                    logger.debug(
                        "Signal %d at idx %d REJECTED (current_exit_idx=%d)",
                        i,
                        signal_idx,
                        current_exit_idx,
                    )
                continue

            # This signal is valid - estimate its exit point
            entry_price = open_prices[signal_idx]
            # Use pip-based stop/target for forex (20 pip stop, 40 pip target)
            # This matches typical forex risk/reward ratios
            pip_size = 0.0001 if entry_price < 10 else 0.01  # JPY pairs
            stop_distance = 20 * pip_size  # 20 pip stop
            target_distance = 40 * pip_size  # 40 pip target (2R)
            stop_price = entry_price - stop_distance
            target_price = entry_price + target_distance

            # Quick scan forward to find exit
            exit_idx = self._quick_exit_scan(
                signal_idx,
                entry_price,
                stop_price,
                target_price,
                high_prices,
                low_prices,
                n_candles,
            )

            if i < 10:  # Log first 10 acceptances for debugging
                logger.debug(
                    "Signal %d at idx %d ACCEPTED (exit_idx=%d, duration=%d bars)",
                    i,
                    signal_idx,
                    exit_idx,
                    exit_idx - signal_idx,
                )

            kept_signals.append(signal_idx)
            current_exit_idx = exit_idx

        original_count = len(signal_indices)
        filtered_count = len(kept_signals)

        if filtered_count < original_count:
            logger.info(
                "Position filter (one-at-a-time): %d -> %d signals "
                "(removed %d overlapping)",
                original_count,
                filtered_count,
                original_count - filtered_count,
            )
        else:
            logger.info(
                "Position filter: All %d signals kept (no overlaps detected)",
                original_count,
            )

        return np.array(kept_signals, dtype=np.int64)

    def _quick_exit_scan(
        self,
        entry_idx: int,
        entry_price: float,
        stop_price: float,
        target_price: float,
        high_prices: np.ndarray,
        low_prices: np.ndarray,
        n_candles: int,
        max_bars: int = 100,  # Reduced from 1000 to 100 for more realistic forex durations
    ) -> int:
        """Quick forward scan to estimate trade exit point.

        Args:
            entry_idx: Entry candle index
            entry_price: Entry price
            stop_price: Stop loss price
            target_price: Target price
            high_prices: High price array
            low_prices: Low price array
            n_candles: Total number of candles
            max_bars: Maximum bars to scan forward (default 100 = ~1.5 hours for 1m bars)

        Returns:
            Estimated exit candle index
        """
        # Assume LONG direction for now (most common)
        for candle_idx in range(entry_idx + 1, min(entry_idx + max_bars, n_candles)):
            curr_high = high_prices[candle_idx]
            curr_low = low_prices[candle_idx]

            # Check stop hit (LONG: low <= stop)
            if curr_low <= stop_price:
                return candle_idx

            # Check target hit (LONG: high >= target)
            if curr_high >= target_price:
                return candle_idx

        # If no exit found within max_bars, assume exit at max_bars
        return min(entry_idx + max_bars, n_candles - 1)

    def _initialize_positions(
        self,
        signal_indices: np.ndarray,
        timestamps: np.ndarray,  # pylint: disable=unused-argument
        ohlc_arrays: tuple[np.ndarray, ...],
    ) -> PositionState:
        """Initialize position state arrays.

        Args:
            signal_indices: Array of signal indices
            timestamps: Array of timestamps
            ohlc_arrays: OHLC price arrays

        Returns:
            PositionState with initialized arrays
        """
        n_signals = len(signal_indices)

        # Extract price arrays
        _, open_prices, _high_prices, _low_prices, _close_prices = ohlc_arrays

        # Initialize state arrays (placeholder values)
        entry_indices = signal_indices.copy()
        exit_indices = np.full(n_signals, -1, dtype=np.int64)  # -1 = still open
        entry_prices = open_prices[signal_indices]  # Entry at signal candle open

        # Placeholder: calculate stop/target prices (to be implemented)
        stop_prices = entry_prices * 0.99  # Placeholder 1% stop
        target_prices = entry_prices * 1.02  # Placeholder 2% target

        # Placeholder: all LONG positions for now
        directions = np.ones(n_signals, dtype=np.int8)  # 1=LONG, -1=SHORT
        position_sizes = np.ones(n_signals)  # Placeholder unit size
        is_open = np.ones(n_signals, dtype=bool)

        logger.debug("Initialized position state for %d signals", n_signals)

        return PositionState(
            entry_indices=entry_indices,
            exit_indices=exit_indices,
            entry_prices=entry_prices,
            stop_prices=stop_prices,
            target_prices=target_prices,
            directions=directions,
            position_sizes=position_sizes,
            is_open=is_open,
        )

    def _simulate_trades(
        self,
        position_state: PositionState,
        timestamps: np.ndarray,
        ohlc_arrays: tuple[np.ndarray, ...],
        progress: Optional[ProgressDispatcher],
    ) -> dict:
        """Simulate trades using vectorized SL/TP evaluation.

        Args:
            position_state: Position state arrays
            timestamps: Array of timestamps
            ohlc_arrays: OHLC price arrays
            progress: Optional progress dispatcher

        Returns:
            Dictionary of trade outcomes with PnL and win/loss classification
        """
        n_candles = len(timestamps)
        n_trades = len(position_state.entry_indices)

        # Extract OHLC arrays
        _, _open_prices, high_prices, low_prices, _close_prices = ohlc_arrays

        # Apply slippage to entry prices
        adjusted_entries = apply_slippage_vectorized(
            position_state.entry_prices,
            position_state.directions,
            slippage_pips=0.5,
        )

        # Arrays to track trades
        exit_prices = np.zeros(n_trades)
        exit_reasons = np.zeros(n_trades, dtype=np.int8)

        # Scan forward from each entry to find exit
        for i in range(n_trades):
            entry_idx = position_state.entry_indices[i]

            # Scan forward candle by candle
            for candle_idx in range(entry_idx + 1, min(entry_idx + 1000, n_candles)):
                # Get current candle prices
                curr_high = high_prices[candle_idx]
                curr_low = low_prices[candle_idx]

                # Evaluate stops and targets for this position
                stop_hit, stop_price = evaluate_stops_vectorized(
                    np.array([position_state.is_open[i]]),
                    np.array([adjusted_entries[i]]),
                    np.array([position_state.stop_prices[i]]),
                    np.array([curr_high]),
                    np.array([curr_low]),
                    np.array([position_state.directions[i]]),
                )

                target_hit, target_price = evaluate_targets_vectorized(
                    np.array([position_state.is_open[i]]),
                    np.array([adjusted_entries[i]]),
                    np.array([position_state.target_prices[i]]),
                    np.array([curr_high]),
                    np.array([curr_low]),
                    np.array([position_state.directions[i]]),
                )

                # Determine exit priority
                exit_mask, exit_price_arr, exit_reason_arr = evaluate_exit_priority(
                    stop_hit,
                    target_hit,
                    stop_price,
                    target_price,
                )

                # If exit occurred, record it
                if exit_mask[0]:
                    exit_prices[i] = exit_price_arr[0]
                    exit_reasons[i] = exit_reason_arr[0]
                    position_state.exit_indices[i] = candle_idx
                    position_state.is_open[i] = False
                    break

            # Emit progress updates
            if progress is not None and (i + 1) % 16384 == 0:
                progress.update(i + 1)

        # Apply slippage to exit prices
        adjusted_exits = apply_slippage_vectorized(
            exit_prices,
            position_state.directions,
            slippage_pips=0.5,
        )

        # Calculate PnL
        pnl_currency, pnl_r = calculate_pnl_vectorized(
            adjusted_entries,
            adjusted_exits,
            position_state.directions,
            position_state.position_sizes,
            pip_value=10.0,
        )

        # Classify winners/losers
        winners = pnl_currency > 0

        outcomes = {
            "pnl": pnl_currency,
            "pnl_r": pnl_r,
            "winners": winners,
            "directions": position_state.directions,
            "exit_reasons": exit_reasons,
            "exit_prices": adjusted_exits,
        }

        # Log trade summary using Rich console if progress bar active
        trade_summary = (
            f"Simulated {n_trades} trades: "
            f"{np.sum(winners)} winners, {n_trades - np.sum(winners)} losers"
        )
        if progress is not None and progress._progress is not None:
            # Use Rich console to print below the progress bar
            progress._progress.console.print(f"[cyan]{trade_summary}[/cyan]")
        else:
            # Fallback to regular logging
            logger.info(
                "Simulated %d trades: %d winners, %d losers",
                n_trades,
                np.sum(winners),
                n_trades - np.sum(winners),
            )

        return outcomes

    def _aggregate_results(
        self,
        position_state: PositionState,
        trade_outcomes: dict,
        duration: float,
        progress_overhead: float,
    ) -> SimulationResult:
        """Aggregate trade outcomes into simulation result.

        Args:
            position_state: Position state with entry/exit/stop/target arrays
            trade_outcomes: Dictionary of trade outcomes
            duration: Simulation duration in seconds
            progress_overhead: Progress overhead percentage

        Returns:
            SimulationResult with aggregated metrics and trade detail arrays
        """
        n_trades = len(trade_outcomes["pnl"])
        winners_mask = trade_outcomes["winners"]
        directions = trade_outcomes["directions"]

        return SimulationResult(
            trade_count=n_trades,
            long_count=int(np.sum(directions == 1)),
            short_count=int(np.sum(directions == -1)),
            winners_count=int(np.sum(winners_mask)),
            losers_count=int(np.sum(~winners_mask)),
            total_pnl=float(np.sum(trade_outcomes["pnl"])),
            total_pnl_r=float(np.sum(trade_outcomes["pnl_r"])),
            simulation_duration_sec=duration,
            progress_overhead_pct=progress_overhead,
            # Trade detail arrays
            entry_indices=position_state.entry_indices,
            exit_indices=position_state.exit_indices,
            entry_prices=position_state.entry_prices,
            exit_prices=trade_outcomes.get("exit_prices", np.array([])),
            stop_prices=position_state.stop_prices,
            target_prices=position_state.target_prices,
            pnl_currency=trade_outcomes["pnl"],
            pnl_r=trade_outcomes["pnl_r"],
            directions=directions,
            exit_reasons=trade_outcomes["exit_reasons"],
        )
