import duckdb
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
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
        # Ensure standard column names and types
        df = df.copy()
        df['symbol'] = symbol
        df['timeframe'] = timeframe

        # Ensure timestamp is datetime
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Ensure numeric columns are float
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Reorder columns to exactly match table schema: symbol, timeframe, timestamp, open, high, low, close, volume
        # This avoids positional mismatches in INSERT
        column_order = ['symbol', 'timeframe', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
        df = df[column_order]

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

    def get_data_range(self, symbol: str, timeframe: str) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Returns (min_timestamp, max_timestamp) for the given symbol/timeframe.
        """
        try:
            query = """
                SELECT MIN(timestamp), MAX(timestamp)
                FROM ohlcv
                WHERE symbol = ? AND timeframe = ?
            """
            result = self.conn.execute(query, [symbol, timeframe]).fetchone()
            if result and result[0] and result[1]:
                min_ts = pd.to_datetime(result[0]).to_pydatetime()
                max_ts = pd.to_datetime(result[1]).to_pydatetime()
                return min_ts, max_ts
            return None, None
        except Exception as e:
            logging.warning(f"Failed to get data range for {symbol} {timeframe}: {e}")
            return None, None

    def list_symbols(self) -> List[str]:
        """Returns a list of distinct symbols available in the vault."""
        try:
            query = "SELECT DISTINCT symbol FROM ohlcv ORDER BY symbol"
            results = self.conn.execute(query).fetchall()
            return [row[0] for row in results]
        except Exception as e:
            logging.warning(f"Failed to list symbols: {e}")
            return []

    def close(self):
        self.conn.close()
