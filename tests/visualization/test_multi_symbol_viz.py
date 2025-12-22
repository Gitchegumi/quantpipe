"""Unit tests for multi-symbol visualization.

Tests the _create_multi_symbol_layout function and related helpers.
"""

import logging
from unittest.mock import MagicMock, patch

import pandas as pd
import polars as pl
import pytest

from src.models.directional import BacktestResult


@pytest.fixture
def mock_multi_symbol_data():
    """Create mock OHLC data with multiple symbols."""
    return pl.DataFrame(
        {
            "timestamp_utc": [
                "2024-01-01 10:00:00",
                "2024-01-01 10:01:00",
                "2024-01-01 10:00:00",
                "2024-01-01 10:01:00",
            ],
            "symbol": ["EURUSD", "EURUSD", "USDJPY", "USDJPY"],
            "open": [1.1000, 1.1010, 145.00, 145.10],
            "high": [1.1020, 1.1030, 145.20, 145.30],
            "low": [1.0990, 1.1000, 144.90, 145.00],
            "close": [1.1010, 1.1020, 145.10, 145.20],
        }
    )


@pytest.fixture
def mock_multi_symbol_result():
    """Create mock BacktestResult with is_multi_symbol=True."""
    # Create individual symbol results
    eurusd_result = MagicMock(spec=BacktestResult)
    eurusd_result.executions = []
    eurusd_result.run_id = "test-run-eurusd"

    usdjpy_result = MagicMock(spec=BacktestResult)
    usdjpy_result.executions = []
    usdjpy_result.run_id = "test-run-usdjpy"

    # Create parent result with results dict
    result = MagicMock(spec=BacktestResult)
    result.is_multi_symbol = True
    result.results = {"EURUSD": eurusd_result, "USDJPY": usdjpy_result}
    result.run_id = "test-run-multi"

    return result


@pytest.fixture
def mock_5plus_symbol_result():
    """Create mock BacktestResult with 5+ symbols for warning test."""
    result = MagicMock(spec=BacktestResult)
    result.is_multi_symbol = True
    result.results = {
        "EURUSD": MagicMock(executions=[]),
        "USDJPY": MagicMock(executions=[]),
        "GBPUSD": MagicMock(executions=[]),
        "AUDUSD": MagicMock(executions=[]),
        "NZDUSD": MagicMock(executions=[]),
    }
    result.run_id = "test-run-5plus"
    return result


class TestCreateLinkedCrosshairHook:
    """Tests for _create_linked_crosshair_hook helper function."""

    def test_hook_returns_callable(self):
        """Verify _create_linked_crosshair_hook returns a callable."""
        from src.visualization.datashader_viz import _create_linked_crosshair_hook

        # Mock CrosshairTool
        mock_crosshair = MagicMock()
        hook = _create_linked_crosshair_hook(mock_crosshair)

        assert callable(hook)

    def test_hook_adds_tool_to_plot(self):
        """Verify hook adds crosshair to plot state."""
        from src.visualization.datashader_viz import _create_linked_crosshair_hook

        mock_crosshair = MagicMock()
        mock_plot = MagicMock()
        mock_element = MagicMock()

        hook = _create_linked_crosshair_hook(mock_crosshair)
        hook(mock_plot, mock_element)

        mock_plot.state.add_tools.assert_called_once_with(mock_crosshair)


class TestSymbolCountWarning:
    """Tests for FR-015: 5+ symbol warning."""

    def test_warning_logged_for_5_symbols(
        self, mock_5plus_symbol_result, mock_multi_symbol_data, caplog
    ):
        """Verify warning is logged when visualizing 5+ symbols."""
        from src.visualization.datashader_viz import _create_multi_symbol_layout

        # Mock the sub-functions to avoid full rendering
        with (
            patch("src.visualization.datashader_viz._prepare_data") as mock_prepare,
            patch(
                "src.visualization.datashader_viz._create_candlestick_chart"
            ) as mock_candle,
            patch("src.visualization.datashader_viz._create_trade_boxes") as mock_boxes,
            patch(
                "src.visualization.datashader_viz._create_indicator_overlays"
            ) as mock_indicators,
            patch(
                "src.visualization.datashader_viz._create_portfolio_curve"
            ) as mock_portfolio,
            patch("src.visualization.datashader_viz._save_and_show"),
        ):
            # Setup mocks
            mock_prepare.return_value = None  # Will cause skip

            with caplog.at_level(logging.WARNING):
                _create_multi_symbol_layout(
                    data=mock_multi_symbol_data,
                    result=mock_5plus_symbol_result,
                    start_date=None,
                    end_date=None,
                    initial_balance=2500.0,
                    risk_per_trade=6.25,
                    show_plot=False,
                    output_file=None,
                    timeframe="1m",
                )

            # Verify warning was logged
            assert any(
                "5 symbols" in record.message or "may impact" in record.message
                for record in caplog.records
            )

    def test_no_warning_for_fewer_than_5_symbols(
        self, mock_multi_symbol_result, mock_multi_symbol_data, caplog
    ):
        """Verify no warning for <5 symbols."""
        from src.visualization.datashader_viz import _create_multi_symbol_layout

        with (
            patch("src.visualization.datashader_viz._prepare_data") as mock_prepare,
            patch("src.visualization.datashader_viz._save_and_show"),
        ):
            mock_prepare.return_value = None  # Will cause skip

            with caplog.at_level(logging.WARNING):
                _create_multi_symbol_layout(
                    data=mock_multi_symbol_data,
                    result=mock_multi_symbol_result,
                    start_date=None,
                    end_date=None,
                    initial_balance=2500.0,
                    risk_per_trade=6.25,
                    show_plot=False,
                    output_file=None,
                    timeframe="1m",
                )

            # Verify warning about symbols was NOT logged
            symbol_warnings = [
                r for r in caplog.records if "symbols" in r.message.lower()
            ]
            assert len(symbol_warnings) == 0


class TestCrosshairToolsPresent:
    """Tests for FR-012 to FR-014: Crosshair tools."""

    def test_crosshair_import_available(self):
        """Verify CrosshairTool is importable from bokeh."""
        from bokeh.models import CrosshairTool

        assert CrosshairTool is not None

    def test_crosshair_dimensions(self):
        """Verify CrosshairTool can be configured with dimensions."""
        from bokeh.models import CrosshairTool

        # Height only (for price panels)
        height_crosshair = CrosshairTool(dimensions="height")
        assert height_crosshair.dimensions == "height"

        # Both (for isolated PnL panel)
        both_crosshair = CrosshairTool(dimensions="both")
        assert both_crosshair.dimensions == "both"
