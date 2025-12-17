from datetime import datetime, timezone
from src.models.directional import BacktestResult


def test_backtest_result_property():
    result = BacktestResult(
        run_id="test_run",
        direction_mode="LONG",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        data_start_date=datetime.now(timezone.utc),
        data_end_date=datetime.now(timezone.utc),
        total_candles=100,
        metrics=None,
        symbols=["A", "B"],
    )

    print(f"Has is_multi_symbol: {hasattr(result, 'is_multi_symbol')}")
    print(f"is_multi_symbol value: {result.is_multi_symbol}")

    result_single = BacktestResult(
        run_id="test_run_single",
        direction_mode="LONG",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        data_start_date=datetime.now(timezone.utc),
        data_end_date=datetime.now(timezone.utc),
        total_candles=100,
        metrics=None,
        symbols=["A"],
    )
    print(f"Single symbol is_multi_symbol: {result_single.is_multi_symbol}")


if __name__ == "__main__":
    test_backtest_result_property()
