"""
Unit tests for BacktestOrchestrator and signal merging logic.

Tests orchestrator initialization, direction mode routing, conflict detection,
and signal merging in BOTH mode.
"""

from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.unit

from src.backtest.orchestrator import BacktestOrchestrator, merge_signals
from src.models.core import Candle, TradeSignal
from src.models.enums import DirectionMode


class TestBacktestOrchestratorInit:
    """Test cases for BacktestOrchestrator initialization."""

    def test_orchestrator_init_long_mode(self):
        """Verify orchestrator initializes correctly in LONG mode."""
        orchestrator = BacktestOrchestrator(
            direction_mode=DirectionMode.LONG, dry_run=False
        )

        assert orchestrator.direction_mode == DirectionMode.LONG
        assert orchestrator.dry_run is False

    def test_orchestrator_init_short_mode(self):
        """Verify orchestrator initializes correctly in SHORT mode."""
        orchestrator = BacktestOrchestrator(
            direction_mode=DirectionMode.SHORT, dry_run=True
        )

        assert orchestrator.direction_mode == DirectionMode.SHORT
        assert orchestrator.dry_run is True

    def test_orchestrator_init_both_mode(self):
        """Verify orchestrator initializes correctly in BOTH mode."""
        orchestrator = BacktestOrchestrator(
            direction_mode=DirectionMode.BOTH, dry_run=False
        )

        assert orchestrator.direction_mode == DirectionMode.BOTH
        assert orchestrator.dry_run is False


class TestMergeSignals:
    """Test cases for merge_signals conflict detection logic."""

    @pytest.fixture()
    def sample_long_signal(self):
        """Provide sample long signal for testing."""
        return TradeSignal(
            id="long_001",
            timestamp_utc=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0990,
            risk_per_trade_pct=0.01,
            calc_position_size=0.1,
            tags=["uptrend", "pullback"],
            version="1.0",
        )

    @pytest.fixture()
    def sample_short_signal(self):
        """Provide sample short signal for testing."""
        return TradeSignal(
            id="short_001",
            timestamp_utc=datetime(2025, 1, 1, 14, 0, 0, tzinfo=UTC),
            pair="EURUSD",
            direction="SHORT",
            entry_price=1.0950,
            initial_stop_price=1.0960,
            risk_per_trade_pct=0.01,
            calc_position_size=0.1,
            tags=["downtrend", "pullback"],
            version="1.0",
        )

    def test_merge_signals_no_conflicts(self, sample_long_signal, sample_short_signal):
        """Verify signals merge chronologically when no conflicts exist."""
        merged, conflicts = merge_signals(
            long_signals=[sample_long_signal],
            short_signals=[sample_short_signal],
            pair="EURUSD",
        )

        assert len(merged) == 2
        assert len(conflicts) == 0
        assert merged[0].direction == "LONG"  # Earlier timestamp
        assert merged[1].direction == "SHORT"  # Later timestamp

    def test_merge_signals_with_conflict(self):
        """Verify conflicting signals are rejected (same timestamp)."""
        conflict_ts = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        long_sig = TradeSignal(
            id="long_conflict",
            timestamp_utc=conflict_ts,
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0990,
            risk_per_trade_pct=0.01,
            calc_position_size=0.1,
            tags=[],
            version="1.0",
        )
        short_sig = TradeSignal(
            id="short_conflict",
            timestamp_utc=conflict_ts,
            pair="EURUSD",
            direction="SHORT",
            entry_price=1.0950,
            initial_stop_price=1.0960,
            risk_per_trade_pct=0.01,
            calc_position_size=0.1,
            tags=[],
            version="1.0",
        )

        merged, conflicts = merge_signals(
            long_signals=[long_sig], short_signals=[short_sig], pair="EURUSD"
        )

        assert len(merged) == 0  # Both signals rejected
        assert len(conflicts) == 1
        assert conflicts[0].timestamp_utc == conflict_ts
        assert conflicts[0].pair == "EURUSD"
        assert conflicts[0].long_signal_id == "long_conflict"
        assert conflicts[0].short_signal_id == "short_conflict"

    def test_merge_signals_multiple_with_partial_conflicts(self):
        """Verify merge handles mix of conflicting and non-conflicting signals."""
        ts1 = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        ts2 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)  # Conflict
        ts3 = datetime(2025, 1, 1, 14, 0, 0, tzinfo=UTC)

        long_signals = [
            TradeSignal(
                id="long_1",
                timestamp_utc=ts1,
                pair="EURUSD",
                direction="LONG",
                entry_price=1.1000,
                initial_stop_price=1.0990,
                risk_per_trade_pct=0.01,
                calc_position_size=0.1,
                tags=[],
                version="1.0",
            ),
            TradeSignal(
                id="long_2",
                timestamp_utc=ts2,
                pair="EURUSD",
                direction="LONG",
                entry_price=1.1010,
                initial_stop_price=1.1000,
                risk_per_trade_pct=0.01,
                calc_position_size=0.1,
                tags=[],
                version="1.0",
            ),
        ]
        short_signals = [
            TradeSignal(
                id="short_2",
                timestamp_utc=ts2,
                pair="EURUSD",
                direction="SHORT",
                entry_price=1.0950,
                initial_stop_price=1.0960,
                risk_per_trade_pct=0.01,
                calc_position_size=0.1,
                tags=[],
                version="1.0",
            ),
            TradeSignal(
                id="short_3",
                timestamp_utc=ts3,
                pair="EURUSD",
                direction="SHORT",
                entry_price=1.0940,
                initial_stop_price=1.0950,
                risk_per_trade_pct=0.01,
                calc_position_size=0.1,
                tags=[],
                version="1.0",
            ),
        ]

        merged, conflicts = merge_signals(
            long_signals=long_signals, short_signals=short_signals, pair="EURUSD"
        )

        assert len(merged) == 2  # long_1 and short_3 (non-conflicting)
        assert len(conflicts) == 1  # ts2 conflict
        assert merged[0].id == "long_1"
        assert merged[1].id == "short_3"
        assert conflicts[0].timestamp_utc == ts2

    def test_merge_signals_empty_inputs(self):
        """Verify merge handles empty signal lists gracefully."""
        merged, conflicts = merge_signals(
            long_signals=[], short_signals=[], pair="EURUSD"
        )

        assert len(merged) == 0
        assert len(conflicts) == 0

    def test_merge_signals_only_long(self, sample_long_signal):
        """Verify merge with only long signals (no short signals)."""
        merged, conflicts = merge_signals(
            long_signals=[sample_long_signal], short_signals=[], pair="EURUSD"
        )

        assert len(merged) == 1
        assert len(conflicts) == 0
        assert merged[0].direction == "LONG"

    def test_merge_signals_only_short(self, sample_short_signal):
        """Verify merge with only short signals (no long signals)."""
        merged, conflicts = merge_signals(
            long_signals=[], short_signals=[sample_short_signal], pair="EURUSD"
        )

        assert len(merged) == 1
        assert len(conflicts) == 0
        assert merged[0].direction == "SHORT"

    def test_conflict_event_structure(self):
        """T055: Verify ConflictEvent contains timestamp and pair when logged."""
        conflict_ts = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        long_sig = TradeSignal(
            id="long_test",
            timestamp_utc=conflict_ts,
            pair="GBPUSD",
            direction="LONG",
            entry_price=1.2500,
            initial_stop_price=1.2490,
            risk_per_trade_pct=0.01,
            calc_position_size=0.1,
            tags=[],
            version="1.0",
        )
        short_sig = TradeSignal(
            id="short_test",
            timestamp_utc=conflict_ts,
            pair="GBPUSD",
            direction="SHORT",
            entry_price=1.2480,
            initial_stop_price=1.2490,
            risk_per_trade_pct=0.01,
            calc_position_size=0.1,
            tags=[],
            version="1.0",
        )

        _, conflicts = merge_signals(
            long_signals=[long_sig], short_signals=[short_sig], pair="GBPUSD"
        )

        # Verify ConflictEvent structure
        assert len(conflicts) == 1
        conflict = conflicts[0]
        assert hasattr(conflict, "timestamp_utc")
        assert hasattr(conflict, "pair")
        assert hasattr(conflict, "long_signal_id")
        assert hasattr(conflict, "short_signal_id")
        assert conflict.timestamp_utc == conflict_ts
        assert conflict.pair == "GBPUSD"
        assert conflict.long_signal_id == "long_test"
        assert conflict.short_signal_id == "short_test"

    def test_timestamp_first_wins_logic(self):
        """T056: Verify earlier timestamp executes when signals have different timestamps."""
        ts_early = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        ts_late = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Earlier LONG signal
        long_early = TradeSignal(
            id="long_early",
            timestamp_utc=ts_early,
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0990,
            risk_per_trade_pct=0.01,
            calc_position_size=0.1,
            tags=[],
            version="1.0",
        )
        # Later SHORT signal
        short_late = TradeSignal(
            id="short_late",
            timestamp_utc=ts_late,
            pair="EURUSD",
            direction="SHORT",
            entry_price=1.0950,
            initial_stop_price=1.0960,
            risk_per_trade_pct=0.01,
            calc_position_size=0.1,
            tags=[],
            version="1.0",
        )

        merged, conflicts = merge_signals(
            long_signals=[long_early], short_signals=[short_late], pair="EURUSD"
        )

        # Both signals should merge (different timestamps = no conflict)
        assert len(merged) == 2
        assert len(conflicts) == 0
        # Verify chronological order: earlier signal first
        assert merged[0].id == "long_early"
        assert merged[0].timestamp_utc == ts_early
        assert merged[1].id == "short_late"
        assert merged[1].timestamp_utc == ts_late

        # Test reverse order (later LONG, earlier SHORT)
        short_early = TradeSignal(
            id="short_early",
            timestamp_utc=ts_early,
            pair="EURUSD",
            direction="SHORT",
            entry_price=1.0950,
            initial_stop_price=1.0960,
            risk_per_trade_pct=0.01,
            calc_position_size=0.1,
            tags=[],
            version="1.0",
        )
        long_late = TradeSignal(
            id="long_late",
            timestamp_utc=ts_late,
            pair="EURUSD",
            direction="LONG",
            entry_price=1.1000,
            initial_stop_price=1.0990,
            risk_per_trade_pct=0.01,
            calc_position_size=0.1,
            tags=[],
            version="1.0",
        )

        merged, conflicts = merge_signals(
            long_signals=[long_late], short_signals=[short_early], pair="EURUSD"
        )

        assert len(merged) == 2
        assert len(conflicts) == 0
        # SHORT executes first (earlier timestamp)
        assert merged[0].id == "short_early"
        assert merged[0].timestamp_utc == ts_early
        assert merged[1].id == "long_late"
        assert merged[1].timestamp_utc == ts_late


class TestBacktestOrchestratorRunBacktest:
    """Test cases for BacktestOrchestrator.run_backtest method."""

    @pytest.fixture()
    def sample_candles(self):
        """Provide sample candle sequence for testing."""
        return [
            Candle(
                timestamp_utc=datetime(2025, 1, 1, i, 0, 0, tzinfo=UTC),
                open=1.1000 + i * 0.0001,
                high=1.1010 + i * 0.0001,
                low=1.0990 + i * 0.0001,
                close=1.1005 + i * 0.0001,
                volume=1000.0,
                ema20=1.1000,
                ema50=1.0995,
                atr=0.0015,
                rsi=55.0,
            )
            for i in range(10)
        ]

    def test_run_backtest_empty_candles_raises_error(self):
        """Verify run_backtest raises ValueError for empty candles."""
        orchestrator = BacktestOrchestrator(
            direction_mode=DirectionMode.LONG, dry_run=False
        )

        with pytest.raises(ValueError, match="Candles sequence cannot be empty"):
            orchestrator.run_backtest(candles=[], pair="EURUSD", run_id="test_run")

    def test_run_backtest_long_mode_returns_result(self, sample_candles):
        """Verify run_backtest executes LONG mode and returns BacktestResult."""
        orchestrator = BacktestOrchestrator(
            direction_mode=DirectionMode.LONG, dry_run=True
        )

        result = orchestrator.run_backtest(
            candles=sample_candles,
            pair="EURUSD",
            run_id="test_run_long",
            cooldown_candles=5,
        )

        assert result.run_id == "test_run_long"
        assert result.direction_mode == "LONG"
        assert result.total_candles == 10
        assert result.dry_run is True
        assert result.data_start_date == sample_candles[0].timestamp_utc
        assert result.data_end_date == sample_candles[-1].timestamp_utc
        assert len(result.conflicts) == 0

    def test_run_backtest_short_mode_returns_result(self, sample_candles):
        """Verify run_backtest executes SHORT mode and returns BacktestResult."""
        orchestrator = BacktestOrchestrator(
            direction_mode=DirectionMode.SHORT, dry_run=False
        )

        result = orchestrator.run_backtest(
            candles=sample_candles, pair="USDJPY", run_id="test_run_short"
        )

        assert result.run_id == "test_run_short"
        assert result.direction_mode == "SHORT"
        assert result.total_candles == 10
        assert result.dry_run is False

    def test_run_backtest_both_mode_returns_result(self, sample_candles):
        """Verify run_backtest executes BOTH mode with conflict detection."""
        orchestrator = BacktestOrchestrator(
            direction_mode=DirectionMode.BOTH, dry_run=True
        )

        result = orchestrator.run_backtest(
            candles=sample_candles, pair="GBPUSD", run_id="test_run_both"
        )

        assert result.run_id == "test_run_both"
        assert result.direction_mode == "BOTH"
        assert result.total_candles == 10
        assert result.dry_run is True
        # Conflicts list exists (may be empty depending on signal generation)
        assert isinstance(result.conflicts, list)
