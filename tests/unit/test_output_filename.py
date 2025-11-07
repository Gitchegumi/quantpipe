import re
from datetime import datetime, timezone

from src.io.formatters import generate_output_filename, format_text_output
from src.models.directional import BacktestResult
from src.models.enums import DirectionMode, OutputFormat
from src.models.core import MetricsSummary


def test_generate_output_filename_with_symbol():
    ts = datetime(2025, 11, 6, 12, 34, 56, tzinfo=timezone.utc)
    fn = generate_output_filename(
        DirectionMode.BOTH, OutputFormat.TEXT, ts, symbol_tag="eurusd"
    )
    assert fn == "backtest_both_eurusd_20251106_123456.txt"
    assert re.match(
        r"^backtest_(long|short|both)_([a-z0-9]{6}|multi)_\d{8}_\d{6}\.txt$", fn
    )


def test_generate_output_filename_multi():
    ts = datetime(2025, 11, 6, 12, 34, 56, tzinfo=timezone.utc)
    fn = generate_output_filename(
        DirectionMode.LONG, OutputFormat.JSON, ts, symbol_tag="multi"
    )
    assert fn == "backtest_long_multi_20251106_123456.json"
    assert re.match(
        r"^backtest_(long|short|both)_(multi|[a-z0-9]{6})_\d{8}_\d{6}\.json$", fn
    )


def test_format_text_output_includes_symbol_line():
    # Minimal BacktestResult with pair
    start = datetime(2025, 11, 6, 12, 0, 0, tzinfo=timezone.utc)
    end = datetime(2025, 11, 6, 12, 5, 0, tzinfo=timezone.utc)
    metrics = MetricsSummary(
        trade_count=0,
        win_count=0,
        loss_count=0,
        win_rate=0.0,
        avg_win_r=0.0,
        avg_loss_r=0.0,
        avg_r=0.0,
        expectancy=0.0,
        sharpe_estimate=0.0,
        profit_factor=0.0,
        max_drawdown_r=0.0,
        latency_p95_ms=0.0,
        latency_mean_ms=0.0,
    )
    result = BacktestResult(
        run_id="test_run",
        direction_mode=DirectionMode.LONG.value,
        start_time=start,
        end_time=end,
        data_start_date=start,
        data_end_date=end,
        total_candles=10,
        metrics=metrics,
        pair="EURUSD",
    )
    text = format_text_output(result)
    assert "Symbol:" in text
    assert "EURUSD" in text
