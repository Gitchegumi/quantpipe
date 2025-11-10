"""Arrow backend configuration for pandas.

This module configures pandas to use the Arrow dtype backend where available
to enable columnar acceleration for ingestion operations.
"""

import logging
from typing import Literal

import pandas as pd

logger = logging.getLogger(__name__)

# Backend type options
ArrowBackend = Literal["arrow", "pandas"]


def configure_arrow_backend() -> ArrowBackend:
    """Configure pandas to use Arrow backend if available.

    Returns:
        ArrowBackend: The backend that was configured ("arrow" or "pandas").
    """
    try:
        # Try to enable Arrow backend
        pd.options.mode.dtype_backend = "pyarrow"
        logger.info("Arrow dtype backend enabled successfully")
        return "arrow"
    except (AttributeError, ImportError, ValueError) as e:
        logger.warning(
            "Arrow backend unavailable, falling back to pandas: %s", str(e)
        )
        return "pandas"


def detect_backend() -> ArrowBackend:
    """Detect which backend is currently active.

    Returns:
        ArrowBackend: The currently active backend.
    """
    backend = getattr(pd.options.mode, "dtype_backend", "pandas")
    if backend == "pyarrow":
        return "arrow"
    return "pandas"


# Future enhancement: GPU acceleration hook (T076)
# def configure_gpu_backend() -> bool:
#     """Configure GPU acceleration if available (future enhancement)."""
#     pass
