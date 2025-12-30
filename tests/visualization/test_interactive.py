"""
Tests for the deprecated interactive visualization module.

Since interactive.py is now a deprecation stub that forwards to datashader_viz,
these tests verify the deprecation warnings and forwarding behavior.
"""

import pytest
from unittest.mock import patch, MagicMock


pytestmark = pytest.mark.unit


class TestDeprecationWarning:
    """Test that deprecation warnings are issued."""

    def test_import_logs_deprecation_warning(self, caplog):
        """Importing the module should log a deprecation warning."""
        import logging

        caplog.set_level(logging.WARNING)

        # Force reimport
        import importlib
        import src.visualization.interactive as interactive_module

        importlib.reload(interactive_module)

        assert any("DEPRECATED" in record.message for record in caplog.records)


class TestForwardingStub:
    """Test that the forwarding stub works correctly."""

    @patch("src.visualization.datashader_viz.plot_backtest_results")
    def test_plot_backtest_results_forwards_to_datashader(self, mock_new_plot):
        """plot_backtest_results should forward to datashader_viz."""
        from src.visualization.interactive import plot_backtest_results

        # Call the stub
        mock_data = MagicMock()
        mock_result = MagicMock()

        plot_backtest_results(mock_data, mock_result, "EURUSD")

        # Verify it forwarded to new implementation
        mock_new_plot.assert_called_once_with(mock_data, mock_result, "EURUSD")

    @patch("src.visualization.datashader_viz.plot_backtest_results")
    def test_plot_backtest_results_forwards_kwargs(self, mock_new_plot):
        """Keyword arguments should be forwarded correctly."""
        from src.visualization.interactive import plot_backtest_results

        mock_data = MagicMock()
        mock_result = MagicMock()

        plot_backtest_results(
            mock_data, mock_result, "EURUSD", show_plot=False, start_date="2023-01-01"
        )

        mock_new_plot.assert_called_once_with(
            mock_data, mock_result, "EURUSD", show_plot=False, start_date="2023-01-01"
        )

    @patch("src.visualization.datashader_viz.plot_backtest_results")
    def test_plot_backtest_results_returns_result(self, mock_new_plot):
        """Return value should be passed through from datashader_viz."""
        from src.visualization.interactive import plot_backtest_results

        mock_new_plot.return_value = "chart_object"

        result = plot_backtest_results(MagicMock(), MagicMock(), "EURUSD")

        assert result == "chart_object"
