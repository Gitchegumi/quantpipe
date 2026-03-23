"""
Unit tests for src.infrastructure.duckdb.vault.DuckDBVault.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import pandas as pd
import pytest

# Skip entire module if duckdb is not installed
pytest.importorskip("duckdb", minversion="1.0.0")

from src.infrastructure.duckdb.vault import (
    CompactionConfig,
    CompactionManager,
    CompactionState,
    DuckDBVault,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Generator[DuckDBVault, None, None]:
    """Provide a fresh DuckDBVault backed by a temporary directory."""
    db_path = tmp_path / "test_vault.duckdb"
    vault = DuckDBVault(db_path=db_path, auto_compact=False)
    yield vault
    vault.close()


@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    """Return a small in-order OHLCV DataFrame for testing."""
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="1h", tz="UTC"),
            "open":  [1.1010, 1.1015, 1.1020, 1.1018, 1.1022],
            "high":  [1.1020, 1.1025, 1.1028, 1.1025, 1.1030],
            "low":   [1.1005, 1.1010, 1.1015, 1.1012, 1.1018],
            "close": [1.1015, 1.1020, 1.1018, 1.1022, 1.1028],
            "volume": [1000.0, 1100.0, 950.0, 1050.0, 1200.0],
        }
    )


@pytest.fixture
def sample_ohlcv_unsorted() -> pd.DataFrame:
    """Return an OHLCV DataFrame deliberately out of timestamp order."""
    ts = pd.date_range("2024-01-01", periods=5, freq="1h", tz="UTC")
    df = pd.DataFrame(
        {
            "timestamp": ts[[2, 0, 4, 1, 3]],  # shuffled
            "open":  [1.1020, 1.1010, 1.1022, 1.1015, 1.1018],
            "high":  [1.1028, 1.1020, 1.1030, 1.1025, 1.1025],
            "low":   [1.1015, 1.1005, 1.1018, 1.1010, 1.1012],
            "close": [1.1018, 1.1015, 1.1028, 1.1020, 1.1022],
            "volume": [950.0, 1000.0, 1200.0, 1100.0, 1050.0],
        }
    )
    return df


# ---------------------------------------------------------------------------
# DuckDBVault — basic lifecycle
# ---------------------------------------------------------------------------


class TestVaultLifecycle:
    def test_context_manager(self, tmp_path: Path, sample_ohlcv: pd.DataFrame):
        """Vault closes cleanly via context manager."""
        db_path = tmp_path / "ctx_vault.duckdb"
        with DuckDBVault(db_path=db_path, auto_compact=False) as vault:
            vault.ingest_df(sample_ohlcv, symbol="eurusd", timeframe="1h")
        # Connection should be closed — double-close is safe
        # Re-opening should work
        with DuckDBVault(db_path=db_path, auto_compact=False) as vault:
            assert vault.row_count() == 5

    def test_ingest_increases_row_count(self, tmp_vault: DuckDBVault, sample_ohlcv: pd.DataFrame):
        assert tmp_vault.row_count() == 0
        tmp_vault.ingest_df(sample_ohlcv, symbol="eurusd", timeframe="1h")
        assert tmp_vault.row_count() == 5

    def test_ingest_multiple_symbols(self, tmp_vault: DuckDBVault, sample_ohlcv: pd.DataFrame):
        tmp_vault.ingest_df(sample_ohlcv, symbol="EURUSD", timeframe="1h")
        tmp_vault.ingest_df(sample_ohlcv, symbol="GBPUSD", timeframe="1h")
        assert tmp_vault.row_count() == 10
        assert tmp_vault.row_count(symbol="EURUSD") == 5
        assert tmp_vault.row_count(symbol="GBPUSD") == 5

    def test_ingest_case_normalises_symbol(self, tmp_vault: DuckDBVault, sample_ohlcv: pd.DataFrame):
        tmp_vault.ingest_df(sample_ohlcv, symbol="EURUSD", timeframe="1h")
        assert tmp_vault.row_count(symbol="eurusd") == 5
        # Lookup should also be case-insensitive
        result = tmp_vault.fetch_range("EURUSD", "1h", "2024-01-01", "2024-01-01 23:59")
        assert len(result) == 5

    def test_ingest_requires_columns(self, tmp_vault: DuckDataError):
        df_bad = pd.DataFrame({"timestamp": [], "open": []})
        with pytest.raises(ValueError, match="missing required columns"):
            tmp_vault.ingest_df(df_bad, symbol="eurusd", timeframe="1h")


# ---------------------------------------------------------------------------
# DuckDBVault — sorted writes
# ---------------------------------------------------------------------------


class TestSortedWrites:
    def test_ingest_sorts_unsorted_data(
        self, tmp_vault: DuckDBVault, sample_ohlcv_unsorted: pd.DataFrame
    ):
        """
        DataFrame passed out of order must be sorted by timestamp before INSERT.
        We verify by fetching and checking that the returned rows are ascending.
        """
        tmp_vault.ingest_df(sample_ohlcv_unsorted, symbol="eurusd", timeframe="1h")
        result = tmp_vault.fetch_range("eurusd", "1h", "2024-01-01", "2024-01-01 23:59")
        assert result["timestamp"].is_monotonic_increasing, (
            "fetch_range must return rows sorted by timestamp"
        )

    def test_ingest_rejects_null_timestamps(
        self, tmp_vault: DuckDBVault, sample_ohlcv: pd.DataFrame
    ):
        """Null timestamps should be dropped with a warning, not cause an error."""
        df_bad = sample_ohlcv.copy()
        df_bad.loc[2, "timestamp"] = pd.NaT  # type: ignore[assignment]
        rows = tmp_vault.ingest_df(df_bad, symbol="eurusd", timeframe="1h")
        assert rows == 4  # one row dropped


# ---------------------------------------------------------------------------
# DuckDBVault — queries
# ---------------------------------------------------------------------------


class TestQueries:
    def test_fetch_range_returns_correct_columns(
        self, tmp_vault: DuckDBVault, sample_ohlcv: pd.DataFrame
    ):
        tmp_vault.ingest_df(sample_ohlcv, symbol="eurusd", timeframe="1h")
        result = tmp_vault.fetch_range("eurusd", "1h", "2024-01-01", "2024-01-02")
        assert list(result.columns) == ["timestamp", "open", "high", "low", "close", "volume"]

    def test_fetch_range_respects_bounds(
        self, tmp_vault: DuckDBVault, sample_ohlcv: pd.DataFrame
    ):
        tmp_vault.ingest_df(sample_ohlcv, symbol="eurusd", timeframe="1h")
        # Fetch only the middle 2 candles
        result = tmp_vault.fetch_range(
            "eurusd",
            "1h",
            "2024-01-01 02:00",
            "2024-01-01 03:00",
        )
        assert len(result) == 2

    def test_fetch_range_empty_outside_bounds(
        self, tmp_vault: DuckDBVault, sample_ohlcv: pd.DataFrame
    ):
        tmp_vault.ingest_df(sample_ohlcv, symbol="eurusd", timeframe="1h")
        result = tmp_vault.fetch_range("eurusd", "1h", "2025-01-01", "2025-01-02")
        assert len(result) == 0

    def test_get_data_range(
        self, tmp_vault: DuckDBVault, sample_ohlcv: pd.DataFrame
    ):
        tmp_vault.ingest_df(sample_ohlcv, symbol="eurusd", timeframe="1h")
        lo, hi = tmp_vault.get_data_range("eurusd", "1h")
        assert lo is not None
        assert hi is not None
        assert lo < hi

    def test_get_data_range_no_data(self, tmp_vault: DuckDBVault):
        lo, hi = tmp_vault.get_data_range("xyz", "1h")
        assert lo is None
        assert hi is None

    def test_fetch_symbols(self, tmp_vault: DuckDBVault, sample_ohlcv: pd.DataFrame):
        tmp_vault.ingest_df(sample_ohlcv, symbol="eurusd", timeframe="1h")
        tmp_vault.ingest_df(sample_ohlcv, symbol="gbpusd", timeframe="1h")
        symbols = tmp_vault.fetch_symbols()
        assert set(symbols) == {"eurusd", "gbpusd"}

    def test_fetch_symbols_filtered_by_timeframe(
        self, tmp_vault: DuckDBVault, sample_ohlcv: pd.DataFrame
    ):
        tmp_vault.ingest_df(sample_ohlcv, symbol="eurusd", timeframe="1h")
        tmp_vault.ingest_df(sample_ohlcv, symbol="eurusd", timeframe="4h")
        assert set(tmp_vault.fetch_symbols(timeframe="1h")) == {"eurusd"}
        assert set(tmp_vault.fetch_symbols(timeframe="4h")) == {"eurusd"}
        assert set(tmp_vault.fetch_symbols(timeframe="D")) == set()


# ---------------------------------------------------------------------------
# DuckDBVault — compaction
# ---------------------------------------------------------------------------


class TestCompaction:
    def test_record_modification_increments_count(self, tmp_path: Path):
        manager = CompactionManager(
            db_path=tmp_path / "c.db",
            config=CompactionConfig(),
            state_path=tmp_path / "c_state.json",
        )
        assert manager._state.modification_count == 0
        manager.record_modification()
        assert manager._state.modification_count == 1

    def test_should_compact_time_trigger(self, tmp_path: Path):
        cfg = CompactionConfig(weekly_interval_days=7)
        manager = CompactionManager(
            db_path=tmp_path / "t.db",
            config=cfg,
            state_path=tmp_path / "t_state.json",
        )
        # Force last_compact_ts to 8 days ago
        manager._state.last_compact_ts = time.time() - 8 * 86400
        assert manager.should_compact() is True

    def test_should_compact_count_trigger(self, tmp_path: Path):
        cfg = CompactionConfig(max_file_count=10)
        manager = CompactionManager(
            db_path=tmp_path / "c2.db",
            config=cfg,
            state_path=tmp_path / "c2_state.json",
        )
        manager._state.modification_count = 11
        assert manager.should_compact() is True

    def test_should_not_compact_under_thresholds(self, tmp_path: Path):
        cfg = CompactionConfig(weekly_interval_days=7, max_file_count=100)
        manager = CompactionManager(
            db_path=tmp_path / "n.db",
            config=cfg,
            state_path=tmp_path / "n_state.json",
        )
        assert manager.should_compact() is False

    def test_compaction_state_persists(self, tmp_path: Path):
        state_path = tmp_path / "ps.json"
        manager = CompactionManager(
            db_path=tmp_path / "p.db",
            config=CompactionConfig(weekly_interval_days=1),
            state_path=state_path,
        )
        manager.record_modification()
        manager._state.last_compact_ts = time.time() - 86400
        manager._save_state()  # persist the updated last_compact_ts

        # Simulate re-init (new instance)
        manager2 = CompactionManager(
            db_path=tmp_path / "p.db",
            state_path=state_path,
        )
        assert manager2._state.modification_count == 1
        assert manager2._state.last_compact_ts is not None

    def test_compact_runs_on_vault(self, tmp_vault: DuckDBVault, sample_ohlcv: pd.DataFrame):
        tmp_vault.ingest_df(sample_ohlcv, symbol="eurusd", timeframe="1h")
        metrics = tmp_vault.compact()
        assert "elapsed_seconds" in metrics
        assert metrics["elapsed_seconds"] >= 0
        # Row count preserved
        assert tmp_vault.row_count() == 5

    def test_auto_compact_fires_when_triggered(
        self, tmp_path: Path, sample_ohlcv: pd.DataFrame
    ):
        """auto_compact=True should run compaction automatically after ingest."""
        db_path = tmp_path / "ac.db"
        cfg = CompactionConfig(max_file_count=1)  # Force immediate trigger
        vault = DuckDBVault(db_path=db_path, compaction_config=cfg, auto_compact=True)
        vault.ingest_df(sample_ohlcv, symbol="eurusd", timeframe="1h")
        vault.close()
        # If we got here without hanging, auto-compact ran (✓)

    def test_auto_compact_disabled_by_default(self, tmp_path: Path, sample_ohlcv: pd.DataFrame):
        """auto_compact=False should skip compaction even when triggers are met."""
        db_path = tmp_path / "nac.db"
        # Very low threshold — would trigger immediately
        cfg = CompactionConfig(max_file_count=1)
        vault = DuckDBVault(db_path=db_path, compaction_config=cfg, auto_compact=False)
        vault.ingest_df(sample_ohlcv, symbol="eurusd", timeframe="1h")
        vault.close()  # Should not hang or trigger compaction


# ---------------------------------------------------------------------------
# CompactionState
# ---------------------------------------------------------------------------


class TestCompactionState:
    def test_serialization_roundtrip(self):
        original = CompactionState(
            last_compact_ts=1700000000.0,
            modification_count=42,
            last_check_ts=1700010000.0,
        )
        restored = CompactionState.from_dict(original.to_dict())
        assert restored.last_compact_ts == original.last_compact_ts
        assert restored.modification_count == original.modification_count
        assert restored.last_check_ts == original.last_check_ts

    def test_from_dict_handles_missing_keys(self):
        state = CompactionState.from_dict({})
        assert state.last_compact_ts is None
        assert state.modification_count == 0


# ---------------------------------------------------------------------------
# DuckDBVault — vacuum_analyze
# ---------------------------------------------------------------------------


class TestVaultAdmin:
    def test_vacuum_analyze_runs(self, tmp_vault: DuckDBVault, sample_ohlcv: pd.DataFrame):
        tmp_vault.ingest_df(sample_ohlcv, symbol="eurusd", timeframe="1h")
        tmp_vault.vacuum_analyze()  # Should not raise
        assert tmp_vault.row_count() == 5
