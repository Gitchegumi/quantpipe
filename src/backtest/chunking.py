"""Dataset slicing and chunking utilities.

This module provides utilities for pre-computation dataset slicing based on
fraction and portion parameters, and chunked processing for memory-bounded
operations.

Requirements: FR-002 (fraction slicing), FR-003 (typed loading), SC-003 (≤60s load+slice).
"""

from typing import Tuple, Optional
import pandas as pd


def slice_dataset(
    data: pd.DataFrame,
    fraction: float = 1.0,
    portion: Optional[int] = None
) -> pd.DataFrame:
    """Slice dataset to specified fraction and optional portion.
    
    Args:
        data: Full chronological dataset.
        fraction: Fraction of dataset to use (0 < fraction ≤ 1.0).
        portion: Optional portion index (1-indexed) when fraction < 1.0.
                 E.g., fraction=0.25, portion=2 selects second quartile.
                 
    Returns:
        Sliced DataFrame containing selected rows.
        
    Raises:
        ValueError: If fraction invalid or portion out of range.
    """
    if not 0 < fraction <= 1.0:
        raise ValueError(f"Fraction must be in (0, 1.0], got {fraction}")
    
    total_rows = len(data)
    slice_size = int(total_rows * fraction)
    
    if fraction == 1.0 or portion is None:
        # Full dataset or default: take first N rows
        return data.iloc[:slice_size]
    
    # Portion-based slicing
    num_portions = int(1.0 / fraction)
    if not 1 <= portion <= num_portions:
        raise ValueError(
            f"Portion must be in [1, {num_portions}] for fraction={fraction}, got {portion}"
        )
    
    start_idx = (portion - 1) * slice_size
    end_idx = start_idx + slice_size
    return data.iloc[start_idx:end_idx]


def chunk_data(
    data: pd.DataFrame,
    chunk_size: int
) -> Tuple[pd.DataFrame, ...]:
    """Split dataset into fixed-size chunks for streaming processing.
    
    Args:
        data: Dataset to chunk.
        chunk_size: Number of rows per chunk.
        
    Returns:
        Tuple of DataFrame chunks.
    """
    num_chunks = (len(data) + chunk_size - 1) // chunk_size
    chunks = []
    for i in range(num_chunks):
        start = i * chunk_size
        end = min(start + chunk_size, len(data))
        chunks.append(data.iloc[start:end])
    return tuple(chunks)
