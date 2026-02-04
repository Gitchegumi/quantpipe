import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from src.infrastructure.duckdb.vault import DuckDBVault

def test_duckdb_vault_lifecycle(tmp_path):
    """Test creating, ingesting into, and fetching from the vault."""
    db_file = tmp_path / "test_vault.duckdb"
    vault = DuckDBVault(db_path=str(db_file))
    
    # Create sample data
    dates = pd.date_range("2023-01-01", periods=10, freq="1min")
    df = pd.DataFrame({
        "timestamp": dates,
        "open": np.random.randn(10),
        "high": np.random.randn(10),
        "low": np.random.randn(10),
        "close": np.random.randn(10),
        "volume": np.random.randn(10)
    })
    
    # Ingest
    vault.ingest_df(df, "EURUSD", "1m")
    
    # Fetch
    fetched = vault.fetch_range("EURUSD", "1m", "2023-01-01 00:00", "2023-01-01 00:05")
    
    assert len(fetched) == 6
    assert "open" in fetched.columns
    assert "close" in fetched.columns
    
    vault.close()
    assert db_file.exists()

def test_duckdb_vault_overwrite(tmp_path):
    """Test that INSERT OR REPLACE works as expected."""
    db_file = tmp_path / "test_vault_overwrite.duckdb"
    vault = DuckDBVault(db_path=str(db_file))
    
    ts = pd.Timestamp("2023-01-01 00:00:00")
    df1 = pd.DataFrame({
        "timestamp": [ts],
        "open": [1.10], "high": [1.11], "low": [1.09], "close": [1.105], "volume": [100]
    })
    
    vault.ingest_df(df1, "EURUSD", "1m")
    
    df2 = pd.DataFrame({
        "timestamp": [ts],
        "open": [1.20], "high": [1.21], "low": [1.19], "close": [1.205], "volume": [200]
    })
    
    vault.ingest_df(df2, "EURUSD", "1m")
    
    fetched = vault.fetch_range("EURUSD", "1m", "2023-01-01 00:00", "2023-01-01 00:00")
    assert len(fetched) == 1
    assert fetched.iloc[0]["open"] == 1.20
    
    vault.close()
