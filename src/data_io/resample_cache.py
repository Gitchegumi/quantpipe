"""Disk caching for resampled OHLCV data.

This module provides caching functionality to avoid recomputing resampled
data on repeated backtest runs with the same parameters.

Cache Location (per spec clarification):
- .time_cache/ directory in project root

Cache Key Components (FR-011):
- instrument: Trading pair (e.g., 'EURUSD')
- timeframe: Target timeframe in minutes (e.g., 15)
- date_range: Start and end dates of the data
- data_version: Hash of source data for invalidation

Cache File Format:
- Parquet files for fast I/O and good compression
- Filename: {instrument}_{tf}m_{start}_{end}_{hash8}.parquet

Telemetry (FR-014):
- Cache hits/misses logged at INFO level
- Resample time recorded for performance monitoring
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl


if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Cache directory relative to project root
CACHE_DIR = Path(".time_cache")
