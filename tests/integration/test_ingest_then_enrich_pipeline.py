"""Integration tests for ingestion then enrichment pipeline.

This module tests the complete pipeline flow: ingest -> enrich, verifying
that both phases work together correctly while maintaining immutability.
"""

import logging

import pytest

logger = logging.getLogger(__name__)


@pytest.mark.integration
def test_ingest_then_enrich_pipeline():
    """Test complete pipeline: ingest core data then enrich with indicators."""
    # Will be implemented in Phase 4 (T058)
    pytest.skip("Integration test to be implemented in Phase 4")


@pytest.mark.integration
def test_pipeline_immutability():
    """Test that enrichment doesn't mutate core ingestion result."""
    # Will be implemented in Phase 4
    pytest.skip("Immutability test to be implemented in Phase 4")
