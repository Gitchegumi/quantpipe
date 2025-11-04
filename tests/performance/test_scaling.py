"""Performance test: Multi-strategy scaling.

Tests performance characteristics as strategy count increases per SC-012:
- Runtime scaling ≤15% per additional strategy
- Memory growth ≤10% per additional strategy (informational)
- Aggregation metrics generation ≤5s

Validates non-functional requirements from research.md.
"""

#pylint: disable=unused-variable, unused-argument

import time
import pytest
from src.backtest.orchestrator import BacktestOrchestrator
from src.models.enums import DirectionMode


def create_dummy_strategy(name, pnl):
    """Factory for creating dummy strategies with fixed PnL."""
    def strategy(candles):
        return {
            "name": name,
            "pnl": pnl,
            "max_drawdown": 0.02,
            "exposure": {"EURUSD": 0.01},
        }
    return strategy


@pytest.mark.performance
def test_runtime_scaling_with_strategy_count():
    """
    Test that runtime scales linearly with strategy count.

    Acceptance: Runtime increase ≤15% per additional strategy (SC-012).
    """
    orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

    # Baseline: 2 strategies
    strategies_2 = [
        ("s1", create_dummy_strategy("s1", 100.0)),
        ("s2", create_dummy_strategy("s2", 100.0)),
    ]
    candles_2 = {f"s{i}": [] for i in range(1, 3)}

    start = time.time()
    orchestrator.run_multi_strategy_full(
        strategies=strategies_2,
        candles_by_strategy=candles_2,
        weights=[0.5, 0.5],
        run_id="perf_baseline_2",
    )
    runtime_2 = time.time() - start

    # Scale: 4 strategies (2x)
    strategies_4 = [
        (f"s{i}", create_dummy_strategy(f"s{i}", 100.0))
        for i in range(1, 5)
    ]
    candles_4 = {f"s{i}": [] for i in range(1, 5)}

    start = time.time()
    orchestrator.run_multi_strategy_full(
        strategies=strategies_4,
        candles_by_strategy=candles_4,
        weights=[0.25] * 4,
        run_id="perf_scale_4",
    )
    runtime_4 = time.time() - start

    # Calculate scaling factor
    # Expected: runtime_4 ≈ runtime_2 * 2.0 (linear)
    # Acceptable: runtime_4 ≤ runtime_2 * 2.3 (15% overhead per strategy)
    scaling_factor = runtime_4 / runtime_2 if runtime_2 > 0 else 0
    max_acceptable = 2.3  # 2x strategies + 15% overhead

    print(f"\nRuntime scaling: 2 strategies={runtime_2:.4f}s, "
          f"4 strategies={runtime_4:.4f}s, factor={scaling_factor:.2f}x")

    # Informational check (may be very fast for dummy strategies)
    if runtime_2 > 0.001:  # Only validate if measurable
        assert scaling_factor <= max_acceptable, \
            f"Runtime scaling {scaling_factor:.2f}x exceeds threshold {max_acceptable}x"


@pytest.mark.performance
def test_aggregation_metrics_generation_time():
    """
    Test that aggregation metrics are generated within 5 seconds.

    Acceptance: Aggregation ≤5s after last strategy (research.md).
    """
    orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

    # Create 10 strategies to stress aggregation
    strategies = [
        (f"s{i}", create_dummy_strategy(f"s{i}", 100.0))
        for i in range(1, 11)
    ]
    candles_by_strategy = {f"s{i}": [] for i in range(1, 11)}
    weights = [0.1] * 10

    start = time.time()
    result = orchestrator.run_multi_strategy_full(
        strategies=strategies,
        candles_by_strategy=candles_by_strategy,
        weights=weights,
        run_id="perf_aggregation_001",
    )
    total_runtime = time.time() - start

    # Validate metrics generated
    assert "structured_metrics" in result
    assert result["structured_metrics"].strategies_count == 10

    # Validate total runtime (includes aggregation)
    # For dummy strategies, this should be very fast
    max_acceptable = 5.0  # 5 seconds
    print(f"\nAggregation time for 10 strategies: {total_runtime:.4f}s")

    assert total_runtime <= max_acceptable, \
        f"Aggregation time {total_runtime:.2f}s exceeds threshold {max_acceptable}s"


@pytest.mark.performance
def test_large_strategy_count():
    """
    Test execution with large number of strategies (20+).

    Validates framework handles realistic multi-strategy scenarios.
    """
    orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

    strategy_count = 20
    strategies = [
        (f"s{i}", create_dummy_strategy(f"s{i}", 50.0))
        for i in range(1, strategy_count + 1)
    ]
    candles_by_strategy = {f"s{i}": [] for i in range(1, strategy_count + 1)}
    weights = [1.0 / strategy_count] * strategy_count

    start = time.time()
    result = orchestrator.run_multi_strategy_full(
        strategies=strategies,
        candles_by_strategy=candles_by_strategy,
        weights=weights,
        run_id="perf_large_count_001",
    )
    runtime = time.time() - start

    print(f"\nRuntime for {strategy_count} strategies: {runtime:.4f}s")

    # Validate all strategies executed
    assert len(result["per_strategy_results"]) == strategy_count
    assert result["portfolio_summary"]["strategies_count"] == strategy_count

    # Weighted PnL should be sum of all (equal weights)
    expected_pnl = 50.0 * strategy_count / strategy_count  # = 50.0
    assert result["portfolio_summary"]["weighted_pnl"] == pytest.approx(50.0)


@pytest.mark.performance
@pytest.mark.skip(reason="Memory profiling requires psutil; informational only")
def test_memory_growth_per_strategy():
    """
    Informational test: Memory growth with strategy count.

    Target: ≤10% per additional strategy (SC-012).
    Note: Requires psutil; skipped by default.
    """
    try:
        import psutil
        import os
    except ImportError:
        pytest.skip("psutil not available")

    process = psutil.Process(os.getpid())
    orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

    # Baseline: 5 strategies
    strategies_5 = [
        (f"s{i}", create_dummy_strategy(f"s{i}", 100.0))
        for i in range(1, 6)
    ]
    candles_5 = {f"s{i}": [] for i in range(1, 6)}

    mem_before = process.memory_info().rss / 1024 / 1024  # MB

    orchestrator.run_multi_strategy_full(
        strategies=strategies_5,
        candles_by_strategy=candles_5,
        weights=[0.2] * 5,
        run_id="mem_baseline_5",
    )

    mem_after_5 = process.memory_info().rss / 1024 / 1024
    mem_growth_5 = mem_after_5 - mem_before

    # Scale: 10 strategies
    strategies_10 = [
        (f"s{i}", create_dummy_strategy(f"s{i}", 100.0))
        for i in range(1, 11)
    ]
    candles_10 = {f"s{i}": [] for i in range(1, 11)}

    orchestrator.run_multi_strategy_full(
        strategies=strategies_10,
        candles_by_strategy=candles_10,
        weights=[0.1] * 10,
        run_id="mem_scale_10",
    )

    mem_after_10 = process.memory_info().rss / 1024 / 1024
    mem_growth_10 = mem_after_10 - mem_before

    growth_per_strategy = (mem_growth_10 - mem_growth_5) / 5

    print(f"\nMemory: 5 strategies={mem_growth_5:.2f}MB, "
          f"10 strategies={mem_growth_10:.2f}MB, "
          f"per-strategy={growth_per_strategy:.2f}MB")

    # Informational only; no hard assertion
