"""Unit tests for weights parsing and normalization."""

import pytest
from src.strategy.weights import parse_and_normalize_weights


def test_valid_weights_pass_through():
    """Valid weights that sum to 1.0 should pass through unchanged."""
    result = parse_and_normalize_weights([0.6, 0.4], 2)
    assert result == [0.6, 0.4]


def test_none_weights_trigger_equal_weight():
    """None weights should trigger equal-weight fallback."""
    result = parse_and_normalize_weights(None, 3)
    expected = [pytest.approx(1/3), pytest.approx(1/3), pytest.approx(1/3)]
    assert result == expected


def test_empty_weights_trigger_equal_weight():
    """Empty list should trigger equal-weight fallback."""
    result = parse_and_normalize_weights([], 2)
    assert result == [0.5, 0.5]


def test_length_mismatch_triggers_fallback():
    """Weights length not matching strategy count triggers fallback."""
    result = parse_and_normalize_weights([0.6, 0.4], 3)
    expected = [pytest.approx(1/3), pytest.approx(1/3), pytest.approx(1/3)]
    assert result == expected


def test_sum_not_one_triggers_fallback():
    """Weights summing to value far from 1.0 triggers fallback."""
    result = parse_and_normalize_weights([0.5, 0.6], 2)  # sum = 1.1
    assert result == [0.5, 0.5]


def test_sum_within_tolerance_passes():
    """Weights summing to ~1.0 within tolerance should pass."""
    weights = [0.333333, 0.333333, 0.333334]  # sum = 1.0
    result = parse_and_normalize_weights(weights, 3)
    assert result == weights


def test_zero_strategy_count_raises():
    """Zero strategy count should raise ValueError."""
    with pytest.raises(ValueError, match="strategy_count must be positive"):
        parse_and_normalize_weights([0.5, 0.5], 0)


def test_negative_strategy_count_raises():
    """Negative strategy count should raise ValueError."""
    with pytest.raises(ValueError, match="strategy_count must be positive"):
        parse_and_normalize_weights([1.0], -1)
