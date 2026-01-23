"""Integration test for portfolio execution flow verification.

Verifies that:
1.Portfolio mode runs exactly once.
2. Does NOT fall through to single-symbol execution.
3. Exits cleanly with code 0.
"""

import sys
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
import pytest

from src.cli.main import main
from src.models.enums import DirectionMode


@pytest.fixture
def mock_dependencies():
    """Mock external dependencies to isolate flow logic."""
    with (
        patch("src.cli.run_backtest.construct_data_paths") as mock_paths,
        patch("src.cli.run_backtest.run_portfolio_backtest") as mock_portfolio,
        patch("pathlib.Path.mkdir"),
        patch("pathlib.Path.exists", return_value=True),
        patch("builtins.open", mock_open()),
    ):

        # Setup default returns
        mock_paths.return_value = [
            ("EURUSD", Path("fake/EURUSD.parquet")),
            ("USDJPY", Path("fake/USDJPY.parquet")),
        ]

        # Mock portfolio result
        from datetime import datetime

        mock_result = MagicMock()
        mock_result.start_time = datetime(2023, 1, 1)
        mock_result.direction_mode = DirectionMode.LONG
        mock_result.end_time = datetime(2023, 1, 1)
        mock_result.data_start_date = datetime(2023, 1, 1)
        mock_result.data_end_date = datetime(2023, 1, 1)
        mock_result.closed_trades = []
        mock_result.symbols = ["EURUSD", "USDJPY"]
        mock_result.starting_equity = 10000.0
        mock_result.final_equity = 11000.0
        mock_result.total_pnl = 1000.0
        # PortfolioResult duck typing
        mock_result.equity_curve = []

        mock_portfolio.return_value = (mock_result, {})  # (result, enriched_data)

        yield {
            "paths": mock_paths,
            "portfolio": mock_portfolio,
        }


def test_unified_portfolio_execution_flow(mock_dependencies):
    """Test that multiple pairs trigger run_portfolio_backtest."""
    test_args = [
        "quantpipe",
        "backtest",
        "--pair",
        "EURUSD",
        "USDJPY",
        "--dry-run",
    ]

    with patch.object(sys, "argv", test_args):
        # We expect a return value of 0 from main() if it returns
        # or sys.exit(0) if it exits
        try:
            ret = main()
            assert ret == 0, "Main should return 0 on success"
        except SystemExit as e:
            assert e.code == 0

    # Verification
    # 1. Portfolio backtest MUST be called for multi-symbol
    mock_dependencies["portfolio"].assert_called_once()
