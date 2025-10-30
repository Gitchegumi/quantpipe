"""Pydantic models for dataset build metadata and summaries.

Feature: 004-timeseries-dataset
Task: T013 - MetadataRecord & BuildSummary models
"""

# pylint: disable=unused-argument line-too-long arguments-differ

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SkipReason(str, Enum):
    """Reasons why a symbol was skipped during dataset build."""

    INSUFFICIENT_ROWS = "insufficient_rows"
    SCHEMA_MISMATCH = "schema_mismatch"
    READ_ERROR = "read_error"


class SkippedSymbol(BaseModel):
    """Record of a symbol that was skipped during build.

    Attributes:
        symbol: Symbol identifier (directory name)
        reason: Categorized skip reason
        details: Human-readable explanation
    """

    symbol: str = Field(..., min_length=1, description="Symbol identifier")
    reason: SkipReason = Field(..., description="Skip reason category")
    details: str = Field(..., min_length=1, description="Detailed explanation")


class MetadataRecord(BaseModel):
    """Per-symbol metadata describing processed dataset.

    Validation Rules:
        - test_rows + validation_rows must equal total_rows
        - canonical_timezone must be 'UTC'
        - All row counts must be non-negative
        - end_timestamp must be >= start_timestamp
        - validation_start_timestamp must be between start and end

    Attributes:
        symbol: Symbol identifier
        total_rows: Total rows in merged raw dataset
        test_rows: Rows in test partition (80% floor)
        validation_rows: Rows in validation partition (remainder)
        start_timestamp: Earliest timestamp in dataset
        end_timestamp: Latest timestamp in dataset
        validation_start_timestamp: First timestamp in validation partition
        gap_count: Number of detected temporal gaps
        overlap_count: Number of duplicate timestamps (deduplicated)
        canonical_timezone: Timezone for all timestamps (always UTC)
        build_timestamp: When this metadata was generated
        schema_version: Data schema identifier
        source_files: List of raw CSV files merged
    """

    symbol: str = Field(..., min_length=1)
    total_rows: int = Field(..., ge=0)
    test_rows: int = Field(..., ge=0)
    validation_rows: int = Field(..., ge=0)
    start_timestamp: datetime
    end_timestamp: datetime
    validation_start_timestamp: datetime
    gap_count: int = Field(default=0, ge=0)
    overlap_count: int = Field(default=0, ge=0)
    canonical_timezone: Literal["UTC"] = "UTC"
    build_timestamp: datetime
    schema_version: str = Field(default="v1")
    source_files: list[str] = Field(default_factory=list)

    @field_validator("total_rows")
    @classmethod
    def validate_total_rows(cls, v: int, info) -> int:
        """Ensure total_rows equals test_rows + validation_rows."""
        # Note: validation happens after all fields set, check in model_validator
        return v

    @field_validator("end_timestamp")
    @classmethod
    def validate_end_after_start(cls, v: datetime, info) -> datetime:
        """Ensure end_timestamp >= start_timestamp."""
        if "start_timestamp" in info.data and v < info.data["start_timestamp"]:
            raise ValueError("end_timestamp must be >= start_timestamp")
        return v

    def model_post_init(self, __context) -> None:
        """Validate consistency after all fields initialized."""
        if self.test_rows + self.validation_rows != self.total_rows:
            raise ValueError(
                f"test_rows ({self.test_rows}) + validation_rows "
                f"({self.validation_rows}) must equal total_rows ({self.total_rows})"
            )

        if not self.start_timestamp <= self.validation_start_timestamp <= self.end_timestamp:
            raise ValueError(
                "validation_start_timestamp must be between start and end timestamps"
            )


class BuildSummary(BaseModel):
    """Consolidated summary of a dataset build run.

    Attributes:
        build_timestamp: When build started
        build_completed_at: When build finished
        symbols_processed: List of successfully processed symbols
        symbols_skipped: List of skipped symbols with reasons
        total_rows_processed: Sum of all processed rows
        total_test_rows: Sum of test partition rows
        total_validation_rows: Sum of validation partition rows
        duration_seconds: Build duration in seconds
    """

    build_timestamp: datetime
    build_completed_at: datetime
    symbols_processed: list[str] = Field(default_factory=list)
    symbols_skipped: list[SkippedSymbol] = Field(default_factory=list)
    total_rows_processed: int = Field(default=0, ge=0)
    total_test_rows: int = Field(default=0, ge=0)
    total_validation_rows: int = Field(default=0, ge=0)
    duration_seconds: float = Field(..., ge=0)

    @field_validator("build_completed_at")
    @classmethod
    def validate_completion_after_start(cls, v: datetime, info) -> datetime:
        """Ensure build_completed_at >= build_timestamp."""
        if "build_timestamp" in info.data and v < info.data["build_timestamp"]:
            raise ValueError("build_completed_at must be >= build_timestamp")
        return v

    def model_post_init(self, __context) -> None:
        """Validate row count consistency."""
        if self.total_test_rows + self.total_validation_rows != self.total_rows_processed:
            raise ValueError(
                f"total_test_rows ({self.total_test_rows}) + "
                f"total_validation_rows ({self.total_validation_rows}) must equal "
                f"total_rows_processed ({self.total_rows_processed})"
            )
