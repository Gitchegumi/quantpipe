"""Quick test script for vectorized scanning with BacktestOrchestrator.

Usage:
    poetry run python scripts/test_vectorized_scan.py [pair] [dataset]
    
    pair: eurusd or usdjpy (default: eurusd)
    dataset: test or validate (default: test)
"""

import sys
from pathlib import Path

import pandas as pd

from src.backtest.orchestrator import BacktestOrchestrator
from src.config.parameters import StrategyParameters
from src.models.enums import DirectionMode
from src.strategy.trend_pullback.strategy import TREND_PULLBACK_STRATEGY


def apply_indicators_pandas(df: pd.DataFrame) -> pd.DataFrame:
    """Apply required indicators to DataFrame using pandas."""
    # EMA 20
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()

    # EMA 50
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()

    # ATR 14
    df["high_low"] = df["high"] - df["low"]
    df["high_close"] = abs(df["high"] - df["close"].shift())
    df["low_close"] = abs(df["low"] - df["close"].shift())
    df["true_range"] = df[["high_low", "high_close", "low_close"]].max(axis=1)
    df["atr14"] = df["true_range"].rolling(window=14).mean()
    df.drop(columns=["high_low", "high_close", "low_close", "true_range"], inplace=True)

    # Stochastic RSI
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    rsi_min = rsi.rolling(window=14).min()
    rsi_max = rsi.rolling(window=14).max()
    df["stoch_rsi"] = (rsi - rsi_min) / (rsi_max - rsi_min)
    df["stoch_rsi"] = df["stoch_rsi"].fillna(0.5)

    return df
def main():
    # Parse arguments
    pair = sys.argv[1] if len(sys.argv) > 1 else "eurusd"
    dataset = sys.argv[2] if len(sys.argv) > 2 else "test"

    # Build data path
    data_path = Path(f"price_data/processed/{pair}/{dataset}/{pair}_{dataset}.parquet")

    if not data_path.exists():
        print(f"Error: Data file not found: {data_path}")
        return 1

    print(f"Testing vectorized scan on {pair.upper()} ({dataset} dataset)")
    print(f"Data: {data_path}")
    print("-" * 60)

    # Load enriched DataFrame from parquet
    print("\nLoading data...")
    df = pd.read_parquet(data_path)

    # Rename timestamp column if needed
    if "timestamp" in df.columns and "timestamp_utc" not in df.columns:
        df = df.rename(columns={"timestamp": "timestamp_utc"})

    print(f"Loaded {len(df):,} candles")
    print(f"Columns: {list(df.columns)}")

    # Load strategy
    strategy = TREND_PULLBACK_STRATEGY
    required_indicators = strategy.metadata.required_indicators

    # Check if indicators are already present
    missing_indicators = [ind for ind in required_indicators if ind not in df.columns]

    if missing_indicators:
        print(f"\nEnriching with indicators: {required_indicators}")
        df = apply_indicators_pandas(df)
        print(f"Enriched columns: {list(df.columns)}")
    else:
        print(f"\nIndicators already present: {required_indicators}")

    # Load strategy parameters
    parameters = StrategyParameters()

    # Create orchestrator for BOTH mode
    orchestrator = BacktestOrchestrator(
        direction_mode=DirectionMode.BOTH, dry_run=False
    )

    # Prepare signal parameters
    signal_params = {
        "ema_fast": parameters.ema_fast,
        "ema_slow": parameters.ema_slow,
        "atr_stop_mult": parameters.atr_stop_mult,
        "target_r_mult": parameters.target_r_mult,
        "cooldown_candles": parameters.cooldown_candles,
        "rsi_length": parameters.rsi_length,
        "rsi_oversold": 0.3,  # Stoch RSI is 0-1 scale
        "rsi_overbought": 0.7,
    }

    # Run backtest
    print("\nRunning optimized backtest with direction=BOTH...")
    result = orchestrator.run_optimized_backtest(
        df=df,
        pair=pair.upper(),
        run_id=f"test_{pair}_{dataset}",
        strategy=strategy,
        **signal_params,
    )

    # Display results
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    print(f"Run ID: {result.run_id}")
    print(f"Direction: {result.direction_mode}")
    print(f"Total candles: {result.total_candles:,}")
    print(f"Dry run: {result.dry_run}")

    # For BOTH mode, metrics is DirectionalMetrics with long_only/short_only
    if hasattr(result.metrics, "long_only"):
        long_metrics = result.metrics.long_only
        print(f"\nLONG trades: {long_metrics.trade_count}")
        if long_metrics.trade_count > 0:
            print(f"  Win rate: {long_metrics.win_rate:.1%}")
            print(f"  Avg R: {long_metrics.avg_r:.2f}")
            print(f"  Sharpe: {long_metrics.sharpe_estimate:.2f}")
    else:
        print("\nLONG trades: 0")

    if hasattr(result.metrics, "short_only"):
        short_metrics = result.metrics.short_only
        print(f"\nSHORT trades: {short_metrics.trade_count}")
        if short_metrics.trade_count > 0:
            print(f"  Win rate: {short_metrics.win_rate:.1%}")
            print(f"  Avg R: {short_metrics.avg_r:.2f}")
            print(f"  Sharpe: {short_metrics.sharpe_estimate:.2f}")
    else:
        print("\nSHORT trades: 0")

    # Display signal counts if available
    if result.signals:
        long_signals = sum(1 for s in result.signals if s.direction == "LONG")
        short_signals = sum(1 for s in result.signals if s.direction == "SHORT")
        print(
            f"\nTotal signals: {len(result.signals)} "
            f"(LONG: {long_signals}, SHORT: {short_signals})"
        )

    print("\n" + "=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
