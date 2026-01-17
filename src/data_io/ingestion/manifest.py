"""Manifest model for dataset provenance and integrity tracking.

This module defines the Manifest pydantic model used to track dataset metadata,
checksums, and schema fingerprints for reproducibility and validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Manifest(BaseModel):
    """Dataset manifest for provenance tracking and integrity validation.

    Captures essential metadata about a dataset including file paths, checksums,
    row counts, and schema information to enable reproducible benchmarking and
    validation of dataset integrity.

    Attributes:
        dataset_path: Relative path to the dataset file
        manifest_sha256: SHA-256 checksum of the manifest file itself
        dataset_sha256: SHA-256 checksum of the dataset file
        candle_count: Total number of candles in the dataset
        schema_fingerprint: Hash of schema (column names and types)
        created_at: Timestamp when manifest was created (UTC)
        source_format: Original format of dataset (e.g., 'csv', 'parquet')
        compression: Compression algorithm used (e.g., 'zstd', 'none')
        version: Manifest schema version for forward compatibility
    """

    dataset_path: str = Field(..., description="Relative path to dataset file")
    manifest_sha256: str = Field(
        ..., min_length=64, max_length=64, description="SHA-256 of manifest"
    )
    dataset_sha256: str = Field(
        ..., min_length=64, max_length=64, description="SHA-256 of dataset"
    )
    candle_count: int = Field(..., gt=0, description="Total candles in dataset")
    schema_fingerprint: str = Field(..., description="Hash of schema structure")
    created_at: datetime = Field(..., description="Manifest creation timestamp (UTC)")
    source_format: str = Field(
        default="csv", description="Original dataset format (csv/parquet)"
    )
    compression: Optional[str] = Field(
        default=None, description="Compression algorithm (zstd/none)"
    )
    version: str = Field(default="1.0.0", description="Manifest schema version")

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
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
        },
    )
