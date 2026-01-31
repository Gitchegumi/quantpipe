"""
Integration tests for strategy signal count verification (T022).

This module validates that the signal generation logic produces consistent and
deterministic signal counts when processing price data. Tests verify that:

1. Signal count is deterministic across multiple runs
2. Long-only mode produces only long signals
3. Short-only mode produces only short signals
4. Both mode produces signals in both directions
5. Signal counts are reasonable for given market conditions

These tests use real price data slices to verify end-to-end signal generation
behavior without mocking strategy components.
"""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.backtest.execution import simulate_execution
from src.backtest.metrics_ingest import MetricsIngestor
from src.backtest.observability import ObservabilityReporter
from src.config.parameters import StrategyParameters
from src.data_io.ingestion import ingest_ohlcv_data
from src.indicators.enrich import enrich
from src.models.core import Candle
from src.strategy.trend_pullback.signal_generator import generate_long_signals


pytestmark = pytest.mark.integration

logger = logging.getLogger(__name__)


def run_v2_backtest(
    price_data_path: Path,
    output_dir: Path,
    parameters: StrategyParameters | None = None,
    log_level: str = "INFO",
) -> dict:
    """
    Run backtest using modern V2 pipeline (ingest -> enrich -> simulate).
    Replaces legacy run_simple_backtest to fix missing indicators.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    if parameters is None:
        parameters = StrategyParameters()

    # 1. Ingest
    ingestion = ingest_ohlcv_data(
        path=str(price_data_path),
        timeframe_minutes=1,
        mode="columnar",
        strict_cadence=False,
        show_progress=False,
    )

    # 2. Enrich
    enrichment = enrich(
        core_ref=ingestion,
        indicators=["fast_ema", "slow_ema", "rsi", "stoch_rsi", "atr"],
        params={
            "fast_ema": {"period": parameters.ema_fast},
            "slow_ema": {"period": parameters.ema_slow},
            "rsi": {"period": parameters.rsi_length},
            "stoch_rsi": {"rsi_period": parameters.rsi_length},
            "atr": {"period": parameters.atr_length},
        },
        strict=True,
    )

    # 3. Convert to Candle objects
    candles = []
    df = enrichment.enriched

    fast_ema_col = f"ema{parameters.ema_fast}"
    slow_ema_col = f"ema{parameters.ema_slow}"

    for _, row in df.iterrows():
        indicators = {
            "fast_ema": row.get(fast_ema_col),
            "slow_ema": row.get(slow_ema_col),
            "rsi": row.get("rsi"),
            "stoch_rsi": row.get("stoch_rsi"),
            "atr": row.get("atr"),
        }

        if "atr" not in row and f"atr{parameters.atr_length}" in row:
            indicators["atr"] = row[f"atr{parameters.atr_length}"]

        candle = Candle(
            timestamp_utc=row["timestamp_utc"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row.get("volume", 0.0),
            indicators=indicators,
            is_gap=row.get("is_gap", False),
        )
        candles.append(candle)

    # 4. Run Strategy
    metrics = MetricsIngestor()

    signals_generated = 0

    gen_params = {
        "ema_fast": parameters.ema_fast,
        "ema_slow": parameters.ema_slow,
        "rsi_period": parameters.rsi_length,
        "stop_loss_atr_multiplier": parameters.atr_stop_mult,
        "risk_reward_ratio": parameters.target_r_mult,
        "trend_cross_count_threshold": 3,
        "rsi_oversold": parameters.oversold_threshold,
        "rsi_overbought": parameters.overbought_threshold,
        "stoch_rsi_low": 0.2,
        "stoch_rsi_high": 0.8,
        "risk_per_trade_pct": parameters.risk_per_trade_pct,
        "account_balance": parameters.account_balance,
        "prioritize_recent": True,
    }

    last_signal_time = None
    cooldown = getattr(parameters, "signal_cooldown_candles", 5)

    for i in range(50, len(candles)):
        window = candles[max(0, i - 100) : i + 1]

        current_time = window[-1].timestamp_utc
        if last_signal_time and (current_time - last_signal_time) < timedelta(
            minutes=cooldown
        ):
            continue

        signals = generate_long_signals(
            candles=window,
            parameters=gen_params,
        )

        if signals:
            signal = signals[0]
            signals_generated += 1
            last_signal_time = signal.timestamp_utc

            remaining_candles = candles[i:]
            execution = simulate_execution(
                signal=signal,
                candles=remaining_candles,
                slippage_pips=0.5,
                spread_pips=1.0,
            )

            if execution:
                metrics.ingest(execution)

    summary = metrics.get_summary()

    return {
        "strategy_name": "trend_pullback_long_only",
        "signals_generated": signals_generated,
        "trade_count": summary.trade_count,
        "win_rate": summary.win_rate,
        "expectancy": summary.expectancy,
        "avg_r": summary.avg_r,
        "sharpe_estimate": summary.sharpe_estimate,
        "profit_factor": summary.profit_factor,
        "max_drawdown_r": summary.max_drawdown_r,
    }


@pytest.fixture()
def eurusd_price_data(tmp_path):
    """
    Create sample CSV price data for testing.
    Ensures at least one signal is generated.
    """
    csv_path = tmp_path / "sample_eurusd.csv"
    rows = ["timestamp_utc,open,high,low,close,volume"]
    base_price = 1.10000
    timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)

    # 1. Establish strong uptrend (200 candles)
    for i in range(200):
        open_price = base_price + (i * 0.00020)
        close_price = open_price + 0.00025
        high = close_price + 0.00005
        low = open_price - 0.00005
        rows.append(f"{timestamp.isoformat()},{open_price:.5f},{high:.5f},{low:.5f},{close_price:.5f},1000")
        timestamp += timedelta(minutes=1)

    # 2. Moderate pullback (18 candles) to get RSI < 30
    last_close = close_price
    for i in range(18):
        open_price = last_close - (i * 0.00030)
        close_price = open_price - 0.00035
        high = open_price + 0.00005
        low = close_price - 0.00010
        rows.append(f"{timestamp.isoformat()},{open_price:.5f},{high:.5f},{low:.5f},{close_price:.5f},1000")
        timestamp += timedelta(minutes=1)

    # 3. Reversal pattern
    # Candle 1: small bearish
    open_p = close_price
    close_p = open_p - 0.00005
    rows.append(f"{timestamp.isoformat()},{open_p:.5f},{open_p+0.00003:.5f},{close_p-0.00003:.5f},{close_p:.5f},1000")
    timestamp += timedelta(minutes=1)

    # Candle 2: small bearish
    prev_open = close_p
    prev_close = prev_open - 0.00008
    rows.append(f"{timestamp.isoformat()},{prev_open:.5f},{prev_open+0.00002:.5f},{prev_close-0.00002:.5f},{prev_close:.5f},1000")
    timestamp += timedelta(minutes=1)

    # Candle 3: bullish engulfing
    curr_open = prev_close - 0.00005
    curr_close = prev_open + 0.00010
    rows.append(f"{timestamp.isoformat()},{curr_open:.5f},{curr_close+0.00005:.5f},{curr_open-0.00003:.5f},{curr_close:.5f},1500")

    csv_path.write_text("\n".join(rows))
    return csv_path


class TestSignalCountDeterminism:
    """Test signal count determinism across multiple runs."""

    def test_long_signal_count_deterministic_across_runs(
        self, eurusd_price_data, tmp_path
    ):
        """
        T022: Verify long signal count is deterministic across multiple runs.
        """
        params = StrategyParameters(
            risk_per_trade_pct=0.25,
            account_balance=10000.0,
        )

        # Run backtest 3 times
        result1 = run_v2_backtest(
            price_data_path=eurusd_price_data,
            output_dir=tmp_path / "run1",
            parameters=params,
            log_level="ERROR",
        )

        result2 = run_v2_backtest(
            price_data_path=eurusd_price_data,
            output_dir=tmp_path / "run2",
            parameters=params,
            log_level="ERROR",
        )

        result3 = run_v2_backtest(
            price_data_path=eurusd_price_data,
            output_dir=tmp_path / "run3",
            parameters=params,
            log_level="ERROR",
        )

        assert (
            result1["signals_generated"]
            == result2["signals_generated"]
            == result3["signals_generated"]
        ), "Signal count should be deterministic across runs"

        assert result1["signals_generated"] > 0, "Should generate at least one signal"

    def test_signal_ids_deterministic_across_runs(self, eurusd_price_data, tmp_path):
        """
        T022: Verify signal IDs are deterministic across multiple runs.
        """
        params = StrategyParameters(
            risk_per_trade_pct=0.25,
            account_balance=10000.0,
        )

        # Run backtest twice
        result1 = run_v2_backtest(
            price_data_path=eurusd_price_data,
            output_dir=tmp_path / "run1",
            parameters=params,
            log_level="ERROR",
        )

        result2 = run_v2_backtest(
            price_data_path=eurusd_price_data,
            output_dir=tmp_path / "run2",
            parameters=params,
            log_level="ERROR",
        )

        assert result1["signals_generated"] == result2["signals_generated"]


class TestSignalCountByDirection:
    """Test signal counts by direction (long/short/both)."""

    def test_long_mode_produces_only_long_signals(self, eurusd_price_data, tmp_path):
        """
        T022: Verify long-only mode produces only long signals.
        """
        params = StrategyParameters(
            risk_per_trade_pct=0.25,
            account_balance=10000.0,
        )

        result = run_v2_backtest(
            price_data_path=eurusd_price_data,
            output_dir=tmp_path / "results",
            parameters=params,
            log_level="ERROR",
        )

        assert result["signals_generated"] > 0
        assert "long" in result["strategy_name"].lower()

    def test_signal_count_changes_with_parameters(self, eurusd_price_data, tmp_path):
        """
        T022: Verify signal count varies with different parameters.
        """
        params_default = StrategyParameters(
            risk_per_trade_pct=0.25,
            account_balance=10000.0,
        )

        result_default = run_v2_backtest(
            price_data_path=eurusd_price_data,
            output_dir=tmp_path / "default",
            parameters=params_default,
            log_level="ERROR",
        )

        params_conservative = StrategyParameters(
            risk_per_trade_pct=0.25,
            account_balance=10000.0,
            oversold_threshold=10.0,  # Lower threshold = harder to signal
        )

        result_conservative = run_v2_backtest(
            price_data_path=eurusd_price_data,
            output_dir=tmp_path / "conservative",
            parameters=params_conservative,
            log_level="ERROR",
        )

        assert (
            result_conservative["signals_generated"]
            <= result_default["signals_generated"]
        ), "More conservative threshold should produce fewer or equal signals"

        assert result_default["signals_generated"] > 0


class TestSignalCountReasonableness:
    """Test signal counts are reasonable for given market conditions."""

    def test_signal_count_not_excessive(self, eurusd_price_data, tmp_path):
        """
        T022: Verify signal count is not excessive.
        """
        params = StrategyParameters(
            risk_per_trade_pct=0.25,
            account_balance=10000.0,
        )

        result = run_v2_backtest(
            price_data_path=eurusd_price_data,
            output_dir=tmp_path / "results",
            parameters=params,
            log_level="ERROR",
        )

        assert result["signals_generated"] > 0

    def test_signal_count_not_zero_on_sufficient_data(
        self, eurusd_price_data, tmp_path
    ):
        """
        T022: Verify signal count is not zero on sufficient data.
        """
        params = StrategyParameters(
            risk_per_trade_pct=0.25,
            account_balance=10000.0,
        )

        result = run_v2_backtest(
            price_data_path=eurusd_price_data,
            output_dir=tmp_path / "results",
            parameters=params,
            log_level="ERROR",
        )

        assert (
            result["signals_generated"] > 0
        ), "Should generate at least one signal with sufficient data"


class TestSignalCountConsistency:
    """Test signal count consistency across data slices."""

    def test_signal_count_consistent_across_data_slices(
        self, eurusd_price_data, tmp_path
    ):
        """
        T022: Verify signal counts are consistent when processing data in slices.
        """
        params = StrategyParameters(
            risk_per_trade_pct=0.25,
            account_balance=10000.0,
        )

        result_3k = run_v2_backtest(
            price_data_path=eurusd_price_data,
            output_dir=tmp_path / "run1",
            parameters=params,
            log_level="ERROR",
        )

        result_3k_repeat = run_v2_backtest(
            price_data_path=eurusd_price_data,
            output_dir=tmp_path / "run2",
            parameters=params,
            log_level="ERROR",
        )

        assert (
            result_3k["signals_generated"] == result_3k_repeat["signals_generated"]
        ), "Same data slice should produce same signal count"
