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
    direction: DirectionMode, output_format: OutputFormat, timestamp: datetime
) -> str:
    """
    Generate standardized filename for backtest output.

    Produces filenames in the format:
    backtest_{direction}_{YYYYMMDD}_{HHMMSS}.{ext}

    Args:
        direction: Direction mode of the backtest (LONG/SHORT/BOTH).
        output_format: Output format (TEXT/JSON).
        timestamp: Timestamp to use for filename generation.

    Returns:
        Formatted filename string.

    Examples:
        >>> from datetime import datetime, timezone
        >>> ts = datetime(2025, 1, 15, 14, 30, 45, tzinfo=timezone.utc)
        >>> generate_output_filename(DirectionMode.LONG, OutputFormat.TEXT, ts)
        'backtest_long_20250115_143045.txt'
        >>> generate_output_filename(DirectionMode.BOTH, OutputFormat.JSON, ts)
        'backtest_both_20250115_143045.json'
    """
    direction_str = direction.value.lower()
    date_str = timestamp.strftime("%Y%m%d")
    time_str = timestamp.strftime("%H%M%S")
    ext = "json" if output_format == OutputFormat.JSON else "txt"

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
