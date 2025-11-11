"""
Core data models for the trading strategy.

This module defines immutable dataclasses that represent the fundamental
entities used throughout the trading system: candles, states, signals,
executions, and backtest metadata.

All dataclasses are frozen to ensure immutability and thread-safety,
supporting deterministic backtest reproducibility per Constitution Principle VI.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Candle:
    """
    Represents a single OHLCV candle with computed technical indicators.

    The Candle model uses a flexible indicators dictionary to support arbitrary
    technical indicators rather than hardcoded fields. This enables strategies
    to use any indicators they need without modifying the core data model.

    Attributes:
        timestamp_utc: Candle close time in UTC timezone.
        open: Opening price for the period.
        high: Highest price during the period.
        low: Lowest price during the period.
        close: Closing price for the period.
        volume: Trading volume during the period.
        indicators: Dictionary mapping indicator names to values
            (e.g., {"ema20": 1.1000}).
        is_gap: True if this candle was synthetically created to fill a
            timestamp gap.

    Examples:
        >>> from datetime import datetime, timezone
        >>> candle = Candle(
        ...     timestamp_utc=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        ...     open=1.1000,
        ...     high=1.1010,
        ...     low=1.0990,
        ...     close=1.1005,
        ...     volume=1000.0,
        ...     indicators={
        ...         "ema20": 1.1000,
        ...         "ema50": 1.0995,
        ...         "atr14": 0.0015,
        ...         "stoch_rsi": 55.0
        ...     }
        ... )
        >>> candle.close
        1.1005
        >>> candle.indicators["ema20"]
        1.1000
    """

    timestamp_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    indicators: dict[str, float] = field(default_factory=dict)
    is_gap: bool = False

    @classmethod
    def from_legacy(
        cls,
        timestamp_utc: datetime,
        open: float,  # pylint: disable=redefined-builtin
        high: float,
        low: float,
        close: float,
        volume: float,
        ema20: float | None = None,
        ema50: float | None = None,
        atr: float | None = None,
        rsi: float | None = None,
        stoch_rsi: float | None = None,
        is_gap: bool = False,
    ) -> "Candle":
        """Create Candle using legacy field names (backward compatibility).

        This factory method allows legacy code to continue using the old
        constructor signature with named indicator parameters.

        Args:
            timestamp_utc: Candle close time in UTC.
            open: Opening price.
            high: Highest price.
            low: Lowest price.
            close: Closing price.
            volume: Trading volume.
            ema20: 20-period EMA value.
            ema50: 50-period EMA value.
            atr: ATR indicator value (stored as atr14).
            rsi: RSI value (stored as rsi).
            stoch_rsi: Stochastic RSI value.
            is_gap: Whether this is a synthetic gap-fill candle.

        Returns:
            Candle instance with indicators dict populated.
        """
        indicators_dict = {}
        if ema20 is not None:
            indicators_dict["ema20"] = ema20
        if ema50 is not None:
            indicators_dict["ema50"] = ema50
        if atr is not None:
            indicators_dict["atr14"] = atr
        if rsi is not None:
            indicators_dict["rsi"] = rsi
        if stoch_rsi is not None:
            indicators_dict["stoch_rsi"] = stoch_rsi

        return cls(
            timestamp_utc=timestamp_utc,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
            indicators=indicators_dict,
            is_gap=is_gap,
        )

    # Backward compatibility properties for legacy code
    @property
    def ema20(self) -> float | None:
        """Backward compatibility: access ema20 from indicators dict."""
        return self.indicators.get("ema20")

    @property
    def ema50(self) -> float | None:
        """Backward compatibility: access ema50 from indicators dict."""
        return self.indicators.get("ema50")

    @property
    def atr(self) -> float | None:
        """Backward compatibility: access atr/atr14 from indicators dict."""
        return self.indicators.get("atr14") or self.indicators.get("atr")

    @property
    def rsi(self) -> float | None:
        """Backward compatibility: access rsi from indicators dict."""
        return self.indicators.get("rsi") or self.indicators.get("stoch_rsi")

    @property
    def stoch_rsi(self) -> float | None:
        """Backward compatibility: access stoch_rsi from indicators dict."""
        return self.indicators.get("stoch_rsi")


@dataclass(frozen=True)
class TrendState:
    """
    Represents the current trend classification state.

    Attributes:
        state: Current trend direction - 'UP', 'DOWN', or 'RANGE'.
        cross_count: Number of EMA crossovers within lookback window.
        last_change_timestamp: UTC timestamp of most recent trend state change.

    Examples:
        >>> from datetime import datetime, timezone
        >>> trend = TrendState(
        ...     state='UP',
        ...     cross_count=1,
        ...     last_change_timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc)
        ... )
        >>> trend.state
        'UP'
    """

    state: str  # Literal['UP', 'DOWN', 'RANGE']
    cross_count: int
    last_change_timestamp: datetime


@dataclass(frozen=True)
class PullbackState:
    """
    Represents an active pullback condition within a trend.

    Attributes:
        active: Whether a pullback is currently active.
        direction: Expected signal direction - 'LONG' or 'SHORT'.
        start_timestamp: UTC timestamp when pullback state was initiated.
        qualifying_candle_ids: Sequence of candle identifiers that satisfy
            pullback criteria.
        oscillator_extreme_flag: True if momentum oscillator reached extreme
            threshold (oversold for longs, overbought for shorts).

    Examples:
        >>> from datetime import datetime, timezone
        >>> pullback = PullbackState(
        ...     active=True,
        ...     direction='LONG',
        ...     start_timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ...     qualifying_candle_ids=['abc123', 'def456'],
        ...     oscillator_extreme_flag=True
        ... )
        >>> pullback.active
        True
    """

    active: bool
    direction: str  # Literal['LONG', 'SHORT']
    start_timestamp: datetime
    qualifying_candle_ids: Sequence[str] = field(default_factory=list)
    oscillator_extreme_flag: bool = False


@dataclass(frozen=True)
class TradeSignal:
    """
    Represents a validated trade signal ready for execution.

    The signal ID is deterministically generated from signal attributes
    to ensure reproducibility across backtest runs.

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

    Examples:
        >>> from datetime import datetime, timezone
        >>> signal = TradeSignal(
        ...     id='a1b2c3d4e5f6g7h8',
        ...     pair='EURUSD',
        ...     direction='LONG',
        ...     entry_price=1.1000,
        ...     initial_stop_price=1.0980,
        ...     risk_per_trade_pct=0.25,
        ...     calc_position_size=10000.0,
        ...     tags=['trend', 'pullback', 'reversal'],
        ...     version='v0.1.0',
        ...     timestamp_utc=datetime(2025, 1, 1, tzinfo=timezone.utc)
        ... )
        >>> signal.direction
        'LONG'
    """

    id: str
    pair: str
    direction: str  # Literal['LONG', 'SHORT']
    entry_price: float
    initial_stop_price: float
    risk_per_trade_pct: float
    calc_position_size: float
    tags: Sequence[str]
    version: str
    timestamp_utc: datetime


@dataclass(frozen=True)
class TradeExecution:
    """
    Represents a completed trade execution with performance metrics.

    Attributes:
        signal_id: Reference to the originating TradeSignal.id.
        direction: Trade direction - 'LONG' or 'SHORT'.
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

    Examples:
        >>> from datetime import datetime, timezone
        >>> execution = TradeExecution(
        ...     signal_id='a1b2c3d4e5f6g7h8',
        ...     direction='LONG',
        ...     open_timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        ...     entry_fill_price=1.1002,
        ...     close_timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
        ...     exit_fill_price=1.1042,
        ...     exit_reason='TARGET',
        ...     pnl_r=2.0,
        ...     slippage_entry_pips=0.2,
        ...     slippage_exit_pips=0.3,
        ...     costs_total=2.0
        ... )
        >>> execution.pnl_r
        2.0
    """

    signal_id: str
    open_timestamp: datetime
    entry_fill_price: float
    close_timestamp: datetime
    exit_fill_price: float
    exit_reason: str  # Literal['TARGET', 'TRAILING_STOP', 'STOP_LOSS', 'EXPIRY']
    pnl_r: float
    slippage_entry_pips: float
    slippage_exit_pips: float
    costs_total: float
    direction: str = ""  # Literal['LONG', 'SHORT'], empty for backward compatibility


@dataclass(frozen=True)
class BacktestRun:
    """
    Metadata and configuration for a backtest execution.

    Attributes:
        run_id: Unique identifier for this backtest run.
        parameters_hash: Hash of strategy parameters used for this run.
        manifest_ref: Reference to the data manifest file path or identifier.
        start_time: UTC timestamp when backtest started.
        end_time: UTC timestamp when backtest completed.
        total_candles_processed: Count of candles processed during backtest.
        reproducibility_hash: Combined hash for full reproducibility verification.

    Examples:
        >>> from datetime import datetime, timezone
        >>> run = BacktestRun(
        ...     run_id='run_20250101_120000',
        ...     parameters_hash='abc123def456',
        ...     manifest_ref='/data/manifests/eurusd_2024.json',
        ...     start_time=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        ...     end_time=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
        ...     total_candles_processed=100000,
        ...     reproducibility_hash='full_hash_xyz'
        ... )
        >>> run.total_candles_processed
        100000
    """

    run_id: str
    parameters_hash: str
    manifest_ref: str
    start_time: datetime
    end_time: datetime
    total_candles_processed: int
    reproducibility_hash: str


@dataclass(frozen=True)
class DataManifest:
    """
    Metadata describing a market data source for provenance tracking.

    Attributes:
        pair: Currency pair symbol (e.g., 'EURUSD').
        timeframe: Candle timeframe (e.g., '1m', '5m', '1h').
        date_range_start: First candle timestamp in the dataset.
        date_range_end: Last candle timestamp in the dataset.
        source_provider: Data provider name (e.g., 'Dukascopy', 'FXCM').
        checksum: SHA-256 hash of the data file for integrity verification.
        preprocessing_notes: Description of any transformations applied.
        total_candles: Total number of candles in the dataset.
        file_path: Relative or absolute path to the data file.

    Examples:
        >>> from datetime import datetime, timezone
        >>> manifest = DataManifest(
        ...     pair='EURUSD',
        ...     timeframe='1m',
        ...     date_range_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ...     date_range_end=datetime(2024, 12, 31, tzinfo=timezone.utc),
        ...     source_provider='Dukascopy',
        ...     checksum='abc123def456...',
        ...     preprocessing_notes='UTC normalization, deduplication applied',
        ...     total_candles=525600,
        ...     file_path='/data/raw/eurusd_1m_2024.csv'
        ... )
        >>> manifest.pair
        'EURUSD'
    """

    pair: str
    timeframe: str
    date_range_start: datetime
    date_range_end: datetime
    source_provider: str
    checksum: str
    preprocessing_notes: str
    total_candles: int
    file_path: str


@dataclass(frozen=True)
class MetricsSummary:
    """
    Aggregated performance metrics for a backtest run.

    Attributes:
        trade_count: Total number of executed trades.
        win_count: Number of profitable trades.
        loss_count: Number of losing trades.
        win_rate: Percentage of profitable trades (0.0 to 1.0).
        avg_win_r: Average profit on winning trades in R-multiples.
        avg_loss_r: Average loss on losing trades in R-multiples.
        avg_r: Average profit/loss across all trades in R-multiples.
        expectancy: Mathematical expectancy (avg_win * win_rate -
            avg_loss * loss_rate).
        sharpe_estimate: Estimated Sharpe ratio.
        profit_factor: Ratio of gross profits to gross losses.
        max_drawdown_r: Maximum drawdown measured in R-multiples.
        latency_p95_ms: 95th percentile processing latency in milliseconds.
        latency_mean_ms: Mean processing latency in milliseconds.

    Examples:
        >>> metrics = MetricsSummary(
        ...     trade_count=100,
        ...     win_count=60,
        ...     loss_count=40,
        ...     win_rate=0.60,
        ...     avg_win_r=2.5,
        ...     avg_loss_r=1.0,
        ...     avg_r=0.9,
        ...     expectancy=0.8,
        ...     sharpe_estimate=1.5,
        ...     profit_factor=2.4,
        ...     max_drawdown_r=5.0,
        ...     latency_p95_ms=3.2,
        ...     latency_mean_ms=1.8
        ... )
        >>> metrics.win_rate
        0.6
    """

    trade_count: int
    win_count: int
    loss_count: int
    win_rate: float
    avg_win_r: float
    avg_loss_r: float
    avg_r: float
    expectancy: float
    sharpe_estimate: float
    profit_factor: float
    max_drawdown_r: float
    latency_p95_ms: float
    latency_mean_ms: float
