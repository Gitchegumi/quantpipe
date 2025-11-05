"""
Integration tests for manifest error handling (US3).

This module tests error paths related to manifest file operations:
- Missing manifest file
- Invalid manifest format
- Manifest checksum mismatch
- Manifest field validation errors

These tests ensure graceful degradation and informative error messages
when manifest operations fail, as required by US3.
"""

import json
from pathlib import Path

import pytest

from src.io.manifest import load_manifest
from src.models.exceptions import DataIntegrityError

pytestmark = pytest.mark.integration


def test_manifest_file_not_found(tmp_path: Path):
    """
    Test that loading a non-existent manifest raises appropriate error.

    Validates:
    - FileNotFoundError is raised
    - Error message includes file path
    """
    nonexistent_path = tmp_path / "missing_manifest.json"

    with pytest.raises(FileNotFoundError) as exc_info:
        load_manifest(nonexistent_path)

    assert "missing_manifest.json" in str(exc_info.value)


def test_manifest_invalid_json(tmp_path: Path):
    """
    Test that malformed JSON in manifest raises appropriate error.

    Validates:
    - DataIntegrityError is raised for invalid JSON
    - Error message indicates JSON parsing failure
    """
    manifest_path = tmp_path / "invalid.json"
    manifest_path.write_text("{ invalid json content }")

    with pytest.raises(DataIntegrityError) as exc_info:
        load_manifest(manifest_path)

    assert "JSON" in str(exc_info.value) or "parse" in str(exc_info.value).lower()


def test_manifest_missing_required_fields(tmp_path: Path):
    """
    Test that manifest with missing required fields raises error.

    Validates:
    - DataIntegrityError is raised
    - Error identifies missing fields
    """
    manifest_path = tmp_path / "incomplete_manifest.json"

    # Missing critical fields like 'pair', 'timeframe', etc.
    incomplete_data = {
        "pair": "EURUSD",
        # Missing timeframe, date_range_start, etc.
    }

    manifest_path.write_text(json.dumps(incomplete_data))

    with pytest.raises(DataIntegrityError) as exc_info:
        load_manifest(manifest_path)

    error_msg = str(exc_info.value).lower()
    assert "missing" in error_msg or "required" in error_msg


def test_manifest_invalid_date_format(tmp_path: Path):
    """
    Test that manifest with invalid date format raises error.

    Validates:
    - DataIntegrityError is raised
    - Error indicates date parsing issue
    """
    manifest_path = tmp_path / "bad_dates_manifest.json"

    bad_manifest = {
        "pair": "EURUSD",
        "timeframe": "1m",
        "date_range_start": "not-a-date",  # Invalid format
        "date_range_end": "2024-12-31T23:59:59Z",
        "source_provider": "TestProvider",
        "checksum": "abc123",
        "preprocessing_notes": "None",
        "total_candles": 1000,
        "file_path": "/data/test.csv",
    }

    manifest_path.write_text(json.dumps(bad_manifest))

    with pytest.raises(DataIntegrityError) as exc_info:
        load_manifest(manifest_path)

    error_msg = str(exc_info.value).lower()
    assert "date" in error_msg or "time" in error_msg or "iso" in error_msg


def test_manifest_checksum_mismatch(tmp_path: Path):
    """
    Test that data file checksum mismatch is detected.

    Validates:
    - DataIntegrityError raised when actual file hash != manifest checksum
    - Error message indicates checksum mismatch
    """
    # Create test data file
    data_file = tmp_path / "test_data.csv"
    data_file.write_text("timestamp_utc,open,high,low,close,volume\n")
    with data_file.open(mode="a") as f:
        f.write("2024-01-01 00:00:00,1.1000,1.1010,1.0990,1.1005,1000\n")

    # Create manifest with incorrect checksum
    manifest_path = tmp_path / "manifest.json"
    manifest_data = {
        "pair": "EURUSD",
        "timeframe": "1m",
        "date_range_start": "2024-01-01T00:00:00Z",
        "date_range_end": "2024-01-01T00:01:00Z",
        "source_provider": "TestProvider",
        "checksum": "wrong_checksum_value",  # Intentionally incorrect
        "preprocessing_notes": "None",
        "total_candles": 1,
        "file_path": str(data_file),
    }

    manifest_path.write_text(json.dumps(manifest_data))

    # load_manifest with verify_checksum=True should detect mismatch
    with pytest.raises(DataIntegrityError) as exc_info:
        load_manifest(manifest_path, verify_checksum=True)

    error_msg = str(exc_info.value).lower()
    assert "checksum" in error_msg or "hash" in error_msg


def test_manifest_negative_total_candles(tmp_path: Path):
    """
    Test that manifest with invalid total_candles value raises error.

    Validates:
    - DataIntegrityError raised for negative candle count
    - Error identifies invalid field value
    """
    manifest_path = tmp_path / "negative_candles.json"

    invalid_manifest = {
        "pair": "EURUSD",
        "timeframe": "1m",
        "date_range_start": "2024-01-01T00:00:00Z",
        "date_range_end": "2024-01-01T00:01:00Z",
        "source_provider": "TestProvider",
        "checksum": "abc123",
        "preprocessing_notes": "None",
        "total_candles": -100,  # Invalid: negative count
        "file_path": "/data/test.csv",
    }

    manifest_path.write_text(json.dumps(invalid_manifest))

    with pytest.raises(DataIntegrityError) as exc_info:
        load_manifest(manifest_path)

    error_msg = str(exc_info.value).lower()
    assert "candle" in error_msg or "negative" in error_msg or "invalid" in error_msg


def test_manifest_data_file_not_found(tmp_path: Path):
    """
    Test that manifest pointing to non-existent data file is detected.

    Validates:
    - DataIntegrityError raised when referenced data file missing
    - Error identifies file path issue
    """
    manifest_path = tmp_path / "manifest.json"

    manifest_data = {
        "pair": "EURUSD",
        "timeframe": "1m",
        "date_range_start": "2024-01-01T00:00:00Z",
        "date_range_end": "2024-01-01T00:01:00Z",
        "source_provider": "TestProvider",
        "checksum": "abc123",
        "preprocessing_notes": "None",
        "total_candles": 1000,
        "file_path": "/nonexistent/path/data.csv",  # Does not exist
    }

    manifest_path.write_text(json.dumps(manifest_data))

    # load_manifest with verify_checksum=True will try to access file
    with pytest.raises((DataIntegrityError, FileNotFoundError)) as exc_info:
        load_manifest(manifest_path, verify_checksum=True)

    error_msg = str(exc_info.value).lower()
    assert "file" in error_msg or "path" in error_msg or "not found" in error_msg


def test_manifest_date_range_inverted(tmp_path: Path):
    """
    Test that manifest with end date before start date is loaded.

    Note: Date range validation should be done at ingestion time,
    not manifest load time. This test verifies manifest loads successfully
    but documents the issue for downstream validation.

    Validates:
    - Manifest loads despite inverted dates
    - Downstream code responsible for date validation
    """
    manifest_path = tmp_path / "inverted_dates.json"

    # Create dummy data file so manifest can reference it
    data_file = tmp_path / "test.csv"
    data_file.write_text("timestamp_utc,open,high,low,close,volume\n")

    # Note: This is intentionally invalid but manifest.py may not validate it
    invalid_manifest = {
        "pair": "EURUSD",
        "timeframe": "1m",
        "start_date": "2024-12-31",  # After end
        "end_date": "2024-01-01",  # Before start
        "source_provider": "TestProvider",
        "checksum": "abc123",
        "preprocessing_notes": "None",
        "total_candles": 1000,
        "file_path": str(data_file),
    }

    manifest_path.write_text(json.dumps(invalid_manifest))

    # Load without checksum verification (file doesn't exist)
    manifest = load_manifest(manifest_path, verify_checksum=False)

    # Manifest loads successfully, date validation is downstream responsibility
    assert manifest.pair == "EURUSD"
    # Date inversion should be caught during backtest, not here


def test_manifest_successful_load(tmp_path: Path):
    """
    Test that valid manifest loads successfully.

    Validates:
    - No errors raised for properly formatted manifest
    - All fields correctly populated in DataManifest object
    """
    # Create valid data file
    data_file = tmp_path / "valid_data.csv"
    data_file.write_text("timestamp_utc,open,high,low,close,volume\n")
    with data_file.open(mode="a") as f:
        f.write("2024-01-01 00:00:00,1.1000,1.1010,1.0990,1.1005,1000\n")

    import hashlib

    checksum = hashlib.sha256(data_file.read_bytes()).hexdigest()

    manifest_path = tmp_path / "valid_manifest.json"
    manifest_data = {
        "pair": "EURUSD",
        "timeframe": "1m",
        "start_date": "2024-01-01",
        "end_date": "2024-01-01",
        "source_provider": "TestProvider",
        "checksum": checksum,
        "preprocessing_notes": "UTC normalization applied",
        "total_candles": 1,
        "file_path": str(data_file),
    }

    manifest_path.write_text(json.dumps(manifest_data))

    # Should load without errors (with checksum verification)
    manifest = load_manifest(manifest_path, verify_checksum=True)

    assert manifest.pair == "EURUSD"
    assert manifest.timeframe == "1m"
    assert manifest.total_candles == 1
    assert manifest.checksum == checksum
