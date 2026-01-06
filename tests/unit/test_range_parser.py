import pytest

from src.backtest.sweep import parse_range_input


def test_empty_input_uses_default():
    values, is_range = parse_range_input("", 20, int)
    assert values == [20]
    assert is_range is False


def test_single_value_int():
    values, is_range = parse_range_input("15", 20, int)
    assert values == [15]
    assert is_range is False
    assert isinstance(values[0], int)


def test_single_value_float():
    values, is_range = parse_range_input("15.5", 20.0, float)
    assert values == [15.5]
    assert is_range is False
    assert isinstance(values[0], float)


def test_range_input_inclusive_int():
    # 10-30 step 5 -> 10, 15, 20, 25, 30
    values, is_range = parse_range_input("10-30 step 5", 20, int)
    assert values == [10, 15, 20, 25, 30]
    assert is_range is True
    assert all(isinstance(v, int) for v in values)


def test_range_input_float():
    # 0.1-0.3 step 0.1 -> 0.1, 0.2, 0.3
    # Float precision might be tricky, usually implementation uses epsilon or np.arange-like logic?
    # Let's check implementation behavior
    values, is_range = parse_range_input("0.1-0.3 step 0.1", 0.5, float)
    assert len(values) == 3
    assert abs(values[0] - 0.1) < 1e-9
    assert abs(values[-1] - 0.3) < 1e-9
    assert is_range is True


def test_range_step_larger_than_range():
    # 10-12 step 5 -> 10
    values, is_range = parse_range_input("10-12 step 5", 20, int)
    assert values == [10]
    assert is_range is True


def test_invalid_step_negative():
    # Negative step doesn't match regex, so raises generic invalid format error
    with pytest.raises(ValueError, match="Invalid input format"):
        parse_range_input("10-30 step -5", 20, int)


def test_invalid_start_greater_than_end():
    with pytest.raises(ValueError, match="Start must be <= end"):
        parse_range_input("30-10 step 5", 20, int)


def test_invalid_syntax_garbage():
    with pytest.raises(ValueError):
        parse_range_input("nonsense", 20, int)
