from datetime import datetime, timezone
import sys
import os

# Add src to path
sys.path.append(os.getcwd())

try:
    from src.models.directional import BacktestResult
    from src.models.enums import DirectionMode
    from src.models.core import TradeSignal

    print("Imported models")

    sig = TradeSignal(
        id="test_sig",
        pair="EURUSD",
        direction="LONG",
        entry_price=1.0,
        initial_stop_price=0.9,
        risk_per_trade_pct=0.01,
        calc_position_size=0.0,
        tags=[],
        version="v1",
        timestamp_utc=datetime.now(timezone.utc),
        metadata={"index": 1},
    )
    print("Created TradeSignal")

    res = BacktestResult(
        run_id="test",
        direction_mode="LONG",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        data_start_date=datetime.now(timezone.utc),
        data_end_date=datetime.now(timezone.utc),
        total_candles=100,
        metrics=None,
        pair="EURUSD",
        signals=[sig],
        executions=[],
        conflicts=[],
        dry_run=True,
    )
    print("Created BacktestResult")

    # Test JSON formatting from formatters
    from src.io.formatters import format_json_output, format_text_output

    json_out = format_json_output(res)
    print("Formatted JSON")

    text_out = format_text_output(res)
    print("Formatted Text")

except Exception as e:
    print(f"Failed: {e}")
    import traceback

    traceback.print_exc()
