import sys

sys.path.append("e:\\GitHub\\trading-strategies")

try:
    print("Importing IngestionMetrics class...")
    from src.io.ingestion import IngestionMetrics

    print(f"Class imported successfully")
    print(f"IngestionMetrics.__module__ = {IngestionMetrics.__module__!r}")
    print(f"Module exists in sys.modules? {IngestionMetrics.__module__ in sys.modules}")

    if IngestionMetrics.__module__ in sys.modules:
        print(f"Module object: {sys.modules[IngestionMetrics.__module__]}")
    else:
        print("Module NOT in sys.modules!")
        print(
            f"Available modules with 'ingestion': {[k for k in sys.modules.keys() if 'ingestion' in k]}"
        )

    print("\nAttempting to create instance...")
    metrics = IngestionMetrics(
        total_rows_input=100,
        total_rows_output=100,
        gaps_inserted=0,
        duplicates_removed=0,
        runtime_seconds=1.0,
        throughput_rows_per_min=6000.0,
        acceleration_backend="arrow",
        downcast_applied=False,
        stretch_runtime_candidate=True,
    )
    print("SUCCESS!")

except Exception as e:
    print(f"\nFAILED: {e}")
    import traceback

    traceback.print_exc()
