from pathlib import Path
from typing import Optional, Union
import polars as pl
from src.models.directional import BacktestResult


def plot_backtest(
    data: pl.DataFrame,
    result: BacktestResult,
    pair: str,
    output_file: Optional[Union[str, Path]] = None,
    show_plot: bool = True,
) -> None:
    """
    Generates an interactive candlestick chart with trade overlays and indicators.

    Args:
        data: Polars DataFrame containing OHLCV data and indicator columns.
              Must have 'timestamp_utc' column.
        result: The `BacktestResult` object containing execution details.
        pair: Symbol name (e.g., 'EURUSD').
        output_file: Optional path to save the HTML output (not supported by all backends,
                     primary mode is `show_plot=True`).
        show_plot: Whether to open the interactive window immediately.
    """
    pass
