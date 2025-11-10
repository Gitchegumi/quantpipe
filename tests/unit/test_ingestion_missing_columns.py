"""Unit tests for missing core columns error handling (T089, FR-020)."""
# pylint: disable=redefined-outer-name  # pytest fixtures

import pandas as pd
import pytest

from src.io.ingestion import ingest_ohlcv_data


@pytest.fixture()
def csv_missing_open(tmp_path):
    """Create CSV file missing 'open' column."""
    csv_path = tmp_path / "missing_open.csv"

    timestamps = pd.date_range("2024-01-01", periods=3, freq="1min", tz="UTC")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            # "open": missing
            "high": [1.001, 1.002, 1.003],
            "low": [0.999, 1.000, 1.001],
            "close": [1.0005, 1.0015, 1.0025],
            "volume": [1000.0, 1100.0, 1200.0],
        }
    )
    df.to_csv(csv_path, index=False)

    return csv_path


@pytest.fixture()
def csv_missing_high_low(tmp_path):
    """Create CSV file missing 'high' and 'low' columns."""
    csv_path = tmp_path / "missing_high_low.csv"

    timestamps = pd.date_range("2024-01-01", periods=3, freq="1min", tz="UTC")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [1.0, 1.001, 1.002],
            # "high": missing
            # "low": missing
            "close": [1.0005, 1.0015, 1.0025],
            "volume": [1000.0, 1100.0, 1200.0],
        }
    )
    df.to_csv(csv_path, index=False)

    return csv_path


@pytest.fixture()
def csv_missing_timestamp(tmp_path):
    """Create CSV file missing 'timestamp' column."""
    csv_path = tmp_path / "missing_timestamp.csv"

    df = pd.DataFrame(
        {
            # "timestamp": missing
            "open": [1.0, 1.001, 1.002],
            "high": [1.001, 1.002, 1.003],
            "low": [0.999, 1.000, 1.001],
            "close": [1.0005, 1.0015, 1.0025],
            "volume": [1000.0, 1100.0, 1200.0],
        }
    )
    df.to_csv(csv_path, index=False)

    return csv_path


@pytest.fixture()
def csv_missing_volume(tmp_path):
    """Create CSV file missing 'volume' column."""
    csv_path = tmp_path / "missing_volume.csv"

    timestamps = pd.date_range("2024-01-01", periods=3, freq="1min", tz="UTC")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [1.0, 1.001, 1.002],
            "high": [1.001, 1.002, 1.003],
            "low": [0.999, 1.000, 1.001],
            "close": [1.0005, 1.0015, 1.0025],
            # "volume": missing
        }
    )
    df.to_csv(csv_path, index=False)

    return csv_path


def test_missing_open_column_raises_error(csv_missing_open):
    """Test that missing 'open' column raises appropriate error (FR-020)."""
    with pytest.raises((ValueError, KeyError)) as exc_info:
        ingest_ohlcv_data(
            path=str(csv_missing_open),
            timeframe_minutes=1,
            mode="columnar",
        )

    # Error message should mention missing column
    error_message = str(exc_info.value).lower()
    assert "open" in error_message or "column" in error_message


def test_missing_high_low_columns_raises_error(csv_missing_high_low):
    """Test that missing 'high' and 'low' columns raises appropriate error."""
    with pytest.raises((ValueError, KeyError)) as exc_info:
        ingest_ohlcv_data(
            path=str(csv_missing_high_low),
            timeframe_minutes=1,
            mode="columnar",
        )

    # Error message should mention missing columns
    error_message = str(exc_info.value).lower()
    assert (
        "high" in error_message or "low" in error_message or "column" in error_message
    )


def test_missing_timestamp_column_raises_error(csv_missing_timestamp):
    """Test that missing 'timestamp' column raises appropriate error."""
    with pytest.raises((ValueError, KeyError)) as exc_info:
        ingest_ohlcv_data(
            path=str(csv_missing_timestamp),
            timeframe_minutes=1,
            mode="columnar",
        )

    # Error message should mention missing timestamp
    error_message = str(exc_info.value).lower()
    assert "timestamp" in error_message or "column" in error_message


def test_missing_volume_column_raises_error(csv_missing_volume):
    """Test that missing 'volume' column raises appropriate error."""
    with pytest.raises((ValueError, KeyError)) as exc_info:
        ingest_ohlcv_data(
            path=str(csv_missing_volume),
            timeframe_minutes=1,
            mode="columnar",
        )

    # Error message should mention missing column
    error_message = str(exc_info.value).lower()
    assert "volume" in error_message or "column" in error_message


def test_extra_columns_are_ignored(tmp_path):
    """Test that extra columns beyond core set are ignored (not an error)."""
    csv_path = tmp_path / "extra_columns.csv"

    timestamps = pd.date_range("2024-01-01", periods=3, freq="1min", tz="UTC")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [1.0, 1.001, 1.002],
            "high": [1.001, 1.002, 1.003],
            "low": [0.999, 1.000, 1.001],
            "close": [1.0005, 1.0015, 1.0025],
            "volume": [1000.0, 1100.0, 1200.0],
            "extra_column_1": [100, 200, 300],
            "extra_column_2": ["a", "b", "c"],
        }
    )
    df.to_csv(csv_path, index=False)

    # Should succeed - extra columns ignored
    result = ingest_ohlcv_data(
        path=str(csv_path),
        timeframe_minutes=1,
        mode="columnar",
    )

    # Extra columns should not appear in output
    assert "extra_column_1" not in result.data.columns
    assert "extra_column_2" not in result.data.columns

    # Core columns should be present
    core_columns = ["timestamp_utc", "open", "high", "low", "close", "volume", "is_gap"]
    assert list(result.data.columns) == core_columns


def test_column_name_case_sensitivity(tmp_path):
    """Test that column names are case-sensitive (OPEN != open)."""
    csv_path = tmp_path / "wrong_case.csv"

    timestamps = pd.date_range("2024-01-01", periods=3, freq="1min", tz="UTC")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "OPEN": [1.0, 1.001, 1.002],  # Wrong case
            "high": [1.001, 1.002, 1.003],
            "low": [0.999, 1.000, 1.001],
            "close": [1.0005, 1.0015, 1.0025],
            "volume": [1000.0, 1100.0, 1200.0],
        }
    )
    df.to_csv(csv_path, index=False)

    # Should fail - 'OPEN' is not 'open'
    with pytest.raises((ValueError, KeyError)):
        ingest_ohlcv_data(
            path=str(csv_path),
            timeframe_minutes=1,
            mode="columnar",
        )
