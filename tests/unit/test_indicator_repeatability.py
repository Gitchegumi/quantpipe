"""
Test indicator calculation reproducibility and determinism.

This module ensures that indicator calculations produce identical results
across multiple runs with the same inputs, validating deterministic behavior
critical for backtesting reliability.

Principle VIII: Complete docstrings for test modules.
Principle X: Black/Ruff/Pylint compliant.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.indicators.basic import atr, ema, rsi


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def read_fixture_csv(filepath: Path) -> pd.DataFrame:
    """
    Read fixture CSV file into DataFrame.

    Args:
        filepath: Path to CSV file.

    Returns:
        DataFrame with OHLC data.
    """
    return pd.read_csv(filepath)


class TestEMARepeatability:
    """Test EMA calculation repeatability across multiple runs."""

    def test_ema_identical_across_three_runs(self):
        """
        Given identical price inputs and parameters,
        When calculating EMA three times,
        Then all results should be bitwise identical.
        """
        # Load fixture
        filepath = FIXTURES_DIR / "fixture_trend_example.csv"
        df = read_fixture_csv(filepath)
        prices = df["close"].to_numpy()

        # Run EMA calculation 3 times
        run1 = ema(prices, period=5)
        run2 = ema(prices, period=5)
        run3 = ema(prices, period=5)

        # All runs should be identical
        np.testing.assert_array_equal(run1, run2, err_msg="Run 1 != Run 2")
        np.testing.assert_array_equal(run2, run3, err_msg="Run 2 != Run 3")
        np.testing.assert_array_equal(run1, run3, err_msg="Run 1 != Run 3")

    @pytest.mark.parametrize("period", [3, 10, 20, 50])
    def test_ema_deterministic_for_various_periods(self, period):
        """
        Given EMA with various periods,
        When calculating multiple times,
        Then results should be deterministic.
        """
        filepath = FIXTURES_DIR / "sample_candles_long.csv"
        df = read_fixture_csv(filepath)
        prices = df["close"].to_numpy()

        results = [ema(prices, period) for _ in range(3)]

        # All should match
        for i in range(len(results) - 1):
            np.testing.assert_array_equal(
                results[i],
                results[i + 1],
                err_msg=f"EMA period={period} not deterministic between run {i} and {i+1}",
            )


class TestATRRepeatability:
    """Test ATR calculation repeatability across multiple runs."""

    def test_atr_identical_across_three_runs(self):
        """
        Given identical OHLC inputs and parameters,
        When calculating ATR three times,
        Then all results should be bitwise identical.
        """
        # Load fixture
        filepath = FIXTURES_DIR / "fixture_spike_outlier.csv"
        df = read_fixture_csv(filepath)

        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()

        # Run ATR calculation 3 times
        run1 = atr(high, low, close, period=5)
        run2 = atr(high, low, close, period=5)
        run3 = atr(high, low, close, period=5)

        # All runs should be identical
        np.testing.assert_array_equal(run1, run2, err_msg="ATR Run 1 != Run 2")
        np.testing.assert_array_equal(run2, run3, err_msg="ATR Run 2 != Run 3")
        np.testing.assert_array_equal(run1, run3, err_msg="ATR Run 1 != Run 3")

    @pytest.mark.parametrize("period", [5, 10, 14, 20])
    def test_atr_deterministic_for_various_periods(self, period):
        """
        Given ATR with various periods,
        When calculating multiple times,
        Then results should be deterministic.
        """
        filepath = FIXTURES_DIR / "sample_candles_short.csv"
        df = read_fixture_csv(filepath)

        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()

        results = [atr(high, low, close, period) for _ in range(3)]

        # All should match
        for i in range(len(results) - 1):
            np.testing.assert_array_equal(
                results[i],
                results[i + 1],
                err_msg=f"ATR period={period} not deterministic between run {i} and {i+1}",
            )


class TestRSIRepeatability:
    """Test RSI calculation repeatability across multiple runs."""

    def test_rsi_identical_across_three_runs(self):
        """
        Given identical price inputs and parameters,
        When calculating RSI three times,
        Then all results should be bitwise identical.
        """
        # Load fixture
        filepath = FIXTURES_DIR / "sample_candles_long.csv"
        df = read_fixture_csv(filepath)
        prices = df["close"].to_numpy()

        # Run RSI calculation 3 times
        run1 = rsi(prices, period=14)
        run2 = rsi(prices, period=14)
        run3 = rsi(prices, period=14)

        # All runs should be identical
        np.testing.assert_array_equal(run1, run2, err_msg="RSI Run 1 != Run 2")
        np.testing.assert_array_equal(run2, run3, err_msg="RSI Run 2 != Run 3")
        np.testing.assert_array_equal(run1, run3, err_msg="RSI Run 1 != Run 3")

    @pytest.mark.parametrize("period", [7, 14, 21])
    def test_rsi_deterministic_for_various_periods(self, period):
        """
        Given RSI with various periods,
        When calculating multiple times,
        Then results should be deterministic.
        """
        filepath = FIXTURES_DIR / "fixture_trend_example.csv"
        df = read_fixture_csv(filepath)
        prices = df["close"].to_numpy()

        # Need sufficient data for RSI
        if len(prices) < period + 1:
            pytest.skip(f"Insufficient data for RSI period={period}")

        results = [rsi(prices, period) for _ in range(3)]

        # All should match
        for i in range(len(results) - 1):
            np.testing.assert_array_equal(
                results[i],
                results[i + 1],
                err_msg=f"RSI period={period} not deterministic between run {i} and {i+1}",
            )


class TestIndicatorNaNConsistency:
    """Test that NaN patterns are consistent across runs."""

    def test_ema_nan_pattern_repeatable(self):
        """
        Given EMA with warm-up period,
        When calculating multiple times,
        Then NaN positions should be identical.
        """
        filepath = FIXTURES_DIR / "sample_candles_long.csv"
        df = read_fixture_csv(filepath)
        prices = df["close"].to_numpy()

        period = 20
        run1 = ema(prices, period)
        run2 = ema(prices, period)
        run3 = ema(prices, period)

        # NaN masks should be identical
        nan_mask1 = np.isnan(run1)
        nan_mask2 = np.isnan(run2)
        nan_mask3 = np.isnan(run3)

        np.testing.assert_array_equal(
            nan_mask1, nan_mask2, err_msg="NaN pattern mismatch run 1 vs 2"
        )
        np.testing.assert_array_equal(
            nan_mask2, nan_mask3, err_msg="NaN pattern mismatch run 2 vs 3"
        )

    def test_atr_nan_pattern_repeatable(self):
        """
        Given ATR with warm-up period,
        When calculating multiple times,
        Then NaN positions should be identical.
        """
        filepath = FIXTURES_DIR / "sample_candles_short.csv"
        df = read_fixture_csv(filepath)

        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()

        period = 14
        run1 = atr(high, low, close, period)
        run2 = atr(high, low, close, period)
        run3 = atr(high, low, close, period)

        # NaN masks should be identical
        nan_mask1 = np.isnan(run1)
        nan_mask2 = np.isnan(run2)
        nan_mask3 = np.isnan(run3)

        np.testing.assert_array_equal(
            nan_mask1, nan_mask2, err_msg="ATR NaN pattern mismatch run 1 vs 2"
        )
        np.testing.assert_array_equal(
            nan_mask2, nan_mask3, err_msg="ATR NaN pattern mismatch run 2 vs 3"
        )


class TestCrossIndicatorConsistency:
    """Test consistency when combining multiple indicators."""

    def test_ema_crossover_deterministic(self):
        """
        Given EMA20 and EMA50 calculations,
        When computing crossover multiple times,
        Then crossover points should be identical.
        """
        filepath = FIXTURES_DIR / "sample_candles_long.csv"
        df = read_fixture_csv(filepath)
        prices = df["close"].to_numpy()

        # Run 3 times
        results = []
        for _ in range(3):
            ema20 = ema(prices, period=20)
            ema50 = ema(prices, period=50)

            # Find crossover points (simplified: just where ema20 > ema50)
            valid_mask = ~(np.isnan(ema20) | np.isnan(ema50))
            crossover = np.zeros_like(ema20, dtype=bool)
            crossover[valid_mask] = ema20[valid_mask] > ema50[valid_mask]

            results.append(crossover)

        # All should match
        np.testing.assert_array_equal(
            results[0], results[1], err_msg="Crossover mismatch run 1 vs 2"
        )
        np.testing.assert_array_equal(
            results[1], results[2], err_msg="Crossover mismatch run 2 vs 3"
        )
