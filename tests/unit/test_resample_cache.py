"""Unit tests for resample caching.

Tests cover:
- Cache hit: second call loads from disk
- Cache miss: first call computes and saves
- Cache key: different timeframes create different cache files
- Cache invalidation: different data hash creates new cache
"""

import shutil
from datetime import datetime, timezone
from pathlib import Path

import polars as pl
import pytest

from src.data_io.resample import resample_ohlcv
from src.data_io.resample_cache import (
    CACHE_DIR,
    compute_data_hash,
    get_cache_path,
    load_cached_resample,
    resample_with_cache,
    save_cached_resample,
)


@pytest.fixture(autouse=True)
def clean_test_cache():
    """Clean up test cache files before and after each test."""
    test_cache = CACHE_DIR / "test_cleanup"
    if test_cache.exists():
        shutil.rmtree(test_cache)
    yield
    # Cleanup after test
    for f in CACHE_DIR.glob("TEST_*"):
        f.unlink(missing_ok=True)


def create_test_ohlcv_data(num_bars: int = 10) -> pl.DataFrame:
    """Create test OHLCV data."""
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    timestamps = [
        start.replace(minute=i % 60, hour=start.hour + i // 60) for i in range(num_bars)
    ]

    return pl.DataFrame(
        {
            "timestamp_utc": timestamps,
            "open": [100.0 + i * 0.1 for i in range(num_bars)],
            "high": [100.5 + i * 0.1 for i in range(num_bars)],
            "low": [99.5 + i * 0.1 for i in range(num_bars)],
            "close": [100.2 + i * 0.1 for i in range(num_bars)],
            "volume": [1000.0 for _ in range(num_bars)],
        }
    ).with_columns(pl.col("timestamp_utc").cast(pl.Datetime("us", "UTC")))


class TestGetCachePath:
    """Tests for get_cache_path function."""

    def test_cache_path_format(self):
        """Test cache path has correct format."""
        path = get_cache_path(
            instrument="EURUSD",
            tf_minutes=15,
            start_date="20240101",
            end_date="20240131",
            data_hash="abc12345def67890",
        )

        assert path.name == "EURUSD_15m_20240101_20240131_abc12345.parquet"
        assert path.parent == CACHE_DIR

    def test_cache_path_uppercase_instrument(self):
        """Test instrument is uppercased."""
        path = get_cache_path("eurusd", 5, "20240101", "20240101", "hash1234")
        assert "EURUSD" in path.name


class TestComputeDataHash:
    """Tests for compute_data_hash function."""

    def test_hash_consistency(self):
        """Test same data produces same hash."""
        df = create_test_ohlcv_data(10)
        hash1 = compute_data_hash(df)
        hash2 = compute_data_hash(df)

        assert hash1 == hash2

    def test_hash_changes_with_data(self):
        """Test different data produces different hash."""
        df1 = create_test_ohlcv_data(10)
        df2 = create_test_ohlcv_data(20)

        hash1 = compute_data_hash(df1)
        hash2 = compute_data_hash(df2)

        assert hash1 != hash2


class TestCacheOperations:
    """Tests for cache save/load operations."""

    def test_cache_miss_returns_none(self):
        """Test loading non-existent cache returns None."""
        result = load_cached_resample(CACHE_DIR / "nonexistent.parquet")
        assert result is None

    def test_save_and_load_cache(self):
        """Test saving and loading cache file."""
        df = create_test_ohlcv_data(10)
        cache_path = CACHE_DIR / "TEST_save_load.parquet"

        save_cached_resample(df, cache_path)
        loaded = load_cached_resample(cache_path)

        assert loaded is not None
        assert len(loaded) == len(df)

        # Cleanup
        cache_path.unlink(missing_ok=True)


class TestResampleWithCache:
    """Tests for resample_with_cache function."""

    def test_cache_miss_then_hit(self):
        """Test first call is cache miss, second is hit."""
        df = create_test_ohlcv_data(15)  # 3 complete 5m bars

        # Clear any existing cache
        for f in CACHE_DIR.glob("TEST_*"):
            f.unlink(missing_ok=True)

        # First call - cache miss
        result1 = resample_with_cache(
            df=df,
            instrument="TEST_CACHE",
            tf_minutes=5,
            resample_fn=resample_ohlcv,
        )

        # Second call - should be cache hit
        result2 = resample_with_cache(
            df=df,
            instrument="TEST_CACHE",
            tf_minutes=5,
            resample_fn=resample_ohlcv,
        )

        # Results should be identical
        assert len(result1) == len(result2)

        # Cleanup
        for f in CACHE_DIR.glob("TEST_CACHE*"):
            f.unlink(missing_ok=True)

    def test_different_timeframes_different_cache(self):
        """Test different timeframes create different cache files."""
        df = create_test_ohlcv_data(30)

        resample_with_cache(df, "TEST_TF", 5, resample_ohlcv)
        resample_with_cache(df, "TEST_TF", 15, resample_ohlcv)

        cache_files = list(CACHE_DIR.glob("TEST_TF*"))
        assert len(cache_files) == 2

        # Cleanup
        for f in cache_files:
            f.unlink(missing_ok=True)

    def test_1m_passthrough_no_cache(self):
        """Test 1m timeframe passes through without caching."""
        df = create_test_ohlcv_data(10)

        result = resample_with_cache(df, "TEST_1M", 1, resample_ohlcv)

        # Should have bar_complete column added but no cache file
        assert "bar_complete" in result.columns
        cache_files = list(CACHE_DIR.glob("TEST_1M*"))
        assert len(cache_files) == 0
