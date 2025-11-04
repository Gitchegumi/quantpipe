import pytest
from src.strategy.registry import StrategyRegistry


def dummy_strategy(_candles):  # placeholder returning minimal result
    return {"pnl": 1.23}


def test_register_and_get_strategy():
    registry = StrategyRegistry()
    registry.register("alpha", dummy_strategy, tags=["trend"], version="0.0.1")
    strat = registry.get("alpha")
    assert strat.name == "alpha"
    assert callable(strat.func)
    assert "trend" in strat.tags


def test_register_duplicate_without_overwrite():
    registry = StrategyRegistry()
    registry.register("alpha", dummy_strategy)
    with pytest.raises(ValueError):
        registry.register("alpha", dummy_strategy)


def test_overwrite_strategy():
    registry = StrategyRegistry()
    registry.register("alpha", dummy_strategy, version="0.0.1")
    registry.register("alpha", dummy_strategy, version="0.0.2", overwrite=True)
    assert registry.get("alpha").version == "0.0.2"


def test_filter_by_name_and_tags():
    registry = StrategyRegistry()
    registry.register("alpha", dummy_strategy, tags=["trend", "pullback"])
    registry.register("beta", dummy_strategy, tags=["range"])
    assert len(registry.filter(names=["alpha"])) == 1
    assert len(registry.filter(tags=["range"])) == 1
    assert len(registry.filter(tags=["trend", "pullback"])) == 1
    assert len(registry.filter(tags=["momentum"])) == 0
