import sys

sys.path.append("e:\\GitHub\\trading-strategies")

try:
    print("Testing IngestionMetrics...")
    from src.io.ingestion import IngestionMetrics

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
    print("SUCCESS: IngestionMetrics created")

    print("\nTesting IngestionResult...")
    from src.io.ingestion import IngestionResult
    import polars as pl

    df = pl.DataFrame({"a": [1, 2, 3]})

    result = IngestionResult(
        data=df,
        metrics=metrics,
        mode="columnar",
        core_hash="test_hash",
    )
    print("SUCCESS: IngestionResult created")

except Exception as e:
    print(f"FAILED: {e}")
    import traceback

    traceback.print_exc()
