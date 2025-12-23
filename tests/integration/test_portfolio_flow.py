"""Integration test for portfolio execution flow verification.

Verifies that:
1.Portfolio mode runs exactly once.
2. Does NOT fall through to single-symbol execution.
3. Exits cleanly with code 0.
"""

import sys
from unittest.mock import MagicMock, patch
from pathlib import Path
import pytest

from src.cli.run_backtest import main
from src.models.enums import DirectionMode


@pytest.fixture
def mock_dependencies():
    """Mock external dependencies to isolate flow logic."""
    with (
        patch("src.cli.run_backtest.construct_data_paths") as mock_paths,
        patch("src.cli.run_backtest.run_portfolio_backtest") as mock_portfolio,
        patch("src.cli.run_backtest.run_multi_symbol_backtest") as mock_multi,
        patch("src.cli.run_backtest.BacktestOrchestrator") as mock_orch,
        patch("src.cli.run_backtest.ingest_ohlcv_data") as mock_ingest,
        patch("src.cli.run_backtest.generate_output_filename") as mock_filename,
        patch("pathlib.Path.mkdir"),
        patch("pathlib.Path.write_text"),
    ):

        # Setup default returns
        mock_paths.return_value = [
            ("EURUSD", Path("fake/EURUSD.parquet")),
            ("USDJPY", Path("fake/USDJPY.parquet")),
        ]

        # Mock portfolio result
        mock_result = MagicMock()
        mock_result.start_time = "20230101_000000"
        mock_result.direction_mode = DirectionMode.LONG
        mock_result.end_time = "20230101_000000"
        mock_result.data_start_date = "2023-01-01"
        mock_result.data_end_date = "2023-01-01"
        mock_result.closed_trades = []

        mock_portfolio.return_value = (mock_result, {})  # (result, enriched_data)

        yield {
            "paths": mock_paths,
            "portfolio": mock_portfolio,
            "multi": mock_multi,
            "orch": mock_orch,
            "ingest": mock_ingest,
        }


def test_portfolio_mode_execution_flow(mock_dependencies):
    """Test that --portfolio-mode executes portfolio path and exits."""
    test_args = [
        "run_backtest.py",
        "--portfolio-mode",
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
    # 1. Portfolio backtest MUST be called
    mock_dependencies["portfolio"].assert_called_once()

    # 2. Multi-symbol (independent) backtest MUST NOT be called
    mock_dependencies["multi"].assert_not_called()

    # 3. Single-symbol Orchestrator MUST NOT be initialized (double check)
    mock_dependencies["orch"].assert_not_called()


def test_independent_mode_fallback(mock_dependencies):
    """Verify that WITHOUT --portfolio-mode, it uses the independent path."""
    test_args = ["run_backtest.py", "--pair", "EURUSD", "USDJPY", "--dry-run"]

    with patch.object(sys, "argv", test_args):
        try:
            main()
        except SystemExit:
            pass

    # Verification
    # 1. Portfolio backtest MUST NOT be called
    mock_dependencies["portfolio"].assert_not_called()

    # 2. Multi-symbol backtest MUST be called
    mock_dependencies["multi"].assert_called_once()
