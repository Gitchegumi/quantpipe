"""
Manifest provenance tests for Spec 010.

Validates Manifest model fields for dataset provenance tracking:
checksum, path, schema_version. Tests serialization/deserialization.

Test Coverage:
- T051: Manifest model field validation (checksums, paths, counts)
- T051: Manifest immutability (frozen model)
- T051: Manifest serialization to JSON
- T051: Manifest deserialization from JSON
- T051: Manifest schema version compatibility
- T051: Manifest checksum validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.io.ingestion.manifest import Manifest


def test_manifest_required_fields():
    """
    T051: Validate Manifest model requires all critical fields.

    Ensures dataset_path, manifest_sha256, dataset_sha256, candle_count,
    schema_fingerprint, and created_at are required.
    """
    # Act & Assert: Missing required fields raises ValidationError
    with pytest.raises(ValidationError) as exc_info:
        Manifest()

    # Assert: Error message mentions required fields
    error_msg = str(exc_info.value)
    assert "dataset_path" in error_msg
    assert "manifest_sha256" in error_msg
    assert "dataset_sha256" in error_msg
    assert "candle_count" in error_msg
    assert "schema_fingerprint" in error_msg
    assert "created_at" in error_msg


def test_manifest_checksum_validation():
    """
    T051: Validate Manifest checksum fields require 64-char SHA-256 hashes.

    Tests manifest_sha256 and dataset_sha256 length constraints.
    """
    # Arrange: Valid 64-char SHA-256 hash
    valid_sha256 = "a" * 64

    # Act: Create valid manifest
    manifest = Manifest(
        dataset_path="price_data/processed/eurusd/eurusd_2020.parquet",
        manifest_sha256=valid_sha256,
        dataset_sha256=valid_sha256,
        candle_count=6900000,
        schema_fingerprint="valid_fingerprint",
        created_at=datetime.now(UTC),
    )

    # Assert: Valid checksums accepted
    assert manifest.manifest_sha256 == valid_sha256
    assert manifest.dataset_sha256 == valid_sha256

    # Act & Assert: Invalid checksum length rejected
    with pytest.raises(ValidationError) as exc_info:
        Manifest(
            dataset_path="price_data/processed/eurusd/eurusd_2020.parquet",
            manifest_sha256="short",  # Too short
            dataset_sha256=valid_sha256,
            candle_count=6900000,
            schema_fingerprint="valid_fingerprint",
            created_at=datetime.now(UTC),
        )
    assert "manifest_sha256" in str(exc_info.value)


def test_manifest_candle_count_validation():
    """
    T051: Validate Manifest candle_count must be positive integer.

    Tests candle_count > 0 constraint.
    """
    # Arrange: Valid SHA-256 hash
    valid_sha256 = "a" * 64

    # Act & Assert: Zero candle_count rejected
    with pytest.raises(ValidationError) as exc_info:
        Manifest(
            dataset_path="price_data/processed/eurusd/eurusd_2020.parquet",
            manifest_sha256=valid_sha256,
            dataset_sha256=valid_sha256,
            candle_count=0,
            schema_fingerprint="valid_fingerprint",
            created_at=datetime.now(UTC),
        )
    assert "candle_count" in str(exc_info.value)

    # Act & Assert: Negative candle_count rejected
    with pytest.raises(ValidationError) as exc_info:
        Manifest(
            dataset_path="price_data/processed/eurusd/eurusd_2020.parquet",
            manifest_sha256=valid_sha256,
            dataset_sha256=valid_sha256,
            candle_count=-100,
            schema_fingerprint="valid_fingerprint",
            created_at=datetime.now(UTC),
        )
    assert "candle_count" in str(exc_info.value)


def test_manifest_immutability():
    """
    T051: Validate Manifest is immutable (frozen=True).

    Tests that manifest fields cannot be modified after creation.
    """
    # Arrange: Create valid manifest
    valid_sha256 = "a" * 64
    manifest = Manifest(
        dataset_path="price_data/processed/eurusd/eurusd_2020.parquet",
        manifest_sha256=valid_sha256,
        dataset_sha256=valid_sha256,
        candle_count=6900000,
        schema_fingerprint="valid_fingerprint",
        created_at=datetime.now(UTC),
    )

    # Act & Assert: Field modification raises ValidationError
    with pytest.raises(ValidationError) as exc_info:
        manifest.candle_count = 1000
    assert "frozen" in str(exc_info.value).lower()


def test_manifest_serialization_to_json():
    """
    T051: Validate Manifest serialization to JSON.

    Tests that manifest can be serialized to JSON with all fields preserved.
    """
    # Arrange: Create valid manifest
    valid_sha256 = "a" * 64
    created_at = datetime(2025, 11, 11, 12, 0, 0, tzinfo=UTC)
    manifest = Manifest(
        dataset_path="price_data/processed/eurusd/eurusd_2020.parquet",
        manifest_sha256=valid_sha256,
        dataset_sha256=valid_sha256,
        candle_count=6900000,
        schema_fingerprint="c" * 32,
        created_at=created_at,
        source_format="csv",
        compression="zstd",
        version="1.0.0",
    )

    # Act: Serialize to JSON
    json_str = manifest.model_dump_json(indent=2)

    # Assert: JSON contains all fields
    assert "dataset_path" in json_str
    assert "price_data/processed/eurusd/eurusd_2020.parquet" in json_str
    assert "manifest_sha256" in json_str
    assert valid_sha256 in json_str
    assert "dataset_sha256" in json_str
    assert "6900000" in json_str
    assert "schema_fingerprint" in json_str
    assert "c" * 32 in json_str
    assert "created_at" in json_str
    assert "source_format" in json_str
    assert "csv" in json_str
    assert "compression" in json_str
    assert "zstd" in json_str
    assert "version" in json_str
    assert "1.0.0" in json_str


def test_manifest_deserialization_from_json():
    """
    T051: Validate Manifest deserialization from JSON.

    Tests that manifest can be reconstructed from JSON with correct types.
    """
    # Arrange: JSON manifest string
    json_data = {
        "dataset_path": "price_data/processed/eurusd/eurusd_2020.parquet",
        "manifest_sha256": "a" * 64,
        "dataset_sha256": "b" * 64,
        "candle_count": 6900000,
        "schema_fingerprint": "c" * 32,
        "created_at": "2025-11-11T12:00:00Z",
        "source_format": "csv",
        "compression": "zstd",
        "version": "1.0.0",
    }

    # Act: Deserialize from JSON
    manifest = Manifest.model_validate(json_data)

    # Assert: All fields correctly deserialized
    assert manifest.dataset_path == "price_data/processed/eurusd/eurusd_2020.parquet"
    assert manifest.manifest_sha256 == "a" * 64
    assert manifest.dataset_sha256 == "b" * 64
    assert manifest.candle_count == 6900000
    assert manifest.schema_fingerprint == "c" * 32
    assert manifest.created_at.year == 2025
    assert manifest.created_at.month == 11
    assert manifest.created_at.day == 11
    assert manifest.source_format == "csv"
    assert manifest.compression == "zstd"
    assert manifest.version == "1.0.0"


def test_manifest_default_fields():
    """
    T051: Validate Manifest default field values.

    Tests source_format, compression, and version defaults.
    """
    # Arrange: Create manifest with only required fields
    valid_sha256 = "a" * 64
    manifest = Manifest(
        dataset_path="price_data/processed/eurusd/eurusd_2020.parquet",
        manifest_sha256=valid_sha256,
        dataset_sha256=valid_sha256,
        candle_count=6900000,
        schema_fingerprint="valid_fingerprint",
        created_at=datetime.now(UTC),
    )

    # Assert: Default values applied
    assert manifest.source_format == "csv"
    assert manifest.compression is None
    assert manifest.version == "1.0.0"


def test_manifest_schema_version_compatibility():
    """
    T051: Validate Manifest schema version field for forward compatibility.

    Tests that version field can represent future schema versions.
    """
    # Arrange: Create manifest with future version
    valid_sha256 = "a" * 64
    manifest = Manifest(
        dataset_path="price_data/processed/eurusd/eurusd_2020.parquet",
        manifest_sha256=valid_sha256,
        dataset_sha256=valid_sha256,
        candle_count=6900000,
        schema_fingerprint="valid_fingerprint",
        created_at=datetime.now(UTC),
        version="2.1.0",  # Future version
    )

    # Assert: Future version accepted
    assert manifest.version == "2.1.0"

    # Act: Serialize and deserialize
    json_str = manifest.model_dump_json()
    manifest_restored = Manifest.model_validate_json(json_str)

    # Assert: Version preserved through round-trip
    assert manifest_restored.version == "2.1.0"


def test_manifest_roundtrip_serialization():
    """
    T051: Validate Manifest round-trip serialization preserves all data.

    Tests serialize -> deserialize produces identical manifest.
    """
    # Arrange: Create manifest with all fields
    valid_sha256 = "a" * 64
    created_at = datetime(2025, 11, 11, 12, 0, 0, tzinfo=UTC)
    original = Manifest(
        dataset_path="price_data/processed/eurusd/eurusd_2020.parquet",
        manifest_sha256=valid_sha256,
        dataset_sha256="b" * 64,
        candle_count=6900000,
        schema_fingerprint="c" * 32,
        created_at=created_at,
        source_format="parquet",
        compression="zstd",
        version="1.0.0",
    )

    # Act: Serialize to JSON and deserialize
    json_str = original.model_dump_json()
    restored = Manifest.model_validate_json(json_str)

    # Assert: All fields match
    assert restored.dataset_path == original.dataset_path
    assert restored.manifest_sha256 == original.manifest_sha256
    assert restored.dataset_sha256 == original.dataset_sha256
    assert restored.candle_count == original.candle_count
    assert restored.schema_fingerprint == original.schema_fingerprint
    assert restored.created_at == original.created_at
    assert restored.source_format == original.source_format
    assert restored.compression == original.compression
    assert restored.version == original.version


def test_manifest_path_validation():
    """
    T051: Validate Manifest dataset_path accepts various path formats.

    Tests relative paths, deep nesting, various file extensions.
    """
    # Arrange: Various path formats
    paths = [
        "price_data/processed/eurusd/eurusd_2020.parquet",
        "price_data/raw/usdjpy/usdjpy_2019.csv",
        "data/symbols/gbpusd/2021/Q1/jan.parquet.zstd",
        "simple.csv",
    ]

    valid_sha256 = "a" * 64

    # Act & Assert: All path formats accepted
    for path in paths:
        manifest = Manifest(
            dataset_path=path,
            manifest_sha256=valid_sha256,
            dataset_sha256=valid_sha256,
            candle_count=1000,
            schema_fingerprint="valid_fingerprint",
            created_at=datetime.now(UTC),
        )
        assert manifest.dataset_path == path
