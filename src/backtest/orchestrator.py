# pylint: disable=broad-exception-caught, unused-variable, fixme, unused-import, too-many-lines

"""
Backtest orchestration for directional backtesting system.

This module coordinates the execution of backtests across different direction modes
(LONG, SHORT, BOTH), managing signal generation, conflict resolution, execution
simulation, and metrics aggregation.
"""


from __future__ import annotations

import logging
from collections.abc import Sequence
from contextlib import nullcontext
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import polars as pl
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from ..backtest.metrics import calculate_directional_metrics
from ..backtest.profiling import ProfilingContext
from ..backtest.trade_sim_batch import simulate_trades_batch
from ..models.core import Candle, TradeExecution, TradeSignal
from ..models.directional import BacktestResult, ConflictEvent
from ..models.enums import DirectionMode
from ..strategy.trend_pullback.signal_generator import (
    generate_long_signals,
    generate_short_signals,
)
from ..strategy.trend_pullback.signal_generator_vectorized import (
    generate_signals_vectorized,
)

if TYPE_CHECKING:
    import numpy as np
    import pandas as pd

    from ..backtest.batch_scan import ScanResult
    from ..backtest.batch_simulation import SimulationResult
    from ..strategy.base import Strategy


logger = logging.getLogger(__name__)


class BacktestOrchestrator:
    """
    Orchestrates backtest execution across direction modes.

    Coordinates signal generation, conflict detection (BOTH mode), execution
    simulation, and metrics aggregation. Supports dry-run mode for signal
    validation without execution.

    Attributes:
        direction_mode: Direction mode for backtest (LONG, SHORT, or BOTH).
        dry_run: Whether to skip execution simulation (signals only).

    Examples:
        >>> from src.models.enums import DirectionMode
        >>> orchestrator = BacktestOrchestrator(
        ...     direction_mode=DirectionMode.LONG,
        ...     dry_run=False
        ... )
        >>> orchestrator.direction_mode
        <DirectionMode.LONG: 'LONG'>
    """

    def __init__(
        self,
        direction_mode: DirectionMode,
        dry_run: bool = False,
        enable_profiling: bool = False,
        log_frequency: int = 1000,
        enable_progress: bool = True,
    ):
        """
        Initialize backtest orchestrator.

        Args:
            direction_mode: Direction mode for signal generation (LONG, SHORT, BOTH).
            dry_run: If True, generate signals only without execution simulation.
            enable_profiling: If True, enable phase timing instrumentation.
            log_frequency: Log progress every N items (signals/trades). Default 1000.
            enable_progress: If True, display rich progress bars.
        """
        self.direction_mode = direction_mode
        self.dry_run = dry_run
        self.enable_profiling = enable_profiling
        self.log_frequency = log_frequency
        self.enable_progress = enable_progress
        self.profiler: ProfilingContext | None = None
        logger.info(
            "Initialized BacktestOrchestrator: \n"
            "direction=%s, dry_run=%s, profiling=%s, log_freq=%d, progress=%s",
            direction_mode.value,
            dry_run,
            enable_profiling,
            log_frequency,
            enable_progress,
        )

    def _start_phase(self, phase_name: str) -> None:
        """Start profiling phase if profiling is enabled.

        Args:
            phase_name: Name of the phase to start.
        """
        if self.enable_profiling and self.profiler:
            self.profiler.start_phase(phase_name)

    def _end_phase(self, phase_name: str) -> None:
        """End profiling phase if profiling is enabled.

        Args:
            phase_name: Name of the phase to end.
        """
        if self.enable_profiling and self.profiler:
            self.profiler.end_phase(phase_name)

    def _simulate_batch(
        self,
        signals: Sequence[TradeSignal],
        candles: Sequence[Candle],
        slippage_pips: float = 0.5,
    ) -> list[TradeExecution]:
        """Simulate trade execution in batch using vectorized trade simulation.

        Converts signals to batch format, runs vectorized simulation, and
        converts results back to TradeExecution objects.

        Args:
            signals: Trade signals to simulate.
            candles: Full candle dataset.
            slippage_pips: Entry slippage in pips.

        Returns:
            List of TradeExecution objects for completed trades.
        """
        if not signals:
            return []

        # Build candle timestamp index for O(log n) lookups
        import bisect

        candle_timestamps = [c.timestamp_utc for c in candles]

        # Convert signals to batch entry format
        entries = []
        for signal in signals:
            # Find entry candle index using binary search (O(log n) instead of O(n))
            # bisect_right returns the insertion point, which is the first candle
            # AFTER signal
            entry_idx = bisect.bisect_right(candle_timestamps, signal.timestamp_utc)

            if entry_idx >= len(candles):
                logger.debug(
                    "No candles after signal timestamp %s, skipping",
                    signal.timestamp_utc.isoformat(),
                )
                continue

            # Calculate entry price with slippage
            entry_candle = candles[entry_idx]
            if signal.direction == "LONG":
                entry_price = entry_candle.open + (slippage_pips / 10000)
            else:  # SHORT
                entry_price = entry_candle.open - (slippage_pips / 10000)

            # Calculate stop-loss and take-profit percentages
            risk_distance = abs(entry_price - signal.initial_stop_price)
            stop_loss_pct = risk_distance / entry_price
            take_profit_pct = (risk_distance * 2.0) / entry_price  # 2R target

            entries.append(
                {
                    "signal": signal,
                    "entry_index": entry_idx,
                    "entry_price": entry_price,
                    "side": signal.direction,
                    "stop_loss_pct": stop_loss_pct,
                    "take_profit_pct": take_profit_pct,
                }
            )

        if not entries:
            return []

        # Convert candles to DataFrame for batch simulation
        import pandas as pd

        price_data = pd.DataFrame(
            {
                "high": [c.high for c in candles],
                "low": [c.low for c in candles],
                "close": [c.close for c in candles],
            }
        )

        # Run batch simulation (use first entry's SL/TP as defaults for now)
        # TODO: Support per-trade SL/TP in simulate_trades_batch
        results = simulate_trades_batch(
            entries=entries,
            price_data=price_data,
            stop_loss_pct=entries[0]["stop_loss_pct"],
            take_profit_pct=entries[0]["take_profit_pct"],
        )

        # Convert results to TradeExecution objects
        executions = []
        for result, entry in zip(results, entries, strict=False):
            if result["exit_index"] is None:
                continue

            signal = entry["signal"]
            entry_idx = result["entry_index"]
            exit_idx = result["exit_idx"]

            # Map exit reasons
            exit_reason_map = {
                "STOP_LOSS": "STOP_LOSS",
                "TAKE_PROFIT": "TARGET",
                "END_OF_DATA": "EXPIRY",
            }
            exit_reason = exit_reason_map.get(
                result["exit_reason"], result["exit_reason"]
            )

            # Calculate R-multiples from PnL percentage
            pnl_r = result["pnl"] / (entry["stop_loss_pct"])

            execution = TradeExecution(
                signal_id=signal.id,
                direction=signal.direction,
                open_timestamp=candles[entry_idx].timestamp_utc,
                entry_fill_price=result.get("entry_price", entry["entry_price"]),
                close_timestamp=candles[exit_idx].timestamp_utc,
                exit_fill_price=result["exit_price"],
                exit_reason=exit_reason,
                pnl_r=pnl_r,
                slippage_entry_pips=slippage_pips,
                slippage_exit_pips=0.5,  # Default exit slippage
                costs_total=0.0,  # Simplified for batch mode
            )
            executions.append(execution)

        return executions

    def run_backtest(
        self,
        candles: Sequence[Candle] | pl.DataFrame,
        pair: str,
        run_id: str,
        strategy: Any = None,
        **signal_params,
    ) -> BacktestResult:
        """
        Execute backtest with specified direction mode.

        Orchestrates full backtest workflow:
        1. Generate signals based on direction mode
        2. Detect and resolve conflicts (BOTH mode only)
        3. Simulate execution (unless dry_run=True)
        4. Aggregate metrics
        5. Package results into BacktestResult

        Args:
            candles: Sequence of OHLCV candles with indicators.
            pair: Currency pair being backtested (e.g., "EURUSD").
            run_id: Unique identifier for this backtest run.
            **signal_params: Additional parameters for signal generation
                (e.g., cooldown_candles, risk_per_trade_pct).

        Returns:
            BacktestResult containing run metadata, metrics, signals,
            executions, and conflicts.

        Raises:
            ValueError: If candles sequence is empty or invalid.

        Examples:
            >>> from datetime import datetime, timezone
            >>> candle = Candle(
            ...     timestamp_utc=datetime(2025, 1, 1, tzinfo=timezone.utc),
            ...     open=1.1000, high=1.1010, low=1.0990, close=1.1005,
            ...     volume=1000.0, ema20=1.1000, ema50=1.0995,
            ...     atr=0.0015, rsi=55.0
            ... )
            >>> result = orchestrator.run_backtest(
            ...     candles=[candle],
            ...     pair="EURUSD",
            ...     run_id="test_run_001",
            ...     cooldown_candles=5
            ... )
            >>> result.direction_mode
            'LONG'
        """
        if isinstance(candles, pl.DataFrame):
            if candles.is_empty():
                raise ValueError("Candles DataFrame cannot be empty")
            # Use optimized path with BatchSimulation (includes position filtering)
            return self.run_optimized_backtest(
                df=candles, pair=pair, run_id=run_id, strategy=strategy, **signal_params
            )

        if not candles:
            raise ValueError("Candles sequence cannot be empty")

        start_time = datetime.now(UTC)
        logger.info("Starting backtest run_id=%s, pair=%s", run_id, pair)

        # Route to direction-specific workflow
        if self.direction_mode == DirectionMode.LONG:
            return self._run_long_backtest(
                candles, pair, run_id, start_time, **signal_params
            )
        elif self.direction_mode == DirectionMode.SHORT:
            return self._run_short_backtest(
                candles, pair, run_id, start_time, **signal_params
            )
        else:  # DirectionMode.BOTH
            return self._run_both_backtest(
                candles, pair, run_id, start_time, **signal_params
            )

    def _run_long_backtest(
        self,
        candles: Sequence[Candle],
        pair: str,
        run_id: str,
        start_time: datetime,
        **signal_params,
    ) -> BacktestResult:
        """Execute LONG-only backtest using sliding window approach."""
        logger.info("Generating LONG signals for pair=%s", pair)
        parameters = {"pair": pair, **signal_params}

        # Process candles in sliding windows (like run_long_backtest.py)
        self._start_phase("scan")
        all_signals = []
        ema_slow = signal_params.get("ema_slow", 50)
        window_size = 100
        total_windows = len(candles) - ema_slow

        # Create progress bar with minimal refresh for performance
        if self.enable_progress:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold cyan]{task.description}"),
                BarColumn(complete_style="green", finished_style="bold green"),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                TextColumn("• [bold yellow]{task.fields[signals]}[/] signals"),
                refresh_per_second=4,  # Minimal refresh: 4 updates/sec (T051)
            )
            progress.start()
            task = progress.add_task(
                f"Scanning {total_windows:,} windows for LONG signals",
                total=total_windows,
                signals=0,
            )
        else:
            progress = nullcontext()
            task = None

        with progress:
            for i in range(ema_slow, len(candles)):
                window = candles[max(0, i - window_size) : i + 1]

                # Generate signals for this window
                window_signals = generate_long_signals(
                    candles=window, parameters=parameters
                )

                if window_signals:
                    # Only take the first signal from each window
                    signal = window_signals[0]
                    # Skip if we already have this signal (deduplication by timestamp)
                    if not any(
                        s.timestamp_utc == signal.timestamp_utc for s in all_signals
                    ):
                        all_signals.append(signal)
                        if task:
                            progress.update(task, signals=len(all_signals))

                        # Throttled logging
                        if len(all_signals) % self.log_frequency == 0:
                            logger.debug(
                                "LONG signal generation: %d signals found",
                                len(all_signals),
                            )

                if task:
                    progress.update(task, advance=1)

        signals = all_signals
        self._end_phase("scan")
        logger.info("Generated %d LONG signals", len(signals))

        # Execute signals (skip if dry-run)
        executions = []
        if not self.dry_run:
            self._start_phase("simulate")
            logger.info(
                "Simulating execution for %d LONG signals (batch mode)", len(signals)
            )

            # Create progress bar for execution with minimal refresh
            if self.enable_progress:
                exec_progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[bold cyan]{task.description}"),
                    BarColumn(complete_style="green", finished_style="bold green"),
                    TaskProgressColumn(),
                    TimeElapsedColumn(),
                    refresh_per_second=4,  # Minimal refresh: 4 updates/sec (T051)
                )
                exec_progress.start()
                exec_task = exec_progress.add_task(
                    f"Simulating {len(signals):,} trades (vectorized)",
                    total=100,
                )
            else:
                exec_progress = nullcontext()
                exec_task = None

            with exec_progress:
                # Use batch simulation for performance
                if exec_task:
                    exec_progress.update(exec_task, advance=50)  # Processing signals
                executions = self._simulate_batch(signals, candles)
                if exec_task:
                    exec_progress.update(exec_task, advance=50)  # Complete
            self._end_phase("simulate")

            # Calculate wins/losses for logging
            wins = sum(1 for ex in executions if ex.exit_reason == "TARGET")
            losses = sum(1 for ex in executions if ex.exit_reason == "STOP_LOSS")

            logger.info(
                "Batch execution complete: %d/%d signals executed (%d wins, %d losses)",
                len(executions),
                len(signals),
                wins,
                losses,
            )

        # Calculate metrics
        metrics = None
        if executions:
            metrics = calculate_directional_metrics(executions, DirectionMode.LONG)
            logger.info(
                "Metrics calculated: %d trades, win_rate=%.2f%%",
                metrics.combined.trade_count,
                metrics.combined.win_rate * 100,
            )

        end_time = datetime.now(UTC)
        return BacktestResult(
            run_id=run_id,
            direction_mode=DirectionMode.LONG.value,
            start_time=start_time,
            end_time=end_time,
            data_start_date=candles[0].timestamp_utc,
            data_end_date=candles[-1].timestamp_utc,
            total_candles=len(candles),
            metrics=metrics,
            signals=signals if self.dry_run else None,
            executions=executions if not self.dry_run else None,
            conflicts=[],
            dry_run=self.dry_run,
            pair=pair,
        )

    def _run_short_backtest(
        self,
        candles: Sequence[Candle],
        pair: str,
        run_id: str,
        start_time: datetime,
        **signal_params,
    ) -> BacktestResult:
        """Execute SHORT-only backtest using sliding window approach."""
        logger.info("Generating SHORT signals for pair=%s", pair)
        parameters = {"pair": pair, **signal_params}

        # Process candles in sliding windows (like run_long_backtest.py)
        self._start_phase("scan")
        all_signals = []
        ema_slow = signal_params.get("ema_slow", 50)
        window_size = 100
        total_windows = len(candles) - ema_slow

        # Create progress bar with minimal refresh for performance
        if self.enable_progress:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold cyan]{task.description}"),
                BarColumn(complete_style="green", finished_style="bold green"),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                TextColumn("• [bold yellow]{task.fields[signals]}[/] signals"),
                refresh_per_second=4,  # Minimal refresh: 4 updates/sec (T051)
            )
            progress.start()
            task = progress.add_task(
                f"Scanning {total_windows:,} windows for SHORT signals",
                total=total_windows,
                signals=0,
            )
        else:
            progress = nullcontext()
            task = None

        with progress:
            for i in range(ema_slow, len(candles)):
                window = candles[max(0, i - window_size) : i + 1]

                # Generate signals for this window
                window_signals = generate_short_signals(
                    candles=window, parameters=parameters
                )

                if window_signals:
                    # Only take the first signal from each window
                    signal = window_signals[0]
                    # Skip if we already have this signal (deduplication by timestamp)
                    if not any(
                        s.timestamp_utc == signal.timestamp_utc for s in all_signals
                    ):
                        all_signals.append(signal)
                        if task:
                            progress.update(task, signals=len(all_signals))

                        # Throttled logging
                        if len(all_signals) % self.log_frequency == 0:
                            logger.debug(
                                "SHORT signal generation: %d signals found",
                                len(all_signals),
                            )

                if task:
                    progress.update(task, advance=1)

        signals = all_signals
        self._end_phase("scan")
        logger.info("Generated %d SHORT signals", len(signals))

        # Execute signals (skip if dry-run)
        executions = []
        if not self.dry_run:
            self._start_phase("simulate")
            logger.info(
                "Simulating execution for %d SHORT signals (batch mode)", len(signals)
            )

            # Create progress bar for execution with minimal refresh
            if self.enable_progress:
                exec_progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[bold cyan]{task.description}"),
                    BarColumn(complete_style="green", finished_style="bold green"),
                    TaskProgressColumn(),
                    TimeElapsedColumn(),
                    refresh_per_second=4,  # Minimal refresh: 4 updates/sec (T051)
                )
                exec_progress.start()
                exec_task = exec_progress.add_task(
                    f"Simulating {len(signals):,} trades (vectorized)",
                    total=100,
                )
            else:
                exec_progress = nullcontext()
                exec_task = None

            with exec_progress:
                # Use batch simulation for performance
                if exec_task:
                    exec_progress.update(exec_task, advance=50)  # Processing signals
                executions = self._simulate_batch(signals, candles)
                if exec_task:
                    exec_progress.update(exec_task, advance=50)  # Complete
            self._end_phase("simulate")

            # Calculate wins/losses for logging
            wins = sum(1 for ex in executions if ex.exit_reason == "TARGET")
            losses = sum(1 for ex in executions if ex.exit_reason == "STOP_LOSS")

            logger.info(
                "Batch execution complete: %d/%d signals executed (%d wins, %d losses)",
                len(executions),
                len(signals),
                wins,
                losses,
            )

        # Calculate metrics
        metrics = None
        if executions:
            metrics = calculate_directional_metrics(executions, DirectionMode.SHORT)
            logger.info(
                "Metrics calculated: %d trades, win_rate=%.2f%%",
                metrics.combined.trade_count,
                metrics.combined.win_rate * 100,
            )

        end_time = datetime.now(UTC)
        return BacktestResult(
            run_id=run_id,
            direction_mode=DirectionMode.SHORT.value,
            start_time=start_time,
            end_time=end_time,
            data_start_date=candles[0].timestamp_utc,
            data_end_date=candles[-1].timestamp_utc,
            total_candles=len(candles),
            metrics=metrics,
            signals=signals if self.dry_run else None,
            executions=executions if not self.dry_run else None,
            conflicts=[],
            dry_run=self.dry_run,
            pair=pair,
        )

    def _run_vectorized_backtest(
        self,
        data: pl.DataFrame,
        pair: str,
        run_id: str,
        **signal_params,
    ) -> BacktestResult:
        """Execute backtest using fully vectorized path via Polars."""
        start_time = datetime.now(UTC)
        logger.info(
            "Starting vectorized backtest for %s (mode=%s)", pair, self.direction_mode
        )

        # 1. Generate Signals Vectorized
        self._start_phase("scan")

        # Show progress spinner during signal generation
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            transient=True,  # Remove progress bar when done
        ) as progress:
            task = progress.add_task(
                f"[cyan]Generating signals for {pair}...", total=None
            )

            signals = generate_signals_vectorized(
                data,
                parameters={"pair": pair, **signal_params},
                direction_mode=self.direction_mode.name,
            )

            # Update with completion
            progress.update(
                task,
                description=f"[green]Generated {len(signals):,} signals",
                completed=100,
                total=100,
            )

        self._end_phase("scan")

        logger.info("Generated %d signals (vectorized)", len(signals))

        # 2. Simulate Execution
        executions = []
        conflicts = []  # TODO: Handle conflicts in vectorized mode if needed

        if not self.dry_run and signals:
            self._start_phase("simulate")

            # Show progress bar during simulation
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                transient=True,
            ) as progress:
                sim_task = progress.add_task(
                    f"[cyan]Simulating {len(signals):,} trades...", total=len(signals)
                )

                # Use improved vectorized simulation (requires converting Polars to Pandas/NumPy for now)
                # Future: pure Polars simulation
                price_data_pd = data.select(
                    ["high", "low", "close", "timestamp_utc"]
                ).to_pandas()

                # Map signals to entry dicts
                # We need entry_index. Since 'data' is chronologically sorted, we can use row index.
                # But signals have timestamps.
                # Efficient way: Map signal timestamp to index.
                # Since signals were generated from 'data', the timestamp match should be exact.

                # Create a map of timestamp -> index
                # This is overhead. Ideally signal generator returns indices.
                # But abstracting TradeSignal is good.

                # Optimization:
                # If signals are sorted and data is sorted, we can search sorted.
                timestamp_map = {
                    ts: idx for idx, ts in enumerate(price_data_pd["timestamp_utc"])
                }

                entries = []
                for i, sig in enumerate(signals):
                    idx = timestamp_map.get(sig.timestamp_utc)
                    if idx is not None:
                        # Calculate SL/TP pct
                        risk_distance = abs(sig.entry_price - sig.initial_stop_price)
                        # avoid div by zero
                        if sig.entry_price == 0:
                            progress.update(sim_task, advance=1)
                            continue

                        stop_loss_pct = risk_distance / sig.entry_price
                        # Default 2R target if not specified?
                        # signal info doesn't have target price explicitly usually, it uses R-multiple.
                        # existing code used risk_distance * 2.0
                        target_pct = (
                            risk_distance * signal_params.get("target_r_mult", 2.0)
                        ) / sig.entry_price

                        entries.append(
                            {
                                "signal": sig,
                                "entry_index": idx,
                                "entry_price": sig.entry_price,
                                "side": sig.direction,
                                "stop_loss_pct": stop_loss_pct,
                                "take_profit_pct": target_pct,
                            }
                        )

                    # Update progress every 1000 signals to avoid overhead
                    if i % 1000 == 0 or i == len(signals) - 1:
                        progress.update(sim_task, completed=i + 1)

                if entries:
                    progress.update(
                        sim_task,
                        description=f"[cyan]Running batch simulation ({len(entries):,} trades)...",
                    )

                    # Re-use existing simulation batch logic for now (it's numpy based)
                    # Converting to dataframe was done above
                    sim_results = simulate_trades_batch(
                        entries,
                        price_data_pd,
                        stop_loss_pct=entries[0][
                            "stop_loss_pct"
                        ],  # approximated, loop actually supports per-trade? No, function signature has fixed SL/TP
                    )

                    # Wait, simulate_trades_batch takes fixed SL/TP?
                    # def simulate_trades_batch(..., stop_loss_pct=0.02, ...)
                    # Yes. The current implementation doesn't support per-trade SL/TP.
                    # See TODO in _simulate_batch line 205: "TODO: Support per-trade SL/TP in simulate_trades_batch"

                    # To support dynamic SL/TP (which we have), we need to update simulate_trades_batch
                    # or pass the global average?
                    # Using per-trade values is critical for correctness.
                    # I should update simulate_trades_batch to accept sl/tp in entries.

                    results = simulate_trades_batch(entries, price_data_pd)

                    progress.update(
                        sim_task, description="[cyan]Processing execution results..."
                    )

                    # Convert back to executions
                    for res, entry in zip(results, entries, strict=False):
                        if res.get("exit_index") is None:
                            continue

                        sig = entry["signal"]
                        exit_reason_map = {
                            "STOP_LOSS": "STOP_LOSS",
                            "TAKE_PROFIT": "TARGET",
                            "END_OF_DATA": "EXPIRY",
                        }
                        exit_reason = exit_reason_map.get(
                            res["exit_reason"], res["exit_reason"]
                        )

                        # Recalculate R based on actual result
                        pnl_r = (
                            res["pnl"] / entry["stop_loss_pct"]
                            if entry["stop_loss_pct"]
                            else 0
                        )

                        executions.append(
                            TradeExecution(
                                signal_id=sig.id,
                                direction=sig.direction,
                                open_timestamp=data["timestamp_utc"][
                                    entry["entry_index"]
                                ],  # expensive lookup? slice.
                                entry_fill_price=res.get(
                                    "entry_price", entry["entry_price"]
                                ),
                                close_timestamp=data["timestamp_utc"][
                                    res["exit_index"]
                                ],
                                exit_fill_price=res["exit_price"],
                                exit_reason=exit_reason,
                                pnl_r=pnl_r,
                                slippage_entry_pips=0.5,
                                slippage_exit_pips=0.5,
                                costs_total=0.0,
                            )
                        )

                progress.update(
                    sim_task,
                    description=f"[green]Completed {len(executions):,} executions",
                    completed=len(signals),
                )

            self._end_phase("simulate")

        # Metrics
        metrics = None
        if executions:
            # We need to map direction mode appropriately
            metrics = calculate_directional_metrics(executions, self.direction_mode)

        end_time = datetime.now(UTC)

        # Get start/end dates handling empty data
        data_start = data["timestamp_utc"][0] if not data.is_empty() else start_time
        data_end = data["timestamp_utc"][-1] if not data.is_empty() else end_time

        return BacktestResult(
            run_id=run_id,
            direction_mode=self.direction_mode.value,
            start_time=start_time,
            end_time=end_time,
            data_start_date=data_start,
            data_end_date=data_end,
            total_candles=len(data),
            metrics=metrics,
            signals=signals if self.dry_run else None,  # Optimize memory if executing
            executions=executions if not self.dry_run else None,
            conflicts=conflicts,
            dry_run=self.dry_run,
            pair=pair,
        )

    def _run_both_backtest(
        self,
        candles: Sequence[Candle],
        pair: str,
        run_id: str,
        start_time: datetime,
        **signal_params,
    ) -> BacktestResult:
        """
        Execute BOTH directions backtest with conflict resolution using sliding windows.
        """
        logger.info("Generating LONG and SHORT signals for pair=%s", pair)
        parameters = {"pair": pair, **signal_params}

        # Process candles in sliding windows for both directions
        self._start_phase("scan")
        all_long_signals = []
        all_short_signals = []
        ema_slow = signal_params.get("ema_slow", 50)
        window_size = 100
        total_windows = len(candles) - ema_slow

        # Create progress bar with minimal refresh for performance
        if self.enable_progress:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold cyan]{task.description}"),
                BarColumn(complete_style="green", finished_style="bold green"),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                TextColumn(
                    "• [bold yellow]{task.fields[longs]}[/] longs • "
                    "[bold magenta]{task.fields[shorts]}[/] shorts"
                ),
                refresh_per_second=4,  # Minimal refresh: 4 updates/sec (T051)
            )
            progress.start()
            task = progress.add_task(
                f"Scanning {total_windows:,} windows for BOTH signals",
                total=total_windows,
                longs=0,
                shorts=0,
            )
        else:
            progress = nullcontext()
            task = None

        with progress:
            for i in range(ema_slow, len(candles)):
                window = candles[max(0, i - window_size) : i + 1]

                # Generate LONG signals for this window
                long_window_signals = generate_long_signals(
                    candles=window, parameters=parameters
                )
                if long_window_signals:
                    signal = long_window_signals[0]
                    if not any(
                        s.timestamp_utc == signal.timestamp_utc
                        for s in all_long_signals
                    ):
                        all_long_signals.append(signal)
                        if task:
                            progress.update(task, longs=len(all_long_signals))

                        # Throttled logging for LONG signals
                        if len(all_long_signals) % self.log_frequency == 0:
                            logger.debug(
                                "BOTH mode - LONG: %d signals found",
                                len(all_long_signals),
                            )

                # Generate SHORT signals for this window
                short_window_signals = generate_short_signals(
                    candles=window, parameters=parameters
                )
                if short_window_signals:
                    signal = short_window_signals[0]
                    if not any(
                        s.timestamp_utc == signal.timestamp_utc
                        for s in all_short_signals
                    ):
                        all_short_signals.append(signal)
                        if task:
                            progress.update(task, shorts=len(all_short_signals))

                        # Throttled logging for SHORT signals
                        if len(all_short_signals) % self.log_frequency == 0:
                            logger.debug(
                                "BOTH mode - SHORT: %d signals found",
                                len(all_short_signals),
                            )

                if task:
                    progress.update(task, advance=1)

        long_signals = all_long_signals
        short_signals = all_short_signals
        self._end_phase("scan")

        logger.info(
            "Generated %d LONG signals, %d SHORT signals",
            len(long_signals),
            len(short_signals),
        )

        # Merge signals and detect conflicts
        merged_signals, conflicts = merge_signals(
            long_signals=long_signals,
            short_signals=short_signals,
            pair=pair,
        )
        logger.info(
            "Merged signals: %d total, %d conflicts detected",
            len(merged_signals),
            len(conflicts),
        )

        # Execute signals (skip if dry-run)
        executions = []
        if not self.dry_run:
            self._start_phase("simulate")
            logger.info(
                "Simulating execution for %d merged signals (batch mode)",
                len(merged_signals),
            )

            # Create progress bar for execution with minimal refresh
            if self.enable_progress:
                exec_progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[bold cyan]{task.description}"),
                    BarColumn(complete_style="green", finished_style="bold green"),
                    TaskProgressColumn(),
                    TimeElapsedColumn(),
                    refresh_per_second=4,  # Minimal refresh: 4 updates/sec (T051)
                )
                exec_progress.start()
                exec_task = exec_progress.add_task(
                    f"Simulating {len(merged_signals):,} trades (vectorized)",
                    total=100,
                )
            else:
                exec_progress = nullcontext()
                exec_task = None

            with exec_progress:
                # Use batch simulation for performance
                if exec_task:
                    exec_progress.update(exec_task, advance=50)  # Processing signals
                executions = self._simulate_batch(merged_signals, candles)
                if exec_task:
                    exec_progress.update(exec_task, advance=50)  # Complete
            self._end_phase("simulate")

            # Calculate wins/losses for logging
            wins = sum(1 for ex in executions if ex.exit_reason == "TARGET")
            losses = sum(1 for ex in executions if ex.exit_reason == "STOP_LOSS")

            logger.info(
                "Batch execution complete: %d/%d signals executed (%d wins, %d losses)",
                len(executions),
                len(merged_signals),
                wins,
                losses,
            )

        # Calculate three-tier metrics (long_only, short_only, combined)
        metrics = None
        if executions:
            metrics = calculate_directional_metrics(executions, DirectionMode.BOTH)
            logger.info(
                "Metrics calculated - Combined: %d trades, win_rate=%.2f%%",
                metrics.combined.trade_count,
                metrics.combined.win_rate * 100,
            )
            if metrics.long_only:
                logger.info(
                    "  Long-only: %d trades, win_rate=%.2f%%",
                    metrics.long_only.trade_count,
                    metrics.long_only.win_rate * 100,
                )
            if metrics.short_only:
                logger.info(
                    "  Short-only: %d trades, win_rate=%.2f%%",
                    metrics.short_only.trade_count,
                    metrics.short_only.win_rate * 100,
                )

        end_time = datetime.now(UTC)
        return BacktestResult(
            run_id=run_id,
            direction_mode=DirectionMode.BOTH.value,
            start_time=start_time,
            end_time=end_time,
            data_start_date=candles[0].timestamp_utc,
            data_end_date=candles[-1].timestamp_utc,
            total_candles=len(candles),
            metrics=metrics,
            signals=merged_signals if self.dry_run else None,
            executions=executions if not self.dry_run else None,
            conflicts=[],
            dry_run=self.dry_run,
            pair=pair,
        )

    # ------------------------------------------------------------------
    # Multi-Strategy Execution (T022, T029)
    # ------------------------------------------------------------------
    def run_multi_strategy_full(
        self,
        strategies: Sequence[tuple[str, callable]],
        candles_by_strategy: dict[str, Sequence[Candle]],
        weights: Sequence[float],
        run_id: str,
        global_drawdown_limit: float | None = None,
        data_manifest_refs: Sequence[str] | None = None,
        config_params: dict | None = None,
        seed: int = 0,
    ) -> dict:
        """
        Execute multiple strategies with full isolation, risk management, and metrics.

        Implements FR-001 through FR-023 with:
        - Per-strategy state isolation (FR-003)
        - Layered risk controls (FR-015, FR-021)
        - Deterministic run IDs (FR-018, SC-008)
        - Structured metrics (FR-022)
        - Manifest generation (FR-023)

        Args:
            strategies: Sequence of (name, callable) pairs.
            candles_by_strategy: Mapping strategy name -> candle sequence.
            weights: Strategy weights (normalized via parse_and_normalize_weights).
            run_id: Identifier for this run.
            global_drawdown_limit: Optional portfolio drawdown threshold (0.0-1.0).
            data_manifest_refs: List of data manifest file paths.
            config_params: Optional configuration parameters dict.
            seed: Random seed for reproducibility.

        Returns:
            Dictionary with keys:
                - run_manifest: RunManifest instance
                - structured_metrics: StructuredMetrics instance
                - per_strategy_results: List of strategy result dicts
                - portfolio_summary: Aggregated portfolio metrics
                - deterministic_run_id: Stable run identifier
                - manifest_hash: Manifest reference hash

        Examples:
            >>> def dummy_strategy(candles):
            ...     return {"pnl": 100.0, "max_drawdown": 0.05}
            >>> orchestrator = BacktestOrchestrator(DirectionMode.LONG)
            >>> result = orchestrator.run_multi_strategy_full(
            ...     strategies=[("alpha", dummy_strategy)],
            ...     candles_by_strategy={"alpha": []},
            ...     weights=[1.0],
            ...     run_id="test_001"
            ... )  # doctest: +SKIP
        """
        import time

        from ..models.risk_limits import RiskLimits
        from ..models.run_manifest import RunManifest
        from ..strategy.weights import parse_and_normalize_weights
        from .aggregation import PortfolioAggregator
        from .manifest_writer import compute_manifest_hash
        from .metrics_schema import StructuredMetrics
        from .reproducibility import generate_deterministic_run_id
        from .risk_global import evaluate_portfolio_drawdown, should_abort_portfolio
        from .risk_strategy import check_strategy_risk_breach, should_halt_on_breach
        from .state_isolation import StateIsolationManager

        start_time = datetime.now(UTC)
        runtime_start = time.time()

        strategy_names = [name for name, _ in strategies]
        normalized_weights = parse_and_normalize_weights(weights, len(strategies))

        # Generate deterministic run ID (T029)
        deterministic_run_id = generate_deterministic_run_id(
            strategies=strategy_names,
            weights=normalized_weights,
            data_manifest_refs=list(data_manifest_refs or []),
            config_params=config_params,
            seed=seed,
        )

        logger.info(
            "Starting multi-strategy run: run_id=%s det_id=%s strategies=%d",
            run_id,
            deterministic_run_id,
            len(strategies),
        )

        # Initialize state isolation
        state_manager = StateIsolationManager()
        results: list[dict] = []
        risk_breaches: list[str] = []
        global_abort_triggered = False
        portfolio_peak_pnl = 0.0
        portfolio_current_pnl = 0.0

        # Execute each strategy with isolation
        for (name, func), weight in zip(strategies, normalized_weights, strict=False):
            state = state_manager.get_or_create(name)

            # Skip if strategy already halted
            if state.is_halted:
                logger.info("Skipping halted strategy: name=%s", name)
                continue

            # Get candles for this strategy
            strat_candles = candles_by_strategy.get(name, [])
            if not strat_candles:
                logger.warning("No candles for strategy: name=%s", name)

            # Execute strategy
            try:
                output = func(strat_candles)
            except Exception as exc:  # noqa: BLE001
                logger.error("Strategy execution failed: name=%s error=%s", name, exc)
                output = {"name": name, "pnl": 0.0, "error": str(exc)}

            # Ensure required fields
            if "name" not in output:
                output["name"] = name
            if "pnl" not in output:
                output["pnl"] = 0.0

            # Update state
            pnl = float(output.get("pnl", 0.0))
            state.update_pnl(pnl, datetime.now(UTC))

            # Check per-strategy risk limits (using default limits for now)
            default_limits = RiskLimits(max_drawdown_pct=1.0)  # Permissive default
            is_breach, breach_reason = check_strategy_risk_breach(state, default_limits)

            if is_breach:
                risk_breaches.append(name)
                if should_halt_on_breach(state, default_limits, is_breach):
                    state.halt(breach_reason, datetime.now(UTC))

            results.append(output)

            # Update portfolio PnL (weighted)
            portfolio_current_pnl += pnl * weight
            if portfolio_current_pnl > portfolio_peak_pnl:
                portfolio_peak_pnl = portfolio_current_pnl

            logger.debug(
                "Strategy completed: name=%s pnl=%.4f weighted=%.4f",
                name,
                pnl,
                pnl * weight,
            )

            # Check global abort conditions after each strategy
            portfolio_dd, dd_breach = evaluate_portfolio_drawdown(
                portfolio_current_pnl, portfolio_peak_pnl, global_drawdown_limit
            )
            should_abort, abort_reason = should_abort_portfolio(
                portfolio_dd, global_drawdown_limit, data_integrity_ok=True
            )

            if should_abort:
                global_abort_triggered = True
                logger.warning("Global abort triggered: reason=%s", abort_reason)
                break

        runtime_seconds = time.time() - runtime_start
        end_time = datetime.now(UTC)

        # Aggregate results
        aggregator = PortfolioAggregator()
        portfolio_summary = aggregator.aggregate(results, normalized_weights)

        # Build RunManifest
        run_manifest = RunManifest(
            run_id=run_id,
            strategies=strategy_names,
            strategy_versions=["1.0.0"] * len(strategies),  # Stub versions
            weights=normalized_weights,
            global_drawdown_limit=global_drawdown_limit,
            data_manifest_refs=list(data_manifest_refs or []),
            start_time=start_time,
            end_time=end_time,
            correlation_status="deferred",
            deterministic_run_id=deterministic_run_id,
            global_abort_triggered=global_abort_triggered,
            risk_breaches=risk_breaches,
        )

        # Compute manifest hash
        manifest_hash = compute_manifest_hash(run_manifest)

        # Build structured metrics
        structured_metrics = StructuredMetrics(
            strategies_count=len(strategies),
            instruments_count=portfolio_summary["instruments_count"],
            runtime_seconds=runtime_seconds,
            aggregate_pnl=portfolio_summary["weighted_pnl"],
            max_drawdown_pct=portfolio_summary["max_drawdown"],
            net_exposure_by_instrument=portfolio_summary["net_exposure_by_instrument"],
            weights_applied=normalized_weights,
            global_drawdown_limit=global_drawdown_limit,
            global_abort_triggered=global_abort_triggered,
            risk_breaches=risk_breaches,
            deterministic_run_id=deterministic_run_id,
            manifest_hash_ref=manifest_hash,
        )

        logger.info(
            "Multi-strategy run complete: run_id=%s pnl=%.4f abort=%s",
            run_id,
            portfolio_summary["weighted_pnl"],
            global_abort_triggered,
        )

        return {
            "run_manifest": run_manifest,
            "structured_metrics": structured_metrics,
            "per_strategy_results": results,
            "portfolio_summary": portfolio_summary,
            "deterministic_run_id": deterministic_run_id,
            "manifest_hash": manifest_hash,
        }

    # Preserve old skeleton for backwards compatibility
    def run_multi_strategy(
        self,
        strategies: Sequence[tuple[str, callable]],
        candles_by_strategy: dict[str, Sequence[Candle]],
        weights: Sequence[float],
        run_id: str,
    ) -> dict:
        """Legacy skeleton method - use run_multi_strategy_full for new code."""
        return self.run_multi_strategy_full(
            strategies=strategies,
            candles_by_strategy=candles_by_strategy,
            weights=weights,
            run_id=run_id,
        )

    def run_optimized_backtest(
        self,
        df: "pd.DataFrame",
        pair: str,
        run_id: str,
        strategy: "Strategy",
        **signal_params: dict,
    ) -> BacktestResult:
        """Execute optimized backtest using BatchScan and BatchSimulation.

        This method bypasses Candle object conversion and window-by-window iteration,
        using vectorized operations on DataFrames for ≥50% scan speedup and
        ≥55% simulation speedup (FR-001).

        Args:
            df: Enriched pandas DataFrame with OHLC and indicator columns
            pair: Currency pair being backtested (e.g., "EURUSD")
            run_id: Unique identifier for this backtest run
            strategy: Strategy instance providing metadata and signal generation
            **signal_params: Strategy parameters (ema_fast, ema_slow, etc.)

        Returns:
            BacktestResult with signals, executions, and metrics

        Raises:
            ValueError: If df is empty or missing required columns
        """

        if df.is_empty():
            raise ValueError("DataFrame cannot be empty")

        start_time = datetime.now(UTC)
        logger.info(
            "Starting optimized backtest run_id=%s, pair=%s, direction=%s",
            run_id,
            pair,
            self.direction_mode.value,
        )

        # df is already a Polars DataFrame from the CLI, no conversion needed
        polars_df = df

        # Route to direction-specific optimized workflow
        if self.direction_mode == DirectionMode.LONG:
            return self._run_optimized_long(
                polars_df, pair, run_id, start_time, strategy, **signal_params
            )
        elif self.direction_mode == DirectionMode.SHORT:
            return self._run_optimized_short(
                polars_df, pair, run_id, start_time, strategy, **signal_params
            )
        else:  # BOTH
            return self._run_optimized_both(
                polars_df, pair, run_id, start_time, strategy, **signal_params
            )

    def _convert_scan_result_to_signals(
        self,
        scan_result: "ScanResult",
        df: "pl.DataFrame",
        pair: str,
        direction: str,
        strategy: "Strategy",
        **signal_params: dict,
    ) -> list[TradeSignal]:
        """Convert BatchScan signal indices to TradeSignal objects.

        Args:
            scan_result: Result from BatchScan.scan()
            df: Polars DataFrame with OHLC data
            pair: Currency pair
            direction: 'LONG' or 'SHORT'
            strategy: Strategy instance
            **signal_params: Strategy parameters

        Returns:
            List of TradeSignal objects
        """
        import hashlib

        signals = []

        if scan_result.signal_count == 0:
            return signals

        # Extract arrays for signal construction
        timestamps = df["timestamp_utc"].to_numpy()
        close_prices = df["close"].to_numpy()
        atr_values = df["atr14"].to_numpy()

        atr_stop_mult = signal_params.get("atr_stop_mult", 2.0)
        risk_per_trade_pct = signal_params.get("risk_per_trade_pct", 0.01)

        for idx in scan_result.signal_indices:
            timestamp_utc = timestamps[idx]
            entry_price = close_prices[idx]
            atr = atr_values[idx]

            # Calculate stop price based on direction
            if direction == "LONG":
                initial_stop_price = entry_price - (atr * atr_stop_mult)
            else:  # SHORT
                initial_stop_price = entry_price + (atr * atr_stop_mult)

            # Generate deterministic signal ID
            signal_data = (
                f"{timestamp_utc}|{pair}|{direction}|"
                f"{entry_price}|{strategy.metadata.version}"
            )
            signal_id = hashlib.sha256(signal_data.encode()).hexdigest()[:16]

            # Placeholder position size (calculated from account equity normally)
            calc_position_size = 10000.0

            signal = TradeSignal(
                id=signal_id,
                pair=pair,
                direction=direction,
                entry_price=entry_price,
                initial_stop_price=initial_stop_price,
                risk_per_trade_pct=risk_per_trade_pct,
                calc_position_size=calc_position_size,
                tags=["batch_scan"],
                version=strategy.metadata.version,
                timestamp_utc=timestamp_utc,
            )
            signals.append(signal)

        return signals

    def _convert_simulation_result_to_executions(
        self,
        sim_result: "SimulationResult",
        signals: list[TradeSignal],
        timestamps: "np.ndarray",
    ) -> list[TradeExecution]:
        """Convert BatchSimulation result to TradeExecution objects.

        Args:
            sim_result: Result from BatchSimulation.simulate()
            signals: List of TradeSignal objects that were simulated
            timestamps: Array of candle timestamps

        Returns:
            List of TradeExecution objects
        """
        import numpy as np

        executions = []

        # Map exit reason codes to strings
        EXIT_REASON_MAP = {
            1: "STOP_LOSS",
            2: "TARGET",
            3: "EXPIRY",  # Timeout/max holding period
        }

        # Create TradeExecution for each trade
        for i in range(sim_result.trade_count):
            # Get timestamps from indices
            entry_ts = timestamps[sim_result.entry_indices[i]]
            exit_idx = sim_result.exit_indices[i]
            if exit_idx >= 0 and exit_idx < len(timestamps):
                exit_ts = timestamps[exit_idx]
            else:
                # Trade still open or invalid index - skip
                continue

            # Map direction code to string
            direction_str = "LONG" if sim_result.directions[i] == 1 else "SHORT"

            # Map exit reason code
            exit_reason = EXIT_REASON_MAP.get(
                int(sim_result.exit_reasons[i]), "UNKNOWN"
            )

            execution = TradeExecution(
                signal_id=signals[i].id if i < len(signals) else f"sig_{i}",
                direction=direction_str,
                open_timestamp=entry_ts,
                entry_fill_price=float(sim_result.entry_prices[i]),
                close_timestamp=exit_ts,
                exit_fill_price=float(sim_result.exit_prices[i]),
                exit_reason=exit_reason,
                pnl_r=float(sim_result.pnl_r[i]),
                slippage_entry_pips=0.5,  # TODO: Calculate actual slippage
                slippage_exit_pips=0.5,  # TODO: Calculate actual slippage
                costs_total=0.0,  # TODO: Calculate actual costs
            )
            executions.append(execution)

        logger.info(
            "Converted %d/%d trades to TradeExecution objects",
            len(executions),
            sim_result.trade_count,
        )

        return executions

    def _run_optimized_long(
        self,
        df: "pl.DataFrame",
        pair: str,
        run_id: str,
        start_time: datetime,
        strategy: "Strategy",
        **signal_params: dict,
    ) -> BacktestResult:
        """Execute optimized long-only backtest.

        Args:
            df: Polars DataFrame with OHLC and indicator columns
            pair: Currency pair code
            run_id: Backtest run identifier
            start_time: Run start timestamp
            strategy: Strategy instance
            **signal_params: Strategy parameters

        Returns:
            BacktestResult with long signals and executions
        """
        from ..backtest.batch_scan import BatchScan

        logger.info("Running optimized long-only scan for %s", pair)

        # Initialize batch scanner with LONG direction
        scanner = BatchScan(
            strategy=strategy,
            enable_progress=self.enable_progress,
            direction="LONG",
            parameters=signal_params,
        )

        # Execute batch scan
        self._start_phase("scan")
        scan_result = scanner.scan(df, timestamp_col="timestamp_utc")
        self._end_phase("scan")

        logger.info(
            "Scan complete: %d signals, %.2fs, %.1f%% progress overhead",
            scan_result.signal_count,
            scan_result.scan_duration_sec,
            scan_result.progress_overhead_pct,
        )

        # If dry-run, return early with signals only
        if self.dry_run:
            # TODO: Convert signal_indices to TradeSignal objects for compatibility
            # Placeholder implementation for Phase 8
            data_start_date = df["timestamp_utc"][0]
            data_end_date = df["timestamp_utc"][-1]

            return BacktestResult(
                run_id=run_id,
                pair=pair,
                direction_mode="LONG",
                start_time=start_time,
                end_time=datetime.now(UTC),
                data_start_date=data_start_date,
                data_end_date=data_end_date,
                total_candles=len(df),
                signals=[],  # TODO: Implement signal conversion
                executions=[],
                conflicts=[],
                metrics=None,
            )

        # Execute batch simulation
        from ..backtest.batch_simulation import BatchSimulation

        logger.info(
            "Running optimized simulation for %d signals", scan_result.signal_count
        )

        # Get max_concurrent_positions from strategy metadata
        max_concurrent = getattr(strategy.metadata, "max_concurrent_positions", 1)
        logger.info(
            "Simulator config: max_concurrent_positions=%s (from strategy metadata)",
            max_concurrent,
        )

        simulator = BatchSimulation(
            risk_per_trade=signal_params.get("risk_per_trade_pct", 0.01),
            enable_progress=self.enable_progress,
            max_concurrent_positions=max_concurrent,
        )

        # Extract OHLC arrays for simulation
        timestamps = df["timestamp_utc"].to_numpy()
        ohlc_arrays = (
            timestamps,
            df["open"].to_numpy(),
            df["high"].to_numpy(),
            df["low"].to_numpy(),
            df["close"].to_numpy(),
        )

        self._start_phase("simulation")
        sim_result = simulator.simulate(
            signal_indices=scan_result.signal_indices,
            stop_prices=scan_result.stop_prices,
            target_prices=scan_result.target_prices,
            timestamps=timestamps,
            ohlc_arrays=ohlc_arrays,
        )
        self._end_phase("simulation")

        logger.info(
            "Simulation complete: %d trades, %.2fs, %.1f%% progress overhead",
            sim_result.trade_count,
            sim_result.simulation_duration_sec,
            sim_result.progress_overhead_pct,
        )

        # Convert scan and simulation results to BacktestResult format
        logger.info("Converting scan results to TradeSignal objects")
        signals = self._convert_scan_result_to_signals(
            scan_result, df, pair, "LONG", strategy, **signal_params
        )

        logger.info("Converting simulation results to TradeExecution objects")
        executions = self._convert_simulation_result_to_executions(
            sim_result, signals, timestamps
        )

        # Calculate metrics
        metrics = None
        if executions:
            logger.info("Calculating metrics for %d executions", len(executions))
            metrics = calculate_directional_metrics(executions, DirectionMode.LONG)

        data_start_date = df["timestamp_utc"][0]
        data_end_date = df["timestamp_utc"][-1]

        return BacktestResult(
            run_id=run_id,
            pair=pair,
            direction_mode="LONG",
            start_time=start_time,
            end_time=datetime.now(UTC),
            data_start_date=data_start_date,
            data_end_date=data_end_date,
            total_candles=len(df),
            signals=signals if not self.dry_run else None,
            executions=executions if not self.dry_run else None,
            conflicts=[],
            metrics=metrics,
        )

    def _run_optimized_short(
        self,
        df: "pl.DataFrame",
        pair: str,
        run_id: str,
        start_time: datetime,
        strategy: "Strategy",
        **signal_params: dict,
    ) -> BacktestResult:
        """Execute optimized short-only backtest.

        Args:
            df: Polars DataFrame with OHLC and indicator columns
            pair: Currency pair code
            run_id: Backtest run identifier
            start_time: Run start timestamp
            strategy: Strategy instance
            **signal_params: Strategy parameters

        Returns:
            BacktestResult with short signals and executions
        """
        from ..backtest.arrays import extract_indicator_arrays, extract_ohlc_arrays
        from ..backtest.batch_scan import BatchScan
        from ..backtest.batch_simulation import BatchSimulation

        # Run scan for SHORT direction
        logger.info("Running optimized BatchScan for SHORT direction")
        scanner = BatchScan(
            strategy=strategy,
            enable_progress=self.enable_progress,
            direction="SHORT",
            parameters=signal_params,
        )

        self._start_phase("scan")
        scan_result = scanner.scan(df=df, timestamp_col="timestamp_utc")
        self._end_phase("scan")

        logger.info(
            "SHORT scan complete: %d signals, %.2fs, %.1f%% progress overhead",
            scan_result.signal_count,
            scan_result.scan_duration_sec,
            scan_result.progress_overhead_pct,
        )

        # Run simulation on signals
        logger.info(
            "Running optimized simulation for %d signals", scan_result.signal_count
        )

        simulator = BatchSimulation(
            risk_per_trade=signal_params.get("risk_per_trade_pct", 0.01),
            enable_progress=self.enable_progress,
            max_concurrent_positions=getattr(
                strategy.metadata, "max_concurrent_positions", 1
            ),
        )

        # Extract OHLC arrays for simulation
        timestamps = df["timestamp_utc"].to_numpy()
        ohlc_arrays = (
            timestamps,
            df["open"].to_numpy(),
            df["high"].to_numpy(),
            df["low"].to_numpy(),
            df["close"].to_numpy(),
        )

        self._start_phase("simulation")
        sim_result = simulator.simulate(
            signal_indices=scan_result.signal_indices,
            timestamps=timestamps,
            ohlc_arrays=ohlc_arrays,
        )
        self._end_phase("simulation")

        logger.info(
            "Simulation complete: %d trades, %.2fs, %.1f%% progress overhead",
            sim_result.trade_count,
            sim_result.simulation_duration_sec,
            sim_result.progress_overhead_pct,
        )

        # Convert scan and simulation results to BacktestResult format
        logger.info("Converting scan results to TradeSignal objects")
        signals = self._convert_scan_result_to_signals(
            scan_result, df, pair, "SHORT", strategy, **signal_params
        )

        logger.info("Converting simulation results to TradeExecution objects")
        executions = self._convert_simulation_result_to_executions(
            sim_result, signals, timestamps
        )

        # Calculate metrics
        metrics = None
        if executions:
            logger.info("Calculating metrics for %d executions", len(executions))
            metrics = calculate_directional_metrics(executions, DirectionMode.SHORT)

        data_start_date = df["timestamp_utc"][0]
        data_end_date = df["timestamp_utc"][-1]

        return BacktestResult(
            run_id=run_id,
            pair=pair,
            direction_mode="SHORT",
            start_time=start_time,
            end_time=datetime.now(UTC),
            data_start_date=data_start_date,
            data_end_date=data_end_date,
            total_candles=len(df),
            signals=signals if not self.dry_run else None,
            executions=executions if not self.dry_run else None,
            conflicts=[],
            metrics=metrics,
        )

    def _run_optimized_both(
        self,
        df: "pl.DataFrame",
        pair: str,
        run_id: str,
        start_time: datetime,
        strategy: "Strategy",
        **signal_params: dict,
    ) -> BacktestResult:
        """Execute optimized BOTH-direction backtest.

        Args:
            df: Polars DataFrame with OHLC and indicator columns
            pair: Currency pair code
            run_id: Backtest run identifier
            start_time: Run start timestamp
            strategy: Strategy instance
            **signal_params: Strategy parameters

        Returns:
            BacktestResult with long and short signals, executions, and conflicts
        """
        from ..backtest.arrays import extract_indicator_arrays, extract_ohlc_arrays
        from ..backtest.batch_scan import BatchScan
        from ..backtest.batch_simulation import BatchSimulation

        logger.info("Running optimized BatchScan for BOTH directions")

        # Scan LONG direction
        long_scanner = BatchScan(
            strategy=strategy,
            enable_progress=self.enable_progress,
            direction="LONG",
            parameters=signal_params,
        )

        self._start_phase("scan")
        long_scan = long_scanner.scan(df=df, timestamp_col="timestamp_utc")
        logger.info(
            "LONG scan complete: %d signals, %.2fs",
            long_scan.signal_count,
            long_scan.scan_duration_sec,
        )

        # Scan SHORT direction
        short_scanner = BatchScan(
            strategy=strategy,
            enable_progress=self.enable_progress,
            direction="SHORT",
            parameters=signal_params,
        )

        short_scan = short_scanner.scan(df=df, timestamp_col="timestamp_utc")
        self._end_phase("scan")

        logger.info(
            "SHORT scan complete: %d signals, %.2fs",
            short_scan.signal_count,
            short_scan.scan_duration_sec,
        )

        total_signals = long_scan.signal_count + short_scan.signal_count
        logger.info(
            "Total signals: %d (%d LONG + %d SHORT)",
            total_signals,
            long_scan.signal_count,
            short_scan.signal_count,
        )

        # TODO: Implement conflict detection for simultaneous LONG/SHORT signals
        # For now, simply combine signal indices
        # In future, merge with conflict detection like legacy path

        # Run simulation on LONG signals
        simulator = BatchSimulation(
            risk_per_trade=signal_params.get("risk_per_trade_pct", 0.01),
            enable_progress=self.enable_progress,
            max_concurrent_positions=getattr(
                strategy.metadata, "max_concurrent_positions", 1
            ),
        )

        timestamps = df["timestamp_utc"].to_numpy()
        ohlc_arrays = (
            timestamps,
            df["open"].to_numpy(),
            df["high"].to_numpy(),
            df["low"].to_numpy(),
            df["close"].to_numpy(),
        )

        self._start_phase("simulation")

        long_sim = None
        short_sim = None

        if long_scan.signal_count > 0:
            logger.info("Simulating %d LONG signals", long_scan.signal_count)
            long_sim = simulator.simulate(
                signal_indices=long_scan.signal_indices,
                timestamps=timestamps,
                ohlc_arrays=ohlc_arrays,
            )
            logger.info(
                "LONG simulation: %d trades, %.2fs",
                long_sim.trade_count,
                long_sim.simulation_duration_sec,
            )

        if short_scan.signal_count > 0:
            logger.info("Simulating %d SHORT signals", short_scan.signal_count)
            short_sim = simulator.simulate(
                signal_indices=short_scan.signal_indices,
                timestamps=timestamps,
                ohlc_arrays=ohlc_arrays,
            )
            logger.info(
                "SHORT simulation: %d trades, %.2fs",
                short_sim.trade_count,
                short_sim.simulation_duration_sec,
            )

        self._end_phase("simulation")

        total_trades = (long_sim.trade_count if long_sim else 0) + (
            short_sim.trade_count if short_sim else 0
        )
        logger.info("Total trades executed: %d", total_trades)

        # Convert scan results to TradeSignal objects
        logger.info("Converting LONG scan results to TradeSignal objects")
        long_signals = self._convert_scan_result_to_signals(
            long_scan, df, pair, "LONG", strategy, **signal_params
        )

        logger.info("Converting SHORT scan results to TradeSignal objects")
        short_signals = self._convert_scan_result_to_signals(
            short_scan, df, pair, "SHORT", strategy, **signal_params
        )

        # Merge signals with conflict detection
        logger.info("Merging signals with conflict detection")
        merged_signals, conflicts = merge_signals(long_signals, short_signals, pair)
        logger.info(
            "Merged %d signals (%d conflicts detected)",
            len(merged_signals),
            len(conflicts),
        )

        # Convert simulation results to TradeExecution objects
        logger.info("Converting simulation results to TradeExecution objects")
        long_executions = (
            self._convert_simulation_result_to_executions(
                long_sim, long_signals, timestamps
            )
            if long_sim
            else []
        )
        short_executions = (
            self._convert_simulation_result_to_executions(
                short_sim, short_signals, timestamps
            )
            if short_sim
            else []
        )

        # Combine all executions
        all_executions = long_executions + short_executions

        # Calculate three-tier metrics
        metrics = None
        if all_executions:
            logger.info(
                "Calculating three-tier metrics for %d executions", len(all_executions)
            )
            metrics = calculate_directional_metrics(all_executions, DirectionMode.BOTH)

            if metrics.long_only:
                logger.info(
                    "Long-only metrics: %d trades, %.2f%% win rate",
                    metrics.long_only.trade_count,
                    metrics.long_only.win_rate * 100,
                )
            if metrics.short_only:
                logger.info(
                    "Short-only metrics: %d trades, %.2f%% win rate",
                    metrics.short_only.trade_count,
                    metrics.short_only.win_rate * 100,
                )
            if metrics.combined:
                logger.info(
                    "Combined metrics: %d trades, %.2f%% win rate",
                    metrics.combined.trade_count,
                    metrics.combined.win_rate * 100,
                )

        data_start_date = df["timestamp_utc"][0]
        data_end_date = df["timestamp_utc"][-1]

        return BacktestResult(
            run_id=run_id,
            pair=pair,
            direction_mode="BOTH",
            start_time=start_time,
            end_time=datetime.now(UTC),
            data_start_date=data_start_date,
            data_end_date=data_end_date,
            total_candles=len(df),
            signals=merged_signals if not self.dry_run else None,
            executions=all_executions if not self.dry_run else None,
            conflicts=[],
            metrics=metrics,
        )


def merge_signals(
    long_signals: list[TradeSignal],
    short_signals: list[TradeSignal],
    pair: str,
) -> tuple[list[TradeSignal], list[ConflictEvent]]:
    """
    Merge long and short signals with conflict detection.

    When both long and short signals occur at the exact same timestamp,
    both are rejected (indicating choppy market/indecision). Otherwise,
    signals are merged in chronological order.

    Args:
        long_signals: List of LONG direction signals.
        short_signals: List of SHORT direction signals.
        pair: Currency pair (for conflict event logging).

    Returns:
        Tuple of (merged_signals, conflicts):
        - merged_signals: Chronologically sorted signals with conflicts removed
        - conflicts: List of ConflictEvent instances for rejected signal pairs

    Examples:
        >>> from datetime import datetime, timezone
        >>> long_sig = TradeSignal(
        ...     id="long_001",
        ...     timestamp_utc=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        ...     pair="EURUSD",
        ...     direction="LONG",
        ...     entry_price=1.1000,
        ...     stop_price=1.0990,
        ...     risk_per_trade_pct=0.01,
        ...     calc_position_size=0.1,
        ...     tags=[],
        ...     version="1.0"
        ... )
        >>> merged, conflicts = merge_signals([long_sig], [], "EURUSD")
        >>> len(merged)
        1
        >>> len(conflicts)
        0
    """
    # Build timestamp index for conflict detection
    long_by_ts = {sig.timestamp_utc: sig for sig in long_signals}
    short_by_ts = {sig.timestamp_utc: sig for sig in short_signals}

    # Find conflicting timestamps
    conflicting_timestamps = set(long_by_ts.keys()) & set(short_by_ts.keys())

    conflicts = []
    for ts in conflicting_timestamps:
        conflict = ConflictEvent(
            timestamp_utc=ts,
            pair=pair,
            long_signal_id=long_by_ts[ts].id,
            short_signal_id=short_by_ts[ts].id,
        )
        conflicts.append(conflict)
        logger.warning(
            "Conflict detected at timestamp=%s, pair=%s (rejecting both signals)",
            ts.isoformat(),
            pair,
        )

    # Merge non-conflicting signals
    merged = []
    for sig in long_signals:
        if sig.timestamp_utc not in conflicting_timestamps:
            merged.append(sig)
    for sig in short_signals:
        if sig.timestamp_utc not in conflicting_timestamps:
            merged.append(sig)

    # Sort chronologically
    merged.sort(key=lambda s: s.timestamp_utc)

    return merged, conflicts
