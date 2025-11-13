"""
Observability reporter for backtest monitoring and diagnostics.

Provides real-time progress reporting, performance metrics logging, and
diagnostic information during backtest execution.

Logging Standards (Constitution Principle X):
    - MUST use lazy % formatting: logger.info("Processing %d items", count)
    - PROHIBITED: F-strings in logging: logger.info(f"Processing {count} items")
    - All logging calls must pass arguments separately, not interpolated strings

Example (Correct):
    logger.info("Building dataset for symbol %s with %d rows", symbol, row_count)

Example (Incorrect):
    logger.info(f"Building dataset for symbol {symbol} with {row_count} rows")
"""

import logging
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from ..models.core import BacktestRun, MetricsSummary


logger = logging.getLogger(__name__)
console = Console()


class ObservabilityReporter:
    """
    Reports backtest progress and metrics to console and logs.

    Provides real-time updates during backtest execution and final
    summary display with formatted tables.

    Attributes:
        backtest_id: Unique identifier for the backtest run.
        start_time: Backtest start timestamp.
        total_candles: Total candles to process.
        processed_candles: Candles processed so far.
        progress: Rich progress bar instance.

    Examples:
        >>> reporter = ObservabilityReporter(backtest_id="run-123", total_candles=10000)
        >>> reporter.start()
        >>> reporter.update_progress(100)
        >>> reporter.report_metrics(summary)
        >>> reporter.finish()
    """

    def __init__(self, backtest_id: str, total_candles: int) -> None:
        """
        Initialize observability reporter.

        Args:
            backtest_id: Unique backtest run identifier.
            total_candles: Total number of candles to process.
        """
        self.backtest_id = backtest_id
        self.start_time: datetime | None = None
        self.total_candles = total_candles
        self.processed_candles = 0
        self.progress: Progress | None = None

    def start(self) -> None:
        """
        Start backtest monitoring.

        Displays initial banner and starts progress bar.

        Examples:
            >>> reporter = ObservabilityReporter("run-123", 10000)
            >>> reporter.start()
        """
        self.start_time = datetime.now()

        console.print("\n[bold cyan]═══ Backtest Starting ═══[/bold cyan]")
        console.print(f"Backtest ID: {self.backtest_id}")
        console.print(f"Total Candles: {self.total_candles:,}")
        console.print(f"Start Time: {self.start_time.isoformat()}\n")

        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        )
        self.progress.start()
        self.progress.add_task(
            description="Processing candles...",
            total=self.total_candles,
        )

        logger.info(
            "Backtest started: id=%s, total_candles=%d",
            self.backtest_id,
            self.total_candles,
        )

    def update_progress(self, candles_processed: int) -> None:
        """
        Update progress bar with processed candle count.

        Args:
            candles_processed: Number of candles processed in this batch.

        Examples:
            >>> reporter.update_progress(100)
        """
        self.processed_candles += candles_processed
        if self.progress:
            self.progress.update(0, completed=self.processed_candles)

    def report_metrics(self, summary: MetricsSummary) -> None:
        """
        Display metrics summary in formatted table.

        Args:
            summary: Computed metrics summary.

        Examples:
            >>> summary = MetricsSummary(...)
            >>> reporter.report_metrics(summary)
        """
        if self.progress:
            self.progress.stop()

        console.print("\n[bold green]═══ Backtest Complete ═══[/bold green]\n")

        # Create metrics table
        table = Table(
            title="Performance Metrics", show_header=True, header_style="bold magenta"
        )
        table.add_column("Metric", style="cyan", width=25)
        table.add_column("Value", style="green", justify="right")

        table.add_row("Total Trades", str(summary.trade_count))
        table.add_row("Winning Trades", str(summary.win_count))
        table.add_row("Losing Trades", str(summary.loss_count))
        table.add_row("Win Rate", f"{summary.win_rate:.2%}")
        table.add_row("Avg Win", f"{summary.avg_win_r:.3f}R")
        table.add_row("Avg Loss", f"{summary.avg_loss_r:.3f}R")
        table.add_row("Avg R", f"{summary.avg_r:.3f}R")
        table.add_row("Expectancy", f"{summary.expectancy:.3f}R")
        table.add_row("Max Drawdown", f"{summary.max_drawdown_r:.2f}R")
        table.add_row("Sharpe Estimate", f"{summary.sharpe_estimate:.3f}")
        table.add_row("Profit Factor", f"{summary.profit_factor:.2f}")

        console.print(table)

        # Display timing
        if self.start_time:
            duration = datetime.now() - self.start_time
            console.print(f"\n[dim]Duration: {duration.total_seconds():.1f}s[/dim]")

        logger.info(
            "Backtest metrics: trade_count=%d, win_rate=%.2f%%, expectancy=%.3fR",
            summary.trade_count,
            summary.win_rate * 100,
            summary.expectancy,
        )

    def report_signal_generated(self, signal_id: str, timestamp: datetime) -> None:
        """
        Log signal generation event.

        Args:
            signal_id: Generated signal identifier.
            timestamp: Signal timestamp.

        Examples:
            >>> reporter.report_signal_generated("sig-123", datetime.now())
        """
        logger.debug(
            "Signal generated: id=%s..., timestamp=%s",
            signal_id[:16],
            timestamp.isoformat(),
        )

    def report_trade_executed(
        self, signal_id: str, pnl_r: float, exit_reason: str
    ) -> None:
        """
        Log trade execution event.

        Args:
            signal_id: Signal identifier.
            pnl_r: Trade PnL in R-multiples.
            exit_reason: Exit condition that closed the trade.

        Examples:
            >>> reporter.report_trade_executed("sig-123", 2.0, "TARGET")
        """
        logger.info(
            "Trade executed: signal_id=%s..., pnl_r=%.2fR, exit_reason=%s",
            signal_id[:16],
            pnl_r,
            exit_reason,
        )

    def report_error(self, error: Exception, context: dict[str, Any]) -> None:
        """
        Log error with context information.

        Args:
            error: Exception that occurred.
            context: Additional context dictionary.

        Examples:
            >>> reporter.report_error(ValueError("Bad data"), {"candle_idx": 42})
        """
        console.print(f"\n[bold red]ERROR:[/bold red] {error}", style="red")
        logger.error("Backtest error: %s", error, extra=context, exc_info=True)

    def finish(self) -> None:
        """
        Clean up reporter resources.

        Examples:
            >>> reporter.finish()
        """
        if self.progress:
            self.progress.stop()

        logger.info("Backtest finished: id=%s", self.backtest_id)


def report_backtest_run(backtest_run: BacktestRun) -> None:
    """
    Display complete BacktestRun information in formatted output.

    Args:
        backtest_run: Completed backtest run to display.

    Examples:
        >>> from models.core import BacktestRun
        >>> run = BacktestRun(...)
        >>> report_backtest_run(run)
    """
    console.print("\n[bold cyan]═══ Backtest Run Summary ═══[/bold cyan]\n")

    # Metadata table
    meta_table = Table(
        title="Run Metadata", show_header=True, header_style="bold magenta"
    )
    meta_table.add_column("Field", style="cyan", width=20)
    meta_table.add_column("Value", style="white")

    meta_table.add_row("Run ID", backtest_run.run_id)
    meta_table.add_row("Strategy Name", backtest_run.strategy_name)
    meta_table.add_row("Parameters Hash", backtest_run.parameters_hash[:16] + "...")
    meta_table.add_row(
        "Data Manifest Hash", backtest_run.data_manifest_hash[:16] + "..."
    )
    meta_table.add_row("Start Time", backtest_run.start_timestamp_utc.isoformat())
    meta_table.add_row("End Time", backtest_run.end_timestamp_utc.isoformat())

    console.print(meta_table)
    console.print()


# ============================================================================
# Multi-Strategy Observability (T030)
# ============================================================================


def log_multi_strategy_start(
    run_id: str,
    deterministic_run_id: str,
    strategies: list[str],
    weights: list[float],
) -> None:
    """
    Log structured event for multi-strategy backtest start.

    Args:
        run_id: User-provided run identifier.
        deterministic_run_id: Computed deterministic hash ID.
        strategies: List of strategy names.
        weights: Normalized strategy weights.

    Examples:
        >>> log_multi_strategy_start(
        ...     "test_run_001",
        ...     "abc123def456",
        ...     ["alpha", "beta"],
        ...     [0.6, 0.4]
        ... )  # doctest: +SKIP
    """
    logger.info(
        "Multi-strategy backtest started: run_id=%s det_id=%s strategies=%s weights=%s",
        run_id,
        deterministic_run_id,
        ",".join(strategies),
        ",".join(f"{w:.4f}" for w in weights),
    )


def log_multi_strategy_completion(
    run_id: str,
    runtime_seconds: float,
    strategies_count: int,
    weighted_pnl: float,
    global_abort_triggered: bool,
    risk_breaches: list[str],
) -> None:
    """
    Log structured event for multi-strategy backtest completion.

    Args:
        run_id: Run identifier.
        runtime_seconds: Wall-clock runtime.
        strategies_count: Number of strategies executed.
        weighted_pnl: Aggregated weighted PnL.
        global_abort_triggered: Whether global abort occurred.
        risk_breaches: List of strategies with risk breaches.

    Examples:
        >>> log_multi_strategy_completion(
        ...     "test_run_001",
        ...     12.5,
        ...     2,
        ...     1250.0,
        ...     False,
        ...     []
        ... )  # doctest: +SKIP
    """
    logger.info(
        "Multi-strategy backtest completed: run_id=%s runtime=%.2fs "
        "strategies=%d pnl=%.4f abort=%s breaches=%d",
        run_id,
        runtime_seconds,
        strategies_count,
        weighted_pnl,
        global_abort_triggered,
        len(risk_breaches),
    )

    if risk_breaches:
        logger.warning(
            "Risk breaches detected: run_id=%s strategies=%s",
            run_id,
            ",".join(risk_breaches),
        )


def log_structured_metrics(metrics_dict: dict[str, Any]) -> None:
    """
    Log structured metrics as JSON for downstream processing.

    Emits a single structured log line containing all portfolio metrics
    per FR-022 research decision.

    Args:
        metrics_dict: Dictionary with portfolio-level metrics.

    Examples:
        >>> import json
        >>> metrics = {
        ...     "strategies_count": 2,
        ...     "aggregate_pnl": 1250.0,
        ...     "max_drawdown_pct": 0.08,
        ...     "deterministic_run_id": "abc123"
        ... }
        >>> log_structured_metrics(metrics)  # doctest: +SKIP
    """
    import json

    logger.info("Structured metrics: %s", json.dumps(metrics_dict, sort_keys=True))
