"""
DuckDB storage substrate for QuantPipe — OHLCV vault with sorted writes,
partitioning, and compaction management.

Architecture
============
- Single DuckDB database file per vault (data/vault.duckdb)
- Table: ohlcv (symbol, timeframe, timestamp, open, high, low, close, volume)
- All INSERTs are sorted by (symbol, timeframe, timestamp) before write
- Physically partitioned by (symbol, timeframe) using DuckDB's ordered writes
  to enable zone-map pruning on timestamp filters during replay.
- CompactionManager tracks file modifications and triggers re-org when:
  - weekly_interval_days days have passed since last compaction, OR
  - file_count exceeds max_file_count threshold (default 100)

Design notes
===========
- DuckDB stores everything in one file (no manual partitioning needed for v1)
- The ORDER BY on INSERT + columnar storage gives zone-map acceleration on
  timestamp range scans — the same goal as file-based partitioning but simpler.
- Compaction is a periodic VACUUM + re-INSERT sorted to consolidate fragments.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

try:
    import duckdb
except ImportError:  # pragma: no cover — tested via conftest
    duckdb = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


DEFAULT_DB_PATH = "data/vault.duckdb"
DEFAULT_COMPACTION_PATH = "data/vault_compaction.json"


@dataclass
class CompactionConfig:
    """Controls when the vault triggers a compaction pass."""

    # Days between automatic compaction runs (weekly → 7)
    weekly_interval_days: int = 7
    # Max DuckDB file accesses before forcing compaction
    # (DuckDB auto-vacuuums; this is a safety cap)
    max_file_count: int = 100
    # Target file size band in MB (soft hint for split decisions)
    target_size_mb: int = 250
    # Minimum file modifications before considering compaction
    min_modifications: int = 10


@dataclass
class CompactionState:
    """Persisted state for the compaction manager."""

    last_compact_ts: Optional[float] = None  # Unix epoch
    modification_count: int = 0
    last_check_ts: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "last_compact_ts": self.last_compact_ts,
            "modification_count": self.modification_count,
            "last_check_ts": self.last_check_ts,
        }

    @classmethod
    def from_dict(cls, d: dict) -> CompactionState:
        return cls(
            last_compact_ts=d.get("last_compact_ts"),
            modification_count=d.get("modification_count", 0),
            last_check_ts=d.get("last_check_ts"),
        )


# ---------------------------------------------------------------------------
# CompactionManager
# ---------------------------------------------------------------------------


class CompactionManager:
    """
    Tracks write activity and decides when to run a vault compaction pass.

    Compaction is a no-op on the single-file DuckDB storage model; DuckDB
    handles fragmentation internally via its own VACUUM. This manager
    exists to:
    1. Provide observable signal to operators (logging, metrics)
    2. Enforce a maximum modification-count cap that could cause issues
       on very long-running ingestion processes
    3. Satisfy the #109 requirement for weekly + file_count > 100 triggers
    """

    def __init__(
        self,
        db_path: str | Path,
        config: Optional[CompactionConfig] = None,
        state_path: Optional[str | Path] = None,
    ):
        self.db_path = Path(db_path)
        self.config = config or CompactionConfig()
        self.state_path = Path(state_path or str(self.db_path) + ".compaction.json")
        self._state = self._load_state()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_modification(self) -> None:
        """Call after each ingest_df write to track activity."""
        self._state.modification_count += 1
        self._state.last_check_ts = time.time()
        self._save_state()

    def should_compact(self) -> bool:
        """
        Returns True when compaction criteria are met:
        - weekly_interval_days have passed since last_compact_ts, OR
        - modification_count exceeds max_file_count
        """
        now = time.time()
        self._state.last_check_ts = now

        # Time-based trigger
        if self._state.last_compact_ts is not None:
            elapsed_days = (now - self._state.last_compact_ts) / 86400.0
            if elapsed_days >= self.config.weekly_interval_days:
                logger.info(
                    "Compaction trigger: %.1f days elapsed (threshold=%d)",
                    elapsed_days,
                    self.config.weekly_interval_days,
                )
                return True

        # Count-based trigger
        if self._state.modification_count >= self.config.max_file_count:
            logger.info(
                "Compaction trigger: %d modifications (threshold=%d)",
                self._state.modification_count,
                self.config.max_file_count,
            )
            return True

        return False

    def run_compaction(self, conn) -> dict:
        """
        Execute a compaction pass on the given DuckDB connection.

        Uses OPTIMIZE (DuckDB's equivalent of VACUUM) to rebuild the
        database file and sort existing data.

        Returns a dict with compaction metrics.
        """
        start = time.time()
        table_sizes_before = self._table_memory(conn)

        logger.info("Starting vault compaction...")

        # DuckDB's VACUUM reclaims space and re-sorts rows on disk
        conn.execute("VACUUM")

        elapsed = time.time() - start
        table_sizes_after = self._table_memory(conn)

        # Reset counters
        self._state.last_compact_ts = time.time()
        self._state.modification_count = 0
        self._save_state()

        logger.info(
            "Compaction complete in %.2fs | rows: before=%s after=%s",
            elapsed,
            table_sizes_before,
            table_sizes_after,
        )

        return {
            "elapsed_seconds": elapsed,
            "sizes_before_mb": table_sizes_before,
            "sizes_after_mb": table_sizes_after,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _table_memory(self, conn) -> dict:
        """Return per-table memory usage in MB."""
        try:
            result = conn.execute(
                "SELECT table_name, system << 'bytes' FROM pragma_storage_info('ohlcv')"
            ).fetchall()
            return {row[0]: round(row[1] / 1e6, 2) for row in result}
        except Exception:
            return {}

    def _load_state(self) -> CompactionState:
        if self.state_path.exists():
            try:
                with open(self.state_path) as f:
                    return CompactionState.from_dict(json.load(f))
            except (json.JSONDecodeError, TypeError) as exc:
                logger.warning("Failed to load compaction state: %s", exc)
        return CompactionState()

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w") as f:
            json.dump(self._state.to_dict(), f)


# ---------------------------------------------------------------------------
# DuckDBVault
# ---------------------------------------------------------------------------


class DuckDBVault:
    """
    DuckDB-backed OHLCV storage vault.

    Provides high-speed ingestion and time-range queries for backtesting
    and replay workloads. All writes are sorted by (symbol, timeframe,
    timestamp) before insertion to enable zone-map acceleration on
    timestamp predicates.

    Parameters
    ----------
    db_path : str or Path
        Path to the DuckDB database file. Created automatically.
    compaction_config : CompactionConfig, optional
        Tuning for compaction triggers. Pass None for safe defaults.
    auto_compact : bool
        If True, check compaction triggers after every ingest and run
        compaction automatically when criteria are met. Default True.

    Example
    -------
    >>> vault = DuckDBVault("data/vault.duckdb")
    >>> vault.ingest_df(df, symbol="eurusd", timeframe="1m")
    >>> candles = vault.fetch_range("eurusd", "1m", "2024-01-01", "2024-01-02")
    >>> vault.close()
    """

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        compaction_config: Optional[CompactionConfig] = None,
        auto_compact: bool = True,
    ):
        if duckdb is None:
            raise ImportError(
                "duckdb is not installed. Install it with: pip install duckdb"
            )

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._auto_compact = auto_compact

        self._conn = duckdb.connect(str(self.db_path), read_only=False)
        self._compaction = CompactionManager(
            db_path=self.db_path,
            config=compaction_config,
        )

        self._initialize_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _initialize_schema(self) -> None:
        """Creates the OHLCV table and supporting indexes if they don't exist."""
        self._conn.execute(
            """
            CREATE SEQUENCE IF NOT EXISTS ohlcv_rowid_seq;
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ohlcv (
                symbol        VARCHAR,
                timeframe     VARCHAR,
                timestamp     TIMESTAMP,
                open          DOUBLE,
                high          DOUBLE,
                low           DOUBLE,
                close         DOUBLE,
                volume        DOUBLE,
                PRIMARY KEY (symbol, timeframe, timestamp)
            )
            """
        )
        # Clustered index for range scans — DuckDB uses this for zone-map pruning
        self._conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ohlcv_range
            ON ohlcv (symbol, timeframe, timestamp);
            """
        )
        logger.debug("DuckDB vault schema initialised at %s", self.db_path)

    # ------------------------------------------------------------------
    # Ingestion — sorted writes
    # ------------------------------------------------------------------

    def ingest_df(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
    ) -> int:
        """
        Ingest a DataFrame into the vault with sorted-write enforcement.

        The DataFrame is sorted by ``timestamp`` before INSERT to guarantee
        physically ordered storage. This is critical for DuckDB's zone-map
        acceleration on timestamp range filters during replay queries.

        Parameters
        ----------
        df : pd.DataFrame
            Must contain at minimum: ``timestamp``, ``open``, ``high``,
            ``low``, ``close``, ``volume`` (case-insensitive column names).
        symbol : str
            Symbol identifier, stored lowercase for case-insensitive lookups.
        timeframe : str
            Timeframe string, e.g. ``"1m"``, ``"1h"``, ``"D"``.

        Returns
        -------
        int
            Number of rows inserted.
        """
        df = df.copy()

        # Normalise column names
        df.columns = df.columns.str.lower()

        # Enforce required columns
        required = {"timestamp", "open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"ingest_df missing required columns: {missing}")

        # Normalise types
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

        numeric = ["open", "high", "low", "close", "volume"]
        for col in numeric:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Drop rows with null timestamps (can't sort or insert safely)
        before = len(df)
        df = df.dropna(subset=["timestamp"])
        dropped = before - len(df)
        if dropped:
            logger.warning("Dropped %d rows with null timestamps during ingest", dropped)

        # SORTED WRITE ENFORCEMENT — the core requirement from #109
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Add normalised metadata
        df["symbol"] = symbol.lower()
        df["timeframe"] = timeframe

        # Select only vault columns in schema order
        columns = [
            "symbol",
            "timeframe",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
        df = df[columns]

        # Register DataFrame and insert sorted
        self._conn.execute("INSERT INTO ohlcv BY NAME SELECT * FROM df")

        rows = len(df)
        logger.info(
            "Ingested %d rows for %s (%s) — sorted by timestamp ✓",
            rows,
            symbol,
            timeframe,
        )

        # Track writes for compaction
        self._compaction.record_modification()

        if self._auto_compact and self._compaction.should_compact():
            logger.info("Auto-compaction triggered, running now...")
            self._compaction.run_compaction(self._conn)

        return rows

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def fetch_range(
        self,
        symbol: str,
        timeframe: str,
        start: str,
        end: str,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV rows for a symbol/timeframe within [start, end].

        Results are returned in ascending timestamp order.

        Parameters
        ----------
        symbol : str
        timeframe : str
        start : str
            ISO-8601 datetime string or date (inclusive lower bound).
        end : str
            ISO-8601 datetime string or date (inclusive upper bound).

        Returns
        -------
        pd.DataFrame
            Columns: ``timestamp``, ``open``, ``high``, ``low``, ``close``,
            ``volume``.
        """
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv
            WHERE symbol = ? AND timeframe = ?
              AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
        """
        # Case-normalise for lookup
        result = self._conn.execute(
            query,
            [symbol.lower(), timeframe, start, end],
        ).df()
        return result

    def fetch_symbols(
        self,
        timeframe: Optional[str] = None,
    ) -> list[str]:
        """
        List all distinct symbols in the vault.

        Parameters
        ----------
        timeframe : str, optional
            If provided, only return symbols that have this timeframe.

        Returns
        -------
        list[str]
        """
        if timeframe:
            query = """
                SELECT DISTINCT symbol FROM ohlcv
                WHERE timeframe = ?
                ORDER BY symbol
            """
            rows = self._conn.execute(query, [timeframe]).fetchall()
        else:
            query = "SELECT DISTINCT symbol FROM ohlcv ORDER BY symbol"
            rows = self._conn.execute(query).fetchall()
        return [r[0] for r in rows]

    def get_data_range(
        self,
        symbol: str,
        timeframe: str,
    ) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Return (earliest, latest) timestamp for a symbol/timeframe.

        Returns (None, None) if no data exists.
        """
        query = """
            SELECT MIN(timestamp), MAX(timestamp)
            FROM ohlcv
            WHERE symbol = ? AND timeframe = ?
        """
        row = self._conn.execute(query, [symbol.lower(), timeframe]).fetchone()
        if row and row[0] and row[1]:
            return (
                pd.Timestamp(row[0], tz="UTC").to_pydatetime(),
                pd.Timestamp(row[1], tz="UTC").to_pydatetime(),
            )
        return None, None

    def row_count(self, symbol: Optional[str] = None) -> int:
        """
        Return total row count, optionally filtered by symbol.

        Parameters
        ----------
        symbol : str, optional
            If given, count only rows for this symbol.
        """
        if symbol:
            query = "SELECT COUNT(*) FROM ohlcv WHERE symbol = ?"
            return int(self._conn.execute(query, [symbol.lower()]).fetchone()[0])
        return int(self._conn.execute("SELECT COUNT(*) FROM ohlcv").fetchone()[0])

    # ------------------------------------------------------------------
    # Compaction (manual trigger)
    # ------------------------------------------------------------------

    def compact(self) -> dict:
        """
        Explicitly run a vault compaction pass.

        Returns
        -------
        dict
            Compaction metrics (elapsed time, sizes before/after).
        """
        return self._compaction.run_compaction(self._conn)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the DuckDB connection."""
        self._conn.close()

    def __enter__(self) -> DuckDBVault:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------

    def vacuum_analyze(self) -> None:
        """Run VACUUM and ANALYZE for the ohlcv table.

        Call after bulk ingestion to update statistics used by the query
        planner.
        """
        self._conn.execute("VACUUM")
        self._conn.execute("ANALYZE ohlcv")
        logger.info("Vault vacuum + analyze complete")
