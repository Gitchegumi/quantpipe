import sys
import polars as pl
from datetime import datetime, timezone

sys.path.append("e:\\GitHub\\trading-strategies")

try:
    print("Loading data...")
    from src.io.ingestion import ingest_ohlcv_data

    result = ingest_ohlcv_data(
        path="price_data/processed/EURUSD/test/eurusd_test.parquet",
        timeframe_minutes=1,
        mode="columnar",
        downcast=False,
        use_arrow=True,
        strict_cadence=False,
        fill_gaps=False,
        return_polars=True,
    )

    print(f"Loaded {len(result.data)} rows")
    print(f"Columns: {result.data.columns}")

    print("\nCalculating indicators...")
    from src.backtest.vectorized_rolling_window import (
        calculate_ema,
        calculate_atr,
        calculate_stoch_rsi,
    )

    df = result.data
    df = calculate_ema(df, period=20, column="close", output_col="ema20")
    df = calculate_ema(df, period=50, column="close", output_col="ema50")
    df = calculate_atr(df, period=14, output_col="atr14")
    df = calculate_stoch_rsi(df, period=14, output_col="stoch_rsi")

    print(
        f"Indicators: {[c for c in df.columns if c not in ['timestamp_utc', 'open', 'high', 'low', 'close', 'volume']]}"
    )

    print("\nCreating orchestrator...")
    from src.backtest.orchestrator import BacktestOrchestrator
    from src.models.enums import DirectionMode

    orch = BacktestOrchestrator(
        direction_mode=DirectionMode.LONG,
        dry_run=True,
    )

    print("\nLoading strategy...")
    from src.strategy.trend_pullback.strategy import TREND_PULLBACK_STRATEGY

    print("\nRunning backtest...")
    result = orch.run_backtest(
        data=df,
        pair="EURUSD",
        run_id="test_001",
        strategy=TREND_PULLBACK_STRATEGY,
        ema_fast=20,
        ema_slow=50,
        atr_stop_mult=1.5,
        target_r_mult=2.0,
        cooldown_candles=0,
        rsi_length=14,
        risk_per_trade_pct=0.01,
    )

    print(f"\nSUCCESS! Generated {len(result.signals)} signals")

except Exception as e:
    print(f"\nFAILED: {e}")
    import traceback

    traceback.print_exc()
