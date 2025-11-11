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


# TODO(Future): GPU acceleration hook (T076, SC-013)
# When GPU libraries (cuDF, RAPIDS) are added to dependencies (requires
# Constitution Principle IX approval), implement optional GPU acceleration:
#
# def configure_gpu_backend() -> Literal["gpu", "cpu"]:
#     """Configure GPU-accelerated dataframe backend if available.
#
#     Potential 15-25% additional runtime reduction for large datasets
#     beyond current CPU-optimized performance (target: ≤75s for 6.9M rows).
#
#     Returns:
#         "gpu" if CUDA-capable device + cuDF available, else "cpu"
#
#     Note: GPU backend is OPTIONAL. Baseline performance targets (SC-001,
#     SC-002, SC-012) must remain achievable without GPU dependencies.
#     See FR-028 and SC-013 for requirements.
#     """
#     try:
#         import cudf  # noqa: F401
#         # Detect CUDA device, configure cuDF options
#         return "gpu"
#     except ImportError:
#         return "cpu"
#     pass
