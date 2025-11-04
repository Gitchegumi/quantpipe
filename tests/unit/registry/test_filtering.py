"""Unit tests for strategy registry filtering logic.

Tests StrategyRegistry.filter() method for:
- Filtering by strategy names
- Filtering by tags
- Combined name and tag filtering
- Empty filter results

Validates FR-004 (CLI selection by name/tag filters).
"""

# pylint: disable=unused-argument, unused-import

import pytest
from src.strategy.registry import StrategyRegistry


def test_filter_by_names_single():
    """Test filtering by single strategy name."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy)
    registry.register("beta", dummy)
    registry.register("gamma", dummy)

    filtered = registry.filter(names=["alpha"])

    assert len(filtered) == 1
    assert filtered[0].name == "alpha"


def test_filter_by_names_multiple():
    """Test filtering by multiple strategy names."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy)
    registry.register("beta", dummy)
    registry.register("gamma", dummy)
    registry.register("delta", dummy)

    filtered = registry.filter(names=["alpha", "gamma"])

    assert len(filtered) == 2
    names = [s.name for s in filtered]
    assert "alpha" in names
    assert "gamma" in names


def test_filter_by_tags_single():
    """Test filtering by single tag."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy, tags=["trend", "pullback"])
    registry.register("beta", dummy, tags=["momentum"])
    registry.register("gamma", dummy, tags=["trend", "breakout"])

    filtered = registry.filter(tags=["trend"])

    assert len(filtered) == 2
    names = [s.name for s in filtered]
    assert "alpha" in names
    assert "gamma" in names


def test_filter_by_tags_multiple_all_required():
    """Test filtering requires ALL specified tags."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy, tags=["trend", "pullback"])
    registry.register("beta", dummy, tags=["trend", "breakout"])
    registry.register("gamma", dummy, tags=["trend"])

    # Must have both "trend" AND "pullback"
    filtered = registry.filter(tags=["trend", "pullback"])

    assert len(filtered) == 1
    assert filtered[0].name == "alpha"


def test_filter_by_names_and_tags():
    """Test combined filtering by names and tags."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy, tags=["trend"])
    registry.register("beta", dummy, tags=["trend"])
    registry.register("gamma", dummy, tags=["momentum"])

    # Name in list AND has tag "trend"
    filtered = registry.filter(names=["alpha", "beta"], tags=["trend"])

    assert len(filtered) == 2
    names = [s.name for s in filtered]
    assert "alpha" in names
    assert "beta" in names


def test_filter_no_matches():
    """Test filtering with no matches returns empty list."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy, tags=["trend"])

    filtered = registry.filter(names=["nonexistent"])

    assert filtered == []


def test_filter_tags_no_matches():
    """Test tag filtering with no matches."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy, tags=["trend"])
    registry.register("beta", dummy, tags=["momentum"])

    filtered = registry.filter(tags=["breakout"])

    assert filtered == []


def test_filter_none_returns_all():
    """Test filter with None arguments returns all strategies."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy)
    registry.register("beta", dummy)
    registry.register("gamma", dummy)

    filtered = registry.filter(names=None, tags=None)

    assert len(filtered) == 3


def test_filter_empty_names_returns_all():
    """Test filter with empty names list returns all strategies."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy)
    registry.register("beta", dummy)

    filtered = registry.filter(names=[])

    assert len(filtered) == 2


def test_filter_preserves_order():
    """Test that filter preserves insertion order."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("charlie", dummy, tags=["trend"])
    registry.register("alpha", dummy, tags=["trend"])
    registry.register("beta", dummy, tags=["trend"])

    filtered = registry.filter(tags=["trend"])

    names = [s.name for s in filtered]
    assert names == ["charlie", "alpha", "beta"]


def test_filter_by_names_case_sensitive():
    """Test that name filtering is case-sensitive."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("Alpha", dummy)
    registry.register("alpha", dummy)

    filtered = registry.filter(names=["alpha"])

    assert len(filtered) == 1
    assert filtered[0].name == "alpha"


def test_filter_partial_tag_match_fails():
    """Test that partial tag matches don't count."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy, tags=["trend"])

    # Strategy has "trend", not "trend-following"
    filtered = registry.filter(tags=["trend-following"])

    assert filtered == []


def test_filter_strategy_with_no_tags():
    """Test filtering strategies that have no tags."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy, tags=[])
    registry.register("beta", dummy, tags=["trend"])

    # Filter by tag should exclude alpha (no tags)
    filtered = registry.filter(tags=["trend"])

    assert len(filtered) == 1
    assert filtered[0].name == "beta"


def test_filter_names_with_duplicates():
    """Test filter handles duplicate names in filter list."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy)
    registry.register("beta", dummy)

    # Duplicate "alpha" in names should not affect result
    filtered = registry.filter(names=["alpha", "alpha"])

    assert len(filtered) == 1
    assert filtered[0].name == "alpha"
