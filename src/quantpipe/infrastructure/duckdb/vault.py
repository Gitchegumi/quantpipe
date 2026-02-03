import duckdb
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict
import logging

class DuckDBVault:
    """
    DuckDB-based OHLCV storage vault for high-fidelity backtesting and replay.
    """
    def __init__(self, db_path: str = "data/vault.duckdb"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.db_path))
        self._initialize_schema()

    def _initialize_schema(self):
        """Initializes the OHLCV table with standard schema."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv (
                symbol VARCHAR,
                timeframe VARCHAR,
                timestamp TIMESTAMP,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                PRIMARY KEY (symbol, timeframe, timestamp)
            )
        """)
        # Index for range lookups (critical for backtesting/replay)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_time ON ohlcv (symbol, timeframe, timestamp)")

    def ingest_df(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """
        Ingests a Pandas DataFrame into the vault.
        Expected columns: timestamp, open, high, low, close, volume
        """
        # Ensure standard column names
        df = df.copy()
        df['symbol'] = symbol
        df['timeframe'] = timeframe
        
        # Use DuckDB's native registration to insert from dataframe
        self.conn.execute("INSERT OR REPLACE INTO ohlcv SELECT * FROM df")
        logging.info(f"Ingested {len(df)} rows for {symbol} ({timeframe}) into DuckDB vault.")

    def fetch_range(self, symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame:
        """Fetches a range of OHLCV data."""
        query = """
            SELECT timestamp, open, high, low, close, volume 
            FROM ohlcv 
            WHERE symbol = ? AND timeframe = ? 
            AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
        """
        return self.conn.execute(query, [symbol, timeframe, start, end]).df()

    def close(self):
        self.conn.close()
