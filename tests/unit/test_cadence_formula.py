"""Unit tests for cadence deviation formula correctness (T100, FR-012, NFR-007)."""

import pandas as pd
import pytest

from src.io.cadence import (
    compute_cadence_deviation,
    compute_expected_intervals,
    validate_cadence_uniformity,
)


def test_compute_expected_intervals_basic():
    """Test expected intervals for simple time range."""
    start = pd.Timestamp("2024-01-01 00:00:00", tz="UTC")
    end = pd.Timestamp("2024-01-01 01:00:00", tz="UTC")

    # 1-minute intervals: 60 minutes → 61 intervals (0, 1, 2, ..., 60)
    result = compute_expected_intervals(start, end, timeframe_minutes=1)
    assert result == 61


def test_compute_expected_intervals_5min():
    """Test expected intervals for 5-minute timeframe."""
    start = pd.Timestamp("2024-01-01 00:00:00", tz="UTC")
    end = pd.Timestamp("2024-01-01 01:00:00", tz="UTC")

    # 5-minute intervals: 60 minutes → 13 intervals (0, 5, 10, ..., 60)
    result = compute_expected_intervals(start, end, timeframe_minutes=5)
    assert result == 13


def test_compute_expected_intervals_single_day():
    """Test expected intervals for full day."""
    start = pd.Timestamp("2024-01-01 00:00:00", tz="UTC")
    end = pd.Timestamp("2024-01-02 00:00:00", tz="UTC")

    # 1-minute intervals: 1440 minutes → 1441 intervals
    result = compute_expected_intervals(start, end, timeframe_minutes=1)
    assert result == 1441


def test_compute_cadence_deviation_zero():
    """Test deviation is zero when actual equals expected."""
    deviation = compute_cadence_deviation(actual_count=100, expected_count=100)
    assert deviation == 0.0


def test_compute_cadence_deviation_formula():
    """Test cadence deviation formula correctness (FR-012).

    Formula: deviation = abs(expected - actual) / expected * 100
    """
    # 100 expected, 98 actual → 2% deviation
    deviation = compute_cadence_deviation(actual_count=98, expected_count=100)
    assert deviation == pytest.approx(2.0)

    # 100 expected, 95 actual → 5% deviation
    deviation = compute_cadence_deviation(actual_count=95, expected_count=100)
    assert deviation == pytest.approx(5.0)

    # 100 expected, 102 actual → 2% deviation (absolute value)
    deviation = compute_cadence_deviation(actual_count=102, expected_count=100)
    assert deviation == pytest.approx(2.0)


def test_compute_cadence_deviation_large_numbers():
    """Test deviation calculation with large counts."""
    # 1M expected, 980k actual → 2% deviation
    deviation = compute_cadence_deviation(
        actual_count=980_000, expected_count=1_000_000
    )
    assert deviation == pytest.approx(2.0)


def test_compute_cadence_deviation_zero_expected():
    """Test deviation is zero when expected count is zero."""
    deviation = compute_cadence_deviation(actual_count=0, expected_count=0)
    assert deviation == 0.0


def test_compute_cadence_deviation_precision():
    """Test deviation calculation precision (NFR-007)."""
    # 10000 expected, 9999 actual → 0.01% deviation
    deviation = compute_cadence_deviation(actual_count=9999, expected_count=10_000)
    assert deviation == pytest.approx(0.01)

    # 10000 expected, 9950 actual → 0.5% deviation
    deviation = compute_cadence_deviation(actual_count=9950, expected_count=10_000)
    assert deviation == pytest.approx(0.5)


def test_validate_cadence_uniformity_perfect():
    """Test validation passes with perfect cadence."""
    timestamps = pd.date_range("2024-01-01", periods=61, freq="1min", tz="UTC")
    df = pd.DataFrame({"timestamp_utc": timestamps})

    actual, expected, deviation = validate_cadence_uniformity(
        df, timeframe_minutes=1, tolerance_percent=2.0
    )

    assert actual == 61
    assert expected == 61
    assert deviation == 0.0


def test_validate_cadence_uniformity_within_tolerance():
    """Test validation passes within 2% tolerance."""
    # Create 100 rows (missing 2 from expected 102 = ~2% deviation)
    timestamps = pd.date_range("2024-01-01", periods=100, freq="1min", tz="UTC")
    df = pd.DataFrame({"timestamp_utc": timestamps})

    # Should pass with 2% tolerance
    actual, expected, deviation = validate_cadence_uniformity(
        df, timeframe_minutes=1, tolerance_percent=2.0
    )

    assert actual == 100
    assert expected == 100  # 99 minutes → 100 intervals
    assert deviation == pytest.approx(0.0)


def test_validate_cadence_uniformity_exceeds_tolerance():
    """Test validation fails when deviation exceeds tolerance."""
    # Create gaps to exceed tolerance
    timestamps = pd.date_range("2024-01-01", periods=95, freq="1min", tz="UTC")
    # Add end timestamp far away to create large expected count
    timestamps = timestamps.append(
        pd.DatetimeIndex(
            [pd.Timestamp("2024-01-01 02:00:00", tz="UTC")], dtype="datetime64[ns, UTC]"
        )
    )
    df = pd.DataFrame({"timestamp_utc": timestamps})

    # Should raise RuntimeError
    with pytest.raises(RuntimeError, match="Cadence deviation"):
        validate_cadence_uniformity(df, timeframe_minutes=1, tolerance_percent=2.0)


def test_validate_cadence_uniformity_empty_dataframe():
    """Test validation with empty DataFrame."""
    df = pd.DataFrame(
        {"timestamp_utc": pd.DatetimeIndex([], dtype="datetime64[ns, UTC]")}
    )

    actual, expected, deviation = validate_cadence_uniformity(
        df, timeframe_minutes=1, tolerance_percent=2.0
    )

    assert actual == 0
    assert expected == 0
    assert deviation == 0.0


def test_cadence_deviation_symmetric():
    """Test that deviation is symmetric (missing vs extra rows)."""
    # Missing rows
    deviation_missing = compute_cadence_deviation(actual_count=98, expected_count=100)

    # Extra rows
    deviation_extra = compute_cadence_deviation(actual_count=102, expected_count=100)

    # Should be equal (absolute value)
    assert deviation_missing == deviation_extra


def test_expected_intervals_fractional_periods():
    """Test expected intervals with fractional period results."""
    start = pd.Timestamp("2024-01-01 00:00:00", tz="UTC")
    end = pd.Timestamp("2024-01-01 00:07:30", tz="UTC")  # 7.5 minutes

    # 1-minute intervals: should round down to 8 intervals (0-7, partial 8)
    result = compute_expected_intervals(start, end, timeframe_minutes=1)
    assert result == 8  # int() truncates: 7.5 + 1 = 8.5 → 8


def test_cadence_deviation_boundary_2_percent():
    """Test deviation calculation at exactly 2% boundary."""
    # 100 expected, 98 actual → exactly 2.0%
    deviation = compute_cadence_deviation(actual_count=98, expected_count=100)
    assert deviation == pytest.approx(2.0, abs=1e-10)

    # 10000 expected, 9800 actual → exactly 2.0%
    deviation = compute_cadence_deviation(actual_count=9800, expected_count=10_000)
    assert deviation == pytest.approx(2.0, abs=1e-10)
