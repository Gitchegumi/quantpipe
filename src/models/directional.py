"""
Data models for directional backtesting system.

This module extends core.py with directional-specific models for
conflict tracking, directional metrics, backtest results, and
partition-aware metrics for split-mode evaluation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from .core import MetricsSummary, TradeSignal


PartitionType = Literal["test", "validation"]


@dataclass(frozen=True)
class ConflictEvent:
    """
    Records a rejected signal due to conflict in BOTH mode.

    When both long and short signals occur at the same timestamp in BOTH mode,
    both signals are rejected (choppy market indicator). This model tracks
    these rejections for observability and debugging.

    Attributes:
        timestamp_utc: Time when conflicting signals were detected.
        pair: Currency pair experiencing conflict.
        long_signal_id: ID of rejected long signal.
        short_signal_id: ID of rejected short signal.

    Examples:
        >>> from datetime import datetime, timezone
        >>> conflict = ConflictEvent(
        ...     timestamp_utc=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        ...     pair="EURUSD",
        ...     long_signal_id="abc123def456",
        ...     short_signal_id="def456ghi789"
        ... )
        >>> conflict.pair
        'EURUSD'
    """

    timestamp_utc: datetime
    pair: str
    long_signal_id: str
    short_signal_id: str


@dataclass(frozen=True)
class DirectionalMetrics:
    """
    Aggregated metrics split by direction for BOTH mode backtests.

    Provides separate performance views for long-only and short-only trades
    within a BOTH mode backtest, plus combined metrics across all trades.

    Attributes:
        long_only: Metrics summary for long trades only.
        short_only: Metrics summary for short trades only.
        combined: Metrics summary for all trades (long + short aggregated).

    Examples:
        >>> from src.models.core import MetricsSummary
        >>> long_metrics = MetricsSummary(
        ...     trade_count=10,
        ...     win_rate=0.60,
        ...     avg_r=1.5,
        ...     sharpe_estimate=1.2,
        ...     max_drawdown_r=3.0,
        ...     max_drawdown_pct=0.06
        ... )
        >>> short_metrics = MetricsSummary(
        ...     trade_count=8,
        ...     win_rate=0.50,
        ...     avg_r=1.2,
        ...     sharpe_estimate=0.9,
        ...     max_drawdown_r=2.5,
        ...     max_drawdown_pct=0.05
        ... )
        >>> combined_metrics = MetricsSummary(
        ...     trade_count=18,
        ...     win_rate=0.556,
        ...     avg_r=1.367,
        ...     sharpe_estimate=1.05,
        ...     max_drawdown_r=3.0,
        ...     max_drawdown_pct=0.06
        ... )
        >>> dir_metrics = DirectionalMetrics(
        ...     long_only=long_metrics,
        ...     short_only=short_metrics,
        ...     combined=combined_metrics
        ... )
        >>> dir_metrics.combined.trade_count
        18
    """

    long_only: MetricsSummary
    short_only: MetricsSummary
    combined: MetricsSummary


@dataclass(frozen=True)
class PartitionMetrics:
    """
    Performance metrics annotated with partition type.

    Wraps MetricsSummary or DirectionalMetrics with partition identifier
    to distinguish test vs validation results in split-mode backtesting.

    Attributes:
        partition: Partition type ('test' or 'validation').
        metrics: Performance metrics for this partition.

    Examples:
        >>> test_metrics = MetricsSummary(
        ...     trade_count=100,
        ...     win_rate=0.55,
        ...     avg_r=1.2,
        ...     sharpe_estimate=1.1,
        ...     max_drawdown_r=5.0,
        ...     max_drawdown_pct=0.10
        ... )
        >>> partition_result = PartitionMetrics(
        ...     partition='test',
        ...     metrics=test_metrics
        ... )
        >>> partition_result.partition
        'test'
        >>> partition_result.metrics.trade_count
        100

    Implementation: T030
    """

    partition: PartitionType
    metrics: MetricsSummary | DirectionalMetrics


@dataclass(frozen=True)
class SplitModeResult:
    """
    Complete backtest result for split-mode execution.

    Contains separate results for test and validation partitions, enabling
    reproducible evaluation with distinct training/validation phases.

    Attributes:
        run_id: Unique identifier for this split-mode backtest run.
        symbol: Symbol identifier (e.g., 'eurusd').
        direction_mode: Direction mode used (LONG, SHORT, or BOTH).
        start_time: Backtest start timestamp (UTC).
        end_time: Backtest completion timestamp (UTC).
        test_partition: Test partition metrics and metadata.
        validation_partition: Validation partition metrics and metadata.

    Examples:
        >>> from datetime import datetime, timezone
        >>> from src.models.enums import DirectionMode
        >>> test_result = PartitionMetrics(
        ...     partition='test',
        ...     metrics=test_metrics
        ... )
        >>> val_result = PartitionMetrics(
        ...     partition='validation',
        ...     metrics=val_metrics
        ... )
        >>> split_result = SplitModeResult(
        ...     run_id="20250130_split_LONG_eurusd",
        ...     symbol="eurusd",
        ...     direction_mode=DirectionMode.LONG,
        ...     start_time=datetime(2025, 1, 30, 10, 0, tzinfo=timezone.utc),
        ...     end_time=datetime(2025, 1, 30, 10, 5, tzinfo=timezone.utc),
        ...     test_partition=test_result,
        ...     validation_partition=val_result
        ... )
        >>> split_result.test_partition.partition
        'test'

    Implementation: T030
    """

    run_id: str
    symbol: str
    direction_mode: str  # DirectionMode value (stored as string for JSON)
    start_time: datetime
    end_time: datetime
    test_partition: PartitionMetrics
    validation_partition: PartitionMetrics


@dataclass(frozen=True)
class BacktestResult:
    """
    Complete backtest execution result with metadata and metrics.

    Encapsulates all backtest outputs including run metadata, performance metrics,
    optional signal/execution lists, and conflict events (BOTH mode only).

    Attributes:
        run_id: Unique identifier for this backtest run.
        direction_mode: Direction mode used (LONG, SHORT, or BOTH).
        start_time: Backtest start timestamp (UTC).
        end_time: Backtest completion timestamp (UTC).
        data_start_date: First candle timestamp in dataset (UTC).
        data_end_date: Last candle timestamp in dataset (UTC).
        total_candles: Number of candles processed.
        metrics: Performance metrics \
            (MetricsSummary for LONG/SHORT, DirectionalMetrics for BOTH).
        signals: Optional list of all generated signals (None in dry-run mode).
        executions: Optional list of all completed trades (None in dry-run mode).
        conflicts: List of conflict events (BOTH mode only; empty for LONG/SHORT).
        dry_run: Whether this was a dry-run (signals only, no execution).

    Examples:
        >>> from datetime import datetime, timezone
        >>> from src.models.enums import DirectionMode
        >>> result = BacktestResult(
        ...     run_id="20250129_120000_LONG",
        ...     direction_mode=DirectionMode.LONG,
        ...     start_time=datetime(2025, 1, 29, 12, 0, 0, tzinfo=timezone.utc),
        ...     end_time=datetime(2025, 1, 29, 12, 5, 30, tzinfo=timezone.utc),
        ...     data_start_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
        ...     data_end_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
        ...     total_candles=100000,
        ...     metrics=long_metrics,
        ...     signals=None,
        ...     executions=None,
        ...     conflicts=[],
        ...     dry_run=False
        ... )
        >>> result.direction_mode
        <DirectionMode.LONG: 'LONG'>
    """

    run_id: str
    direction_mode: str  # DirectionMode value (stored as string for JSON serialization)
    start_time: datetime
    end_time: datetime
    data_start_date: datetime
    data_end_date: datetime
    total_candles: int
    metrics: MetricsSummary | DirectionalMetrics
    signals: list[TradeSignal] | None = None
    executions: list | None = None  # TradeExecution list (avoid circular import)
    conflicts: list[ConflictEvent] = field(default_factory=list)
    dry_run: bool = False
