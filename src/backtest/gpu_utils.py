"""
GPU utility functions for quantpipe.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Global flag to check if CuPy is available
_CUPY_AVAILABLE = False
_CP = None

try:
    import cupy as cp
    _CUPY_AVAILABLE = True
    _CP = cp
    logger.info("CuPy detected. GPU acceleration available.")
except ImportError:
    logger.info("CuPy not detected. GPU acceleration disabled.")

def is_gpu_available() -> bool:
    """Check if CuPy and a compatible GPU are available."""
    if not _CUPY_AVAILABLE:
        return False
    try:
        # Check if we can actually use the device
        _CP.cuda.Device(0).use()
        return True
    except Exception as e:
        logger.warning(f"CuPy found but GPU not accessible: {e}")
        return False

def get_cupy():
    """Get the cupy module if available."""
    return _CP

def to_gpu(array):
    """Move an array to GPU if available, otherwise return as is."""
    if is_gpu_available() and array is not None:
        if isinstance(array, (_CP.ndarray if _CP else type(None))):
            return array
        return _CP.asarray(array)
    return array

def to_cpu(array):
    """Move an array back to CPU if it's on GPU."""
    if _CUPY_AVAILABLE and isinstance(array, _CP.ndarray):
        return _CP.asnumpy(array)
    return array
