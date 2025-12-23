"""Integration test for portfolio visualization data structure.

Verifies that the object passed to plot_backtest_results:
1. Is a BacktestResult
2. Has is_multi_symbol=True (or equivalent structure)
3. Has populated `results` dictionary with child results per symbol
"""

import sys
from unittest.mock import MagicMock, patch
from pathlib import Path
import pytest
from datetime import datetime, timezone

from src.cli.run_backtest import main
from src.models.enums import DirectionMode
from src.backtest.portfolio.portfolio_simulator import ClosedTrade


@pytest.fixture
def mock_viz_dependencies():
    """Mock dependencies to reach visualization block with populated data."""
    with (
        patch("src.cli.run_backtest.construct_data_paths") as mock_paths,
        patch("src.cli.run_backtest.run_portfolio_backtest") as mock_portfolio,
        patch("src.visualization.datashader_viz.plot_backtest_results") as mock_plot,
        patch("src.cli.run_backtest.ingest_ohlcv_data"),
        patch("src.cli.run_backtest.generate_output_filename"),
        patch("pathlib.Path.mkdir"),
        patch("pathlib.Path.write_text"),
        patch("sys.exit"),
    ):  # Prevent actual exit

        # Setup fake paths
        mock_paths.return_value = [
            ("EURUSD", Path("fake/EURUSD.parquet")),
            ("USDJPY", Path("fake/USDJPY.parquet")),
        ]

        # Setup fake portfolio result
        mock_result = MagicMock()
        mock_result.start_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
        mock_result.direction_mode = DirectionMode.LONG
        mock_result.end_time = datetime(2023, 2, 1, tzinfo=timezone.utc)
        mock_result.data_start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        mock_result.data_end_date = datetime(2023, 2, 1, tzinfo=timezone.utc)
        mock_result.run_id = "test_run_123"
        mock_result.timeframe = "1m"
        mock_result.starting_equity = 2500.0
        mock_result.final_equity = 2600.0
        mock_result.total_trades = 2
        mock_result.total_pnl = 100.0

        # Add some dummy trades for different symbols
        msg_trade = MagicMock(spec=ClosedTrade)
        msg_trade.symbol = "EURUSD"
        msg_trade.entry_timestamp = datetime(2023, 1, 2)
        msg_trade.exit_timestamp = datetime(2023, 1, 3)
        msg_trade.entry_price = 1.05
        msg_trade.exit_price = 1.06
        msg_trade.direction = "LONG"
        msg_trade.exit_reason = "TAKE_PROFIT"
        msg_trade.pnl_r = 2.0
        msg_trade.signal_id = "sig1"

        msg_trade_2 = MagicMock(spec=ClosedTrade)
        msg_trade_2.symbol = "USDJPY"
        msg_trade_2.entry_timestamp = datetime(2023, 1, 5)
        msg_trade_2.exit_timestamp = datetime(2023, 1, 6)
        msg_trade_2.entry_price = 110.0
        msg_trade_2.exit_price = 111.0
        msg_trade_2.direction = "LONG"
        msg_trade_2.exit_reason = "TAKE_PROFIT"
        msg_trade_2.pnl_r = 1.5
        msg_trade_2.signal_id = "sig2"

        mock_result.closed_trades = [msg_trade, msg_trade_2]

        # Mock enriched data
        import polars as pl

        enriched_data = {
            "EURUSD": pl.DataFrame(
                {"close": [1.0, 1.1], "symbol": ["EURUSD", "EURUSD"]}
            ),
            "USDJPY": pl.DataFrame(
                {"close": [100.0, 101.0], "symbol": ["USDJPY", "USDJPY"]}
            ),
        }

        mock_portfolio.return_value = (mock_result, enriched_data)

        yield {"plot": mock_plot}


def test_visualization_structure_is_multi_symbol(mock_viz_dependencies):
    """Verify that portfolio visualization passes a structured multi-symbol result."""
    test_args = [
        "run_backtest.py",
        "--portfolio-mode",
        "--pair",
        "EURUSD",
        "USDJPY",
        "--visualize",
        "--dry-run",
    ]

    with patch.object(sys, "argv", test_args):
        try:
            main()
        except Exception as e:
            import traceback

            print(f"DEBUG EXCEPTION: {e}")
            traceback.print_exc()
            pass  # Ignore potential exit codes, we care about the call args

    # Check if plot_backtest_results was called
    mock_plot = mock_viz_dependencies["plot"]
    assert mock_plot.call_count == 1, "Visualization should be called exactly once"

    # Inspect arguments
    call_kwargs = mock_plot.call_args.kwargs
    result_obj = call_kwargs["result"]

    # THIS ASSERTION IS EXPECTED TO FAIL BEFORE THE FIX
    # Currently it's a flat result (empty results dict)
    # After fix, 'results' should contain keys 'EURUSD' and 'USDJPY'

    # Check if it has the results dictionary populated
    # (The test implementation assumes the fix will use result.results dict)
    is_multi = getattr(result_obj, "is_multi_symbol", False) or (
        hasattr(result_obj, "results") and result_obj.results
    )

    assert is_multi, "Visualization result should be marked as multi-symbol"
    assert "EURUSD" in result_obj.results, "EURUSD should be in sub-results"
    assert "USDJPY" in result_obj.results, "USDJPY should be in sub-results"

    # Verify trades are distributed correctly
    eur_execs = result_obj.results["EURUSD"].executions
    assert len(eur_execs) == 1

    jpy_execs = result_obj.results["USDJPY"].executions
    assert len(jpy_execs) == 1
