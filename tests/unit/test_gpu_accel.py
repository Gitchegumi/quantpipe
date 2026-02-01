"""
Unit tests for GPU acceleration and fallback.
"""

import pytest
import polars as pl
import numpy as np
from src.backtest.gpu_utils import is_gpu_available
from src.backtest.vectorized_rolling_window import calculate_ema, calculate_atr
from src.strategy.trend_pullback.signal_generator_vectorized import generate_signals_vectorized

@pytest.fixture
def sample_df():
    """Create a sample Polars DataFrame."""
    n = 100
    return pl.DataFrame({
        "timestamp_utc": np.arange(n),
        "open": np.random.randn(n) + 100,
        "high": np.random.randn(n) + 101,
        "low": np.random.randn(n) + 99,
        "close": np.random.randn(n) + 100,
    })

def test_gpu_fallback_graceful(sample_df):
    """Ensure that if GPU is requested but not available, it falls back to CPU."""
    # We can't easily force GPU unavailability if it's there, 
    # but we can check that it doesn't crash.
    result = calculate_ema(sample_df, period=20, use_gpu=True)
    assert "ema20" in result.columns
    assert len(result) == len(sample_df)

def test_cpu_gpu_equivalence(sample_df):
    """Ensure CPU and GPU paths produce identical results (if GPU available)."""
    res_cpu = calculate_ema(sample_df, period=10, use_gpu=False)
    res_gpu = calculate_ema(sample_df, period=10, use_gpu=True)
    
    # Even if GPU path is just a fallback to CPU, they should be equal.
    # If GPU path is implemented, they should match within floating point precision.
    np.testing.assert_array_almost_equal(
        res_cpu["ema10"].to_numpy(),
        res_gpu["ema10"].to_numpy()
    )

def test_signal_generation_gpu_flag(sample_df):
    """Ensure signal generation accepts use_gpu flag."""
    # Add required indicators for strategy
    df = sample_df.with_columns([
        pl.lit(100.0).alias("fast_ema"),
        pl.lit(100.0).alias("slow_ema"),
        pl.lit(50.0).alias("rsi"),
        pl.lit(0.5).alias("stoch_rsi"),
        pl.lit(0.001).alias("atr"),
    ])
    
    params = {"pullback_max_age": 20}
    signals = generate_signals_vectorized(df, parameters=params, use_gpu=True)
    assert isinstance(signals, list)

def test_gpu_availability_check():
    """Test the utility function."""
    avail = is_gpu_available()
    assert isinstance(avail, bool)
