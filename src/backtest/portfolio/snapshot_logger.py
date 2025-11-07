"""Portfolio snapshot logger for periodic state recording.

This module provides JSONL-based snapshot logging for portfolio backtesting.
Records are written at configurable intervals capturing correlation matrix,
allocations, positions, and portfolio metrics.

Per research Decision 7 and FR-022.
"""
import json
import logging
from pathlib import Path
from typing import Optional, TextIO

from src.models.snapshots import PortfolioSnapshotRecord

logger = logging.getLogger(__name__)


class SnapshotLogger:
    """Logs portfolio snapshots to JSONL file at configurable intervals.

    Maintains periodic state records during portfolio execution including
    positions, PnL, exposure, correlation state, and diversification metrics.

    Attributes:
        output_path: Path to JSONL output file
        interval: Snapshot recording interval in bars (e.g., 100)
        file_handle: Open file handle for writing
        bar_count: Current bar counter for interval tracking
    """

    def __init__(self, output_path: Path, interval: int = 100):
        """Initialize snapshot logger.

        Args:
            output_path: Path to JSONL output file
            interval: Snapshot recording interval in bars (default 100)

        Raises:
            ValueError: If interval < 1
        """
        if interval < 1:
            raise ValueError(f"interval must be >= 1, got {interval}")

        self.output_path = output_path
        self.interval = interval
        self.file_handle: Optional[TextIO] = None
        self.bar_count = 0

        logger.info(
            "Initialized snapshot logger: %s (interval=%d bars)",
            output_path,
            interval,
        )

    def open(self) -> None:
        """Open snapshot file for writing.

        Creates parent directories if needed.
        """
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        # pylint: disable=consider-using-with,R1732
        self.file_handle = open(self.output_path, "w", encoding="utf-8")
        logger.info("Opened snapshot log: %s", self.output_path)

    def close(self) -> None:
        """Close snapshot file."""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None
            logger.info("Closed snapshot log: %s", self.output_path)

    def record(self, snapshot: PortfolioSnapshotRecord) -> None:
        """Record a snapshot if interval reached.

        Increments bar counter and writes snapshot if at interval boundary.

        Args:
            snapshot: PortfolioSnapshotRecord to log
        """
        self.bar_count += 1

        if self.bar_count % self.interval == 0:
            self._write_snapshot(snapshot)

    def force_record(self, snapshot: PortfolioSnapshotRecord) -> None:
        """Force record a snapshot regardless of interval.

        Useful for recording final state or on-demand snapshots.

        Args:
            snapshot: PortfolioSnapshotRecord to log
        """
        self._write_snapshot(snapshot)

    def _write_snapshot(self, snapshot: PortfolioSnapshotRecord) -> None:
        """Write snapshot record to JSONL file.

        Args:
            snapshot: PortfolioSnapshotRecord to write
        """
        if not self.file_handle:
            logger.warning("Attempted to write snapshot with closed file handle")
            return

        json_dict = snapshot.to_json_dict()
        json_line = json.dumps(json_dict, ensure_ascii=False)
        self.file_handle.write(json_line + "\n")
        self.file_handle.flush()

        logger.debug(
            "Wrote snapshot at bar %d: t=%s, pnl=%.2f",
            self.bar_count,
            snapshot.t.isoformat(),
            snapshot.portfolio_pnl,
        )

    def get_bar_count(self) -> int:
        """Get current bar count.

        Returns:
            Current bar counter value
        """
        return self.bar_count

    def reset_bar_count(self) -> None:
        """Reset bar counter to zero.

        Useful for restarting interval tracking.
        """
        self.bar_count = 0
        logger.debug("Reset snapshot bar counter")

    def __enter__(self):
        """Context manager entry - opens snapshot file."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes snapshot file."""
        self.close()
        return False
