"""Unit tests for chunking and slicing utilities.

Tests dataset fraction slicing (FR-002), portion selection, chunking logic,
and load+slice timing (SC-003: ≤60s for 10M rows).
"""

# pylint: disable=unused-import, fixme

import time
import pytest
import pandas as pd
from src.backtest.chunking import (
    slice_dataset,
    slice_dataset_list,
    slice_dataset_dataframe,
    chunk_data,
)


class TestSliceDatasetList:
    """Test list-based dataset slicing."""

    def test_slice_full_dataset(self):
        """Full dataset (fraction=1.0) returns all items."""
        data = list(range(1, 101))
        result = slice_dataset_list(data, fraction=1.0)
        assert len(result) == 100
        assert result == data

    def test_slice_quarter_first_portion(self):
        """Fraction=0.25 portion=1 returns first quartile."""
        data = list(range(1, 101))
        result = slice_dataset_list(data, fraction=0.25, portion=1)
        assert len(result) == 25
        assert result == list(range(1, 26))

    def test_slice_quarter_second_portion(self):
        """Fraction=0.25 portion=2 returns second quartile."""
        data = list(range(1, 101))
        result = slice_dataset_list(data, fraction=0.25, portion=2)
        assert len(result) == 25
        assert result == list(range(26, 51))

    def test_slice_half_portions(self):
        """Fraction=0.5 with portions selects correct halves."""
        data = list(range(1, 101))
        first_half = slice_dataset_list(data, fraction=0.5, portion=1)
        second_half = slice_dataset_list(data, fraction=0.5, portion=2)
        assert len(first_half) == 50
        assert len(second_half) == 50
        assert first_half == list(range(1, 51))
        assert second_half == list(range(51, 101))

    def test_slice_default_portion_none(self):
        """Portion=None defaults to first portion."""
        data = list(range(1, 101))
        result = slice_dataset_list(data, fraction=0.25, portion=None)
        assert len(result) == 25
        assert result[0] == 1

    def test_slice_validation_zero_fraction(self):
        """Fraction=0 raises ValueError."""
        data = list(range(1, 101))
        with pytest.raises(ValueError, match="Fraction must be in"):
            slice_dataset_list(data, fraction=0.0)

    def test_slice_validation_negative_fraction(self):
        """Negative fraction raises ValueError."""
        data = list(range(1, 101))
        with pytest.raises(ValueError, match="Fraction must be in"):
            slice_dataset_list(data, fraction=-0.5)

    def test_slice_validation_over_one_fraction(self):
        """Fraction >1.0 raises ValueError."""
        data = list(range(1, 101))
        with pytest.raises(ValueError, match="Fraction must be in"):
            slice_dataset_list(data, fraction=1.5)

    def test_slice_validation_portion_too_low(self):
        """Portion < 1 raises ValueError."""
        data = list(range(1, 101))
        with pytest.raises(ValueError, match="Portion must be in"):
            slice_dataset_list(data, fraction=0.25, portion=0)

    def test_slice_validation_portion_too_high(self):
        """Portion > max_portions raises ValueError."""
        data = list(range(1, 101))
        with pytest.raises(ValueError, match="Portion must be in"):
            slice_dataset_list(data, fraction=0.25, portion=5)

    def test_slice_uneven_division_last_portion(self):
        """Last portion extends to end for uneven division."""
        data = list(range(1, 103))  # 102 items
        result = slice_dataset_list(data, fraction=0.25, portion=4)
        # First 3 portions: 25 each (75 total)
        # Last portion: remaining 27
        assert len(result) == 27
        assert result[-1] == 102


class TestSliceDatasetDataFrame:
    """Test DataFrame-based dataset slicing."""

    def test_slice_full_dataframe(self):
        """Full dataset (fraction=1.0) returns all rows."""
        df = pd.DataFrame({"value": range(1, 101)})
        result = slice_dataset_dataframe(df, fraction=1.0)
        assert len(result) == 100
        pd.testing.assert_frame_equal(result, df)

    def test_slice_quarter_dataframe(self):
        """Fraction=0.25 returns first quarter by default."""
        df = pd.DataFrame({"value": range(1, 101)})
        result = slice_dataset_dataframe(df, fraction=0.25)
        assert len(result) == 25
        assert result["value"].iloc[0] == 1
        assert result["value"].iloc[-1] == 25

    def test_slice_portion_dataframe(self):
        """Portion selection works with DataFrame."""
        df = pd.DataFrame({"value": range(1, 101)})
        result = slice_dataset_dataframe(df, fraction=0.25, portion=2)
        assert len(result) == 25
        assert result["value"].iloc[0] == 26
        assert result["value"].iloc[-1] == 50


class TestSliceDatasetDispatch:
    """Test generic slice_dataset dispatcher."""

    def test_dispatch_to_list(self):
        """Dispatches list to slice_dataset_list."""
        data = list(range(1, 101))
        result = slice_dataset(data, fraction=0.5)
        assert isinstance(result, list)
        assert len(result) == 50

    def test_dispatch_to_dataframe(self):
        """Dispatches DataFrame to slice_dataset_dataframe."""
        df = pd.DataFrame({"value": range(1, 101)})
        result = slice_dataset(df, fraction=0.5)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 50


class TestChunkData:
    """Test chunk_data function."""

    def test_chunk_even_division(self):
        """Evenly divisible dataset chunked correctly."""
        df = pd.DataFrame({"value": range(1, 101)})
        chunks = chunk_data(df, chunk_size=25)
        assert len(chunks) == 4
        assert all(len(chunk) == 25 for chunk in chunks)

    def test_chunk_uneven_division(self):
        """Unevenly divisible dataset handled correctly."""
        df = pd.DataFrame({"value": range(1, 103)})
        chunks = chunk_data(df, chunk_size=25)
        assert len(chunks) == 5
        assert len(chunks[-1]) == 2  # Last chunk has remainder


class TestPerformance:
    """Performance tests for slicing operations (SC-003)."""

    def test_large_list_slice_performance(self):
        """Slicing 1M items completes quickly (proxy for SC-003)."""
        data = list(range(1, 1_000_001))
        start = time.perf_counter()
        result = slice_dataset_list(data, fraction=0.1, portion=1)
        elapsed = time.perf_counter() - start

        assert len(result) == 100_000
        # Should be nearly instant (<0.1s)
        assert elapsed < 0.1, f"Slicing took {elapsed:.3f}s"
