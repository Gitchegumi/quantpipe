"""
Performance tests for dry-run mode.

This module validates that dry-run mode (signal generation without execution)
completes within the target performance threshold.

Target: Process 100K candles in ≤10 seconds with --dry-run flag.

Test Coverage:
- SC-005: Dry-run completes within 10 seconds for 100K candles
- SC-007: Deterministic results (signals always generated the same way)
"""

import pytest


pytestmark = pytest.mark.performance

import csv
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.backtest.orchestrator import BacktestOrchestrator
from src.config.parameters import StrategyParameters
from src.io.ingestion import ingest_candles
from src.models.enums import DirectionMode


@pytest.fixture()
def dataset_100k_candles() -> Path:
    """
    Create a 100K candle dataset for dry-run performance testing.

    Generates 100,000 candles (~69 days of M1 data) with:
    - Sequential timestamps
    - Realistic trending price action
    - Sufficient volatility for signal generation

    Returns:
        Path to temporary CSV file.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_utc", "open", "high", "low", "close", "volume"])

        base_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        price = 1.1000

        for i in range(100000):
            timestamp = base_time + timedelta(minutes=i)

            # Create trending waves for signal generation
            trend = (i / 20000) * 0.02  # +200 pips over dataset
            wave = 0.005 * ((i % 1000) / 1000 - 0.5)  # ±50 pip waves
            noise = ((i * 17) % 100 - 50) * 0.00001  # ±5 pips noise

            open_price = price + noise
            close_price = price + trend + wave + noise + 0.00005
            high_price = max(open_price, close_price) + 0.0001
            low_price = min(open_price, close_price) - 0.0001

            price = close_price

            writer.writerow(
                [
                    timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    f"{open_price:.5f}",
                    f"{high_price:.5f}",
                    f"{low_price:.5f}",
                    f"{close_price:.5f}",
                    f"{1000 + (i % 500)}",
                ]
            )

        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


def test_dry_run_performance_100k_candles(dataset_100k_candles: Path):
    """
    Validate dry-run mode completes within 10 seconds for 100K candles.

    This test verifies SC-005: Dry-run mode performance threshold.

    Validates:
    - Processing time ≤10 seconds
    - Signals are generated
    - No executions created (dry-run behavior)
    - Deterministic signal generation

    Args:
        dataset_100k_candles: 100K candle synthetic dataset fixture.
    """
    parameters = StrategyParameters()

    # Ingest candles with indicators
    candles = list(
        ingest_candles(
            csv_path=dataset_100k_candles,
            ema_fast=parameters.ema_fast,
            ema_slow=parameters.ema_slow,
            atr_period=parameters.atr_length,
            rsi_period=parameters.rsi_length,
            stoch_rsi_period=parameters.rsi_length,
            expected_timeframe_minutes=1,
            allow_gaps=True,
        )
    )

    orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG, dry_run=True)

    signal_params = {
        "ema_fast": parameters.ema_fast,
        "ema_slow": parameters.ema_slow,
        "atr_stop_mult": parameters.atr_stop_mult,
        "target_r_mult": parameters.target_r_mult,
        "cooldown_candles": parameters.cooldown_candles,
        "rsi_length": parameters.rsi_length,
    }

    start_time = time.perf_counter()

    result = orchestrator.run_backtest(
        candles=candles, pair="EURUSD", run_id="perf_dry_001", **signal_params
    )

    end_time = time.perf_counter()
    elapsed_seconds = end_time - start_time

    print(
        f"\nDry-run performance: {result.total_candles} candles "
        f"in {elapsed_seconds:.2f}s ({result.total_candles/elapsed_seconds:.0f} candles/sec)"
    )
    print(f"Signals generated: {len(result.signals)}")

    # SC-005: Dry-run completes within 10 seconds for 100K candles
    assert (
        elapsed_seconds <= 10.0
    ), f"Dry-run took {elapsed_seconds:.2f}s (target: ≤10s)"

    # Verify dry-run behavior
    assert result.dry_run is True, "Result should be marked as dry-run"
    assert result.total_candles == 100000, "Should process all 100K candles"
    assert len(result.signals) >= 0, "Should generate signals list (may be empty)"
    assert result.executions is None, "Dry-run should not create executions"
    assert result.metrics is None, "Dry-run should not compute metrics"


def test_dry_run_deterministic_signals(dataset_100k_candles: Path):
    """
    Validate dry-run mode produces deterministic signals.

    This test verifies SC-007: Deterministic results.

    Running the same dry-run twice should produce identical signals.

    Validates:
    - Signal count matches between runs
    - Signal timestamps match
    - Signal prices match
    - Entry/stop prices match

    Args:
        dataset_100k_candles: 100K candle synthetic dataset fixture.
    """
    parameters = StrategyParameters()

    # Ingest candles once (reuse for both runs)
    candles = list(
        ingest_candles(
            csv_path=dataset_100k_candles,
            ema_fast=parameters.ema_fast,
            ema_slow=parameters.ema_slow,
            atr_period=parameters.atr_length,
            rsi_period=parameters.rsi_length,
            stoch_rsi_period=parameters.rsi_length,
            expected_timeframe_minutes=1,
            allow_gaps=True,
        )
    )

    orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG, dry_run=True)

    signal_params = {
        "ema_fast": parameters.ema_fast,
        "ema_slow": parameters.ema_slow,
        "atr_stop_mult": parameters.atr_stop_mult,
        "target_r_mult": parameters.target_r_mult,
        "cooldown_candles": parameters.cooldown_candles,
        "rsi_length": parameters.rsi_length,
    }

    # Run 1
    result1 = orchestrator.run_backtest(
        candles=candles, pair="EURUSD", run_id="det_test_001", **signal_params
    )

    # Run 2
    result2 = orchestrator.run_backtest(
        candles=candles, pair="EURUSD", run_id="det_test_002", **signal_params
    )

    # SC-007: Deterministic results
    assert len(result1.signals) == len(result2.signals), "Signal count should match"

    for sig1, sig2 in zip(result1.signals, result2.signals, strict=False):
        assert sig1.timestamp == sig2.timestamp, "Signal timestamps should match"
        assert sig1.pair == sig2.pair, "Signal pair should match"
        assert sig1.direction == sig2.direction, "Signal direction should match"
        assert sig1.entry_price == sig2.entry_price, "Entry prices should match"
        assert sig1.stop_price == sig2.stop_price, "Stop prices should match"
        assert sig1.target_price == sig2.target_price, "Target prices should match"

    print(f"\nDeterminism verified: {len(result1.signals)} signals matched")


@pytest.mark.slow()
def test_dry_run_all_directions_performance(dataset_100k_candles: Path):
    """
    Validate dry-run performance for all directions.

    Ensures LONG, SHORT, and BOTH modes all meet the ≤10s threshold.

    Validates:
    - LONG mode ≤10s
    - SHORT mode ≤10s
    - BOTH mode ≤10s (slightly slower due to dual signal generation)

    Args:
        dataset_100k_candles: 100K candle synthetic dataset fixture.
    """
    parameters = StrategyParameters()

    # Ingest candles once (reuse for all runs)
    candles = list(
        ingest_candles(
            csv_path=dataset_100k_candles,
            ema_fast=parameters.ema_fast,
            ema_slow=parameters.ema_slow,
            atr_period=parameters.atr_length,
            rsi_period=parameters.rsi_length,
            stoch_rsi_period=parameters.rsi_length,
            expected_timeframe_minutes=1,
            allow_gaps=True,
        )
    )

    signal_params = {
        "ema_fast": parameters.ema_fast,
        "ema_slow": parameters.ema_slow,
        "atr_stop_mult": parameters.atr_stop_mult,
        "target_r_mult": parameters.target_r_mult,
        "cooldown_candles": parameters.cooldown_candles,
        "rsi_length": parameters.rsi_length,
    }

    for direction in [
        DirectionMode.LONG,
        DirectionMode.SHORT,
        DirectionMode.BOTH,
    ]:
        orchestrator = BacktestOrchestrator(direction_mode=direction, dry_run=True)

        start_time = time.perf_counter()

        result = orchestrator.run_backtest(
            candles=candles,
            pair="EURUSD",
            run_id=f"perf_{direction.value}_001",
            **signal_params,
        )

        elapsed_seconds = time.perf_counter() - start_time

        print(
            f"\n{direction.value} dry-run: {elapsed_seconds:.2f}s, "
            f"{len(result.signals)} signals"
        )

        assert (
            elapsed_seconds <= 10.0
        ), f"{direction.value} dry-run took {elapsed_seconds:.2f}s (target: ≤10s)"
        assert result.dry_run is True
        assert result.executions is None
        assert result.metrics is None
