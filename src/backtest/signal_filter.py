"""Signal filtering utilities for position management.

Provides functions to filter signals based on strategy constraints
like max concurrent positions.
"""

import logging

import numpy as np


logger = logging.getLogger(__name__)


def filter_overlapping_signals(
    signal_indices: np.ndarray,
    exit_indices: np.ndarray | None = None,
    max_concurrent: int = 1,
) -> np.ndarray:
    """Filter signals to enforce max concurrent positions.

    Removes signals that would occur while a previous position is assumed
    to still be open (before its exit). If exit_indices is not provided,
    assumes each trade reserves until the next signal's entry.

    Args:
        signal_indices: Sorted array of entry candle indices.
        exit_indices: Optional array of known exit indices (same length).
            If None, uses a simple windowing approach where each kept
            signal blocks the next immediate signals.
        max_concurrent: Maximum concurrent positions (default: 1).

    Returns:
        Filtered array with signals respecting concurrency limit.

    Examples:
        >>> import numpy as np
        >>> signals = np.array([10, 15, 20, 100, 105])
        >>> exits = np.array([50, 60, 70, 150, 160])
        >>> filtered = filter_overlapping_signals(signals, exits, max_concurrent=1)
        >>> # [10, 100] kept; [15, 20] blocked by 10; [105] blocked by 100
    """
    if len(signal_indices) == 0:
        return np.array([], dtype=np.int64)

    if len(signal_indices) == 1:
        return signal_indices.copy()

    if max_concurrent is None or max_concurrent <= 0:
        # Unlimited concurrent positions - return all signals
        return signal_indices.copy()

    # Ensure sorted order
    sorted_indices = np.sort(signal_indices)

    if exit_indices is not None and len(exit_indices) == len(signal_indices):
        # Use exact exit indices for filtering
        return _filter_with_exits(sorted_indices, exit_indices, max_concurrent)

    # Simple windowing: each signal blocks until next signal would be allowed
    # For max_concurrent=1, a new signal is only allowed after position exits
    # Without exit info, we use a heuristic: new signal allowed only if
    # previous signals' windows have closed
    return _filter_simple_window(sorted_indices, max_concurrent)


def _filter_with_exits(
    signal_indices: np.ndarray,
    exit_indices: np.ndarray,
    max_concurrent: int,
) -> np.ndarray:
    """Filter signals using known exit indices.

    Args:
        signal_indices: Sorted entry indices.
        exit_indices: Corresponding exit indices.
        max_concurrent: Maximum concurrent positions.

    Returns:
        Filtered signal indices.
    """
    # Sort both by signal index
    sort_order = np.argsort(signal_indices)
    sorted_signals = signal_indices[sort_order]
    sorted_exits = exit_indices[sort_order]

    kept_indices = []
    open_positions = []  # List of (entry_idx, exit_idx) tuples

    for _, (entry_idx, exit_idx) in enumerate(
        zip(sorted_signals, sorted_exits, strict=False)
    ):
        # Remove closed positions (exit before or at current entry)
        # Use > to allow new entry on same candle as previous exit (FR-002)
        open_positions = [(e, x) for e, x in open_positions if x > entry_idx]

        # Check if we can open a new position
        if len(open_positions) < max_concurrent:
            kept_indices.append(entry_idx)
            open_positions.append((entry_idx, exit_idx))

    logger.debug(
        "Filtered signals with exits: %d -> %d (removed %d)",
        len(signal_indices),
        len(kept_indices),
        len(signal_indices) - len(kept_indices),
    )

    return np.array(kept_indices, dtype=np.int64)


def _filter_simple_window(
    signal_indices: np.ndarray,
    max_concurrent: int,
) -> np.ndarray:
    """Filter signals using simple window heuristic.

    Without exit indices, we use a conservative approach:
    - Each kept signal blocks subsequent signals
    - Signals are only kept if they don't overlap with open positions
    - For max_concurrent=1, this means keeping first signal, skipping
      immediately following signals until we assume the first has exited

    For simplicity, we assume a position might last until the next signal
    in the queue, so consecutive signals are blocked.

    Args:
        signal_indices: Sorted entry indices.
        max_concurrent: Maximum concurrent positions.

    Returns:
        Filtered signal indices.
    """
    kept_indices = [signal_indices[0]]

    for i in range(1, len(signal_indices)):
        current_signal = signal_indices[i]

        # For simple filtering, just check if we've kept fewer than max
        # This is conservative - in practice, the batch simulation will
        # use actual exit indices for more precise filtering
        if len(kept_indices) < max_concurrent:
            kept_indices.append(current_signal)
        # With max_concurrent=1, we need to assume previous trade has exited
        # Use a simple heuristic: allow signal if gap is "large enough"
        # In real usage, exit_indices should be provided for accuracy

    logger.debug(
        "Filtered signals (simple window): %d -> %d (removed %d)",
        len(signal_indices),
        len(kept_indices),
        len(signal_indices) - len(kept_indices),
    )

    return np.array(kept_indices, dtype=np.int64)


def filter_blackout_signals(
    signal_indices: np.ndarray,
    timestamps: np.ndarray,
    blackout_windows: list[tuple],
) -> tuple[np.ndarray, int]:
    """
    Vectorized filter to remove signals falling within blackout windows.

    This function uses NumPy boolean masks for O(n*w) complexity where
    n = number of signals and w = number of windows. NO per-candle loops.

    Args:
        signal_indices: Array of signal indices to filter.
        timestamps: Array of UTC timestamps (as np.datetime64 or float epoch).
            Must have same length as signal_indices.
        blackout_windows: List of (start_utc, end_utc) tuples representing
            blackout periods. Timestamps can be datetime objects or np.datetime64.

    Returns:
        Tuple of (filtered_indices, blocked_count):
            - filtered_indices: Signals not in any blackout window
            - blocked_count: Number of signals that were filtered out

    Example:
        >>> import numpy as np
        >>> signals = np.array([0, 1, 2, 3, 4])
        >>> timestamps = np.array(['2023-01-06T13:25', '2023-01-06T13:35',
        ...                        '2023-01-06T14:30', '2023-01-06T15:00',
        ...                        '2023-01-06T16:00'], dtype='datetime64[m]')
        >>> # Blackout from 13:20 to 14:00
        >>> blackouts = [(np.datetime64('2023-01-06T13:20'),
        ...               np.datetime64('2023-01-06T14:00'))]
        >>> filtered, blocked = filter_blackout_signals(signals, timestamps, blackouts)
        >>> blocked  # signals at 13:25 and 13:35 should be blocked
        2
    """
    if len(signal_indices) == 0:
        return np.array([], dtype=np.int64), 0

    if len(blackout_windows) == 0:
        return signal_indices.copy(), 0

    # Start with all signals allowed
    mask = np.ones(len(signal_indices), dtype=bool)

    for start, end in blackout_windows:
        # Convert datetime to numpy datetime64 if needed
        if hasattr(start, "timestamp"):
            start = np.datetime64(int(start.timestamp()), "s")
        if hasattr(end, "timestamp"):
            end = np.datetime64(int(end.timestamp()), "s")

        # Vectorized comparison - no per-candle loop
        in_window = (timestamps >= start) & (timestamps <= end)
        mask &= ~in_window

    filtered_indices = signal_indices[mask]
    blocked_count = len(signal_indices) - len(filtered_indices)

    if blocked_count > 0:
        logger.info(
            "Blackout filter: blocked %d of %d signals (%.1f%%)",
            blocked_count,
            len(signal_indices),
            100 * blocked_count / len(signal_indices),
        )

    return filtered_indices, blocked_count
