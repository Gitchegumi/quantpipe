"""Logging constants for ingestion process.

This module defines standardized stage names and logging conventions
used throughout the ingestion pipeline.
"""

from enum import Enum


class IngestionStage(str, Enum):
    """Ingestion pipeline stage identifiers (max 5 stages for progress)."""

    READ = "read"
    PROCESS = "process"  # Covers: sort, dedupe, validate
    GAP_FILL = "gap_fill"
    SCHEMA = "schema"  # Column restriction
    FINALIZE = "finalize"  # Metrics & output


class EnrichmentStage(str, Enum):
    """Enrichment pipeline stage identifiers."""

    VALIDATE = "validate"
    RESOLVE = "resolve"  # Dependency resolution
    COMPUTE = "compute"
    ASSEMBLE = "assemble"


# Progress update limit (NFR-003 / SC-008)
MAX_PROGRESS_UPDATES = 5
