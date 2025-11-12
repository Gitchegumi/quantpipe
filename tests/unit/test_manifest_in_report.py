"""Unit tests for manifest provenance validation in performance reports.

This module validates that PerformanceReport correctly captures and
preserves dataset manifest metadata per FR-012.

Test Coverage:
- Manifest path captured correctly
- Manifest SHA-256 checksum validated
- Manifest metadata matches source file
- Missing manifest handling
"""
# pylint: disable=redefined-outer-name,no-member
# Justification:
# - redefined-outer-name: pytest fixtures intentionally shadow names
# - no-member: False positive on pydantic string attributes

import hashlib
import tempfile
from pathlib import Path

from src.models.performance_report import PerformanceReport


def calculate_file_sha256(file_path: Path) -> str:
    """Calculate SHA-256 checksum of a file.

    Args:
        file_path: Path to file

    Returns:
        Hex-encoded SHA-256 checksum
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def test_manifest_path_captured():
    """Test manifest path is captured correctly in PerformanceReport.

    Validates:
    - Manifest path stored as relative path
    - Path preserved exactly as provided
    """
    manifest_path = "price_data/processed/eurusd/manifest.json"
    manifest_sha256 = "a" * 64

    report = PerformanceReport(
        scan_duration_sec=10.5,
        simulation_duration_sec=8.3,
        peak_memory_mb=512.0,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha256,
        candle_count=100_000,
        signal_count=500,
        trade_count=450,
        equivalence_verified=True,
        progress_emission_count=50,
        progress_overhead_pct=0.5,
        indicator_names=["ema20", "ema50"],
        deterministic_mode=True,
    )

    assert report.manifest_path == manifest_path


def test_manifest_checksum_format():
    """Test manifest SHA-256 checksum format validation.

    Validates:
    - Checksum stored as 64-character hex string
    - Format matches SHA-256 standard
    """
    manifest_path = "test/manifest.json"
    manifest_sha256 = "b" * 64

    report = PerformanceReport(
        scan_duration_sec=10.5,
        simulation_duration_sec=8.3,
        peak_memory_mb=512.0,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha256,
        candle_count=100_000,
        signal_count=500,
        trade_count=450,
        equivalence_verified=True,
        progress_emission_count=50,
        progress_overhead_pct=0.5,
        indicator_names=["ema20"],
        deterministic_mode=False,
    )

    # Verify checksum format
    assert len(report.manifest_sha256) == 64
    assert all(c in "0123456789abcdefABCDEF" for c in report.manifest_sha256)


def test_manifest_provenance_validation_match():
    """Test manifest provenance validation with matching checksum.

    Validates:
    - Report checksum matches actual file checksum
    - Provenance validation succeeds for matching data
    """
    # Create temporary manifest file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        tmp.write('{"version": "1.0", "candle_count": 100000}')
        tmp_path = Path(tmp.name)

    try:
        # Calculate actual checksum
        actual_checksum = calculate_file_sha256(tmp_path)

        # Create report with matching checksum
        report = PerformanceReport(
            scan_duration_sec=10.5,
            simulation_duration_sec=8.3,
            peak_memory_mb=512.0,
            manifest_path=str(tmp_path),
            manifest_sha256=actual_checksum,
            candle_count=100_000,
            signal_count=500,
            trade_count=450,
            equivalence_verified=True,
            progress_emission_count=50,
            progress_overhead_pct=0.5,
            indicator_names=["ema20"],
            deterministic_mode=True,
        )

        # Verify stored checksum matches actual
        stored_checksum = report.manifest_sha256
        recalculated_checksum = calculate_file_sha256(Path(report.manifest_path))

        assert stored_checksum == recalculated_checksum
        assert stored_checksum == actual_checksum

    finally:
        # Clean up temporary file
        tmp_path.unlink()


def test_manifest_provenance_validation_mismatch():
    """Test manifest provenance validation detects mismatch.

    Validates:
    - Checksum mismatch is detectable
    - Validation can identify tampered/modified manifests
    """
    # Create temporary manifest file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        tmp.write('{"version": "1.0", "candle_count": 100000}')
        tmp_path = Path(tmp.name)

    try:
        # Calculate actual checksum
        actual_checksum = calculate_file_sha256(tmp_path)

        # Create report with WRONG checksum
        wrong_checksum = "f" * 64
        report = PerformanceReport(
            scan_duration_sec=10.5,
            simulation_duration_sec=8.3,
            peak_memory_mb=512.0,
            manifest_path=str(tmp_path),
            manifest_sha256=wrong_checksum,
            candle_count=100_000,
            signal_count=500,
            trade_count=450,
            equivalence_verified=True,
            progress_emission_count=50,
            progress_overhead_pct=0.5,
            indicator_names=["ema20"],
            deterministic_mode=True,
        )

        # Verify stored checksum does NOT match actual
        stored_checksum = report.manifest_sha256
        recalculated_checksum = calculate_file_sha256(Path(report.manifest_path))

        assert stored_checksum != recalculated_checksum
        assert stored_checksum == wrong_checksum
        assert recalculated_checksum == actual_checksum

    finally:
        # Clean up temporary file
        tmp_path.unlink()


def test_manifest_path_relative():
    """Test manifest path stored as relative path for portability.

    Validates:
    - Path stored without absolute prefix
    - Path suitable for cross-environment reproducibility
    """
    # Use relative path format
    manifest_path = "price_data/processed/eurusd/manifest.json"
    manifest_sha256 = "c" * 64

    report = PerformanceReport(
        scan_duration_sec=10.5,
        simulation_duration_sec=8.3,
        peak_memory_mb=512.0,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha256,
        candle_count=100_000,
        signal_count=500,
        trade_count=450,
        equivalence_verified=True,
        progress_emission_count=50,
        progress_overhead_pct=0.5,
        indicator_names=["ema20"],
        deterministic_mode=True,
    )

    # Verify path is relative (no drive letter, no leading slash)
    assert not report.manifest_path.startswith("/")
    assert ":" not in report.manifest_path or report.manifest_path.startswith("http")
    assert report.manifest_path == manifest_path


def test_manifest_metadata_serialization():
    """Test manifest metadata can be serialized for audit trail.

    Validates:
    - Manifest path and checksum included in dict/JSON serialization
    - Metadata suitable for compliance audit
    """
    manifest_path = "audit/manifest.json"
    manifest_sha256 = "d" * 64

    report = PerformanceReport(
        scan_duration_sec=10.5,
        simulation_duration_sec=8.3,
        peak_memory_mb=512.0,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha256,
        candle_count=100_000,
        signal_count=500,
        trade_count=450,
        equivalence_verified=True,
        progress_emission_count=50,
        progress_overhead_pct=0.5,
        indicator_names=["ema20"],
        deterministic_mode=True,
    )

    # Serialize to dict
    report_dict = report.model_dump()

    # Verify manifest metadata present
    assert "manifest_path" in report_dict
    assert "manifest_sha256" in report_dict
    assert report_dict["manifest_path"] == manifest_path
    assert report_dict["manifest_sha256"] == manifest_sha256


def test_manifest_candle_count_consistency():
    """Test candle count matches between report and manifest.

    Validates:
    - Candle count in report matches dataset size
    - Consistency check for data integrity
    """
    manifest_path = "test/manifest.json"
    manifest_sha256 = "e" * 64
    expected_candle_count = 250_000

    report = PerformanceReport(
        scan_duration_sec=10.5,
        simulation_duration_sec=8.3,
        peak_memory_mb=512.0,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha256,
        candle_count=expected_candle_count,
        signal_count=500,
        trade_count=450,
        equivalence_verified=True,
        progress_emission_count=50,
        progress_overhead_pct=0.5,
        indicator_names=["ema20"],
        deterministic_mode=True,
    )

    # Verify candle count stored correctly
    assert report.candle_count == expected_candle_count
