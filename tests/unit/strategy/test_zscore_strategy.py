"""Unit tests for the Z-Score Mean Reversion Strategy."""

from datetime import datetime, timezone
import numpy as np
import pytest
from src.models.core import Candle
from src.strategy.zscore_mean_reversion import ZScoreMeanReversionStrategy


@pytest.fixture
def strategy():
    return ZScoreMeanReversionStrategy()


@pytest.fixture
def sample_candles():
    """Create a sequence of candles with Z-score indicators."""
    candles = []
    base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    
    # Need at least 101 candles for zscore_100
    for i in range(110):
        # Mock Z-score values
        z_val = 0.0
        if i == 105:
            z_val = -2.1  # LONG signal trigger
        elif i == 106:
            z_val = -2.2  # Still in oversold, but shouldn't trigger again
        elif i == 108:
            z_val = 2.1   # SHORT signal trigger
            
        candles.append(
            Candle(
                timestamp_utc=datetime.fromtimestamp(base_time.timestamp() + i * 3600, tz=timezone.utc),
                open=1.1000,
                high=1.1010,
                low=1.0990,
                close=1.1005,
                volume=1000.0,
                indicators={
                    "zscore_100": z_val,
                    "mean_100": 1.1000,
                    "atr14": 0.0010
                }
            )
        )
    return candles


def test_metadata(strategy):
    """Test strategy metadata."""
    metadata = strategy.metadata
    assert metadata.name == "zscore_mean_reversion"
    assert "zscore_100" in metadata.required_indicators
    assert "mean_100" in metadata.required_indicators
    assert metadata.max_concurrent_positions == 1


def test_generate_long_signal(strategy, sample_candles):
    """Test long signal generation."""
    parameters = {
        "zscore_period": 100,
        "entry_threshold": 2.0,
        "stop_atr_multiplier": 3.0,
        "pair": "EURUSD"
    }
    
    signals = strategy.generate_signals(sample_candles, parameters, direction="LONG")
    
    # Should only have one LONG signal from candle 105
    # (Candle 106 is also < -2.0 but it's not a cross)
    assert len(signals) == 1
    assert signals[0].direction == "LONG"
    assert signals[0].entry_price == sample_candles[105].close
    assert signals[0].initial_stop_price < signals[0].entry_price
    assert signals[0].target_price == sample_candles[105].indicators["mean_100"]


def test_generate_short_signal(strategy, sample_candles):
    """Test short signal generation."""
    parameters = {
        "zscore_period": 100,
        "entry_threshold": 2.0,
        "stop_atr_multiplier": 3.0,
        "pair": "EURUSD"
    }
    
    signals = strategy.generate_signals(sample_candles, parameters, direction="SHORT")
    
    assert len(signals) == 1
    assert signals[0].direction == "SHORT"
    assert signals[0].entry_price == sample_candles[108].close
    assert signals[0].initial_stop_price > signals[0].entry_price
    assert signals[0].target_price == sample_candles[108].indicators["mean_100"]


def test_no_signal_when_threshold_not_met(strategy, sample_candles):
    """Test that no signal is generated when threshold is not met."""
    parameters = {
        "zscore_period": 100,
        "entry_threshold": 3.0, # Higher threshold
        "pair": "EURUSD"
    }
    
    signals = strategy.generate_signals(sample_candles, parameters)
    assert len(signals) == 0


def test_custom_indicators(strategy):
    """Test custom indicator definitions."""
    indicators = strategy.get_custom_indicators()
    assert "zscore_100" in indicators
    assert "zscore_50" in indicators
    assert "mean_100" in indicators
    assert "mean_50" in indicators
