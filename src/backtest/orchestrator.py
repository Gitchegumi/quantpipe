"""
Backtest orchestration for directional backtesting system.

This module coordinates the execution of backtests across different direction modes
(LONG, SHORT, BOTH), managing signal generation, conflict resolution, execution
simulation, and metrics aggregation.
"""

# pylint: disable=broad-exception-caught, unused-variable

import logging
from collections.abc import Sequence
from datetime import UTC, datetime

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from ..backtest.execution import simulate_execution
from ..backtest.metrics import calculate_directional_metrics
from ..models.core import Candle, TradeSignal
from ..models.directional import BacktestResult, ConflictEvent
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
        all_signals = []
        ema_slow = signal_params.get("ema_slow", 50)
        window_size = 100
        total_windows = len(candles) - ema_slow

        # Create progress bar
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("• {task.fields[signals]} signals"),
        )
        progress.start()
        task = progress.add_task(
            f"Scanning {total_windows:,} windows for LONG signals",
            total=total_windows,
            signals=0,
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
                    progress.update(task, signals=len(all_signals))

            progress.update(task, advance=1)

        progress.stop()

        signals = all_signals
        logger.info("Generated %d LONG signals", len(signals))

        # Execute signals (skip if dry-run)
        executions = []
        if not self.dry_run:
            logger.info("Simulating execution for %d LONG signals", len(signals))

            # Create progress bar for execution
            exec_progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TextColumn("• {task.fields[wins]} wins • {task.fields[losses]} losses"),
            )
            exec_progress.start()
            exec_task = exec_progress.add_task(
                f"Simulating {len(signals):,} trades",
                total=len(signals),
                wins=0,
                losses=0,
            )

            wins = 0
            losses = 0
            for signal in signals:
                execution = simulate_execution(signal, candles)
                if execution:
                    executions.append(execution)
                    # Track wins vs losses
                    if execution.exit_reason == "TARGET":
                        wins += 1
                    elif execution.exit_reason == "STOP_LOSS":
                        losses += 1
                    exec_progress.update(exec_task, wins=wins, losses=losses)
                exec_progress.update(exec_task, advance=1)

            exec_progress.stop()

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
        total_windows = len(candles) - ema_slow

        # Create progress bar
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("• {task.fields[signals]} signals"),
        )
        progress.start()
        task = progress.add_task(
            f"Scanning {total_windows:,} windows for SHORT signals",
            total=total_windows,
            signals=0,
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
                    progress.update(task, signals=len(all_signals))

            progress.update(task, advance=1)

        progress.stop()

        signals = all_signals
        logger.info("Generated %d SHORT signals", len(signals))

        # Execute signals (skip if dry-run)
        executions = []
        if not self.dry_run:
            logger.info("Simulating execution for %d SHORT signals", len(signals))

            # Create progress bar for execution
            exec_progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TextColumn("• {task.fields[wins]} wins • {task.fields[losses]} losses"),
            )
            exec_progress.start()
            exec_task = exec_progress.add_task(
                f"Simulating {len(signals):,} trades",
                total=len(signals),
                wins=0,
                losses=0,
            )

            wins = 0
            losses = 0
            for signal in signals:
                execution = simulate_execution(signal, candles)
                if execution:
                    executions.append(execution)
                    # Track wins vs losses
                    if execution.exit_reason == "TARGET":
                        wins += 1
                    elif execution.exit_reason == "STOP_LOSS":
                        losses += 1
                    exec_progress.update(exec_task, wins=wins, losses=losses)
                exec_progress.update(exec_task, advance=1)

            exec_progress.stop()

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
        all_long_signals = []
        all_short_signals = []
        ema_slow = signal_params.get("ema_slow", 50)
        window_size = 100
        total_windows = len(candles) - ema_slow

        # Create progress bar
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("• {task.fields[longs]} longs • {task.fields[shorts]} shorts"),
        )
        progress.start()
        task = progress.add_task(
            f"Scanning {total_windows:,} windows for BOTH signals",
            total=total_windows,
            longs=0,
            shorts=0,
        )

        for i in range(ema_slow, len(candles)):
            window = candles[max(0, i - window_size) : i + 1]

            # Generate LONG signals for this window
            long_window_signals = generate_long_signals(
                candles=window, parameters=parameters
            )
            if long_window_signals:
                signal = long_window_signals[0]
                if not any(
                    s.timestamp_utc == signal.timestamp_utc for s in all_long_signals
                ):
                    all_long_signals.append(signal)
                    progress.update(task, longs=len(all_long_signals))

            # Generate SHORT signals for this window
            short_window_signals = generate_short_signals(
                candles=window, parameters=parameters
            )
            if short_window_signals:
                signal = short_window_signals[0]
                if not any(
                    s.timestamp_utc == signal.timestamp_utc for s in all_short_signals
                ):
                    all_short_signals.append(signal)
                    progress.update(task, shorts=len(all_short_signals))

            progress.update(task, advance=1)

        progress.stop()

        long_signals = all_long_signals
        short_signals = all_short_signals

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
            logger.info(
                "Simulating execution for %d merged signals", len(merged_signals)
            )

            # Create progress bar for execution
            exec_progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TextColumn("• {task.fields[wins]} wins • {task.fields[losses]} losses"),
            )
            exec_progress.start()
            exec_task = exec_progress.add_task(
                f"Simulating {len(merged_signals):,} trades",
                total=len(merged_signals),
                wins=0,
                losses=0,
            )

            wins = 0
            losses = 0
            for signal in merged_signals:
                execution = simulate_execution(signal, candles)
                if execution:
                    executions.append(execution)
                    # Track wins vs losses
                    if execution.exit_reason == "TARGET":
                        wins += 1
                    elif execution.exit_reason == "STOP_LOSS":
                        losses += 1
                    exec_progress.update(exec_task, wins=wins, losses=losses)
                exec_progress.update(exec_task, advance=1)

            exec_progress.stop()

            logger.info(
                "Execution complete: %d/%d signals executed",
                len(executions),
                len(merged_signals),
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
            conflicts=conflicts,
            dry_run=self.dry_run,
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
        from .state_isolation import StateIsolationManager
        from .aggregation import PortfolioAggregator
        from .risk_global import evaluate_portfolio_drawdown, should_abort_portfolio
        from .risk_strategy import check_strategy_risk_breach, should_halt_on_breach
        from .reproducibility import generate_deterministic_run_id
        from .manifest_writer import compute_manifest_hash
        from ..models.run_manifest import RunManifest
        from ..models.risk_limits import RiskLimits
        from .metrics_schema import StructuredMetrics
        from ..strategy.weights import parse_and_normalize_weights

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
        for (name, func), weight in zip(strategies, normalized_weights):
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
