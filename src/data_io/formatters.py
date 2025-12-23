"""
Output formatters for directional backtesting results.

This module provides functions to format backtest results into human-readable
text and JSON formats, including filename generation with timestamps.
Supports both single-mode and split-mode (test/validation) outputs.
"""

import json
import logging
from datetime import datetime

from src.models.directional import BacktestResult, SplitModeResult
from src.models.enums import DirectionMode, OutputFormat


logger = logging.getLogger(__name__)


def generate_output_filename(
    direction: DirectionMode,
    output_format: OutputFormat,
    timestamp: datetime,
    symbol_tag: str | None = None,
    timeframe_tag: str | None = None,
) -> str:
    """
    Generate standardized filename for backtest output.

    Produces filenames in the format:
    backtest_{direction}_{symbol}_{timeframe}_{YYYYMMDD}_{HHMMSS}.{ext}

    If `symbol_tag` is provided it is used directly (expected lowercase, e.g. 'eurusd').
    If `timeframe_tag` is provided it is included after the symbol (e.g. '15m', '1h').
    If `symbol_tag` is not provided the legacy format WITHOUT symbol is used for
    backward compatibility (will be deprecated). Callers implementing multi-symbol
    MUST pass 'multi' for aggregated runs.

    Args:
        direction: Direction mode of the backtest (LONG/SHORT/BOTH).
        output_format: Output format (TEXT/JSON).
        timestamp: Timestamp to use for filename generation.
        symbol_tag: Optional symbol identifier (e.g., 'eurusd', 'multi').
        timeframe_tag: Optional timeframe identifier (e.g., '15m', '1h').

    Returns:
        Formatted filename string.

    Examples:
        >>> from datetime import datetime, timezone
        >>> ts = datetime(2025, 1, 15, 14, 30, 45, tzinfo=timezone.utc)
        >>> generate_output_filename(DirectionMode.LONG, OutputFormat.TEXT, ts)
        'backtest_long_20250115_143045.txt'
        >>> generate_output_filename(DirectionMode.BOTH, OutputFormat.JSON, ts, 'eurusd', '15m')
        'backtest_both_eurusd_15m_20250115_143045.json'
    """
    direction_str = direction.value.lower()
    date_str = timestamp.strftime("%Y%m%d")
    time_str = timestamp.strftime("%H%M%S")
    ext = "json" if output_format == OutputFormat.JSON else "txt"

    if symbol_tag and timeframe_tag:
        filename = f"backtest_{direction_str}_{symbol_tag}_{timeframe_tag}_{date_str}_{time_str}.{ext}"
    elif symbol_tag:
        filename = f"backtest_{direction_str}_{symbol_tag}_{date_str}_{time_str}.{ext}"
    else:
        # Legacy fallback (pre-FR-023) - no symbol component
        filename = f"backtest_{direction_str}_{date_str}_{time_str}.{ext}"
    logger.debug("Generated filename: %s", filename)

    return filename


def format_text_output(result: BacktestResult) -> str:
    """
    Format backtest result as human-readable text.

    Produces a structured text report including:
    - Run metadata (ID, direction, timestamps, data range)
    - Metrics summary (if available)
    - Directional breakdown (for BOTH mode)
    - Conflict summary (if any)
    - Dry-run indicator (if applicable)

    Args:
        result: BacktestResult to format.

    Returns:
        Formatted text string.

    Examples:
        >>> text = format_text_output(backtest_result)
        >>> print(text)
        === Backtest Results ===
        Run ID: test_run_001
        Direction: LONG
        ...
    """
    lines = []
    lines.append("=" * 60)
    lines.append("BACKTEST RESULTS")
    lines.append("=" * 60)
    lines.append("")

    # Metadata
    lines.append("RUN METADATA")
    lines.append("-" * 60)
    lines.append(f"Run ID:           {result.run_id}")
    lines.append(f"Direction Mode:   {result.direction_mode}")
    # Symbol(s) line (FR-023) - BacktestResult may have attribute 'pair' or 'symbols'
    if hasattr(result, "symbols") and isinstance(getattr(result, "symbols"), list):
        syms = getattr(result, "symbols")
        lines.append(f"Symbols:          {', '.join(syms)}")
    elif hasattr(result, "pair"):
        lines.append(f"Symbol:           {getattr(result, 'pair')}")
    # Timeframe line (FR-015)
    if hasattr(result, "timeframe") and result.timeframe:
        lines.append(f"Timeframe:        {result.timeframe}")
    lines.append(f"Start Time:       {result.start_time.isoformat()}")
    lines.append(f"End Time:         {result.end_time.isoformat()}")
    duration = (result.end_time - result.start_time).total_seconds()
    lines.append(f"Duration:         {duration:.2f} seconds")
    lines.append("")

    # Data range
    lines.append("DATA RANGE")
    lines.append("-" * 60)
    lines.append(f"Start Date:       {result.data_start_date.isoformat()}")
    lines.append(f"End Date:         {result.data_end_date.isoformat()}")
    lines.append(f"Total Candles:    {result.total_candles}")
    lines.append("")

    # Metrics
    if result.metrics is not None:
        lines.append("PERFORMANCE METRICS")
        lines.append("-" * 60)

        # Check if directional metrics
        if hasattr(result.metrics, "combined"):
            # DirectionalMetrics
            if result.metrics.long_only is not None:
                lines.append("LONG-ONLY METRICS:")
                lines.extend(_format_metrics_summary(result.metrics.long_only))
                lines.append("")

            if result.metrics.short_only is not None:
                lines.append("SHORT-ONLY METRICS:")
                lines.extend(_format_metrics_summary(result.metrics.short_only))
                lines.append("")

            if result.metrics.combined is not None:
                lines.append("COMBINED METRICS:")
                lines.extend(_format_metrics_summary(result.metrics.combined))
                lines.append("")
        else:
            # Regular MetricsSummary
            lines.extend(_format_metrics_summary(result.metrics))
            lines.append("")
    else:
        lines.append("PERFORMANCE METRICS")
        lines.append("-" * 60)
        lines.append("(No metrics available)")
        lines.append("")

    # Conflicts
    if result.conflicts:
        lines.append("SIGNAL CONFLICTS")
        lines.append("-" * 60)
        lines.append(f"Total Conflicts:  {len(result.conflicts)}")
        lines.append("")
        for idx, conflict in enumerate(result.conflicts[:10], 1):  # Show first 10
            lines.append(
                f"  {idx}. {conflict.timestamp_utc.isoformat()} - "
                f"LONG: {conflict.long_signal_id} vs SHORT: {conflict.short_signal_id}"
            )
        if len(result.conflicts) > 10:
            lines.append(f"  ... and {len(result.conflicts) - 10} more conflicts")
        lines.append("")

    # Dry-run indicator
    if result.dry_run:
        lines.append("DRY-RUN MODE")
        lines.append("-" * 60)
        lines.append("This was a dry-run (signals only, no execution)")
        lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)


def _format_metrics_summary(metrics) -> list[str]:
    """
    Format MetricsSummary into text lines.

    Args:
        metrics: MetricsSummary object.

    Returns:
        List of formatted text lines.
    """
    lines = []
    lines.append(f"  Trades:           {metrics.trade_count}")
    lines.append(f"  Wins:             {metrics.win_count}")
    lines.append(f"  Losses:           {metrics.loss_count}")
    lines.append(f"  Win Rate:         {metrics.win_rate:.2%}")
    lines.append(f"  Avg Win (R):      {metrics.avg_win_r:.2f}")
    lines.append(f"  Avg Loss (R):     {metrics.avg_loss_r:.2f}")
    lines.append(f"  Avg R:            {metrics.avg_r:.2f}")
    lines.append(f"  Expectancy (R):   {metrics.expectancy:.2f}")
    lines.append(f"  Sharpe Estimate:  {metrics.sharpe_estimate:.2f}")
    lines.append(f"  Profit Factor:    {metrics.profit_factor:.2f}")
    lines.append(f"  Max Drawdown (R): {metrics.max_drawdown_r:.2f}")

    return lines


def format_json_output(result: BacktestResult) -> str:
    """
    Format backtest result as JSON.

    Serializes BacktestResult to JSON format with:
    - ISO 8601 UTC timestamps
    - NaN/Infinity handling (converted to null)
    - Pretty-printed formatting

    Args:
        result: BacktestResult to format.

    Returns:
        JSON string.

    Examples:
        >>> json_str = format_json_output(backtest_result)
        >>> data = json.loads(json_str)
        >>> data['run_id']
        'test_run_001'
    """
    # Convert to dict (dataclasses.asdict would work but we need custom handling)
    data = {
        "run_id": result.run_id,
        "direction_mode": result.direction_mode,
        "start_time": result.start_time.isoformat(),
        "end_time": result.end_time.isoformat(),
        "data_start_date": result.data_start_date.isoformat(),
        "data_end_date": result.data_end_date.isoformat(),
        "total_candles": result.total_candles,
        "dry_run": result.dry_run,
    }

    # Add metrics if available
    if result.metrics is not None:
        if hasattr(result.metrics, "combined"):
            # DirectionalMetrics
            data["metrics"] = {
                "long_only": (
                    _metrics_to_dict(result.metrics.long_only)
                    if result.metrics.long_only
                    else None
                ),
                "short_only": (
                    _metrics_to_dict(result.metrics.short_only)
                    if result.metrics.short_only
                    else None
                ),
                "combined": (
                    _metrics_to_dict(result.metrics.combined)
                    if result.metrics.combined
                    else None
                ),
            }
        else:
            # Regular MetricsSummary
            data["metrics"] = _metrics_to_dict(result.metrics)
    else:
        data["metrics"] = None

    # Add conflicts
    data["conflicts"] = [
        {
            "timestamp_utc": c.timestamp_utc.isoformat(),
            "pair": c.pair,
            "long_signal_id": c.long_signal_id,
            "short_signal_id": c.short_signal_id,
        }
        for c in result.conflicts
    ]

    # Add signals and executions if available
    data["signals"] = (
        [_signal_to_dict(s) for s in result.signals] if result.signals else None
    )
    data["executions"] = (
        [_execution_to_dict(e) for e in result.executions]
        if result.executions
        else None
    )

    return json.dumps(data, indent=2)


def _metrics_to_dict(metrics) -> dict:
    """Convert MetricsSummary to dict with NaN handling."""
    import math

    def clean_value(val):
        """Convert NaN/Inf to None for JSON serialization."""
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return val

    return {
        "trade_count": metrics.trade_count,
        "win_count": metrics.win_count,
        "loss_count": metrics.loss_count,
        "win_rate": clean_value(metrics.win_rate),
        "avg_win_r": clean_value(metrics.avg_win_r),
        "avg_loss_r": clean_value(metrics.avg_loss_r),
        "avg_r": clean_value(metrics.avg_r),
        "expectancy": clean_value(metrics.expectancy),
        "sharpe_estimate": clean_value(metrics.sharpe_estimate),
        "profit_factor": clean_value(metrics.profit_factor),
        "max_drawdown_r": clean_value(metrics.max_drawdown_r),
        "latency_p95_ms": clean_value(metrics.latency_p95_ms),
        "latency_mean_ms": clean_value(metrics.latency_mean_ms),
    }


def _signal_to_dict(signal) -> dict:
    """Convert TradeSignal to dict."""
    return {
        "id": signal.id,
        "timestamp_utc": signal.timestamp_utc.isoformat(),
        "pair": signal.pair,
        "direction": signal.direction,
        "entry_price": signal.entry_price,
        "initial_stop_price": signal.initial_stop_price,
        "risk_per_trade_pct": signal.risk_per_trade_pct,
        "calc_position_size": signal.calc_position_size,
        "tags": signal.tags,
        "version": signal.version,
    }


def _execution_to_dict(execution) -> dict:
    """Convert TradeExecution to dict."""
    return {
        "signal_id": execution.signal_id,
        "open_timestamp": execution.open_timestamp.isoformat(),
        "entry_fill_price": execution.entry_fill_price,
        "close_timestamp": execution.close_timestamp.isoformat(),
        "exit_fill_price": execution.exit_fill_price,
        "exit_reason": execution.exit_reason,
        "pnl_r": execution.pnl_r,
        "slippage_entry_pips": execution.slippage_entry_pips,
        "slippage_exit_pips": execution.slippage_exit_pips,
        "costs_total": execution.costs_total,
        "direction": execution.direction,
    }


def format_split_mode_text(result: SplitModeResult) -> str:
    """
    Format split-mode backtest result as human-readable text.

    Produces a structured text report showing test and validation metrics
    side-by-side for reproducible evaluation.

    Args:
        result: Split-mode backtest result containing test/validation metrics.

    Returns:
        Formatted text string.

    Implementation: T030
    """
    lines = [
        "=" * 80,
        "SPLIT-MODE BACKTEST RESULTS",
        "=" * 80,
        "",
        "RUN METADATA",
        "-" * 80,
        f"Run ID:         {result.run_id}",
        f"Symbol:         {result.symbol}",
        f"Direction:      {result.direction_mode}",
        f"Start Time:     {result.start_time.isoformat()}",
        f"End Time:       {result.end_time.isoformat()}",
        f"Duration:       {(result.end_time - result.start_time).total_seconds():.2f}s",
        "",
        "=" * 80,
        "TEST PARTITION METRICS",
        "=" * 80,
        "",
    ]

    # Format test partition metrics
    test_metrics = result.test_partition.metrics
    lines.extend(_format_metrics_section(test_metrics))

    lines.extend(
        [
            "",
            "=" * 80,
            "VALIDATION PARTITION METRICS",
            "=" * 80,
            "",
        ]
    )

    # Format validation partition metrics
    val_metrics = result.validation_partition.metrics
    lines.extend(_format_metrics_section(val_metrics))

    lines.append("=" * 80)

    return "\n".join(lines)


def _format_metrics_section(metrics) -> list[str]:
    """Helper to format a MetricsSummary or DirectionalMetrics section."""
    from src.models.directional import DirectionalMetrics
    from src.models.core import MetricsSummary

    if isinstance(metrics, DirectionalMetrics):
        # Directional metrics (BOTH mode)
        lines = [
            "COMBINED METRICS",
            "-" * 80,
        ]
        lines.extend(_format_single_metrics(metrics.combined))
        lines.extend(
            [
                "",
                "LONG-ONLY METRICS",
                "-" * 80,
            ]
        )
        lines.extend(_format_single_metrics(metrics.long_only))
        lines.extend(
            [
                "",
                "SHORT-ONLY METRICS",
                "-" * 80,
            ]
        )
        lines.extend(_format_single_metrics(metrics.short_only))
    elif isinstance(metrics, MetricsSummary):
        lines = _format_single_metrics(metrics)
    else:
        lines = [f"Unknown metrics type: {type(metrics)}"]

    return lines


def _format_single_metrics(metrics) -> list[str]:
    """Helper to format a single MetricsSummary."""
    return [
        f"Total Trades:   {metrics.trade_count}",
        f"Win Rate:       {metrics.win_rate:.2%} \
            ({metrics.win_count}W / {metrics.loss_count}L)",
        f"Average R:      {metrics.avg_r:.2f}",
        f"Expectancy:     {metrics.expectancy:.2f}",
        f"Sharpe Est:     {metrics.sharpe_estimate:.2f}",
        f"Profit Factor:  {metrics.profit_factor:.2f}",
        f"Max Drawdown:   {metrics.max_drawdown_r:.2f}R",
    ]


def format_split_mode_json(result: SplitModeResult) -> str:
    """
    Format split-mode backtest result as JSON.

    Produces machine-readable JSON output with test and validation metrics.

    Args:
        result: Split-mode backtest result containing test/validation metrics.

    Returns:
        JSON string.

    Implementation: T030
    """
    from src.models.directional import DirectionalMetrics

    def serialize_metrics(metrics):
        """Serialize MetricsSummary or DirectionalMetrics to dict."""
        if isinstance(metrics, DirectionalMetrics):
            return {
                "type": "DirectionalMetrics",
                "long_only": _serialize_single_metrics(metrics.long_only),
                "short_only": _serialize_single_metrics(metrics.short_only),
                "combined": _serialize_single_metrics(metrics.combined),
            }
        else:
            return _serialize_single_metrics(metrics)

    output = {
        "run_id": result.run_id,
        "symbol": result.symbol,
        "direction_mode": result.direction_mode,
        "start_time": result.start_time.isoformat(),
        "end_time": result.end_time.isoformat(),
        "test_partition": {
            "partition": result.test_partition.partition,
            "metrics": serialize_metrics(result.test_partition.metrics),
        },
        "validation_partition": {
            "partition": result.validation_partition.partition,
            "metrics": serialize_metrics(result.validation_partition.metrics),
        },
    }

    return json.dumps(output, indent=2)


def _serialize_single_metrics(metrics) -> dict:
    """Helper to serialize a single MetricsSummary to dict."""
    return {
        "trade_count": metrics.trade_count,
        "win_count": metrics.win_count,
        "loss_count": metrics.loss_count,
        "win_rate": metrics.win_rate,
        "avg_win_r": metrics.avg_win_r,
        "avg_loss_r": metrics.avg_loss_r,
        "avg_r": metrics.avg_r,
        "expectancy": metrics.expectancy,
        "sharpe_estimate": metrics.sharpe_estimate,
        "profit_factor": metrics.profit_factor,
        "max_drawdown_r": metrics.max_drawdown_r,
        "latency_p95_ms": metrics.latency_p95_ms,
        "latency_mean_ms": metrics.latency_mean_ms,
    }


def format_multi_symbol_text_output(multi_result) -> str:
    """Format multi-symbol independent backtest results as text.

    Shows full per-symbol metrics (identical to single-symbol runs) plus
    aggregate portfolio summary.

    Args:
        multi_result: Object with attributes: run_id, direction_mode, start_time,
                     symbols, results (dict[str, BacktestResult]), failures

    Returns:
        Formatted text string
    """
    from ..backtest.portfolio.results import MultiSymbolResultsAggregator

    lines = []
    lines.append("=" * 80)
    lines.append("MULTI-SYMBOL PORTFOLIO BACKTEST RESULTS")
    lines.append("=" * 80)
    lines.append("")

    # Run metadata
    lines.append("RUN METADATA")
    lines.append("-" * 80)
    lines.append(f"Run ID:           {multi_result.run_id}")
    lines.append(f"Direction Mode:   {multi_result.direction_mode}")
    lines.append(f"Symbols:          {', '.join(multi_result.symbols)}")
    # Timeframe line (FR-015)
    if hasattr(multi_result, "timeframe") and multi_result.timeframe:
        lines.append(f"Timeframe:        {multi_result.timeframe}")
    lines.append(f"Start Time:       {multi_result.start_time.isoformat()}")
    lines.append("Portfolio Capital: $2,500.00 (shared across all symbols)")
    lines.append("")

    # Aggregate portfolio summary
    aggregator = MultiSymbolResultsAggregator(multi_result.results)
    summary = aggregator.get_aggregate_summary()

    lines.append("AGGREGATE PORTFOLIO SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Total Symbols:    {summary['total_symbols']}")
    lines.append(f"Total Trades:     {summary['total_trades']}")
    lines.append(f"Avg Win Rate:     {summary['average_win_rate']:.2%}")
    lines.append(f"Portfolio P&L:    ${summary['total_pnl']:.2f}")
    lines.append("")

    # Full per-symbol metrics (same format as single-symbol runs)
    lines.append("=" * 80)
    lines.append("PER-SYMBOL DETAILED METRICS")
    lines.append("=" * 80)

    for symbol in sorted(multi_result.symbols):
        if symbol in multi_result.results:
            result = multi_result.results[symbol]
            lines.append("")
            lines.append("=" * 80)
            lines.append(f"SYMBOL: {symbol}")
            lines.append("=" * 80)
            lines.append("")

            # Data range for this symbol
            lines.append("DATA RANGE")
            lines.append("-" * 80)
            lines.append(f"Start Date:       {result.data_start_date.isoformat()}")
            lines.append(f"End Date:         {result.data_end_date.isoformat()}")
            lines.append(f"Total Candles:    {result.total_candles}")
            lines.append("")

            # Full metrics for this symbol
            if result.metrics is not None:
                lines.append("PERFORMANCE METRICS")
                lines.append("-" * 80)

                # Check if directional metrics (BOTH mode)
                if hasattr(result.metrics, "combined"):
                    # DirectionalMetrics
                    if result.metrics.long_only is not None:
                        lines.append("LONG-ONLY METRICS:")
                        lines.extend(_format_metrics_summary(result.metrics.long_only))
                        lines.append("")

                    if result.metrics.short_only is not None:
                        lines.append("SHORT-ONLY METRICS:")
                        lines.extend(_format_metrics_summary(result.metrics.short_only))
                        lines.append("")

                    if result.metrics.combined is not None:
                        lines.append("COMBINED METRICS:")
                        lines.extend(_format_metrics_summary(result.metrics.combined))
                        lines.append("")
                else:
                    # Regular MetricsSummary
                    lines.extend(_format_metrics_summary(result.metrics))
                    lines.append("")
            else:
                lines.append("PERFORMANCE METRICS")
                lines.append("-" * 80)
                lines.append("(No metrics available)")
                lines.append("")

    # Failures summary
    if multi_result.failures:
        lines.append("")
        lines.append("=" * 80)
        lines.append("FAILURES")
        lines.append("=" * 80)
        for failure in multi_result.failures:
            if isinstance(failure, dict):
                lines.append(
                    f"  {failure.get('pair', 'Unknown')}: {failure.get('error', 'Unknown error')}"
                )
            else:
                lines.append(f"  {failure}")
        lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)


def format_multi_symbol_json_output(multi_result) -> str:
    """Format multi-symbol independent backtest results as JSON.

    Args:
        multi_result: Object with attributes: run_id, direction_mode, start_time,
                     symbols, results, failures

    Returns:
        JSON string
    """
    from ..backtest.portfolio.results import MultiSymbolResultsAggregator

    aggregator = MultiSymbolResultsAggregator(multi_result.results)
    summary = aggregator.get_aggregate_summary()
    per_symbol = aggregator.get_per_symbol_summary()

    data = {
        "run_id": multi_result.run_id,
        "direction_mode": str(multi_result.direction_mode),
        "start_time": multi_result.start_time.isoformat(),
        "symbols": multi_result.symbols,
        "mode": "independent",
        "summary": {
            "total_symbols": summary["total_symbols"],
            "total_trades": summary["total_trades"],
            "average_win_rate": summary["average_win_rate"],
            "total_pnl": summary["total_pnl"],
        },
        "per_symbol": per_symbol,
        "failures": multi_result.failures,
    }

    return json.dumps(data, indent=2)


def format_portfolio_text_output(result) -> str:
    """Format portfolio-mode backtest results as human-readable text.

    Shows full aggregate metrics (same as per-symbol) plus equity curve and
    per-symbol breakdown.

    Args:
        result: PortfolioResult from PortfolioSimulator

    Returns:
        Formatted text string
    """
    lines = []
    lines.append("=" * 80)
    lines.append("PORTFOLIO MODE BACKTEST RESULTS")
    lines.append("=" * 80)
    lines.append("")

    # Run metadata
    lines.append("RUN METADATA")
    lines.append("-" * 80)
    lines.append(f"Run ID:           {result.run_id}")
    lines.append(f"Direction Mode:   {result.direction_mode}")
    lines.append(f"Symbols:          {', '.join(result.symbols)}")
    # Timeframe line (T014)
    if hasattr(result, "timeframe") and result.timeframe:
        lines.append(f"Timeframe:        {result.timeframe}")
    lines.append(f"Start Time:       {result.start_time.isoformat()}")
    lines.append(f"End Time:         {result.end_time.isoformat()}")
    duration = (result.end_time - result.start_time).total_seconds()
    lines.append(f"Duration:         {duration:.2f} seconds")
    lines.append("")

    # Data range
    lines.append("DATA RANGE")
    lines.append("-" * 80)
    if result.data_start_date:
        lines.append(f"Start Date:       {result.data_start_date.isoformat()}")
    if result.data_end_date:
        lines.append(f"End Date:         {result.data_end_date.isoformat()}")
    lines.append("")

    # Portfolio summary
    lines.append("PORTFOLIO SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Starting Equity:  ${result.starting_equity:,.2f}")
    lines.append(f"Final Equity:     ${result.final_equity:,.2f}")
    pnl_pct = (result.final_equity / result.starting_equity - 1) * 100
    lines.append(f"Portfolio P&L:    ${result.total_pnl:,.2f} ({pnl_pct:+.2f}%)")
    lines.append("Position Sizing:  0.25% of current equity per trade")
    lines.append("")

    # Aggregate performance metrics (full metrics like single-symbol)
    lines.append("AGGREGATE PERFORMANCE METRICS")
    lines.append("-" * 80)

    # Calculate aggregate metrics from closed trades
    trades = result.closed_trades
    total_trades = len(trades)
    wins = [t for t in trades if t.pnl_r > 0]
    losses = [t for t in trades if t.pnl_r <= 0]
    win_count = len(wins)
    loss_count = len(losses)

    lines.append(f"  Trades:           {total_trades}")
    lines.append(f"  Wins:             {win_count}")
    lines.append(f"  Losses:           {loss_count}")

    if total_trades > 0:
        win_rate = win_count / total_trades
        total_r = sum(t.pnl_r for t in trades)
        avg_r = total_r / total_trades

        avg_win_r = sum(t.pnl_r for t in wins) / win_count if wins else 0.0
        avg_loss_r = sum(t.pnl_r for t in losses) / loss_count if losses else 0.0

        # Expectancy
        expectancy = avg_r

        # Profit factor
        gross_wins = sum(t.pnl_r for t in wins) if wins else 0.0
        gross_losses = abs(sum(t.pnl_r for t in losses)) if losses else 0.001
        profit_factor = gross_wins / gross_losses if gross_losses > 0 else 0.0

        # Max drawdown from equity curve
        max_equity = result.starting_equity
        max_drawdown = 0.0
        for ts, equity in result.equity_curve:
            if equity > max_equity:
                max_equity = equity
            drawdown = (max_equity - equity) / max_equity if max_equity > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        lines.append(f"  Win Rate:         {win_rate:.2%}")
        lines.append(f"  Avg Win (R):      {avg_win_r:.2f}")
        lines.append(f"  Avg Loss (R):     {avg_loss_r:.2f}")
        lines.append(f"  Avg R:            {avg_r:.2f}")
        lines.append(f"  Expectancy (R):   {expectancy:.2f}")
        lines.append(f"  Profit Factor:    {profit_factor:.2f}")
        lines.append(f"  Max Drawdown:     {max_drawdown:.2%}")
    lines.append("")

    # Per-symbol breakdown
    lines.append("=" * 80)
    lines.append("PER-SYMBOL BREAKDOWN")
    lines.append("=" * 80)

    for symbol, stats in sorted(result.per_symbol_trades.items()):
        lines.append("")
        lines.append(f"SYMBOL: {symbol}")
        lines.append("-" * 80)
        lines.append(f"  Trades:         {stats['trade_count']}")
        lines.append(f"  Wins:           {stats['win_count']}")
        lines.append(f"  Losses:         {stats['loss_count']}")
        if stats["trade_count"] > 0:
            lines.append(f"  Win Rate:       {stats['win_rate']:.2%}")
            lines.append(f"  Avg R:          {stats['avg_r']:.2f}")
        lines.append(f"  Total P&L:      ${stats['total_pnl']:.2f}")

    lines.append("")
    lines.append("=" * 80)

    return "\n".join(lines)


def format_portfolio_json_output(result) -> str:
    """Format portfolio-mode backtest results as JSON.

    Args:
        result: PortfolioResult from PortfolioSimulator

    Returns:
        JSON string
    """

    # Calculate aggregate metrics from closed trades
    trades = result.closed_trades
    total_trades = len(trades)
    wins = [t for t in trades if t.pnl_r > 0]
    losses = [t for t in trades if t.pnl_r <= 0]
    win_count = len(wins)
    loss_count = len(losses)

    metrics = {
        "trade_count": total_trades,
        "win_count": win_count,
        "loss_count": loss_count,
    }

    if total_trades > 0:
        win_rate = win_count / total_trades
        total_r = sum(t.pnl_r for t in trades)
        avg_r = total_r / total_trades
        avg_win_r = sum(t.pnl_r for t in wins) / win_count if wins else 0.0
        avg_loss_r = sum(t.pnl_r for t in losses) / loss_count if losses else 0.0
        gross_wins = sum(t.pnl_r for t in wins) if wins else 0.0
        gross_losses = abs(sum(t.pnl_r for t in losses)) if losses else 0.001
        profit_factor = gross_wins / gross_losses if gross_losses > 0 else 0.0

        # Max drawdown from equity curve
        max_equity = result.starting_equity
        max_drawdown = 0.0
        for ts, equity in result.equity_curve:
            if equity > max_equity:
                max_equity = equity
            drawdown = (max_equity - equity) / max_equity if max_equity > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        metrics.update(
            {
                "win_rate": win_rate,
                "avg_win_r": avg_win_r,
                "avg_loss_r": avg_loss_r,
                "avg_r": avg_r,
                "expectancy": avg_r,
                "profit_factor": profit_factor,
                "max_drawdown": max_drawdown,
            }
        )
    else:
        metrics.update(
            {
                "win_rate": 0.0,
                "avg_win_r": 0.0,
                "avg_loss_r": 0.0,
                "avg_r": 0.0,
                "expectancy": 0.0,
                "profit_factor": 0.0,
                "max_drawdown": 0.0,
            }
        )

    data = {
        "run_id": result.run_id,
        "direction_mode": result.direction_mode,
        "mode": "portfolio",
        "start_time": result.start_time.isoformat(),
        "end_time": result.end_time.isoformat(),
        "data_start_date": (
            result.data_start_date.isoformat() if result.data_start_date else None
        ),
        "data_end_date": (
            result.data_end_date.isoformat() if result.data_end_date else None
        ),
        "symbols": result.symbols,
        "portfolio": {
            "starting_equity": result.starting_equity,
            "final_equity": result.final_equity,
            "total_pnl": result.total_pnl,
            "total_pnl_pct": (
                (result.final_equity / result.starting_equity - 1) * 100
                if result.starting_equity > 0
                else 0.0
            ),
        },
        "metrics": metrics,
        "per_symbol": result.per_symbol_trades,
        "equity_curve": [
            {"timestamp": ts.isoformat(), "equity": equity}
            for ts, equity in result.equity_curve
        ],
    }

    return json.dumps(data, indent=2)
