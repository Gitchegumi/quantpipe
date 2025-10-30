pytestmark = pytest.mark.unit
"""
Unit tests for manifest loading and validation.

Tests manifest file parsing, checksum verification, and error handling for
missing or corrupt manifest/data files.
"""

import hashlib
import json
from pathlib import Path

import pytest

from src.io.manifest import _compute_file_checksum, create_manifest, load_manifest
from src.models.exceptions import DataIntegrityError


class TestLoadManifest:
    """Test suite for manifest loading and validation."""

    def test_load_manifest_success(self, tmp_path: Path):
        """Test successful manifest loading with valid checksum."""
        # Create test data file
        data_file = tmp_path / "data.csv"
        data_file.write_text("timestamp_utc,open,high,low,close,volume\n")
        data_file.write_text("2025-01-01 00:00:00,1.1,1.11,1.09,1.1,1000\n")

        # Compute checksum
        checksum = _compute_file_checksum(data_file)

        # Create manifest
        manifest_file = tmp_path / "manifest.json"
        manifest_data = {
            "pair": "EURUSD",
            "timeframe": "M5",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "source_provider": "HistData.com",
            "checksum": checksum,
            "preprocessing_notes": "None",
            "total_candles": 1,
            "file_path": "data.csv",
        }
        manifest_file.write_text(json.dumps(manifest_data, indent=2))

        # Load manifest
        manifest = load_manifest(manifest_file, verify_checksum=True)

        assert manifest.pair == "EURUSD"
        assert manifest.timeframe == "M5"
        assert manifest.total_candles == 1
        assert manifest.checksum == checksum

    def test_load_manifest_checksum_mismatch(self, tmp_path: Path):
        """Test manifest loading fails on checksum mismatch."""
        # Create test data file
        data_file = tmp_path / "data.csv"
        data_file.write_text("timestamp_utc,open,high,low,close,volume\n")

        # Create manifest with wrong checksum
        manifest_file = tmp_path / "manifest.json"
        manifest_data = {
            "pair": "EURUSD",
            "timeframe": "M5",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "source_provider": "HistData.com",
            "checksum": "wrong_checksum_12345",
            "preprocessing_notes": "None",
            "total_candles": 1,
            "file_path": "data.csv",
        }
        manifest_file.write_text(json.dumps(manifest_data, indent=2))

        # Should raise DataIntegrityError
        with pytest.raises(DataIntegrityError, match="checksum mismatch"):
            load_manifest(manifest_file, verify_checksum=True)

    def test_load_manifest_skip_checksum(self, tmp_path: Path):
        """Test manifest loading succeeds when checksum verification skipped."""
        # Create test data file
        data_file = tmp_path / "data.csv"
        data_file.write_text("timestamp_utc,open,high,low,close,volume\n")

        # Create manifest with wrong checksum
        manifest_file = tmp_path / "manifest.json"
        manifest_data = {
            "pair": "EURUSD",
            "timeframe": "M5",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "source_provider": "HistData.com",
            "checksum": "wrong_checksum",
            "preprocessing_notes": "None",
            "total_candles": 1,
            "file_path": "data.csv",
        }
        manifest_file.write_text(json.dumps(manifest_data, indent=2))

        # Should succeed when verification disabled
        manifest = load_manifest(manifest_file, verify_checksum=False)
        assert manifest.pair == "EURUSD"

    def test_load_manifest_missing_file(self, tmp_path: Path):
        """Test manifest loading fails when manifest file missing."""
        manifest_file = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            load_manifest(manifest_file)

    def test_load_manifest_invalid_json(self, tmp_path: Path):
        """Test manifest loading fails on malformed JSON."""
        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text("{ invalid json }")

        with pytest.raises(DataIntegrityError, match="Invalid JSON"):
            load_manifest(manifest_file)

    def test_load_manifest_missing_fields(self, tmp_path: Path):
        """Test manifest loading fails when required fields missing."""
        manifest_file = tmp_path / "manifest.json"
        manifest_data = {
            "pair": "EURUSD",
            # Missing: timeframe, dates, checksum, etc.
        }
        manifest_file.write_text(json.dumps(manifest_data, indent=2))

        with pytest.raises(DataIntegrityError, match="Missing required"):
            load_manifest(manifest_file)

    def test_load_manifest_data_file_missing(self, tmp_path: Path):
        """Test manifest loading fails when referenced data file missing."""
        manifest_file = tmp_path / "manifest.json"
        manifest_data = {
            "pair": "EURUSD",
            "timeframe": "M5",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "source_provider": "HistData.com",
            "checksum": "abc123",
            "preprocessing_notes": "None",
            "total_candles": 1,
            "file_path": "missing_data.csv",  # Doesn't exist
        }
        manifest_file.write_text(json.dumps(manifest_data, indent=2))

        with pytest.raises(DataIntegrityError, match="Data file.*not found"):
            load_manifest(manifest_file)


class TestCreateManifest:
    """Test suite for manifest creation."""

    def test_create_manifest_success(self, tmp_path: Path):
        """Test successful manifest creation."""
        # Create test data file
        data_file = tmp_path / "data.csv"
        data_content = "timestamp_utc,open,high,low,close,volume\n"
        data_file.write_text(data_content)

        # Create manifest
        manifest_file = tmp_path / "manifest.json"
        manifest = create_manifest(
            data_file_path=data_file,
            pair="EURUSD",
            timeframe="M5",
            start_date="2025-01-01",
            end_date="2025-01-31",
            source_provider="HistData.com",
            preprocessing_notes="None",
            total_candles=1,
            output_path=manifest_file,
        )

        # Verify manifest object
        assert manifest.pair == "EURUSD"
        assert manifest.timeframe == "M5"
        assert manifest.total_candles == 1
        assert len(manifest.checksum) == 64  # SHA-256 hex length

        # Verify JSON file was created
        assert manifest_file.exists()

        # Load and verify JSON content
        with open(manifest_file) as f:
            manifest_data = json.load(f)
        assert manifest_data["pair"] == "EURUSD"
        assert manifest_data["checksum"] == manifest.checksum

    def test_create_manifest_missing_data_file(self, tmp_path: Path):
        """Test manifest creation fails when data file missing."""
        data_file = tmp_path / "nonexistent.csv"
        manifest_file = tmp_path / "manifest.json"

        with pytest.raises(FileNotFoundError):
            create_manifest(
                data_file_path=data_file,
                pair="EURUSD",
                timeframe="M5",
                start_date="2025-01-01",
                end_date="2025-01-31",
                source_provider="HistData.com",
                preprocessing_notes="None",
                total_candles=0,
                output_path=manifest_file,
            )


class TestComputeFileChecksum:
    """Test suite for file checksum computation."""

    def test_compute_checksum_consistent(self, tmp_path: Path):
        """Test checksum is consistent for same file content."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        content = "test content"
        file1.write_text(content)
        file2.write_text(content)

        checksum1 = _compute_file_checksum(file1)
        checksum2 = _compute_file_checksum(file2)

        assert checksum1 == checksum2
        assert len(checksum1) == 64  # SHA-256 hex length

    def test_compute_checksum_different_content(self, tmp_path: Path):
        """Test checksum differs for different content."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("content A")
        file2.write_text("content B")

        checksum1 = _compute_file_checksum(file1)
        checksum2 = _compute_file_checksum(file2)

        assert checksum1 != checksum2

    def test_compute_checksum_missing_file(self, tmp_path: Path):
        """Test checksum computation fails for missing file."""
        file_path = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            _compute_file_checksum(file_path)

    def test_compute_checksum_empty_file(self, tmp_path: Path):
        """Test checksum computation for empty file."""
        file_path = tmp_path / "empty.txt"
        file_path.write_text("")

        checksum = _compute_file_checksum(file_path)

        # Empty file has a known SHA-256 hash
        expected = hashlib.sha256(b"").hexdigest()
        assert checksum == expected
