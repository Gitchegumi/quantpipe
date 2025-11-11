"""Unit tests for zero-indicator strategy edge case.

This module validates that the system handles strategies declaring zero
indicators without errors (edge case from spec: "Strategy declares zero
indicators: system runs and produces zero indicator-derived signals without error").

Tests verify:
- Zero-indicator strategy can be instantiated
- IndicatorRegistry handles zero indicators correctly
- BatchScan processes zero-indicator strategies
- No false signals generated from missing indicators
"""

import numpy as np
import polars as pl
import pytest

from src.backtest.batch_scan import BatchScan
from src.preprocess.indicator_inputs import IndicatorInputExtractor
from src.strategy.indicator_registry import IndicatorRegistry


@pytest.fixture
def zero_indicator_strategy():
    """Create a strategy declaring zero indicators."""

    class ZeroIndicatorMetadata:
        """Mock metadata with zero indicators."""

        name = "zero_indicator_strategy"
        version = "1.0.0"
        required_indicators = []  # Empty list

    class ZeroIndicatorStrategy:
        """Strategy with no indicators."""

        @property
        def metadata(self):
            """Return metadata."""
            return ZeroIndicatorMetadata()

        def generate_signals(self, candles, parameters):
            """Mock signal generation without indicators."""
            return []

    return ZeroIndicatorStrategy()


@pytest.fixture
def ohlc_only_dataframe():
    """Create DataFrame with OHLC data only (no indicators)."""
    n_rows = 1000
    timestamps = np.arange(n_rows, dtype=np.int64) * 60

    return pl.DataFrame(
        {
            "timestamp_utc": timestamps,
            "open": np.random.uniform(1.1, 1.2, n_rows),
            "high": np.random.uniform(1.2, 1.3, n_rows),
            "low": np.random.uniform(1.0, 1.1, n_rows),
            "close": np.random.uniform(1.1, 1.2, n_rows),
        }
    )


def test_zero_indicator_strategy_instantiation(zero_indicator_strategy):
    """Test that zero-indicator strategy can be instantiated.

    Verifies:
    - Strategy with empty required_indicators list is valid
    - Metadata is properly structured
    """
    assert zero_indicator_strategy.metadata.required_indicators == []
    assert zero_indicator_strategy.metadata.name == "zero_indicator_strategy"


def test_indicator_registry_zero_indicators(zero_indicator_strategy):
    """Test IndicatorRegistry handles zero indicators.

    Verifies:
    - Registry accepts zero-indicator strategy
    - is_zero_indicator_strategy() returns True
    - get_indicator_count() returns 0
    - get_indicator_names() returns empty tuple
    """
    registry = IndicatorRegistry(zero_indicator_strategy)

    assert registry.is_zero_indicator_strategy()
    assert registry.get_indicator_count() == 0
    assert registry.get_indicator_names() == ()


def test_indicator_registry_zero_validation(zero_indicator_strategy):
    """Test IndicatorRegistry validation with zero indicators.

    Verifies:
    - validate_exact_match() accepts empty list
    - validate_no_extras() accepts empty list
    - validate_subset() accepts empty list
    """
    registry = IndicatorRegistry(zero_indicator_strategy)

    # All validations should pass with empty lists
    registry.validate_exact_match([])
    registry.validate_no_extras([])
    registry.validate_subset([])


def test_indicator_registry_zero_rejects_extras(zero_indicator_strategy):
    """Test IndicatorRegistry rejects any indicators when zero declared.

    Verifies:
    - Any indicator is considered "unauthorized" for zero-indicator strategy
    - Appropriate error raised
    """
    registry = IndicatorRegistry(zero_indicator_strategy)

    # Should reject any indicator
    with pytest.raises(ValueError, match="Unauthorized indicators"):
        registry.validate_no_extras(["ema20"])

    with pytest.raises(ValueError, match="not declared by strategy"):
        registry.validate_subset(["ema20"])


def test_indicator_extractor_zero_indicators(zero_indicator_strategy):
    """Test IndicatorInputExtractor handles zero indicators.

    Verifies:
    - Extractor accepts zero-indicator strategy
    - get_indicator_names() returns empty list
    - get_zero_indicator_flag() returns True
    """
    extractor = IndicatorInputExtractor(zero_indicator_strategy)

    assert extractor.get_indicator_names() == []
    assert extractor.get_zero_indicator_flag()


def test_indicator_extractor_zero_validation(
    zero_indicator_strategy, ohlc_only_dataframe
):
    """Test IndicatorInputExtractor validation with zero indicators.

    Verifies:
    - validate_inputs() succeeds with OHLC-only DataFrame
    - validate_arrays() succeeds with empty dict
    """
    extractor = IndicatorInputExtractor(zero_indicator_strategy)

    # Should validate successfully even without indicators
    extractor.validate_inputs(ohlc_only_dataframe)
    assert extractor.is_validated()

    # Should validate empty arrays dict
    extractor.validate_arrays({})


def test_batch_scan_zero_indicators(zero_indicator_strategy, ohlc_only_dataframe):
    """Test BatchScan processes zero-indicator strategy.

    Verifies:
    - BatchScan accepts zero-indicator strategy
    - Scan completes without errors
    - No signals generated (expected for placeholder implementation)
    - Metrics are properly tracked
    """
    scanner = BatchScan(strategy=zero_indicator_strategy, enable_progress=False)
    result = scanner.scan(ohlc_only_dataframe)

    assert result is not None
    assert result.candles_processed == len(ohlc_only_dataframe)
    assert result.signal_count == 0
    assert result.scan_duration_sec > 0


def test_batch_scan_zero_indicators_with_progress(
    zero_indicator_strategy, ohlc_only_dataframe
):
    """Test BatchScan with progress enabled for zero-indicator strategy.

    Verifies:
    - Progress tracking works with zero indicators
    - Overhead is tracked correctly
    """
    scanner = BatchScan(strategy=zero_indicator_strategy, enable_progress=True)
    result = scanner.scan(ohlc_only_dataframe)

    assert result.progress_overhead_pct >= 0.0


def test_zero_indicator_mapping(zero_indicator_strategy):
    """Test indicator mapping for zero-indicator strategy.

    Verifies:
    - get_indicator_mapping() returns empty dict
    - No index mapping exists
    """
    registry = IndicatorRegistry(zero_indicator_strategy)
    mapping = registry.get_indicator_mapping()

    assert mapping == {}


def test_zero_indicator_strategy_repr(zero_indicator_strategy):
    """Test string representation of zero-indicator components.

    Verifies:
    - __repr__ methods produce readable output
    """
    registry = IndicatorRegistry(zero_indicator_strategy)
    repr_str = repr(registry)

    assert "indicators=0" in repr_str
    assert "zero_indicator_strategy" in repr_str


def test_zero_indicator_with_extra_columns(zero_indicator_strategy):
    """Test zero-indicator strategy ignores extra DataFrame columns.

    Verifies:
    - Extra columns (e.g., volume, is_gap) are ignored
    - Only OHLC columns are required
    - No errors raised for additional data
    """
    n_rows = 100
    timestamps = np.arange(n_rows, dtype=np.int64) * 60

    df_with_extras = pl.DataFrame(
        {
            "timestamp_utc": timestamps,
            "open": np.random.uniform(1.1, 1.2, n_rows),
            "high": np.random.uniform(1.2, 1.3, n_rows),
            "low": np.random.uniform(1.0, 1.1, n_rows),
            "close": np.random.uniform(1.1, 1.2, n_rows),
            "volume": np.random.uniform(1000, 10000, n_rows),
            "is_gap": np.zeros(n_rows, dtype=bool),
            "extra_column": np.random.uniform(0, 1, n_rows),
        }
    )

    scanner = BatchScan(strategy=zero_indicator_strategy, enable_progress=False)
    result = scanner.scan(df_with_extras)

    assert result.candles_processed == n_rows


def test_zero_indicator_deterministic_behavior(
    zero_indicator_strategy, ohlc_only_dataframe
):
    """Test zero-indicator strategy produces deterministic results.

    Verifies:
    - Multiple scans produce identical results
    - No random signal generation
    """
    scanner = BatchScan(strategy=zero_indicator_strategy, enable_progress=False)

    result1 = scanner.scan(ohlc_only_dataframe)
    result2 = scanner.scan(ohlc_only_dataframe)

    assert result1.signal_count == result2.signal_count
    assert result1.candles_processed == result2.candles_processed
    assert np.array_equal(result1.signal_indices, result2.signal_indices)
