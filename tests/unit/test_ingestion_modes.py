"""Unit tests for ingestion mode selection and validation (T064, T065)."""
# pylint: disable=redefined-outer-name  # pytest fixtures

from datetime import datetime

import pandas as pd
import pytest

from src.io.ingestion import ingest_ohlcv_data
from src.io.iterator_mode import CoreCandleRecord, DataFrameIteratorWrapper


@pytest.fixture()
def temp_csv_file(tmp_path):
    """Create a temporary CSV file for testing."""
    csv_path = tmp_path / "test_data.csv"

    timestamps = pd.date_range("2024-01-01", periods=10, freq="1min", tz="UTC")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [1.0 + i * 0.001 for i in range(10)],
            "high": [1.0 + i * 0.001 + 0.0005 for i in range(10)],
            "low": [1.0 + i * 0.001 - 0.0005 for i in range(10)],
            "close": [1.0 + i * 0.001 + 0.0002 for i in range(10)],
            "volume": [1000.0] * 10,
        }
    )
    df.to_csv(csv_path, index=False)

    return csv_path


def test_invalid_mode_raises_error(temp_csv_file):
    """Test that invalid mode values raise ValueError."""
    with pytest.raises(ValueError, match="Invalid mode: invalid"):
        ingest_ohlcv_data(
            path=str(temp_csv_file),
            timeframe_minutes=1,
            mode="invalid",
        )


def test_empty_string_mode_raises_error(temp_csv_file):
    """Test that empty string mode raises ValueError."""
    with pytest.raises(ValueError, match="Invalid mode"):
        ingest_ohlcv_data(
            path=str(temp_csv_file),
            timeframe_minutes=1,
            mode="",
        )


def test_numeric_mode_raises_error(temp_csv_file):
    """Test that numeric mode value raises error."""
    with pytest.raises((ValueError, TypeError)):
        ingest_ohlcv_data(
            path=str(temp_csv_file),
            timeframe_minutes=1,
            mode=123,  # type: ignore
        )


def test_columnar_mode_returns_dataframe(temp_csv_file):
    """Test that columnar mode returns DataFrame."""
    result = ingest_ohlcv_data(
        path=str(temp_csv_file),
        timeframe_minutes=1,
        mode="columnar",
    )

    assert result.mode == "columnar"
    assert isinstance(result.data, pd.DataFrame)
    assert len(result.data) == 10


def test_iterator_mode_returns_wrapper(temp_csv_file):
    """Test that iterator mode returns DataFrameIteratorWrapper."""
    result = ingest_ohlcv_data(
        path=str(temp_csv_file),
        timeframe_minutes=1,
        mode="iterator",
    )

    assert result.mode == "iterator"
    assert isinstance(result.data, DataFrameIteratorWrapper)
    assert len(result.data) == 10


def test_iterator_yields_correct_objects(temp_csv_file):
    """Test that iterator yields CoreCandleRecord objects with correct schema."""
    result = ingest_ohlcv_data(
        path=str(temp_csv_file),
        timeframe_minutes=1,
        mode="iterator",
    )

    records = list(result.data)

    # Should yield 10 records
    assert len(records) == 10

    # Check first record
    first_record = records[0]
    assert isinstance(first_record, CoreCandleRecord)
    assert isinstance(first_record.timestamp_utc, datetime)
    assert isinstance(first_record.open, float)
    assert isinstance(first_record.high, float)
    assert isinstance(first_record.low, float)
    assert isinstance(first_record.close, float)
    assert isinstance(first_record.volume, float)
    assert isinstance(first_record.is_gap, bool)


def test_iterator_preserves_data_values(temp_csv_file):
    """Test that iterator preserves data values correctly."""
    result = ingest_ohlcv_data(
        path=str(temp_csv_file),
        timeframe_minutes=1,
        mode="iterator",
    )

    records = list(result.data)

    # Check first record values
    first = records[0]
    assert first.open == pytest.approx(1.0, abs=0.01)
    assert first.high > first.open
    assert first.low < first.open
    assert first.is_gap is False

    # Check timestamps are chronological
    for i in range(len(records) - 1):
        assert records[i].timestamp_utc < records[i + 1].timestamp_utc


def test_iterator_immutability(temp_csv_file):
    """Test that CoreCandleRecord objects are immutable."""
    result = ingest_ohlcv_data(
        path=str(temp_csv_file),
        timeframe_minutes=1,
        mode="iterator",
    )

    records = list(result.data)
    first = records[0]

    # Attempt to modify should raise AttributeError (frozen dataclass)
    with pytest.raises(AttributeError):
        first.open = 999.0  # type: ignore


def test_columnar_and_iterator_same_row_count(temp_csv_file):
    """Test that columnar and iterator modes produce same row counts."""
    columnar_result = ingest_ohlcv_data(
        path=str(temp_csv_file),
        timeframe_minutes=1,
        mode="columnar",
    )

    iterator_result = ingest_ohlcv_data(
        path=str(temp_csv_file),
        timeframe_minutes=1,
        mode="iterator",
    )

    columnar_rows = len(columnar_result.data)
    iterator_rows = len(iterator_result.data)

    assert columnar_rows == iterator_rows
    assert columnar_rows == 10


def test_iterator_can_be_consumed_multiple_times(temp_csv_file):
    """Test that iterator wrapper can be iterated multiple times."""
    result = ingest_ohlcv_data(
        path=str(temp_csv_file),
        timeframe_minutes=1,
        mode="iterator",
    )

    # First iteration
    first_pass = list(result.data)
    assert len(first_pass) == 10

    # Second iteration
    second_pass = list(result.data)
    assert len(second_pass) == 10

    # Values should be same
    assert first_pass[0].open == second_pass[0].open


def test_iterator_all_required_columns_present(temp_csv_file):
    """Test that all required columns are present in CoreCandleRecord."""
    result = ingest_ohlcv_data(
        path=str(temp_csv_file),
        timeframe_minutes=1,
        mode="iterator",
    )

    record = next(iter(result.data))

    # Check all required attributes exist
    assert hasattr(record, "timestamp_utc")
    assert hasattr(record, "open")
    assert hasattr(record, "high")
    assert hasattr(record, "low")
    assert hasattr(record, "close")
    assert hasattr(record, "volume")
    assert hasattr(record, "is_gap")


def test_iterator_high_low_close_relationships(temp_csv_file):
    """Test that OHLC relationships are maintained in iterator mode."""
    result = ingest_ohlcv_data(
        path=str(temp_csv_file),
        timeframe_minutes=1,
        mode="iterator",
    )

    for record in result.data:
        # High should be >= open, low, close
        assert record.high >= record.open
        assert record.high >= record.low
        assert record.high >= record.close

        # Low should be <= open, high, close
        assert record.low <= record.open
        assert record.low <= record.high
        assert record.low <= record.close
