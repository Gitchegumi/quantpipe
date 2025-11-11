"""Unit tests for indicator registry system.

Tests for indicator specs, registry storage, and dependency resolution.
"""

# pylint: disable=attribute-defined-outside-init

import pytest

from src.indicators.registry.specs import IndicatorSpec
from src.indicators.registry.store import IndicatorRegistry
from src.indicators.registry.deps import (
    topological_sort,
    DependencyCycleError,
    resolve_dependencies,
)


class TestIndicatorSpec:
    """Tests for IndicatorSpec data structure."""

    def test_valid_spec_creation(self):
        """Test creating a valid indicator spec."""
        def dummy_compute(_df, _params):
            return {"result": _df["close"] * 2}

        spec = IndicatorSpec(
            name="test_indicator",
            requires=["close"],
            provides=["result"],
            compute=dummy_compute,
            version="1.0.0",
        )

        assert spec.name == "test_indicator"
        assert spec.requires == ["close"]
        assert spec.provides == ["result"]

    def test_spec_requires_name(self):
        """Test that spec requires a non-empty name."""
        def dummy_compute(_df, _params):
            return {}

        with pytest.raises(ValueError, match="name cannot be empty"):
            IndicatorSpec(
                name="",
                requires=["close"],
                provides=["result"],
                compute=dummy_compute,
            )

    def test_spec_requires_dependencies(self):
        """Test that spec requires dependencies."""
        def dummy_compute(_df, _params):
            return {}

        with pytest.raises(ValueError, match="must specify required columns"):
            IndicatorSpec(
                name="test",
                requires=[],
                provides=["result"],
                compute=dummy_compute,
            )

    def test_spec_requires_provides(self):
        """Test that spec requires provides list."""
        def dummy_compute(_df, _params):
            return {}

        with pytest.raises(ValueError, match="must specify provided columns"):
            IndicatorSpec(
                name="test",
                requires=["close"],
                provides=[],
                compute=dummy_compute,
            )


class TestIndicatorRegistry:
    """Tests for IndicatorRegistry storage and management."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = IndicatorRegistry()

        def dummy_compute(_df, _params):
            return {"result": _df["close"] * 2}

        self.spec = IndicatorSpec(
            name="test_indicator",
            requires=["close"],
            provides=["test_result"],
            compute=dummy_compute,
        )

    def test_register_indicator(self):
        """Test registering an indicator."""
        self.registry.register(self.spec)
        assert self.registry.exists("test_indicator")

    def test_register_duplicate_fails(self):
        """Test registering duplicate indicator fails."""
        self.registry.register(self.spec)

        with pytest.raises(ValueError, match="already registered"):
            self.registry.register(self.spec)

    def test_get_indicator(self):
        """Test retrieving an indicator."""
        self.registry.register(self.spec)
        retrieved = self.registry.get("test_indicator")
        assert retrieved is not None
        assert retrieved.name == "test_indicator"

    def test_get_nonexistent_indicator(self):
        """Test retrieving nonexistent indicator returns None."""
        result = self.registry.get("nonexistent")
        assert result is None

    def test_unregister_indicator(self):
        """Test unregistering an indicator."""
        self.registry.register(self.spec)
        self.registry.unregister("test_indicator")
        assert not self.registry.exists("test_indicator")

    def test_unregister_nonexistent_fails(self):
        """Test unregistering nonexistent indicator fails."""
        with pytest.raises(KeyError, match="not registered"):
            self.registry.unregister("nonexistent")

    def test_list_all_indicators(self):
        """Test listing all indicators."""
        def dummy_compute(_df, _params):
            return {}

        spec2 = IndicatorSpec(
            name="test_indicator2",
            requires=["close"],
            provides=["result2"],
            compute=dummy_compute,
        )

        self.registry.register(self.spec)
        self.registry.register(spec2)

        names = self.registry.list_all()
        assert len(names) == 2
        assert "test_indicator" in names
        assert "test_indicator2" in names

    def test_clear_registry(self):
        """Test clearing the registry."""
        self.registry.register(self.spec)
        self.registry.clear()
        assert len(self.registry.list_all()) == 0


class TestDependencyResolution:
    """Tests for indicator dependency resolution."""

    def setup_method(self):
        """Set up test fixtures."""
        def dummy_compute(_df, _params):
            return {}

        self.indicators = {
            "ema": IndicatorSpec(
                name="ema",
                requires=["close"],
                provides=["ema20"],
                compute=dummy_compute,
            ),
            "atr": IndicatorSpec(
                name="atr",
                requires=["high", "low", "close"],
                provides=["atr14"],
                compute=dummy_compute,
            ),
            "stochrsi": IndicatorSpec(
                name="stochrsi",
                requires=["rsi"],
                provides=["stochrsi"],
                compute=dummy_compute,
            ),
            "rsi": IndicatorSpec(
                name="rsi",
                requires=["close"],
                provides=["rsi"],
                compute=dummy_compute,
            ),
        }

    def test_topological_sort_simple(self):
        """Test topological sort with no dependencies."""
        requested = ["ema", "atr"]
        result = topological_sort(self.indicators, requested)
        assert set(result) == {"ema", "atr"}

    def test_topological_sort_with_dependencies(self):
        """Test topological sort respects dependencies."""
        requested = ["stochrsi", "rsi"]
        result = topological_sort(self.indicators, requested)

        # rsi must come before stochrsi
        assert result.index("rsi") < result.index("stochrsi")

    def test_topological_sort_circular_dependency(self):
        """Test topological sort detects circular dependencies."""
        def dummy_compute(_df, _params):
            return {}

        circular_indicators = {
            "ind1": IndicatorSpec(
                name="ind1",
                requires=["ind2"],
                provides=["result1"],
                compute=dummy_compute,
            ),
            "ind2": IndicatorSpec(
                name="ind2",
                requires=["ind1"],
                provides=["result2"],
                compute=dummy_compute,
            ),
        }

        requested = ["ind1", "ind2"]
        with pytest.raises(DependencyCycleError, match="Circular dependency"):
            topological_sort(circular_indicators, requested)

    def test_topological_sort_missing_indicator(self):
        """Test topological sort fails on missing indicator."""
        requested = ["nonexistent"]
        with pytest.raises(KeyError, match="not found in registry"):
            topological_sort(self.indicators, requested)

    def test_resolve_dependencies(self):
        """Test resolve_dependencies returns specs in order."""
        requested = ["stochrsi", "rsi"]
        specs = resolve_dependencies(self.indicators, requested)

        assert len(specs) == 2
        assert specs[0].name == "rsi"
        assert specs[1].name == "stochrsi"
