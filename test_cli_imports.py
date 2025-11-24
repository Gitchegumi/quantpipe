import sys

sys.path.append("e:\\GitHub\\trading-strategies")

print("Step 1: Importing BacktestOrchestrator...")
try:
    from src.backtest.orchestrator import BacktestOrchestrator

    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("\nStep 2: Importing vectorized functions...")
try:
    from src.backtest.vectorized_rolling_window import calculate_ema

    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("\nStep 3: Importing strategy...")
try:
    from src.strategy.trend_pullback.strategy import TREND_PULLBACK_STRATEGY

    print("SUCCESS")
    print(f"  Strategy: {TREND_PULLBACK_STRATEGY}")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("\nStep 4: Importing DirectionMode...")
try:
    from src.models.enums import DirectionMode

    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("\nAll imports successful!")
