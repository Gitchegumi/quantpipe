"""Dataset slicing and chunking utilities.

This module provides utilities for pre-computation dataset slicing based on
fraction and portion parameters, and chunked processing for memory-bounded
operations.

Requirements: FR-002 (fraction slicing), FR-003 (typed loading),
SC-003 (≤60s load+slice).
"""

# pylint: disable=line-too-long

from typing import Tuple, Optional, List, TypeVar, Union
import pandas as pd

T = TypeVar("T")


def slice_dataset_list(
    data: List[T], fraction: float = 1.0, portion: Optional[int] = None
) -> List[T]:
    """Slice list dataset to specified fraction and optional portion.

    Args:
        data: Full chronological list (e.g., candles).
        fraction: Fraction of dataset to use (0 < fraction ≤ 1.0).
        portion: Optional portion index (1-indexed) when fraction < 1.0.
                 E.g., fraction=0.25, portion=2 selects second quartile.

    Returns:
        Sliced list containing selected items.

    Raises:
        ValueError: If fraction invalid or portion out of range.

    Examples:
        >>> candles = list(range(1, 101))  # 100 items
        >>> slice_dataset_list(candles, fraction=0.25, portion=1)
        [1, 2, ..., 25]  # First quartile
        >>> slice_dataset_list(candles, fraction=0.25, portion=2)
        [26, 27, ..., 50]  # Second quartile
        >>> slice_dataset_list(candles, fraction=1.0)
        [1, 2, ..., 100]  # Full dataset
    """
    if not 0 < fraction <= 1.0:
        raise ValueError(f"Fraction must be in (0, 1.0], got {fraction}")

    total_rows = len(data)
    slice_size = int(total_rows * fraction)

    if fraction == 1.0 or portion is None:
        # Full dataset or default: take first N rows
        return data[:slice_size]

    # Portion-based slicing
    num_portions = int(1.0 / fraction)
    if not 1 <= portion <= num_portions:
        raise ValueError(
            f"Portion must be in [1, {num_portions}] for fraction={fraction}, got {portion}"
        )

    start_idx = (portion - 1) * slice_size
    end_idx = start_idx + slice_size

    # Last portion extends to end (handles uneven division)
    if portion == num_portions:
        end_idx = total_rows

    return data[start_idx:end_idx]


def slice_dataset(
    data: Union[pd.DataFrame, List[T]], fraction: float = 1.0, portion: Optional[int] = None
) -> Union[pd.DataFrame, List[T]]:
    """Slice dataset to specified fraction and optional portion.

    Supports both DataFrame and List inputs, dispatching to appropriate handler.

    Args:
        data: Full chronological dataset (DataFrame or List).
        fraction: Fraction of dataset to use (0 < fraction ≤ 1.0).
        portion: Optional portion index (1-indexed) when fraction < 1.0.
                 E.g., fraction=0.25, portion=2 selects second quartile.

    Returns:
        Sliced dataset containing selected rows/items.

    Raises:
        ValueError: If fraction invalid or portion out of range.
    """
    if isinstance(data, list):
        return slice_dataset_list(data, fraction, portion)
    return slice_dataset_dataframe(data, fraction, portion)


def slice_dataset_dataframe(
    data: pd.DataFrame, fraction: float = 1.0, portion: Optional[int] = None
) -> pd.DataFrame:
    """Slice DataFrame dataset to specified fraction and optional portion.

    Args:
        data: Full chronological DataFrame.
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


def chunk_data(data: pd.DataFrame, chunk_size: int) -> Tuple[pd.DataFrame, ...]:
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
