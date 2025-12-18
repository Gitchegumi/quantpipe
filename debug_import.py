print("Importing src.io.ingestion...")
try:
    from src.io.ingestion import ingest_ohlcv_data

    print("Ingestion imported successfully.")
except Exception as e:
    print(f"Failed to import ingestion: {e}")
    import traceback

    traceback.print_exc()
