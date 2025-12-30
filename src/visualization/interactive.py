"""
DEPRECATED: This module used lightweight_charts which has been removed.

The visualization functionality has been migrated to datashader_viz.py
which uses Dash, Bokeh, and Holoviews for rendering.

For backtest visualization, use:
    from src.visualization.datashader_viz import plot_backtest_results
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Deprecation warning on import
logger.warning(
    "src.visualization.interactive is DEPRECATED. "
    "Use src.visualization.datashader_viz instead."
)


def plot_backtest_results(*args, **kwargs) -> Any:
    """
    DEPRECATED: Use datashader_viz.plot_backtest_results instead.

    This stub imports and calls the new implementation for backward
    compatibility during migration.
    """
    from src.visualization.datashader_viz import plot_backtest_results as new_plot

    logger.warning(
        "interactive.plot_backtest_results is DEPRECATED. "
        "Import from datashader_viz instead."
    )
    return new_plot(*args, **kwargs)
