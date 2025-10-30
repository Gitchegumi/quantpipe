"""Protocol interface definitions for Trend Pullback Continuation Strategy.

This module defines the core data structures and protocol interfaces for the
trend pullback continuation trading strategy. It establishes contracts between
components to enable loose coupling, straightforward testing, and mocking.

The module follows a layered architecture:
- Data classes (immutable): Candle, TrendState, PullbackState, TradeSignal,
  TradeExecution, MetricsSummary
- Protocol interfaces: CandleIngestion, TrendClassifier, PullbackDetector,
  SignalGenerator, RiskManager, ExecutionSimulator, MetricsAggregator,
  ReproducibilityService, ObservabilityReporter
- Custom exceptions: DataIntegrityError, RiskLimitError,
  ExecutionSimulationError

All implementations of these protocols MUST maintain determinism for
reproducibility requirements per Constitution Principle VI.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, Optional, Protocol, Sequence


@dataclass(frozen=True)
class Candle:
    """Represents a single OHLCV candle with computed technical indicators.

    Attributes:
        timestamp_utc: Candle close time in UTC timezone.
        open: Opening price for the period.
        high: Highest price during the period.
        low: Lowest price during the period.
        close: Closing price for the period.
        volume: Trading volume during the period.
        ema20: 20-period exponential moving average at candle close.
        ema50: 50-period exponential moving average at candle close.
        atr: Average True Range indicator value.
        rsi: Relative Strength Index (14-period default).
        stoch_rsi: Optional Stochastic RSI value for additional confirmation.
    """

    timestamp_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    ema20: float
    ema50: float
    atr: float
    rsi: float
    stoch_rsi: Optional[float] = None


@dataclass(frozen=True)
class TrendState:
    """Represents the current trend classification state.

    Attributes:
        state: Current trend direction - 'UP', 'DOWN', or 'RANGE'.
        cross_count: Number of EMA crossovers within lookback window.
        last_change_timestamp: UTC timestamp of most recent trend state change.
    """

    state: str  # 'UP' | 'DOWN' | 'RANGE'
    cross_count: int
    last_change_timestamp: datetime


@dataclass(frozen=True)
class PullbackState:
    """Represents an active pullback condition within a trend.

    Attributes:
        active: Whether a pullback is currently active.
        direction: Expected signal direction - 'LONG' or 'SHORT'.
        start_timestamp: UTC timestamp when pullback state was initiated.
        qualifying_candle_ids: Sequence of candle identifiers that satisfy
            pullback criteria.
        oscillator_extreme_flag: True if momentum oscillator reached extreme
            threshold (oversold for longs, overbought for shorts).
    """

    active: bool
    direction: str  # 'LONG' | 'SHORT'
    start_timestamp: datetime
    qualifying_candle_ids: Sequence[str]
    oscillator_extreme_flag: bool


@dataclass(frozen=True)
class TradeSignal:
    """Represents a validated trade signal ready for execution.

    Attributes:
        id: Deterministic lowercase hex hash (SHA-256 truncated to 16 chars)
            derived from timestamp_utc|pair|direction|entry_price|version.
        pair: Currency pair symbol (e.g., 'EURUSD').
        direction: Trade direction - 'LONG' or 'SHORT'.
        entry_price: Proposed entry price level.
        initial_stop_price: Initial stop-loss price level.
        risk_per_trade_pct: Risk allocation as percentage of account equity.
        calc_position_size: Calculated position size in lots/units.
        tags: Sequence of string tags for signal classification and filtering.
        version: Strategy version identifier for reproducibility.
        timestamp_utc: Signal generation timestamp in UTC.
    """

    id: str
    pair: str
    direction: str  # 'LONG' | 'SHORT'
    entry_price: float
    initial_stop_price: float
    risk_per_trade_pct: float
    calc_position_size: float
    tags: Sequence[str]
    version: str
    timestamp_utc: datetime


@dataclass(frozen=True)
class TradeExecution:
    """Represents a completed trade execution with performance metrics.

    Attributes:
        signal_id: Reference to the originating TradeSignal.id.
        open_timestamp: UTC timestamp of trade entry.
        entry_fill_price: Actual entry fill price including slippage.
        close_timestamp: UTC timestamp of trade exit.
        exit_fill_price: Actual exit fill price including slippage.
        exit_reason: Exit trigger - 'TARGET', 'TRAILING_STOP', 'STOP_LOSS',
            or 'EXPIRY'.
        pnl_r: Profit/loss measured in R-multiples (risk units).
        slippage_entry_pips: Entry slippage in pips.
        slippage_exit_pips: Exit slippage in pips.
        costs_total: Total transaction costs (spread + commission).
    """

    signal_id: str
    open_timestamp: datetime
    entry_fill_price: float
    close_timestamp: datetime
    exit_fill_price: float
    exit_reason: str  # 'TARGET' | 'TRAILING_STOP' | 'STOP_LOSS' | 'EXPIRY'
    pnl_r: float
    slippage_entry_pips: float
    slippage_exit_pips: float
    costs_total: float


@dataclass(frozen=True)
class MetricsSummary:
    """Aggregated performance metrics for a backtest run.

    Attributes:
        trade_count: Total number of executed trades.
        win_rate: Percentage of profitable trades (0.0 to 1.0).
        avg_r: Average profit/loss in R-multiples.
        expectancy: Mathematical expectancy (avg_win * win_rate -
            avg_loss * loss_rate).
        sharpe_estimate: Estimated Sharpe ratio.
        max_drawdown_r: Maximum drawdown measured in R-multiples.
        latency_p95_ms: 95th percentile processing latency in milliseconds.
        latency_mean_ms: Mean processing latency in milliseconds.
        drawdown_curve: Sequence of drawdown values over time for visualization.
        slippage_stats: Dictionary containing slippage statistics
            (mean, median, p95, etc.).
    """

    trade_count: int
    win_rate: float
    avg_r: float
    expectancy: float
    sharpe_estimate: float
    max_drawdown_r: float
    latency_p95_ms: float
    latency_mean_ms: float
    drawdown_curve: Sequence[float]
    slippage_stats: Dict[str, float]


class CandleIngestion(Protocol):
    """Protocol for streaming market data candles.

    Implementations provide sequential access to OHLCV candles with
    pre-computed technical indicators, ensuring data integrity and
    monotonic timestamp ordering.
    """

    def stream(self, pair: str, timeframe: str) -> Iterable[Candle]:
        """Yield candles with monotonically increasing timestamps.

        Args:
            pair: Currency pair symbol (e.g., 'EURUSD').
            timeframe: Candle timeframe (e.g., '1m', '5m', '1h', '1d').

        Yields:
            Candle objects in chronological order with all indicators computed.

        Raises:
            DataIntegrityError: When timestamp gap exceeds threshold or data
                validation fails.
        """
        ...


class TrendClassifier(Protocol):
    """Protocol for classifying market trend state based on EMA analysis.

    Implementations maintain internal state to track EMA crossovers and
    determine whether the market is in an uptrend, downtrend, or range.
    """

    def update(self, candle: Candle) -> TrendState:
        """Update internal state with the latest candle and return trend.

        Args:
            candle: Latest market candle with computed EMAs.

        Returns:
            Current TrendState reflecting market direction and EMA cross count.
        """
        ...


class PullbackDetector(Protocol):
    """Protocol for detecting pullback conditions within established trends.

    Implementations assess price proximity to EMAs combined with oscillator
    extremes to identify potential reversal opportunities.
    """

    def update(self, candle: Candle, trend: TrendState) -> Optional[PullbackState]:
        """Assess for new or ongoing pullback context.

        Args:
            candle: Latest market candle with indicators.
            trend: Current trend classification state.

        Returns:
            PullbackState if pullback criteria met, None otherwise.
            Expired pullback states return None.
        """
        ...


class SignalGenerator(Protocol):
    """Protocol for generating trade signals from confirmed reversal patterns.

    Implementations evaluate candle patterns and momentum confirmation to
    produce deterministic trade signals with reproducible IDs.
    """

    def generate(
        self,
        candle: Candle,
        trend: TrendState,
        pullback: Optional[PullbackState],
    ) -> Optional[TradeSignal]:
        """Return trade signal if reversal and filters satisfied.

        Args:
            candle: Current candle for pattern analysis.
            trend: Current trend state for directional alignment.
            pullback: Active pullback state if present.

        Returns:
            TradeSignal with deterministic ID if all criteria met, None otherwise.
        """
        ...


class RiskManager(Protocol):
    """Protocol for position sizing and risk limit enforcement.

    Implementations calculate position sizes based on account equity and
    risk percentage, validate stop distances, and enforce risk controls.
    """

    def size(self, signal: TradeSignal, account_equity: float) -> TradeSignal:
        """Augment signal with position size and validated stop.

        Args:
            signal: Trade signal requiring position sizing.
            account_equity: Current account equity for risk calculation.

        Returns:
            Updated TradeSignal with calc_position_size populated.

        Raises:
            RiskLimitError: If risk limits would be violated.
        """
        ...


class ExecutionSimulator(Protocol):
    """Protocol for simulating trade execution with realistic market conditions.

    Implementations manage trade lifecycle from entry to exit, applying
    slippage models and transaction costs.
    """

    def execute(self, signal: TradeSignal, candle: Candle) -> TradeExecution:
        """Simulate fill and manage lifecycle until exit.

        Args:
            signal: Trade signal to execute.
            candle: Initial candle for entry simulation.

        Returns:
            TradeExecution record with fill prices, slippage, and P&L.

        Raises:
            ExecutionSimulationError: If simulation encounters invalid state.
        """
        ...


class MetricsAggregator(Protocol):
    """Protocol for accumulating and summarizing backtest performance metrics.

    Implementations collect trade executions and compute statistical measures,
    latency profiles, and drawdown curves.
    """

    def ingest(self, execution: TradeExecution) -> None:
        """Accumulate performance and latency metrics per execution.

        Args:
            execution: Completed trade execution to incorporate into metrics.
        """
        ...

    def finalize(self) -> MetricsSummary:
        """Produce immutable summary statistics and curves.

        Returns:
            MetricsSummary containing all aggregated performance metrics.
        """
        ...


class ReproducibilityService(Protocol):
    """Protocol for generating and verifying reproducibility hashes.

    Implementations create deterministic hashes from backtest parameters,
    data manifests, and results to ensure identical reruns produce identical
    outputs per Constitution Principle VI.
    """

    def hash_run(
        self,
        parameters: Dict[str, Any],
        manifest: Dict[str, Any],
        metrics: MetricsSummary,
    ) -> str:
        """Return combined SHA256-derived reproducibility hash.

        Args:
            parameters: Strategy and backtest configuration parameters.
            manifest: Data manifest with source, checksums, and date ranges.
            metrics: Final backtest metrics summary.

        Returns:
            Lowercase hexadecimal hash string for run identification.
        """
        ...

    def verify(
        self,
        run_hash: str,
        parameters: Dict[str, Any],
        manifest: Dict[str, Any],
        metrics: MetricsSummary,
    ) -> bool:
        """Validate that current inputs produce the same hash.

        Args:
            run_hash: Expected hash from previous run.
            parameters: Current strategy and backtest parameters.
            manifest: Current data manifest.
            metrics: Current backtest metrics.

        Returns:
            True if computed hash matches run_hash, False otherwise.
        """
        ...


class ObservabilityReporter(Protocol):
    """Protocol for emitting structured metrics and log events.

    Implementations publish performance data and operational metrics for
    monitoring, analysis, and alerting. Operations are non-blocking and
    best-effort.
    """

    def emit(self, metrics: MetricsSummary, extra: Dict[str, Any]) -> None:
        """Publish structured metrics/log event.

        Args:
            metrics: Performance metrics to report.
            extra: Additional context (tags, metadata, environment info).

        Note:
            This method operates on a best-effort basis and should not block
            or raise exceptions in normal operation.
        """
        ...


class DataIntegrityError(Exception):
    """Exception raised when data validation or integrity checks fail.

    Examples include timestamp gaps exceeding threshold, missing required fields,
    checksum mismatches, or invalid data ranges.
    """


class RiskLimitError(Exception):
    """Exception raised when risk management limits would be violated.

    Examples include exceeding maximum position size, insufficient account
    equity, or attempting to bypass mandatory risk controls.
    """


class ExecutionSimulationError(Exception):
    """Exception raised during trade execution simulation errors.

    Examples include invalid state transitions, missing required candle data,
    or logical inconsistencies in trade lifecycle management.
    """


__all__ = [
    "Candle",
    "TrendState",
    "PullbackState",
    "TradeSignal",
    "TradeExecution",
    "MetricsSummary",
    "CandleIngestion",
    "TrendClassifier",
    "PullbackDetector",
    "SignalGenerator",
    "RiskManager",
    "ExecutionSimulator",
    "MetricsAggregator",
    "ReproducibilityService",
    "ObservabilityReporter",
    "DataIntegrityError",
    "RiskLimitError",
    "ExecutionSimulationError",
]
