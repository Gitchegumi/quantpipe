"""Integration test: Unknown strategy error handling.

Tests error path when user selects non-existent strategy.

Validates FR-011 (fail fast), FR-020 (clear error messages).
"""

# pylint: disable=unused-argument

import pytest
from src.strategy.registry import StrategyRegistry
from src.backtest.validation import validate_pre_run, ValidationError


def test_unknown_strategy_raises_validation_error():
    """
    Test that selecting unknown strategy raises ValidationError.

    Validates FR-011: System fails fast with clear error on unknown strategy.
    """
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy)
    registry.register("beta", dummy)

    with pytest.raises(ValidationError, match="Unknown strategies: gamma"):
        validate_pre_run(
            selected_strategies=["alpha", "gamma"],
            registry=registry,
        )


def test_multiple_unknown_strategies_listed():
    """
    Test that multiple unknown strategies are listed in error.

    Validates FR-020: Clear error messages.
    """
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy)

    with pytest.raises(ValidationError) as exc_info:
        validate_pre_run(
            selected_strategies=["alpha", "unknown1", "unknown2"],
            registry=registry,
        )

    error_msg = str(exc_info.value)
    assert "unknown1" in error_msg
    assert "unknown2" in error_msg


def test_all_unknown_strategies():
    """
    Test error when all selected strategies are unknown.
    """
    registry = StrategyRegistry()

    # Empty registry
    assert registry.count() == 0

    with pytest.raises(ValidationError, match="Unknown strategies"):
        validate_pre_run(
            selected_strategies=["nonexistent1", "nonexistent2"],
            registry=registry,
        )


def test_validation_passes_when_all_known():
    """
    Test validation succeeds when all strategies are registered.
    """
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy)
    registry.register("beta", dummy)
    registry.register("gamma", dummy)

    # Should not raise
    validate_pre_run(
        selected_strategies=["alpha", "beta", "gamma"],
        registry=registry,
    )


def test_empty_selection_raises_error():
    """
    Test that empty strategy list raises validation error.

    Validates FR-011: Fail fast on invalid input.
    """
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy)

    with pytest.raises(ValidationError, match="No strategies selected"):
        validate_pre_run(
            selected_strategies=[],
            registry=registry,
        )


def test_registry_get_unknown_raises_keyerror():
    """
    Test that registry.get() raises KeyError for unknown strategy.
    """
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy)

    with pytest.raises(KeyError):
        registry.get("unknown")


def test_has_method_returns_false_for_unknown():
    """
    Test that registry.has() returns False for unknown strategy.
    """
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy)

    assert registry.has("alpha") is True
    assert registry.has("unknown") is False


def test_case_sensitive_strategy_names():
    """
    Test that strategy names are case-sensitive.

    Validates that "Alpha" and "alpha" are distinct.
    """
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("Alpha", dummy)

    # "alpha" (lowercase) is unknown
    with pytest.raises(ValidationError, match="Unknown strategies: alpha"):
        validate_pre_run(
            selected_strategies=["alpha"],
            registry=registry,
        )


def test_unknown_strategy_with_weights():
    """
    Test unknown strategy error even when weights provided.
    """
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("alpha", dummy)

    with pytest.raises(ValidationError, match="Unknown strategies"):
        validate_pre_run(
            selected_strategies=["alpha", "unknown"],
            registry=registry,
            weights=[0.5, 0.5],
        )


def test_validation_error_message_clarity():
    """
    Test that ValidationError provides clear, actionable message.

    Validates FR-020: Error messages are clear and actionable.
    """
    registry = StrategyRegistry()

    def dummy(candles):
        return {}

    registry.register("trend_strategy", dummy)
    registry.register("momentum_strategy", dummy)

    with pytest.raises(ValidationError) as exc_info:
        validate_pre_run(
            selected_strategies=["trend_strategy", "typo_strategy"],
            registry=registry,
        )

    error_msg = str(exc_info.value)
    # Should clearly indicate which strategy is unknown
    assert "typo_strategy" in error_msg
    assert "Unknown strategies" in error_msg
