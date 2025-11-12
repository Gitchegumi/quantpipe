"""Arrow backend configuration for pandas.

This module provides utilities for using the Arrow dtype backend in pandas.
The Arrow backend is enabled per-operation (e.g., pd.read_csv(dtype_backend='pyarrow'))
rather than globally, to enable columnar acceleration for ingestion operations.
"""

import logging
from typing import Literal


logger = logging.getLogger(__name__)

# Backend type options
ArrowBackend = Literal["arrow", "pandas"]


def configure_arrow_backend() -> ArrowBackend:
    """Check if Arrow backend is available for pandas operations.

    Note: Arrow backend is enabled per-operation in pandas 2.x+
    (e.g., pd.read_csv(dtype_backend='pyarrow')), not globally.

    Returns:
        ArrowBackend: "arrow" if pyarrow is available, else "pandas".
    """
    try:
        # Check if pyarrow is importable
        import pyarrow  # noqa: F401 pylint: disable=unused-import,import-outside-toplevel

        logger.info("Arrow dtype backend available (pyarrow installed)")
        return "arrow"
    except ImportError as e:
        logger.warning("Arrow backend unavailable, falling back to pandas: %s", str(e))
        return "pandas"


def detect_backend() -> ArrowBackend:
    """Detect if Arrow backend is available.

    Returns:
        ArrowBackend: "arrow" if pyarrow is available, else "pandas".
    """
    try:
        import pyarrow  # noqa: F401 pylint: disable=unused-import,import-outside-toplevel

        return "arrow"
    except ImportError:
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
