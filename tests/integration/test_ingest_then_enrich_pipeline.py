"""Integration tests for ingestion then enrichment pipeline.

This module tests the complete pipeline flow: ingest -> enrich, verifying
that both phases work together correctly while maintaining immutability.
"""
# pylint: disable=redefined-outer-name  # pytest fixtures

import logging

import pandas as pd
import pytest

from src.indicators.enrich import enrich
from src.data_io.ingestion import ingest_ohlcv_data

logger = logging.getLogger(__name__)


@pytest.fixture
def temp_raw_csv(tmp_path):
    """Create a temporary CSV file with sample OHLCV data."""
    csv_path = tmp_path / "test_data.csv"

    # Create sample data with uniform 1-minute cadence
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2024-01-01 00:00:00", periods=1000, freq="1min", tz="UTC"
            ),
            "open": range(1000, 2000),
            "high": range(1001, 2001),
            "low": range(999, 1999),
            "close": range(1000, 2000),
            "volume": [10000] * 1000,
        }
    )

    df.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def temp_output_path(tmp_path):
    """Create temporary output path for ingestion."""
    return tmp_path / "processed_data.csv"

@pytest.mark.integration
def test_ingest_then_enrich_pipeline(temp_raw_csv):
    """Test complete pipeline: ingest core data then enrich with indicators."""
    # Step 1: Ingest raw OHLCV data
    ingestion_result = ingest_ohlcv_data(
        path=str(temp_raw_csv),
        timeframe_minutes=1,
        mode="columnar",
    )

    # Verify ingestion succeeded
    assert ingestion_result.data is not None
    assert ingestion_result.data.shape[0] == 1000
    assert "timestamp_utc" in ingestion_result.data.columns
    assert "is_gap" in ingestion_result.data.columns

    # Step 2: Enrich with indicators
    enrichment_result = enrich(
        ingestion_result.data,
        indicators=["ema20", "ema50", "atr14"],
        strict=True,
    )

    # Verify enrichment succeeded
    assert enrichment_result is not None
    assert len(enrichment_result.indicators_applied) == 3
    assert "ema20" in enrichment_result.enriched.columns
    assert "ema50" in enrichment_result.enriched.columns
    assert "atr14" in enrichment_result.enriched.columns


@pytest.mark.integration
def test_pipeline_immutability(temp_raw_csv):
    """Test that enrichment doesn't mutate core ingestion result."""
    from src.data_io.hash_utils import compute_dataframe_hash

    CORE_COLUMNS = ["timestamp_utc", "open", "high", "low", "close", "volume", "is_gap"]

    # Ingest
    ingestion_result = ingest_ohlcv_data(
        path=str(temp_raw_csv),
        timeframe_minutes=1,
        mode="columnar",
    )

    # Compute hash before enrichment
    hash_before = compute_dataframe_hash(ingestion_result.data, CORE_COLUMNS)

    # Enrich
    enrichment_result = enrich(
        ingestion_result.data, indicators=["ema20", "atr14"], strict=True
    )

    # Compute hash after enrichment
    hash_after = compute_dataframe_hash(enrichment_result.enriched, CORE_COLUMNS)

    # Core columns should be unchanged
    assert hash_before == hash_after


@pytest.mark.integration
def test_pipeline_with_gap_filling(tmp_path):
    """Test full pipeline with automatic gap filling."""
    csv_path = tmp_path / "gap_data.csv"

    # Create data with 1 gap (within 2% tolerance for validation)
    timestamps = list(pd.date_range("2024-01-01", periods=100, freq="1min", tz="UTC"))
    timestamps.pop(50)  # Remove 1 timestamp (1% deviation)

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": range(len(timestamps)),
            "high": range(1, len(timestamps) + 1),
            "low": range(len(timestamps)),
            "close": range(len(timestamps)),
            "volume": [1000] * len(timestamps),
        }
    )
    df.to_csv(csv_path, index=False)

    # Ingest - should fill the gap
    ingestion_result = ingest_ohlcv_data(
        path=str(csv_path),
        timeframe_minutes=1,
        mode="columnar",
    )

    # Should have filled the gap (99 input → 100 output)
    assert ingestion_result.data is not None
    assert ingestion_result.data.shape[0] == 100
    assert "is_gap" in ingestion_result.data.columns

    # Enrich
    enrichment_result = enrich(
        ingestion_result.data, indicators=["ema20"], strict=True
    )

    # Should succeed with all 100 rows
    assert "ema20" in enrichment_result.enriched.columns
    assert enrichment_result.enriched.shape[0] == 100


@pytest.mark.integration
def test_pipeline_metrics_captured(temp_raw_csv):
    """Test that both ingestion and enrichment metrics are captured."""
    # Ingest
    ingestion_result = ingest_ohlcv_data(
        path=str(temp_raw_csv),
        timeframe_minutes=1,
        mode="columnar",
    )

    assert ingestion_result.data is not None

    # Enrich
    enrichment_result = enrich(
        ingestion_result.data, indicators=["ema20", "atr14"], strict=True
    )


    # Check enrichment metrics
    assert enrichment_result.runtime_seconds > 0
    assert len(enrichment_result.indicators_applied) == 2
