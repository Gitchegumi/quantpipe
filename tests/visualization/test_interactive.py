import pandas as pd
import polars as pl
import pytest
from unittest.mock import MagicMock, patch
from src.visualization.interactive import (
    plot_backtest_results,
    _prepare_candle_data,
    _prepare_indicator_data,
)
from src.models.directional import BacktestResult


@pytest.fixture
def mock_ohlcv_data():
    return pl.DataFrame(
        {
            "timestamp_utc": ["2023-01-01 10:00:00", "2023-01-01 10:01:00"],
            "open": [1.0, 1.1],
            "high": [1.2, 1.3],
            "low": [0.9, 1.0],
            "close": [1.1, 1.2],
            "ema_50": [1.05, 1.15],
        }
    )


@pytest.fixture
def mock_result():
    return MagicMock(spec=BacktestResult)


def test_prepare_candle_data_success(mock_ohlcv_data):
    df = _prepare_candle_data(mock_ohlcv_data)
    assert isinstance(df, pd.DataFrame)
    assert "time" in df.columns
    assert "open" in df.columns
    assert len(df) == 2


def test_prepare_candle_data_missing_cols():
    bad_data = pl.DataFrame({"timestamp_utc": []})
    with pytest.raises(ValueError):
        _prepare_candle_data(bad_data)


def test_prepare_indicator_data_success(mock_ohlcv_data):
    indicators = _prepare_indicator_data(mock_ohlcv_data)
    assert "ema_50" in indicators
    assert isinstance(indicators["ema_50"], pd.DataFrame)
    assert "value" in indicators["ema_50"].columns
    # Should exclude open/high/low/close
    assert "open" not in indicators


@patch("src.visualization.interactive.Chart")
def test_plot_backtest_results_calls(mock_chart_cls, mock_ohlcv_data, mock_result):
    mock_chart_instance = mock_chart_cls.return_value
    mock_line = mock_chart_instance.create_line.return_value

    plot_backtest_results(mock_ohlcv_data, mock_result, "EURUSD", show_plot=False)

    mock_chart_cls.assert_called()
    mock_chart_instance.set.assert_called()  # Set candles
    mock_chart_instance.create_line.assert_called_with(name="ema_50")
    mock_line.set.assert_called()  # Set indicator data

    # show_plot=False should prevent show call
    mock_chart_instance.show.assert_not_called()


@patch("src.visualization.interactive.Chart")
def test_plot_backtest_results_show(mock_chart_cls, mock_ohlcv_data, mock_result):
    mock_chart_instance = mock_chart_cls.return_value
    plot_backtest_results(mock_ohlcv_data, mock_result, "EURUSD", show_plot=True)
    mock_chart_instance.show.assert_called_with(block=True)
