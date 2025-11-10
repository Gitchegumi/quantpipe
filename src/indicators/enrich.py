"""Indicator enrichment module for opt-in indicator computation.

This module provides selective indicator computation on immutable core datasets,
ensuring that only requested indicators are calculated without mutating the
original ingestion result.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentResult:
    """Result of indicator enrichment operation.

    Attributes:
        core: Reference to original core DataFrame (unchanged).
        enriched: New DataFrame with indicator columns appended.
        indicators_applied: List of successfully computed indicator names.
        failed_indicators: List of indicators that failed (non-strict only).
        runtime_seconds: Total enrichment runtime.
    """

    core: pd.DataFrame
    enriched: pd.DataFrame
    indicators_applied: List[str]
    failed_indicators: List[str]
    runtime_seconds: float


def enrich(
    core_ref: Any,  # IngestionResult reference
    indicators: List[str],
    params: Dict[str, Any] = None,
    strict: bool = False,
) -> EnrichmentResult:
    """Compute requested indicators on core dataset without mutation.

    Args:
        core_ref: Reference to IngestionResult from ingestion.
        indicators: List of indicator names to compute.
        params: Optional parameters for indicator computation.
        strict: If True, abort on first unknown indicator error.

    Returns:
        EnrichmentResult: Enriched dataset with metadata.

    Raises:
        ValueError: If duplicate indicator names or core ref invalid (always).
        KeyError: If unknown indicator and strict=True.
    """
    # Implementation will be completed in Phase 4 (US2)
    raise NotImplementedError("Enrichment pipeline to be implemented in Phase 4")
