"""Unit tests for StrategyMetadata max_concurrent_positions field.

Tests for the max_concurrent_positions attribute added in
feature 018-strategy-trade-rules.
"""

import pytest

from src.strategy.base import StrategyMetadata


class TestStrategyMetadataMaxConcurrent:
    """Tests for max_concurrent_positions field in StrategyMetadata."""

    def test_metadata_default_max_concurrent(self):
        """Default max_concurrent_positions is 1."""
        metadata = StrategyMetadata(
            name="test-strategy",
            version="1.0.0",
            required_indicators=["ema20"],
        )
        assert metadata.max_concurrent_positions == 1

    def test_metadata_custom_max_concurrent(self):
        """Can set max_concurrent_positions to other values."""
        metadata = StrategyMetadata(
            name="test-strategy",
            version="1.0.0",
            required_indicators=["ema20"],
            max_concurrent_positions=3,
        )
        assert metadata.max_concurrent_positions == 3

    def test_metadata_unlimited_concurrent(self):
        """None means unlimited concurrent positions."""
        metadata = StrategyMetadata(
            name="test-strategy",
            version="1.0.0",
            required_indicators=["ema20"],
            max_concurrent_positions=None,
        )
        assert metadata.max_concurrent_positions is None

    def test_metadata_with_tags_and_max_concurrent(self):
        """max_concurrent_positions works with tags."""
        metadata = StrategyMetadata(
            name="test-strategy",
            version="1.0.0",
            required_indicators=["ema20", "ema50"],
            tags=["trend-following"],
            max_concurrent_positions=2,
        )
        assert metadata.max_concurrent_positions == 2
        assert metadata.tags == ["trend-following"]

    def test_metadata_frozen_dataclass(self):
        """StrategyMetadata is immutable (frozen dataclass)."""
        metadata = StrategyMetadata(
            name="test-strategy",
            version="1.0.0",
            required_indicators=["ema20"],
            max_concurrent_positions=1,
        )
        with pytest.raises(AttributeError):
            metadata.max_concurrent_positions = 5
