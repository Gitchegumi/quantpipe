"""Unit tests for snapshot logger interval behavior.

Tests verify:
- Snapshot writes at correct intervals
- Bar counter tracking
- Force record functionality
- Context manager behavior
- JSONL format output
"""
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.backtest.portfolio.snapshot_logger import SnapshotLogger
from src.models.snapshots import PortfolioSnapshotRecord


class TestSnapshotInterval:
    """Test snapshot logger interval recording behavior."""

    def test_snapshot_written_at_interval(self, tmp_path):
        """Verify snapshot written at exact interval boundaries."""
        output_file = tmp_path / "snapshots.jsonl"
        logger = SnapshotLogger(output_path=output_file, interval=10)

        with logger:
            # Record 9 snapshots - none should be written
            for i in range(9):
                snapshot = PortfolioSnapshotRecord(
                    t=datetime.now(UTC),
                    portfolio_pnl=float(i),
                )
                logger.record(snapshot)

            # No file should have content yet
            assert output_file.stat().st_size == 0

            # 10th snapshot should trigger write
            snapshot = PortfolioSnapshotRecord(
                t=datetime.now(UTC),
                portfolio_pnl=10.0,
            )
            logger.record(snapshot)

            # Now file should have one line
            with open(output_file, encoding="utf-8") as f:
                lines = f.readlines()
                assert len(lines) == 1

    def test_multiple_intervals_written(self, tmp_path):
        """Verify snapshots written at each interval boundary."""
        output_file = tmp_path / "snapshots.jsonl"
        logger = SnapshotLogger(output_path=output_file, interval=5)

        with logger:
            # Record 23 snapshots - should write at 5, 10, 15, 20
            for i in range(23):
                snapshot = PortfolioSnapshotRecord(
                    t=datetime.now(UTC),
                    portfolio_pnl=float(i),
                )
                logger.record(snapshot)

        # Should have 4 lines (bars 5, 10, 15, 20)
        with open(output_file, encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 4

    def test_force_record_bypasses_interval(self, tmp_path):
        """Verify force_record writes regardless of interval."""
        output_file = tmp_path / "snapshots.jsonl"
        logger = SnapshotLogger(output_path=output_file, interval=100)

        with logger:
            # Force record at bar 1 (before interval)
            snapshot = PortfolioSnapshotRecord(
                t=datetime.now(UTC),
                portfolio_pnl=100.0,
            )
            logger.force_record(snapshot)

        # Should have 1 line despite not reaching interval
        with open(output_file, encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1

    def test_bar_counter_increments_correctly(self, tmp_path):
        """Verify bar counter increments with each record call."""
        output_file = tmp_path / "snapshots.jsonl"
        logger = SnapshotLogger(output_path=output_file, interval=10)

        with logger:
            assert logger.get_bar_count() == 0

            for i in range(5):
                snapshot = PortfolioSnapshotRecord(t=datetime.now(UTC))
                logger.record(snapshot)
                assert logger.get_bar_count() == i + 1

    def test_reset_bar_count(self, tmp_path):
        """Verify bar counter can be reset."""
        output_file = tmp_path / "snapshots.jsonl"
        logger = SnapshotLogger(output_path=output_file, interval=10)

        with logger:
            # Record some snapshots
            for _ in range(5):
                snapshot = PortfolioSnapshotRecord(t=datetime.now(UTC))
                logger.record(snapshot)

            assert logger.get_bar_count() == 5

            # Reset counter
            logger.reset_bar_count()
            assert logger.get_bar_count() == 0

    def test_jsonl_format_valid(self, tmp_path):
        """Verify output is valid JSON Lines format."""
        output_file = tmp_path / "snapshots.jsonl"
        logger = SnapshotLogger(output_path=output_file, interval=1)

        timestamp = datetime.now(UTC)
        snapshot = PortfolioSnapshotRecord(
            t=timestamp,
            positions={"EURUSD": 10000.0, "GBPUSD": 5000.0},
            unrealized={"EURUSD": 150.0, "GBPUSD": -50.0},
            portfolio_pnl=100.0,
            exposure=0.75,
            diversification_ratio=0.8,
            corr_window=50,
        )

        with logger:
            logger.record(snapshot)

        # Read and parse JSON
        with open(output_file, encoding="utf-8") as f:
            line = f.readline()
            data = json.loads(line)

        # Verify all fields present
        assert "t" in data
        assert data["positions"] == {"EURUSD": 10000.0, "GBPUSD": 5000.0}
        assert data["unrealized"] == {"EURUSD": 150.0, "GBPUSD": -50.0}
        assert data["portfolio_pnl"] == 100.0
        assert data["exposure"] == 0.75
        assert data["diversification_ratio"] == 0.8
        assert data["corr_window"] == 50

    def test_context_manager_creates_file(self, tmp_path):
        """Verify context manager creates output file."""
        output_file = tmp_path / "snapshots.jsonl"
        logger = SnapshotLogger(output_path=output_file, interval=10)

        assert not output_file.exists()

        with logger:
            snapshot = PortfolioSnapshotRecord(t=datetime.now(UTC))
            logger.force_record(snapshot)

        assert output_file.exists()

    def test_context_manager_closes_file(self, tmp_path):
        """Verify context manager closes file handle."""
        output_file = tmp_path / "snapshots.jsonl"
        logger = SnapshotLogger(output_path=output_file, interval=10)

        with logger:
            assert logger.file_handle is not None

        # File should be closed after context exit
        assert logger.file_handle is None

    def test_creates_parent_directories(self, tmp_path):
        """Verify parent directories created if needed."""
        output_file = tmp_path / "nested" / "dir" / "snapshots.jsonl"
        logger = SnapshotLogger(output_path=output_file, interval=10)

        assert not output_file.parent.exists()

        with logger:
            snapshot = PortfolioSnapshotRecord(t=datetime.now(UTC))
            logger.force_record(snapshot)

        assert output_file.parent.exists()
        assert output_file.exists()

    def test_invalid_interval_raises_error(self):
        """Verify ValueError raised for invalid interval."""
        with pytest.raises(ValueError, match="interval must be >= 1"):
            SnapshotLogger(output_path=Path("test.jsonl"), interval=0)

        with pytest.raises(ValueError, match="interval must be >= 1"):
            SnapshotLogger(output_path=Path("test.jsonl"), interval=-5)

    def test_multiple_snapshots_different_data(self, tmp_path):
        """Verify multiple snapshots with different data written correctly."""
        output_file = tmp_path / "snapshots.jsonl"
        logger = SnapshotLogger(output_path=output_file, interval=2)

        snapshots_data = [
            {"pnl": 100.0, "exposure": 0.5},
            {"pnl": 150.0, "exposure": 0.6},
            {"pnl": 200.0, "exposure": 0.7},
        ]

        with logger:
            for data in snapshots_data:
                snapshot = PortfolioSnapshotRecord(
                    t=datetime.now(UTC),
                    portfolio_pnl=data["pnl"],
                    exposure=data["exposure"],
                )
                logger.record(snapshot)

        # Should have 1 snapshot (at bar 2)
        with open(output_file, encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1

            # Verify it's the second snapshot
            data = json.loads(lines[0])
            assert data["portfolio_pnl"] == 150.0
            assert data["exposure"] == 0.6

    def test_force_record_increments_bar_count(self, tmp_path):
        """Verify force_record does NOT increment bar counter."""
        output_file = tmp_path / "snapshots.jsonl"
        logger = SnapshotLogger(output_path=output_file, interval=10)

        with logger:
            snapshot = PortfolioSnapshotRecord(t=datetime.now(UTC))

            # Force record should not affect counter
            logger.force_record(snapshot)
            assert logger.get_bar_count() == 0

            # Regular record should increment
            logger.record(snapshot)
            assert logger.get_bar_count() == 1
