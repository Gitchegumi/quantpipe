"""Direct test of vectorized backtest bypassing ingestion module.

This integration test requires local price data (gitignored) and will be
skipped automatically in CI environments.
"""

from pathlib import Path
from datetime import datetime, timezone

import pytest
import polars as pl

from src.strategy.trend_pullback.strategy import TREND_PULLBACK_STRATEGY
from src.backtest.vectorized_rolling_window import (
    calculate_ema,
    calculate_atr,
    calculate_rsi,
    calculate_stoch_rsi,
)
from src.backtest.orchestrator import BacktestOrchestrator
from src.models.enums import DirectionMode


DATA_PATH = Path("price_data/processed/eurusd/test/eurusd_test.parquet")


@pytest.mark.local_data
@pytest.mark.skipif(
    not DATA_PATH.exists(),
    reason=f"Test data not found at {DATA_PATH} (gitignored)",
)
def test_vectorized_backtest_direct():
    """Test vectorized backtest execution with real price data."""
    # Step 1: Load data directly with Polars
    df = pl.read_parquet(DATA_PATH)

    # Rename columns to match expected names and convert timestamp to datetime
    if "timestamp" in df.columns and "timestamp_utc" not in df.columns:
        df = df.with_columns(
            pl.col("timestamp")
            .str.to_datetime("%Y-%m-%d %H:%M:%S%z")
            .alias("timestamp_utc")
        ).drop("timestamp")

    assert len(df) > 0, "Data should have rows"

    # Step 2: Calculate indicators with vectorized functions
    df = calculate_ema(df, period=20, column="close")  # Creates ema20
    df = calculate_ema(df, period=50, column="close")  # Creates ema50
    df = calculate_rsi(df, period=14, column="close")  # Creates rsi
    df = calculate_atr(df, period=14)  # Creates atr14
    df = calculate_stoch_rsi(df, period=14, rsi_col="rsi")  # Creates stoch_rsi

    expected_cols = ["ema20", "ema50", "atr14", "rsi", "stoch_rsi"]
    for col in expected_cols:
        assert col in df.columns, f"Expected column {col} in DataFrame"

    # Step 3: Create orchestrator
    orch = BacktestOrchestrator(
        direction_mode=DirectionMode.LONG,
        dry_run=True,
        enable_profiling=False,
    )

    # Step 4: Run vectorized backtest
    start = datetime.now(timezone.utc)

    result = orch.run_backtest(
        candles=df,
        pair="EURUSD",
        run_id="test_vectorized_001",
        strategy=TREND_PULLBACK_STRATEGY,
        ema_fast=20,
        ema_slow=50,
        atr_stop_mult=1.5,
        target_r_mult=2.0,
        cooldown_candles=0,
        rsi_length=14,
        risk_per_trade_pct=0.01,
    )

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()

    # Assertions
    assert result is not None, "Backtest should return a result"
    assert result.run_id == "test_vectorized_001"
    assert result.direction_mode == DirectionMode.LONG.value
    assert result.total_candles > 0
    assert result.dry_run is True

    # Performance check: vectorized should complete quickly
    assert elapsed < 60, f"Backtest took too long: {elapsed:.2f}s"
