"""Protocol interface definitions for Trend Pullback Continuation Strategy.

These are preliminary contracts; implementation modules will depend on these
protocols to enable loose coupling and straightforward testing/mocking.
"""
from __future__ import annotations
from typing import Protocol, Iterable, Optional, Sequence, Dict, Any
from dataclasses import dataclass
from datetime import datetime

# --- Data Classes (minimal skeletons matching data-model.md) --- #

@dataclass(frozen=True)
class Candle:
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
    state: str  # 'UP' | 'DOWN' | 'RANGE'
    cross_count: int
    last_change_timestamp: datetime

@dataclass(frozen=True)
class PullbackState:
    active: bool
    direction: str  # 'LONG' | 'SHORT'
    start_timestamp: datetime
    qualifying_candle_ids: Sequence[str]
    oscillator_extreme_flag: bool

@dataclass(frozen=True)
class TradeSignal:
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
    signal_id: str
    open_timestamp: datetime
    entry_fill_price: float
    close_timestamp: datetime
    exit_fill_price: float
    exit_reason: str  # 'TARGET' | 'TRAILING_STOP' | 'STOP_LOSS' | 'EXPIRY'
    pnl_R: float
    slippage_entry_pips: float
    slippage_exit_pips: float
    costs_total: float

@dataclass(frozen=True)
class MetricsSummary:
    trade_count: int
    win_rate: float
    avg_R: float
    expectancy: float
    sharpe_estimate: float
    max_drawdown_R: float
    latency_p95_ms: float
    latency_mean_ms: float
    drawdown_curve: Sequence[float]
    slippage_stats: Dict[str, float]

# --- Protocol Definitions --- #

class CandleIngestion(Protocol):
    def stream(self, pair: str, timeframe: str) -> Iterable[Candle]:
        """Yield candles with monotonically increasing timestamps.
        Should raise DataIntegrityError on gap > threshold."""
        ...

class TrendClassifier(Protocol):
    def update(self, candle: Candle) -> TrendState:
        """Update internal state with the latest candle and return current TrendState."""
        ...

class PullbackDetector(Protocol):
    def update(self, candle: Candle, trend: TrendState) -> Optional[PullbackState]:
        """Assess for new or ongoing pullback context; expire when invalid."""
        ...

class SignalGenerator(Protocol):
    def generate(self, candle: Candle, trend: TrendState, pullback: Optional[PullbackState]) -> Optional[TradeSignal]:
        """Return a deterministic TradeSignal if reversal + filters satisfied."""
        ...

class RiskManager(Protocol):
    def size(self, signal: TradeSignal, account_equity: float) -> TradeSignal:
        """Augment signal with position size and validated stop; enforce risk limits."""
        ...

class ExecutionSimulator(Protocol):
    def execute(self, signal: TradeSignal, candle: Candle) -> TradeExecution:
        """Simulate fill and manage lifecycle until exit; apply slippage & costs."""
        ...

class MetricsAggregator(Protocol):
    def ingest(self, execution: TradeExecution) -> None:
        """Accumulate performance and latency metrics per execution."""
        ...

    def finalize(self) -> MetricsSummary:
        """Produce immutable summary statistics and curves."""
        ...

class ReproducibilityService(Protocol):
    def hash_run(self, parameters: Dict[str, Any], manifest: Dict[str, Any], metrics: MetricsSummary) -> str:
        """Return combined SHA256-derived reproducibility hash."""
        ...

    def verify(self, run_hash: str, parameters: Dict[str, Any], manifest: Dict[str, Any], metrics: MetricsSummary) -> bool:
        """Validate that current inputs produce the same hash."""
        ...

class ObservabilityReporter(Protocol):
    def emit(self, metrics: MetricsSummary, extra: Dict[str, Any]) -> None:
        """Publish structured metrics/log event; non-blocking best-effort."""
        ...

# --- Potential Custom Exceptions (stubs) --- #
class DataIntegrityError(Exception):
    pass

class RiskLimitError(Exception):
    pass

class ExecutionSimulationError(Exception):
    pass

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
