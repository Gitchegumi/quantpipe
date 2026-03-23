"""Integration tests for CLI risk argument mapping and precedence.
"""

from unittest.mock import MagicMock, patch, mock_open
import pytest
import textwrap
from src.cli.main import main
from pathlib import Path


@pytest.fixture(autouse=True)
def mock_setup_logging():
    with patch("src.cli.run_backtest.setup_logging"):
        yield


@pytest.fixture
def mock_run_portfolio_backtest():
    with patch("src.cli.run_backtest.run_portfolio_backtest") as mock:
        from datetime import datetime

        mock_result = MagicMock()
        mock_result.start_time = datetime(2024, 1, 1)
        mock_result.is_multi_symbol = False
        mock_result.direction_mode = "LONG"
        mock_result.pair = "EURUSD"
        mock_result.run_id = "test_run_1"
        mock_result.end_time = datetime(2024, 1, 2)
        mock_result.total_candles = 100
        mock_result.metrics = MagicMock(
            trade_count=10,
            win_rate=0.5,
            total_pnl=1000.0,
            sharpe_ratio=1.2,
            max_drawdown=0.15,
        )
        mock_result.starting_equity = 10000.0
        mock_result.final_equity = 11000.0
        mock_result.total_pnl = 1000.0
        mock_result.closed_trades = []
        mock_result.equity_curve = []
        mock_result.per_symbol_trades = {}
        mock_result.symbols = ["EURUSD"]
        mock_result.data_start_date = datetime(2024, 1, 1)
        mock_result.data_end_date = datetime(2024, 1, 31)

        mock.return_value = (mock_result, {})
        yield mock


@pytest.fixture(autouse=True)
def mock_write_text():
    with patch("pathlib.Path.write_text") as mock:
        yield mock


@pytest.fixture
def mock_data_paths():
    """Mock data path construction to avoid needing actual data files."""
    with patch("src.cli.run_backtest.construct_data_paths") as mock:
        mock.return_value = [("EURUSD", Path("fake/EURUSD.parquet"))]
        yield mock


def test_cli_risk_args_override_defaults(mock_run_portfolio_backtest, mock_data_paths):
    """Test that CLI arguments override default values."""
    test_args = [
        "quantpipe",
        "backtest",
        "--risk-pct",
        "0.5",
        "--atr-mult",
        "3.5",
        "--rr-ratio",
        "4.0",
        "--starting-balance",
        "5000.0",
        "--max-position-size",
        "5.0",
    ]

    with (
        patch("sys.argv", test_args),
        patch("src.cli.run_backtest.format_portfolio_text_output", return_value="mocked output"),
        patch("src.cli.run_backtest.format_portfolio_json_output", return_value='{"mocked": true}'),
    ):
        main()

    call_args = mock_run_portfolio_backtest.call_args
    assert call_args is not None

    params = call_args.kwargs["strategy_params"]
    assert params.risk_per_trade_pct == 0.5
    assert params.atr_stop_mult == 3.5
    assert params.target_r_mult == 4.0
    assert params.account_balance == 5000.0
    assert params.max_position_size == 5.0
    assert call_args.kwargs["starting_equity"] == 5000.0


def test_cli_precedence_over_config(mock_run_portfolio_backtest, mock_data_paths):
    """Test that CLI arguments override config file values."""
    config_content = textwrap.dedent(
        """
    risk_per_trade_pct: 1.0
    atr_stop_mult: 1.5
    target_r_mult: 1.5
    account_balance: 1000.0
    max_position_size: 2.0
    """
    )

    test_args = [
        "quantpipe",
        "backtest",
        "--config",
        "config.yaml",
        "--risk-pct",
        "0.5",  # Override config
    ]

    with (
        patch("sys.argv", test_args),
        patch("builtins.open", mock_open(read_data=config_content)),
        patch("pathlib.Path.exists", return_value=True),
        patch("src.cli.run_backtest.format_portfolio_text_output", return_value="mocked output"),
        patch("src.cli.run_backtest.format_portfolio_json_output", return_value='{"mocked": true}'),
    ):
        main()

    params = mock_run_portfolio_backtest.call_args.kwargs["strategy_params"]
    assert params.risk_per_trade_pct == 0.5  # CLI wins
    assert params.atr_stop_mult == 1.5  # From config
    assert params.account_balance == 1000.0  # From config


def test_defaults_when_no_args(mock_run_portfolio_backtest, mock_data_paths):
    """Test that defaults are used when no CLI args or config provided."""
    test_args = ["quantpipe", "backtest"]

    with (
        patch("sys.argv", test_args),
        patch("src.cli.run_backtest.format_portfolio_text_output", return_value="mocked output"),
        patch("src.cli.run_backtest.format_portfolio_json_output", return_value='{"mocked": true}'),
    ):
        main()

    params = mock_run_portfolio_backtest.call_args.kwargs["strategy_params"]
    assert params.risk_per_trade_pct == 0.25
    assert params.atr_stop_mult == 2.0
    assert params.target_r_mult == 2.0
    assert params.account_balance == 2500.0
    assert params.max_position_size == 10.0
