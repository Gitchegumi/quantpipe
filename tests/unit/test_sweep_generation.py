from src.backtest.sweep import (
    ParameterRange,
    ParameterSet,
    filter_invalid_combinations,
    generate_combinations,
)


def test_generate_combinations_single_param():
    r1 = ParameterRange("inda", "p1", [10, 20])
    combos = generate_combinations([r1])
    assert len(combos) == 2
    assert combos[0].params == {"inda": {"p1": 10}}
    assert combos[1].params == {"inda": {"p1": 20}}


def test_generate_combinations_cross_product():
    r1 = ParameterRange("inda", "p1", [1, 2])
    r2 = ParameterRange("indb", "p2", [10, 20])
    combos = generate_combinations([r1, r2])
    assert len(combos) == 4
    # Order depends on sort, but we expect all 4: (1,10), (1,20), (2,10), (2,20)
    # inda comes before indb
    assert combos[0].params["inda"]["p1"] == 1
    assert combos[0].params["indb"]["p2"] == 10


def test_generate_combinations_nested_params():
    # Same indicator, different params
    r1 = ParameterRange("inda", "p1", [1])
    r2 = ParameterRange("inda", "p2", [10, 20])
    combos = generate_combinations([r1, r2])
    assert len(combos) == 2
    assert combos[0].params == {"inda": {"p1": 1, "p2": 10}}
    assert combos[1].params == {"inda": {"p1": 1, "p2": 20}}


def test_filter_invalid_combinations_default_ema():
    # Default constraint: fast_ema.period < slow_ema.period

    # Valid: 10 < 20
    p1 = ParameterSet(params={"fast_ema": {"period": 10}, "slow_ema": {"period": 20}})
    # Invalid: 20 < 10 (False)
    p2 = ParameterSet(params={"fast_ema": {"period": 20}, "slow_ema": {"period": 10}})
    # Invalid: 20 < 20 (False)
    p3 = ParameterSet(params={"fast_ema": {"period": 20}, "slow_ema": {"period": 20}})

    valid, skipped = filter_invalid_combinations([p1, p2, p3])

    assert len(valid) == 1
    assert valid[0] == p1
    assert skipped == 2


def test_filter_invalid_combinations_no_ema():
    # If no EMA params, should pass default constraint
    p1 = ParameterSet(params={"rsi": {"period": 14}})
    valid, skipped = filter_invalid_combinations([p1])
    assert len(valid) == 1
    assert valid[0] == p1
    assert skipped == 0


def test_filter_invalid_combinations_custom_constraint():
    def custom_rule(ps: ParameterSet):
        return ps.params["ind"]["p"] > 5

    p1 = ParameterSet(params={"ind": {"p": 10}})  # Valid
    p2 = ParameterSet(params={"ind": {"p": 3}})  # Invalid

    valid, skipped = filter_invalid_combinations([p1, p2], constraints=[custom_rule])
    assert len(valid) == 1
    assert valid[0] == p1
    assert skipped == 1
