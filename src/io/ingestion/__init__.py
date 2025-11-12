"""Ingestion module for Parquet conversion and loading.

This module provides utilities for converting CSV market data to Parquet format
and loading data via Polars LazyFrame for optimized performance.

Also re-exports legacy pandas-based ingest_ohlcv_data for backward compatibility.
"""

# Import from the sibling ingestion.py file (not this package)
# This works because we use importlib to load the specific file directly
from importlib import util as _importlib_util
from pathlib import Path


# Get parent directory (src/io/) and import the .py file directly
_parent_dir = Path(__file__).parent.parent
_ingestion_py = _parent_dir / "ingestion.py"

# Use importlib to load the specific file
_spec = _importlib_util.spec_from_file_location("_ingestion_module", _ingestion_py)
_ingestion_module = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_ingestion_module)

# Re-export the function
ingest_ohlcv_data = _ingestion_module.ingest_ohlcv_data

__all__ = ["ingest_ohlcv_data"]
