"""Unit tests for chunking and slicing utilities.

Tests dataset fraction slicing (FR-002), portion selection, chunking logic,
and load+slice timing (SC-003: ≤60s for 10M rows).
"""

# pylint: disable=unused-import, fixme

import pytest
import pandas as pd
from src.backtest.chunking import slice_dataset, chunk_data


class TestChunking:
    """Test suite for chunking and slicing functions."""

    def test_slice_dataset_full(self):
        """Full dataset (fraction=1.0) returns all rows."""
        # TODO: Implement test with mock DataFrame

    def test_slice_dataset_fraction(self):
        """Fractional slice returns correct row count."""
        # TODO: Test fraction=0.25 returns 25% of rows

    def test_slice_dataset_portion_selection(self):
        """Portion parameter selects correct quartile."""
        # TODO: Test fraction=0.25, portion=2 selects rows [25%, 50%)

    def test_slice_dataset_validation(self):
        """Invalid fraction/portion raises ValueError."""
        # TODO: Test fraction=0, fraction=1.5, portion out of range

    def test_chunk_data(self):
        """Chunking splits dataset into fixed-size chunks."""
        # TODO: Implement chunking test

    # TODO: Add tests for:
    # - Edge case: zero rows
    # - Performance: slice timing for large datasets
