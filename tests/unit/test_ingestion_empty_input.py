"""Unit tests for empty input handling (T088, FR-013)."""
# pylint: disable=redefined-outer-name  # pytest fixtures

import pandas as pd
import pytest

from src.io.ingestion import ingest_ohlcv_data


@pytest.fixture()
def empty_csv_file(tmp_path):
    """Create an empty CSV file (header only, no data rows)."""
    csv_path = tmp_path / "empty_data.csv"

    # Write only header, no data rows
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("timestamp,open,high,low,close,volume\n")

    return csv_path


@pytest.fixture()
def no_header_csv_file(tmp_path):
    """Create a completely empty CSV file (no header, no data)."""
    csv_path = tmp_path / "no_header.csv"

    # Create empty file
    csv_path.touch()

    return csv_path


def test_empty_csv_with_header_only(empty_csv_file):
    """Test that CSV with header but no data rows is handled gracefully (FR-013)."""
    result = ingest_ohlcv_data(
        path=str(empty_csv_file),
        timeframe_minutes=1,
        mode="columnar",
    )

    # Should return empty DataFrame with proper schema
    assert isinstance(result.data, pd.DataFrame)
    assert len(result.data) == 0

    # Should have all core columns
    expected_columns = [
        "timestamp_utc",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "is_gap",
    ]
    assert list(result.data.columns) == expected_columns

    # Metrics should reflect empty input
    assert result.metrics.total_rows_input == 0
    assert result.metrics.total_rows_output == 0
    assert result.metrics.gaps_inserted == 0
    assert result.metrics.duplicates_removed == 0


def test_completely_empty_csv_raises_error(no_header_csv_file):
    """Test that completely empty CSV (no header) raises appropriate error."""
    with pytest.raises((ValueError, KeyError, pd.errors.EmptyDataError)):
        ingest_ohlcv_data(
            path=str(no_header_csv_file),
            timeframe_minutes=1,
            mode="columnar",
        )


def test_empty_iterator_mode(empty_csv_file):
    """Test empty input in iterator mode yields no records."""
    result = ingest_ohlcv_data(
        path=str(empty_csv_file),
        timeframe_minutes=1,
        mode="iterator",
    )

    # Should be able to iterate with no records
    records = list(result.data)
    assert len(records) == 0

    # Length should be 0
    assert len(result.data) == 0


def test_single_row_csv(tmp_path):
    """Test that CSV with single data row is handled correctly."""
    csv_path = tmp_path / "single_row.csv"

    # Create CSV with one data row
    timestamps = pd.date_range("2024-01-01", periods=1, freq="1min", tz="UTC")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [1.0],
            "high": [1.001],
            "low": [0.999],
            "close": [1.0005],
            "volume": [1000.0],
        }
    )
    df.to_csv(csv_path, index=False)

    result = ingest_ohlcv_data(
        path=str(csv_path),
        timeframe_minutes=1,
        mode="columnar",
    )

    # Should return single row
    assert len(result.data) == 1
    assert result.metrics.total_rows_input == 1
    assert result.metrics.total_rows_output == 1
    assert result.metrics.gaps_inserted == 0


def test_empty_input_throughput_metrics(empty_csv_file):
    """Test that empty input still produces valid throughput metrics."""
    result = ingest_ohlcv_data(
        path=str(empty_csv_file),
        timeframe_minutes=1,
        mode="columnar",
    )

    # Runtime should be recorded even for empty input
    assert result.metrics.runtime_seconds > 0
    assert result.metrics.runtime_seconds < 1.0  # Should be very fast

    # Throughput should be 0 or handled gracefully
    assert result.metrics.total_rows_output == 0
