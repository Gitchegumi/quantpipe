from pathlib import Path

import pytest

from src.backtest.sweep import ParameterSet, SweepResult, run_sweep


# Assuming we have EURUSD test data loaded.
# If not, we might need to skip this test if data missing, or mock run_portfolio_backtest.
# For integration test, we prefer real execution if possible.
# But running full backtest is slow.
# We will check if data exists first.

DATA_EXISTS = Path("price_data/processed/eurusd/test/eurusd_test.parquet").exists()


@pytest.mark.skipif(not DATA_EXISTS, reason="EURUSD test data not found")
def test_full_sweep_execution():
    # Define a small sweep
    combinations = [
        ParameterSet(params={"fast_ema": {"period": 5}}, label="Fast=5"),
        ParameterSet(params={"fast_ema": {"period": 10}}, label="Fast=10"),
    ]

    pairs = ["EURUSD"]

    # Run sweep (sequential for deterministic debugging, or parallel to test full stack)
    # Let's run parallel with 2 workers to test that path too
    result = run_sweep(
        combinations=combinations,
        pairs=pairs,
        dataset="test",
        direction="BOTH",
        max_workers=2,
        sequential=False,
    )

    assert isinstance(result, SweepResult)
    assert len(result.results) == 2
    assert result.total_combinations == 2
    assert result.successful_count == 2
    assert result.failed_count == 0

    # Verify results content
    res1 = next(r for r in result.results if r.params.label == "Fast=5")
    res2 = next(r for r in result.results if r.params.label == "Fast=10")

    # Just verify they ran and produced metrics
    assert res1.total_pnl is not None
    assert res2.total_pnl is not None

    # Verify ranking (though with 2, fast=5 vs fast=10 might produce same if no trades, or different)
    # Just check structure
    assert result.best_params is not None
    assert result.execution_time_seconds > 0


@pytest.mark.skipif(not DATA_EXISTS, reason="EURUSD test data not found")
def test_sweep_export(tmp_path):
    from src.backtest.sweep import export_results_to_csv

    combinations = [
        ParameterSet(params={"fast_ema": {"period": 5}}, label="Fast=5"),
    ]
    result = run_sweep(
        combinations=combinations,
        pairs=["EURUSD"],
        dataset="test",
        direction="BOTH",
        max_workers=1,
    )

    export_path = tmp_path / "sweep_results.csv"
    export_results_to_csv(result, export_path)

    assert export_path.exists()
    content = export_path.read_text(encoding="utf-8")
    assert "rank,sharpe_ratio" in content
    assert "fast_ema_period" in content
    assert "5" in content
