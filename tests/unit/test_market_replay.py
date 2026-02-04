import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.infrastructure.duckdb.vault import DuckDBVault
from src.backtest.replay import ReplaySession

@pytest.fixture
def populated_vault(tmp_path):
    """Fixture to create a vault with some test data."""
    db_file = tmp_path / "replay_test.duckdb"
    vault = DuckDBVault(db_path=str(db_file))
    
    # Create 2 days of 1m data
    start = datetime(2023, 1, 1)
    dates = pd.date_range(start, periods=2880, freq="1min")
    df = pd.DataFrame({
        "timestamp": dates,
        "open": np.random.randn(2880),
        "high": np.random.randn(2880),
        "low": np.random.randn(2880),
        "close": np.random.randn(2880),
        "volume": np.random.randn(2880)
    })
    
    vault.ingest_df(df, "EURUSD", "1m")
    vault.close()
    return str(db_file)

def test_replay_session_stepping(populated_vault):
    """Test that ReplaySession yields candles correctly."""
    start = datetime(2023, 1, 1, 0, 0)
    end = datetime(2023, 1, 1, 0, 10)
    
    session = ReplaySession(
        symbol="EURUSD",
        timeframe="1m",
        start_time=start,
        end_time=end,
        vault_path=populated_vault
    )
    
    candles = []
    while True:
        c = session.next_candle()
        if c is None:
            break
        candles.append(c)
        
    # 00:00 to 00:10 inclusive is 11 minutes
    assert len(candles) == 11
    assert candles[0]["timestamp"] == pd.Timestamp(start)
    assert candles[-1]["timestamp"] == pd.Timestamp(end)
    
    session.close()

def test_replay_session_reset(populated_vault):
    """Test that session reset works."""
    start = datetime(2023, 1, 1, 0, 0)
    end = datetime(2023, 1, 1, 0, 5)
    
    session = ReplaySession("EURUSD", "1m", start, end, vault_path=populated_vault)
    
    c1 = session.next_candle()
    c2 = session.next_candle()
    assert c1 != c2
    
    session.reset()
    c3 = session.next_candle()
    assert c1["timestamp"] == c3["timestamp"]
    
    session.close()
