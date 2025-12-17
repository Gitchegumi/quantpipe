"""Direct test of vectorized backtest bypassing ingestion module."""

import polars as pl
from datetime import datetime, timezone

print("Step 1: Loading data directly with Polars...")
df = pl.read_parquet("price_data/processed/eurusd/test/eurusd_test.parquet")

# Rename columns to match expected names
if "timestamp" in df.columns and "timestamp_utc" not in df.columns:
    df = df.rename({"timestamp": "timestamp_utc"})

print(f"✓ Loaded {len(df)} rows")
print(f"  Columns: {df.columns}")

print("\nStep 2: Calculating indicators with vectorized functions...")
from src.backtest.vectorized_rolling_window import (
    calculate_ema,
    calculate_atr,
    calculate_rsi,
    calculate_stoch_rsi,
)

df = calculate_ema(df, period=20, column="close")  # Creates ema20
df = calculate_ema(df, period=50, column="close")  # Creates ema50
df = calculate_rsi(df, period=14, column="close")  # Creates rsi
df = calculate_atr(df, period=14)  # Creates atr14
df = calculate_stoch_rsi(df, period=14, rsi_col="rsi")  # Creates stoch_rsi

print(
    f"✓ Indicators added: {[c for c in df.columns if c in ['ema20', 'ema50', 'atr14', 'rsi', 'stoch_rsi']]}"
)

print("\nStep 3: Creating orchestrator...")
from src.backtest.orchestrator import BacktestOrchestrator
from src.models.enums import DirectionMode

orch = BacktestOrchestrator(
    direction_mode=DirectionMode.LONG,
    dry_run=True,
    enable_profiling=False,
)
print("✓ Orchestrator created")

print("\nStep 4: Loading strategy...")
from src.strategy.trend_pullback.strategy import TREND_PULLBACK_STRATEGY

print(f"✓ Strategy loaded: {TREND_PULLBACK_STRATEGY.metadata.name}")

print("\nStep 5: Running vectorized backtest...")
start = datetime.now(timezone.utc)

result = orch.run_backtest(
    data=df,
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

print(f"\n{'='*60}")
print(f"SUCCESS! Vectorized backtest completed in {elapsed:.2f}s")
print(f"{'='*60}")
print(f"Run ID: {result.run_id}")
print(f"Direction: {result.direction_mode}")
print(f"Total candles: {result.total_candles}")
print(f"Signals generated: {len(result.signals) if result.signals else 0}")
print(f"Dry run: {result.dry_run}")

if result.signals:
    print(f"\nFirst 3 signals:")
    for i, sig in enumerate(result.signals[:3]):
        print(
            f"  {i+1}. {sig.direction} @ {sig.entry_price:.5f} (stop: {sig.initial_stop_price:.5f})"
        )

print(f"\nTest completed successfully! ✓")
