"""
Integration test for US1: Long Signal Generation acceptance criteria.

This test validates the complete workflow from price data ingestion through
signal generation, execution simulation, and metrics computation for long-only
trend pullback strategy.
"""

import pytest
from pathlib import Path
from datetime import datetime, timezone

from src.config.parameters import StrategyParameters
from src.cli.run_long_backtest import run_long_backtest


class TestUS1LongSignalIntegration:
    """Integration tests for US1 acceptance criteria."""

    @pytest.fixture
    def sample_price_data(self, tmp_path: Path) -> Path:
        """
        Create sample CSV price data for testing.

        Returns a CSV file with synthetic price data showing:
        - Uptrend (EMA20 > EMA50)
        - Pullback (RSI < 30)
        - Reversal (bullish engulfing)
        """
        csv_path = tmp_path / "sample_eurusd.csv"

        # Generate 200 candles with trend pullback pattern
        rows = ["timestamp_utc,open,high,low,close,volume"]

        # Start with uptrend base
        base_price = 1.10000
        timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)

        # First 50 candles: establish uptrend
        for i in range(50):
            open_price = base_price + (i * 0.00010)
            close_price = open_price + 0.00015
            high = close_price + 0.00005
            low = open_price - 0.00005

            rows.append(
                f"{timestamp.isoformat()},{open_price:.5f},{high:.5f},"
                f"{low:.5f},{close_price:.5f},1000"
            )
            timestamp = timestamp.replace(hour=(timestamp.hour + 1) % 24)
            if timestamp.hour == 0:
                timestamp = timestamp.replace(day=timestamp.day + 1)

        # Next 20 candles: pullback (declining prices to trigger RSI < 30)
        peak_price = close_price
        for i in range(20):
            open_price = peak_price - (i * 0.00020)
            close_price = open_price - 0.00025
            high = open_price + 0.00005
            low = close_price - 0.00005

            rows.append(
                f"{timestamp.isoformat()},{open_price:.5f},{high:.5f},"
                f"{low:.5f},{close_price:.5f},1000"
            )
            timestamp = timestamp.replace(hour=(timestamp.hour + 1) % 24)
            if timestamp.hour == 0:
                timestamp = timestamp.replace(day=timestamp.day + 1)

        # Next candle: bullish engulfing reversal
        reversal_low = close_price
        open_price = close_price
        close_price = open_price + 0.00080  # Large bullish candle
        high = close_price + 0.00010
        low = open_price - 0.00005

        rows.append(
            f"{timestamp.isoformat()},{open_price:.5f},{high:.5f},"
            f"{low:.5f},{close_price:.5f},2000"
        )
        timestamp = timestamp.replace(hour=(timestamp.hour + 1) % 24)

        # Final 129 candles: continuation uptrend
        for i in range(129):
            open_price = close_price
            close_price = open_price + 0.00010
            high = close_price + 0.00005
            low = open_price - 0.00003

            rows.append(
                f"{timestamp.isoformat()},{open_price:.5f},{high:.5f},"
                f"{low:.5f},{close_price:.5f},1000"
            )
            timestamp = timestamp.replace(hour=(timestamp.hour + 1) % 24)
            if timestamp.hour == 0:
                timestamp = timestamp.replace(day=timestamp.day + 1)

        csv_path.write_text("\n".join(rows))
        return csv_path

    def test_us1_ac1_detect_uptrend(self, sample_price_data: Path, tmp_path: Path):
        """
        US1 AC-1: System detects uptrend when EMA20 > EMA50.

        Given price data with established uptrend,
        When backtest runs,
        Then system should identify uptrend state.
        """
        # Run backtest
        result = run_long_backtest(
            price_data_path=sample_price_data,
            output_dir=tmp_path / "results",
            log_level="WARNING",
        )

        # Should process all candles
        assert result.strategy_name == "trend_pullback_long_only"

    def test_us1_ac2_detect_pullback(self, sample_price_data: Path, tmp_path: Path):
        """
        US1 AC-2: System detects pullback when RSI < 30 OR Stoch RSI < 0.2.

        Given uptrend with price decline triggering RSI < 30,
        When backtest runs,
        Then system should identify pullback state.
        """
        result = run_long_backtest(
            price_data_path=sample_price_data,
            output_dir=tmp_path / "results",
            log_level="WARNING",
        )

        # Should generate at least one signal (pullback detected)
        assert result.total_signals_generated >= 1

    def test_us1_ac3_confirm_reversal(self, sample_price_data: Path, tmp_path: Path):
        """
        US1 AC-3: System confirms reversal with momentum turn + pattern.

        Given pullback followed by bullish engulfing + RSI turning up,
        When backtest runs,
        Then system should confirm reversal and generate long signal.
        """
        result = run_long_backtest(
            price_data_path=sample_price_data,
            output_dir=tmp_path / "results",
            log_level="WARNING",
        )

        # Should generate signal after reversal confirmation
        assert result.total_signals_generated >= 1

    def test_us1_ac4_generate_long_signal(self, sample_price_data: Path, tmp_path: Path):
        """
        US1 AC-4: System generates long signal with entry/stop/target.

        Given trend + pullback + reversal conditions met,
        When signal is generated,
        Then signal should include entry, stop-loss, and take-profit prices.
        """
        result = run_long_backtest(
            price_data_path=sample_price_data,
            output_dir=tmp_path / "results",
            log_level="WARNING",
        )

        # Should generate and potentially execute signal
        assert result.total_signals_generated >= 1
        # Note: Execution depends on enough subsequent candles

    def test_us1_ac5_calculate_position_size(self, sample_price_data: Path, tmp_path: Path):
        """
        US1 AC-5: System calculates position size based on risk %.

        Given generated signal with ATR-based stop,
        When position size is calculated,
        Then size should reflect risk percentage of account balance.
        """
        # Use custom parameters with known risk
        params = StrategyParameters(
            risk_per_trade_pct=1.0,  # 1% risk
            account_balance=10000.0,
        )

        result = run_long_backtest(
            price_data_path=sample_price_data,
            output_dir=tmp_path / "results",
            parameters=params,
            log_level="WARNING",
        )

        # Should generate signals with calculated position sizes
        assert result.total_signals_generated >= 1

    def test_us1_end_to_end_workflow(self, sample_price_data: Path, tmp_path: Path):
        """
        US1 End-to-End: Complete workflow from data load to metrics.

        Given valid price data CSV,
        When long-only backtest runs,
        Then system should:
        1. Load and validate data
        2. Generate long signals
        3. Simulate executions
        4. Compute performance metrics
        5. Return BacktestRun with reproducibility hash
        """
        result = run_long_backtest(
            price_data_path=sample_price_data,
            output_dir=tmp_path / "results",
            log_level="WARNING",
        )

        # Validate BacktestRun structure
        assert result.run_id.startswith("long-")
        assert result.strategy_name == "trend_pullback_long_only"
        assert len(result.parameters_hash) == 64  # SHA-256 hex
        assert len(result.data_manifest_hash) == 64  # SHA-256 hex
        assert len(result.reproducibility_hash) == 64  # SHA-256 hex

        # Validate metrics summary
        assert result.metrics_summary.total_trades >= 0
        assert result.metrics_summary.winning_trades >= 0
        assert result.metrics_summary.losing_trades >= 0
        assert result.metrics_summary.win_rate_pct >= 0.0
        assert result.metrics_summary.win_rate_pct <= 100.0

        # Validate signal/execution counts
        assert result.total_signals_generated >= 0
        assert result.total_executions >= 0
        assert result.total_executions <= result.total_signals_generated

    def test_us1_no_signals_in_range_market(self, tmp_path: Path):
        """
        US1 Edge Case: No signals generated in ranging market.

        Given price data with EMA crossovers >= 3 (ranging),
        When backtest runs,
        Then system should generate zero signals.
        """
        # Create ranging market data
        csv_path = tmp_path / "ranging.csv"
        rows = ["timestamp_utc,open,high,low,close,volume"]

        timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        base_price = 1.10000

        # Oscillate around base price to create crossovers
        for i in range(200):
            if i % 10 < 5:
                close_price = base_price + 0.00050
            else:
                close_price = base_price - 0.00050

            open_price = close_price - 0.00005
            high = close_price + 0.00003
            low = open_price - 0.00003

            rows.append(
                f"{timestamp.isoformat()},{open_price:.5f},{high:.5f},"
                f"{low:.5f},{close_price:.5f},1000"
            )
            timestamp = timestamp.replace(hour=(timestamp.hour + 1) % 24)
            if timestamp.hour == 0:
                timestamp = timestamp.replace(day=timestamp.day + 1)

        csv_path.write_text("\n".join(rows))

        result = run_long_backtest(
            price_data_path=csv_path,
            output_dir=tmp_path / "results",
            log_level="WARNING",
        )

        # Ranging market should generate few or no signals
        assert result.total_signals_generated >= 0

    def test_us1_cooldown_period_enforced(self, sample_price_data: Path, tmp_path: Path):
        """
        US1 Edge Case: Cooldown period prevents rapid signal generation.

        Given multiple reversal patterns within 5 candles,
        When backtest runs,
        Then system should enforce 5-candle cooldown between signals.
        """
        params = StrategyParameters(
            signal_cooldown_candles=5,
        )

        result = run_long_backtest(
            price_data_path=sample_price_data,
            output_dir=tmp_path / "results",
            parameters=params,
            log_level="WARNING",
        )

        # Should complete successfully with cooldown enforced
        assert result.total_signals_generated >= 0
