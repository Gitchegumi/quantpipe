"""Unit tests for pre-run validation (FR-011, SC-007)."""

# pylint: disable=unused-argument

import pytest
from src.backtest.validation import (
    validate_strategies_exist,
    validate_weights_count,
    validate_pre_run,
    ValidationError,
)
from src.strategy.registry import StrategyRegistry


def dummy_strategy(data):
    """Minimal strategy for testing."""
    return {"signal": 0}


class TestValidateStrategiesExist:
    """Test strategy existence validation."""

    def test_all_strategies_exist_passes(self):
        """Valid case: all selected strategies are registered."""
        registry = StrategyRegistry()
        registry.register("alpha", dummy_strategy)
        registry.register("beta", dummy_strategy)

        # Should not raise
        validate_strategies_exist(["alpha", "beta"], registry)

    def test_unknown_strategy_raises_error(self):
        """Single unknown strategy triggers ValidationError."""
        registry = StrategyRegistry()
        registry.register("alpha", dummy_strategy)

        with pytest.raises(ValidationError, match="Unknown strategies: unknown"):
            validate_strategies_exist(["unknown"], registry)

    def test_multiple_unknown_strategies_listed(self):
        """Multiple unknown strategies listed in error message."""
        registry = StrategyRegistry()
        registry.register("alpha", dummy_strategy)

        with pytest.raises(ValidationError, match="unknown1, unknown2"):
            validate_strategies_exist(["alpha", "unknown1", "unknown2"], registry)

    def test_empty_strategy_list_raises_error(self):
        """Empty strategy list triggers ValidationError."""
        registry = StrategyRegistry()

        with pytest.raises(ValidationError, match="No strategies selected"):
            validate_strategies_exist([], registry)

    def test_partial_match_still_fails(self):
        """If any strategy unknown, validation fails (no partial success)."""
        registry = StrategyRegistry()
        registry.register("alpha", dummy_strategy)

        with pytest.raises(ValidationError, match="unknown"):
            validate_strategies_exist(["alpha", "unknown"], registry)


class TestValidateWeightsCount:
    """Test weights count validation."""

    def test_none_weights_pass(self):
        """None weights are valid (fallback will apply)."""
        # Should not raise
        validate_weights_count(None, 3)

    def test_matching_count_passes(self):
        """Weights count matches strategy count."""
        # Should not raise
        validate_weights_count([0.5, 0.3, 0.2], 3)

    def test_count_mismatch_raises_error(self):
        """Weights count mismatch triggers ValidationError."""
        with pytest.raises(ValidationError, match="Weights count mismatch"):
            validate_weights_count([0.5, 0.5], 3)

    def test_zero_weights_for_nonzero_strategies_fails(self):
        """Empty weights list for non-zero strategies fails."""
        with pytest.raises(ValidationError, match="Weights count mismatch"):
            validate_weights_count([], 2)


class TestValidatePreRun:
    """Test combined pre-run validation."""

    def test_valid_configuration_passes(self):
        """Fully valid configuration passes all checks."""
        registry = StrategyRegistry()
        registry.register("alpha", dummy_strategy)
        registry.register("beta", dummy_strategy)

        # Should not raise
        validate_pre_run(["alpha", "beta"], registry, weights=[0.6, 0.4])

    def test_valid_without_weights_passes(self):
        """Valid configuration with None weights passes."""
        registry = StrategyRegistry()
        registry.register("alpha", dummy_strategy)

        # Should not raise (None weights OK, fallback will apply)
        validate_pre_run(["alpha"], registry, weights=None)

    def test_unknown_strategy_fails_pre_run(self):
        """Unknown strategy fails combined validation."""
        registry = StrategyRegistry()
        registry.register("alpha", dummy_strategy)

        with pytest.raises(ValidationError, match="Unknown strategies"):
            validate_pre_run(["unknown"], registry, weights=[1.0])

    def test_weights_mismatch_fails_pre_run(self):
        """Weights count mismatch fails combined validation."""
        registry = StrategyRegistry()
        registry.register("alpha", dummy_strategy)
        registry.register("beta", dummy_strategy)

        with pytest.raises(ValidationError, match="Weights count mismatch"):
            validate_pre_run(["alpha", "beta"], registry, weights=[1.0])

    def test_empty_strategies_fails_pre_run(self):
        """Empty strategy list fails combined validation."""
        registry = StrategyRegistry()

        with pytest.raises(ValidationError, match="No strategies selected"):
            validate_pre_run([], registry)
