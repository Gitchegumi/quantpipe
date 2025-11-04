"""Unit tests for CLI strategy listing and registration.

Tests CLI commands:
- --list-strategies
- --register-strategy

Validates FR-001 (registry), FR-017 (CLI listing).
"""

# pylint: disable=unused-argument

import pytest
from src.strategy.registry import StrategyRegistry, RegisteredStrategy


def test_registry_list_empty():
    """Test listing when registry is empty."""
    registry = StrategyRegistry()
    strategies = registry.list()

    assert not strategies


def test_registry_list_single_strategy():
    """Test listing with one registered strategy."""
    registry = StrategyRegistry()

    def dummy_strategy(candles):
        return {"pnl": 100.0}

    registry.register("alpha", dummy_strategy, tags=["trend"], version="1.0.0")
    strategies = registry.list()

    assert len(strategies) == 1
    assert strategies[0].name == "alpha"
    assert strategies[0].tags == ["trend"]
    assert strategies[0].version == "1.0.0"


def test_registry_list_multiple_strategies():
    """Test listing with multiple strategies."""
    registry = StrategyRegistry()

    def strategy_a(candles):
        return {}

    def strategy_b(candles):
        return {}

    registry.register("alpha", strategy_a, tags=["trend", "pullback"])
    registry.register("beta", strategy_b, tags=["momentum"])

    strategies = registry.list()

    assert len(strategies) == 2
    names = [s.name for s in strategies]
    assert "alpha" in names
    assert "beta" in names


def test_registry_register_duplicate_raises_error():
    """Test that registering duplicate name raises ValueError."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy)

    with pytest.raises(ValueError, match="already registered"):
        registry.register("alpha", dummy)


def test_registry_register_duplicate_with_overwrite():
    """Test that overwrite=True allows replacing strategies."""
    registry = StrategyRegistry()

    def old_version(candles):
        return {"version": "old"}

    def new_version(candles):
        return {"version": "new"}

    registry.register("alpha", old_version, version="1.0.0")
    registry.register("alpha", new_version, version="2.0.0", overwrite=True)

    retrieved = registry.get("alpha")
    assert retrieved.version == "2.0.0"


def test_registry_get_existing_strategy():
    """Test retrieving a registered strategy."""
    registry = StrategyRegistry()

    def my_strategy(candles):
        return {"pnl": 50.0}

    registry.register("test_strat", my_strategy)

    retrieved = registry.get("test_strat")
    assert retrieved.name == "test_strat"
    assert callable(retrieved.func)


def test_registry_get_unknown_strategy_raises_error():
    """Test that retrieving unknown strategy raises KeyError."""
    registry = StrategyRegistry()

    with pytest.raises(KeyError):
        registry.get("nonexistent")


def test_registry_preserves_insertion_order():
    """Test that list() preserves registration order."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("charlie", dummy)
    registry.register("alpha", dummy)
    registry.register("beta", dummy)

    strategies = registry.list()
    names = [s.name for s in strategies]

    assert names == ["charlie", "alpha", "beta"]


def test_registered_strategy_immutability():
    """Test that RegisteredStrategy is frozen (immutable)."""

    def dummy(candles):
        return {}

    strat = RegisteredStrategy(
        name="alpha", func=dummy, tags=["trend"], version="1.0.0"
    )

    with pytest.raises((AttributeError, Exception)):  # Frozen dataclass
        strat.name = "beta"  # type: ignore


def test_registry_tags_stored_as_list():
    """Test that tags are converted to list even if provided as tuple."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy, tags=("tag1", "tag2"))

    retrieved = registry.get("alpha")
    assert isinstance(retrieved.tags, list)
    assert retrieved.tags == ["tag1", "tag2"]


def test_registry_no_tags_defaults_to_empty_list():
    """Test that omitting tags results in empty list."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy)

    retrieved = registry.get("alpha")
    assert retrieved.tags == []


def test_registry_no_version_defaults_to_none():
    """Test that omitting version results in None."""
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy)

    retrieved = registry.get("alpha")
    assert retrieved.version is None
