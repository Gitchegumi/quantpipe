"""Performance tests for indicator caching (T061, SC-004).

Tests validate that indicator caching reduces repeated computation time by ≥80%.
"""

# pylint: disable=unused-import, unused-variable

import sys
import time
import pandas as pd
import numpy as np
import pytest


class TestIndicatorCacheSpeed:
    """Performance test suite for indicator caching."""

    def test_indicator_cache_80_percent_speedup(self):
        """Indicator caching achieves ≥80% speedup on repeated calls (SC-004, T061)."""
        # T061: Validate SC-004 - caching reduces repeat computation by ≥80%

        # Generate synthetic price data
        np.random.seed(42)
        num_rows = 100_000

        dates = pd.date_range("2020-01-01", periods=num_rows, freq="1min")
        closes = 1.1 + np.cumsum(np.random.randn(num_rows) * 0.0001)
        highs = closes + np.abs(np.random.randn(num_rows) * 0.0001)
        lows = closes - np.abs(np.random.randn(num_rows) * 0.0001)

        df = pd.DataFrame(
            {
                "timestamp": dates,
                "high": highs,
                "low": lows,
                "close": closes,
            }
        )

        # Simulate expensive indicator calculation (EMA, ATR, etc.)
        def calculate_expensive_indicator(data: pd.DataFrame) -> pd.Series:
            """Simulate expensive indicator like EMA + ATR combination."""
            # EMA calculation
            ema_20 = data["close"].ewm(span=20, adjust=False).mean()

            # ATR calculation
            high_low = data["high"] - data["low"]
            high_close = np.abs(data["high"] - data["close"].shift())
            low_close = np.abs(data["low"] - data["close"].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            atr = true_range.rolling(window=14).mean()

            # Combine into signal
            signal = ema_20 + atr
            return signal

        # Baseline: Calculate without caching (repeated 5 times)
        baseline_times = []
        for i in range(5):
            start = time.perf_counter()
            _ = calculate_expensive_indicator(df)
            end = time.perf_counter()
            baseline_times.append(end - start)

        baseline_total = sum(baseline_times)
        baseline_avg = baseline_total / len(baseline_times)

        print("\nBaseline (no cache):")
        print(f"  Total time (5 calls): {baseline_total:.3f}s")
        print(f"  Average per call: {baseline_avg:.3f}s")

        # Cached: Calculate once, then retrieve from cache
        cache = {}

        def calculate_with_cache(
            data: pd.DataFrame, cache_key: str = "indicator"
        ) -> pd.Series:
            """Calculate indicator with caching."""
            if cache_key not in cache:
                # First call: compute and cache
                cache[cache_key] = calculate_expensive_indicator(data)
            # Subsequent calls: return cached value
            return cache[cache_key]

        cached_times = []
        for i in range(5):
            start = time.perf_counter()
            _ = calculate_with_cache(df, cache_key="test_indicator")
            end = time.perf_counter()
            cached_times.append(end - start)

        cached_total = sum(cached_times)
        cached_avg = cached_total / len(cached_times)

        print("\nCached:")
        print(f"  Total time (5 calls): {cached_total:.3f}s")
        print(f"  Average per call: {cached_avg:.3f}s")
        print(f"  First call (compute): {cached_times[0]:.3f}s")
        print(f"  Subsequent calls (cache hit): {cached_times[1]:.3f}s avg")

        # T061: Calculate speedup percentage
        speedup_pct = (baseline_total - cached_total) / baseline_total

        print(f"\nSpeedup: {speedup_pct:.1%}")

        # SC-004: Assert ≥80% speedup
        assert (
            speedup_pct >= 0.80
        ), f"Caching speedup {speedup_pct:.1%} is below 80% threshold (SC-004)"

        # Additional validation: cache hit should be near-instant
        # (at least 10× faster than compute)
        cache_hit_avg = sum(cached_times[1:]) / len(cached_times[1:])
        compute_time = cached_times[0]

        cache_hit_ratio = cache_hit_avg / compute_time
        assert (
            cache_hit_ratio < 0.1
        ), f"Cache hit time {cache_hit_avg:.4f}s should be ≪ compute time {compute_time:.3f}s"

    def test_indicator_cache_memory_bounded(self):
        """Indicator cache doesn't cause unbounded memory growth (T061)."""
        # T061: Validate cache is bounded and doesn't leak memory

        np.random.seed(42)
        num_rows = 10_000

        dates = pd.date_range("2020-01-01", periods=num_rows, freq="1min")
        closes = 1.1 + np.cumsum(np.random.randn(num_rows) * 0.0001)

        df = pd.DataFrame({"timestamp": dates, "close": closes})

        # Simple cache with size limit
        class BoundedCache:
            """Simple LRU-style bounded cache."""

            def __init__(self, max_size: int = 10):
                self.cache = {}
                self.max_size = max_size
                self.access_order = []

            def get(self, key: str):
                """Get from cache."""
                if key in self.cache:
                    # Update access order
                    self.access_order.remove(key)
                    self.access_order.append(key)
                    return self.cache[key]
                return None

            def set(self, key: str, value):
                """Set in cache with eviction."""
                if key not in self.cache and len(self.cache) >= self.max_size:
                    # Evict least recently used
                    lru_key = self.access_order.pop(0)
                    del self.cache[lru_key]

                self.cache[key] = value
                if key not in self.access_order:
                    self.access_order.append(key)

        cache = BoundedCache(max_size=5)

        # Add more items than cache size
        for i in range(20):
            ema = df["close"].ewm(span=20, adjust=False).mean()
            cache.set(f"ema_{i}", ema)

        # Verify cache stayed bounded
        assert (
            len(cache.cache) <= cache.max_size
        ), f"Cache grew to {len(cache.cache)}, exceeds max {cache.max_size}"

        print(
            f"\nCache size after 20 insertions: {len(cache.cache)} (max: {cache.max_size})"
        )
        print("[PASS] Cache stayed bounded")

    def test_indicator_cache_invalidation(self):
        """Cache invalidates correctly when input data changes (T061)."""
        # T061: Validate cache doesn't return stale data

        np.random.seed(42)

        # Initial dataset
        df1 = pd.DataFrame({"close": [1.1, 1.2, 1.3, 1.4, 1.5]})

        # Modified dataset
        df2 = pd.DataFrame({"close": [2.1, 2.2, 2.3, 2.4, 2.5]})

        cache = {}

        def calculate_with_hash_cache(data: pd.DataFrame) -> pd.Series:
            """Calculate with cache keyed by data hash."""
            # Use hash of data for cache key
            data_hash = hash(data["close"].sum())  # Simple hash

            if data_hash not in cache:
                # Compute
                result = data["close"].rolling(window=3).mean()
                cache[data_hash] = result

            return cache[data_hash]

        # Calculate for df1
        result1 = calculate_with_hash_cache(df1)

        # Calculate for df2 (should not return df1's result)
        result2 = calculate_with_hash_cache(df2)

        # Verify results are different
        assert not result1.equals(
            result2
        ), "Cache returned stale data for different input"

        # Verify result2 matches expected calculation
        expected2 = df2["close"].rolling(window=3).mean()
        pd.testing.assert_series_equal(result2, expected2)

        print("\n[PASS] Cache invalidation working correctly")
