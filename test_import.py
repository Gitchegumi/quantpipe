import sys

sys.path.append("e:\\GitHub\\trading-strategies")

try:
    print("Importing directional...")
    from src.models.directional import BacktestResult

    print("SUCCESS: Imported BacktestResult")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback

    traceback.print_exc()

try:
    print("\nImporting orchestrator...")
    from src.backtest.orchestrator import BacktestOrchestrator

    print("SUCCESS: Imported BacktestOrchestrator")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback

    traceback.print_exc()
