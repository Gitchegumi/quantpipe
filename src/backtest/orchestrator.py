"""
Backtest orchestration for directional backtesting system.

This module coordinates the execution of backtests across different direction modes
(LONG, SHORT, BOTH), managing signal generation, conflict resolution, execution
simulation, and metrics aggregation.
"""

import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Literal

from ..backtest.execution import simulate_execution
from ..backtest.metrics import calculate_directional_metrics
from ..models.core import Candle, TradeExecution, TradeSignal
from ..models.directional import BacktestResult, ConflictEvent, DirectionalMetrics
from ..models.enums import DirectionMode
from ..strategy.trend_pullback.signal_generator import (
    generate_long_signals,
    generate_short_signals,
)

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
    ):
        """
        Initialize backtest orchestrator.

        Args:
            direction_mode: Direction mode for signal generation (LONG, SHORT, BOTH).
            dry_run: If True, generate signals only without execution simulation.
        """
        self.direction_mode = direction_mode
        self.dry_run = dry_run
        logger.info(
            "Initialized BacktestOrchestrator: direction=%s, dry_run=%s",
            direction_mode.value,
            dry_run,
        )

    def run_backtest(
        self,
        candles: Sequence[Candle],
        pair: str,
        run_id: str,
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
        if not candles:
            raise ValueError("Candles sequence cannot be empty")

        start_time = datetime.now(timezone.utc)
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
        all_signals = []
        ema_slow = signal_params.get("ema_slow", 50)
        window_size = 100

        logger.info(
            "Processing %d candles with sliding window (size=%d)",
            len(candles),
            window_size,
        )

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
                    logger.debug("New signal at %s", signal.timestamp_utc)

        signals = all_signals
        logger.info("Generated %d LONG signals", len(signals))

        # Execute signals (skip if dry-run)
        executions = []
        if not self.dry_run:
            logger.info("Simulating execution for %d LONG signals", len(signals))
            for idx, signal in enumerate(signals, 1):
                execution = simulate_execution(signal, candles)
                if execution:
                    executions.append(execution)
                if idx % 10 == 0:
                    logger.debug("Processed %d/%d signals", idx, len(signals))
            logger.info(
                "Execution complete: %d/%d signals executed",
                len(executions),
                len(signals),
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

        end_time = datetime.now(timezone.utc)
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
        all_signals = []
        ema_slow = signal_params.get("ema_slow", 50)
        window_size = 100

        logger.info(
            "Processing %d candles with sliding window (size=%d)",
            len(candles),
            window_size,
        )

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
                    logger.debug("New signal at %s", signal.timestamp_utc)

        signals = all_signals
        logger.info("Generated %d SHORT signals", len(signals))

        # Execute signals (skip if dry-run)
        executions = []
        if not self.dry_run:
            logger.info("Simulating execution for %d SHORT signals", len(signals))
            for idx, signal in enumerate(signals, 1):
                execution = simulate_execution(signal, candles)
                if execution:
                    executions.append(execution)
                if idx % 10 == 0:
                    logger.debug("Processed %d/%d signals", idx, len(signals))
            logger.info(
                "Execution complete: %d/%d signals executed",
                len(executions),
                len(signals),
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

        end_time = datetime.now(timezone.utc)
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
        )

    def _run_both_backtest(
        self,
        candles: Sequence[Candle],
        pair: str,
        run_id: str,
        start_time: datetime,
        **signal_params,
    ) -> BacktestResult:
        """Execute BOTH directions backtest with conflict resolution."""
        logger.info("Generating LONG and SHORT signals for pair=%s", pair)
        parameters = {"pair": pair, **signal_params}
        long_signals = generate_long_signals(candles, parameters)
        short_signals = generate_short_signals(candles, parameters)
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

        # Placeholder: execution and metrics logic to be implemented
        end_time = datetime.now(timezone.utc)
        return BacktestResult(
            run_id=run_id,
            direction_mode=DirectionMode.BOTH.value,
            start_time=start_time,
            end_time=end_time,
            data_start_date=candles[0].timestamp_utc,
            data_end_date=candles[-1].timestamp_utc,
            total_candles=len(candles),
            metrics=None,  # Placeholder for DirectionalMetrics
            signals=merged_signals if self.dry_run else None,
            executions=None,
            conflicts=conflicts,
            dry_run=self.dry_run,
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
