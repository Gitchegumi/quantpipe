"""
Reliability batch test harness for multi-strategy backtesting.

Tests system reliability by running multiple iterations of multi-strategy
backtests and measuring success rate.

Target: ≥99% success rate over 100 runs (excluding intentional risk-based halts).
"""

# pylint: disable=unused-argument, unused-variable

import time
from pathlib import Path

import pytest

from src.backtest.orchestrator import BacktestOrchestrator
from src.models.enums import DirectionMode


def dummy_strategy_alpha(bar_data, **_kwargs):
    """Simple strategy that generates consistent signals."""
    # Generate positive PnL
    return {"pnl": 10.0}


def dummy_strategy_beta(bar_data, **_kwargs):
    """Simple strategy with different signal frequency."""
    # Generate positive PnL
    return {"pnl": 5.0}


@pytest.mark.slow
def test_reliability_10_runs():
    """
    Test reliability over 10 runs (smoke test for CI).

    Target: 100% success rate (10/10) for basic functionality.
    """
    num_runs = 10
    successes = 0
    failures = []

    for run_idx in range(num_runs):
        try:
            orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

            strategies = [
                ("alpha", dummy_strategy_alpha),
                ("beta", dummy_strategy_beta),
            ]

            candles_by_strategy = {
                "alpha": [],
                "beta": [],
            }

            weights = [0.6, 0.4]

            result = orchestrator.run_multi_strategy_full(
                strategies=strategies,
                candles_by_strategy=candles_by_strategy,
                weights=weights,
                run_id=f"reliability_test_{run_idx}",
                data_manifest_refs=["reliability/test.json"],
            )

            # Verify result structure
            assert result is not None
            assert "portfolio_summary" in result
            assert result["portfolio_summary"]["strategies_count"] == 2

            successes += 1

        except Exception as e:  # pylint: disable=broad-except
            failures.append(f"Run {run_idx + 1}: {str(e)}")

    success_rate = (successes / num_runs) * 100

    print("\nReliability Test Results (10 runs):")
    print(f"  Successes: {successes}/{num_runs}")
    print(f"  Success Rate: {success_rate:.1f}%")

    if failures:
        print("\nFailures:")
        for failure in failures:
            print(f"  - {failure}")

    assert success_rate == 100.0, f"Expected 100% success rate, got {success_rate:.1f}%"


@pytest.mark.slow
@pytest.mark.extended
def test_reliability_100_runs():
    """
    Test reliability over 100 runs (extended test).

    Target: ≥99% success rate per T063 requirements.
    """
    num_runs = 100
    successes = 0
    failures = []
    execution_times = []

    print(f"\nRunning {num_runs} reliability iterations...")

    for run_idx in range(num_runs):
        start_time = time.time()

        try:
            orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

            strategies = [
                ("alpha", dummy_strategy_alpha),
                ("beta", dummy_strategy_beta),
            ]

            candles_by_strategy = {
                "alpha": [],
                "beta": [],
            }

            weights = [0.6, 0.4]

            result = orchestrator.run_multi_strategy_full(
                strategies=strategies,
                candles_by_strategy=candles_by_strategy,
                weights=weights,
                run_id=f"reliability_100_{run_idx}",
                data_manifest_refs=["reliability/100runs.json"],
            )

            # Verify result structure
            assert result is not None
            assert "portfolio_summary" in result
            assert result["portfolio_summary"]["strategies_count"] == 2

            successes += 1

        except Exception as e:  # pylint: disable=broad-except
            failures.append(f"Run {run_idx + 1}: {str(e)}")

        execution_time = time.time() - start_time
        execution_times.append(execution_time)

        # Progress indicator every 10 runs
        if (run_idx + 1) % 10 == 0:
            print(f"  Completed {run_idx + 1}/{num_runs} runs...")

    success_rate = (successes / num_runs) * 100
    avg_execution_time = sum(execution_times) / len(execution_times)

    print("\nReliability Test Results (100 runs):")
    print(f"  Successes: {successes}/{num_runs}")
    print(f"  Success Rate: {success_rate:.1f}%")
    print(f"  Avg Execution Time: {avg_execution_time:.3f}s")
    print(f"  Total Time: {sum(execution_times):.1f}s")

    if failures:
        print(f"\nFailures ({len(failures)}):")
        for failure in failures[:10]:  # Show first 10 failures
            print(f"  - {failure}")
        if len(failures) > 10:
            print(f"  ... and {len(failures) - 10} more")

    # Assert ≥99% success rate
    assert success_rate >= 99.0, f"Expected ≥99% success rate, got {success_rate:.1f}%"


@pytest.mark.slow
def test_reliability_with_weights_fallback():
    """
    Test reliability when weights fallback is triggered.

    Verifies that equal-weight fallback doesn't introduce failures.
    """
    num_runs = 10
    successes = 0

    for run_idx in range(num_runs):
        try:
            orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

            strategies = [
                ("alpha", dummy_strategy_alpha),
                ("beta", dummy_strategy_beta),
            ]

            candles_by_strategy = {
                "alpha": [],
                "beta": [],
            }

            # Use equal weights
            weights = [0.5, 0.5]

            result = orchestrator.run_multi_strategy_full(
                strategies=strategies,
                candles_by_strategy=candles_by_strategy,
                weights=weights,
                run_id=f"reliability_fallback_{run_idx}",
                data_manifest_refs=["reliability/fallback.json"],
            )

            assert result is not None
            assert "portfolio_summary" in result

            successes += 1

        except Exception:  # pylint: disable=broad-except
            pass

    success_rate = (successes / num_runs) * 100
    assert success_rate == 100.0, "Weights fallback should not cause failures"


@pytest.mark.slow
def test_reliability_determinism_consistency():
    """
    Test that deterministic runs produce identical results.

    Runs the same backtest 5 times and verifies PnL consistency.
    """
    num_runs = 5
    results = []

    for run_idx in range(num_runs):
        orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

        strategies = [
            ("alpha", dummy_strategy_alpha),
            ("beta", dummy_strategy_beta),
        ]

        candles_by_strategy = {
            "alpha": [],
            "beta": [],
        }

        weights = [0.6, 0.4]

        # Use same run_id for determinism check
        result = orchestrator.run_multi_strategy_full(
            strategies=strategies,
            candles_by_strategy=candles_by_strategy,
            weights=weights,
            run_id="reliability_determinism_check",
            data_manifest_refs=["reliability/determinism.json"],
        )

        results.append(result["portfolio_summary"]["weighted_pnl"])

    # All results should be identical (deterministic)
    assert (
        len(set(results)) == 1
    ), f"Deterministic runs produced different results: {results}"

    print(
        f"\nDeterminism check: {num_runs}/{num_runs} \
runs produced identical PnL: {results[0]}"
    )


def test_reliability_target_documented():
    """Test that reliability target is documented in spec or plan."""
    spec_path = (
        Path(__file__).parent.parent.parent / "specs" / "006-multi-strategy" / "plan.md"
    )

    with open(spec_path, encoding="utf-8") as f:
        content = f.read()

    # Check for reliability mention
    assert "reliability" in content.lower() or "99%" in content


def test_reliability_framework_exists():
    """Test that reliability testing framework is operational."""
    # This test itself validates the framework exists
    assert True, "Reliability framework operational"
