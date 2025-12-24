"""Vectorized stop-loss and take-profit evaluation helpers.

This module provides efficient vectorized functions for evaluating stop-loss
and take-profit conditions across batches of positions, eliminating per-trade
Python loops for performance optimization.
"""

import logging

import numpy as np


logger = logging.getLogger(__name__)


def evaluate_stops_vectorized(
    positions_open: np.ndarray,
    entry_prices: np.ndarray,
    stop_prices: np.ndarray,
    high_prices: np.ndarray,
    low_prices: np.ndarray,
    directions: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate stop-loss conditions vectorially across positions.

    Args:
        positions_open: Boolean mask of open positions
        entry_prices: Entry fill prices
        stop_prices: Stop-loss prices
        high_prices: High prices for current candle
        low_prices: Low prices for current candle
        directions: Position directions (1=LONG, -1=SHORT)

    Returns:
        Tuple of (stops_hit_mask, exit_prices) where stops_hit_mask is boolean
        array indicating which positions hit stop, and exit_prices contains
        the stop price for those positions
    """
    # Only evaluate open positions
    n_positions = len(positions_open)
    stops_hit = np.zeros(n_positions, dtype=bool)
    exit_prices = np.zeros(n_positions)

    # LONG positions: stop hit if low <= stop_price
    long_mask = (directions == 1) & positions_open
    stops_hit[long_mask] = low_prices[long_mask] <= stop_prices[long_mask]

    # SHORT positions: stop hit if high >= stop_price
    short_mask = (directions == -1) & positions_open
    stops_hit[short_mask] = high_prices[short_mask] >= stop_prices[short_mask]

    # Set exit prices to stop prices for hit stops
    exit_prices[stops_hit] = stop_prices[stops_hit]

    if np.any(stops_hit):
        logger.debug(
            "Stops hit: %d positions (LONG: %d, SHORT: %d)",
            np.sum(stops_hit),
            np.sum(stops_hit & long_mask),
            np.sum(stops_hit & short_mask),
        )

    return stops_hit, exit_prices


def evaluate_targets_vectorized(
    positions_open: np.ndarray,
    entry_prices: np.ndarray,
    target_prices: np.ndarray,
    high_prices: np.ndarray,
    low_prices: np.ndarray,
    directions: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate take-profit conditions vectorially across positions.

    Args:
        positions_open: Boolean mask of open positions
        entry_prices: Entry fill prices
        target_prices: Take-profit prices
        high_prices: High prices for current candle
        low_prices: Low prices for current candle
        directions: Position directions (1=LONG, -1=SHORT)

    Returns:
        Tuple of (targets_hit_mask, exit_prices) where targets_hit_mask is
        boolean array indicating which positions hit target, and exit_prices
        contains the target price for those positions
    """
    n_positions = len(positions_open)
    targets_hit = np.zeros(n_positions, dtype=bool)
    exit_prices = np.zeros(n_positions)

    # LONG positions: target hit if high >= target_price
    long_mask = (directions == 1) & positions_open
    targets_hit[long_mask] = high_prices[long_mask] >= target_prices[long_mask]

    # SHORT positions: target hit if low <= target_price
    short_mask = (directions == -1) & positions_open
    targets_hit[short_mask] = low_prices[short_mask] <= target_prices[short_mask]

    # Set exit prices to target prices for hit targets
    exit_prices[targets_hit] = target_prices[targets_hit]

    if np.any(targets_hit):
        logger.debug(
            "Targets hit: %d positions (LONG: %d, SHORT: %d)",
            np.sum(targets_hit),
            np.sum(targets_hit & long_mask),
            np.sum(targets_hit & short_mask),
        )

    return targets_hit, exit_prices


def evaluate_exit_priority(
    stops_hit: np.ndarray,
    targets_hit: np.ndarray,
    stop_exit_prices: np.ndarray,
    target_exit_prices: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Determine exit priority when both stop and target hit in same candle.

    When both SL and TP are hit in the same candle, assume stop is hit first
    (conservative assumption for realistic simulation).

    Args:
        stops_hit: Boolean mask of positions where stop was hit
        targets_hit: Boolean mask of positions where target was hit
        stop_exit_prices: Exit prices at stop level
        target_exit_prices: Exit prices at target level

    Returns:
        Tuple of (exit_mask, exit_prices, exit_reasons) where:
        - exit_mask: Boolean array of positions that exited
        - exit_prices: Final exit prices
        - exit_reasons: Integer array (0=none, 1=stop, 2=target)
    """
    n_positions = len(stops_hit)
    exit_mask = np.zeros(n_positions, dtype=bool)
    exit_prices = np.zeros(n_positions)
    exit_reasons = np.zeros(n_positions, dtype=np.int8)

    # Priority: Stop takes precedence over target
    # (Conservative assumption: stop hit first when both triggered)

    # Mark stops
    stop_only = stops_hit & ~targets_hit
    both_hit = stops_hit & targets_hit
    stop_exit = stop_only | both_hit

    exit_mask[stop_exit] = True
    exit_prices[stop_exit] = stop_exit_prices[stop_exit]
    exit_reasons[stop_exit] = 1  # 1=stop

    # Mark targets (only if stop not hit)
    target_only = targets_hit & ~stops_hit
    exit_mask[target_only] = True
    exit_prices[target_only] = target_exit_prices[target_only]
    exit_reasons[target_only] = 2  # 2=target

    if np.any(both_hit):
        logger.debug(
            "Both SL & TP hit in same candle: %d positions (prioritizing stop)",
            np.sum(both_hit),
        )

    return exit_mask, exit_prices, exit_reasons


def calculate_pnl_vectorized(
    entry_prices: np.ndarray,
    exit_prices: np.ndarray,
    directions: np.ndarray,
    position_sizes: np.ndarray,
    stop_prices: np.ndarray,
    pip_value: float = 10.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Calculate PnL vectorially for closed positions.

    Args:
        entry_prices: Entry fill prices
        exit_prices: Exit fill prices
        directions: Position directions (1=LONG, -1=SHORT)
        position_sizes: Position sizes (lots)
        stop_prices: Stop loss prices for calculating R-multiples
        pip_value: Value per pip per lot (default: 10.0 for standard forex)

    Returns:
        Tuple of (pnl_currency, pnl_r) where:
        - pnl_currency: PnL in base currency
        - pnl_r: PnL in R multiples (risk-normalized)
    """
    # Calculate price difference (in pips)
    price_diff_pips = (exit_prices - entry_prices) * 10000  # Convert to pips

    # Apply direction
    directional_pips = price_diff_pips * directions

    # Calculate currency PnL
    pnl_currency = directional_pips * pip_value * position_sizes

    # Calculate R multiples based on actual stop distance
    # R = price_move / stop_distance
    stop_distance_pips = np.abs(entry_prices - stop_prices) * 10000
    stop_distance_pips = np.maximum(stop_distance_pips, 0.1)  # Avoid div by zero
    pnl_r = directional_pips / stop_distance_pips

    logger.debug(
        "Calculated PnL for %d positions: total=%.2f currency, avg_r=%.2f",
        len(pnl_currency),
        np.sum(pnl_currency),
        np.mean(pnl_r),
    )

    return pnl_currency, pnl_r


def find_exit_indices_vectorized(
    entry_indices: np.ndarray,
    n_candles: int,
    high_prices: np.ndarray,
    low_prices: np.ndarray,
    stop_prices: np.ndarray,
    target_prices: np.ndarray,
    directions: np.ndarray,
    max_holding_period: int = 1000,
) -> tuple[np.ndarray, np.ndarray]:
    """Find exit candle indices for positions using vectorized scan.

    Scans forward from entry to find first candle where SL or TP is hit.

    Args:
        entry_indices: Entry candle indices
        n_candles: Total number of candles in dataset
        high_prices: High price array for all candles
        low_prices: Low price array for all candles
        stop_prices: Stop-loss prices for positions
        target_prices: Take-profit prices for positions
        directions: Position directions (1=LONG, -1=SHORT)
        max_holding_period: Maximum candles to scan forward (default: 1000)

    Returns:
        Tuple of (exit_indices, exit_reasons) where:
        - exit_indices: Candle indices where exit occurred (-1 if no exit)
        - exit_reasons: Integer array (0=no_exit, 1=stop, 2=target, 3=timeout)
    """
    n_positions = len(entry_indices)
    exit_indices = np.full(n_positions, -1, dtype=np.int64)
    exit_reasons = np.zeros(n_positions, dtype=np.int8)

    # This is a placeholder implementation
    # Full implementation would scan forward from each entry index
    # For now, mark all as timeout
    for i in range(n_positions):
        entry_idx = entry_indices[i]
        end_idx = min(entry_idx + max_holding_period, n_candles - 1)

        # Placeholder: just mark as timeout at max holding period
        exit_indices[i] = end_idx
        exit_reasons[i] = 3  # 3=timeout

    logger.debug(
        "Found exit indices for %d positions (placeholder implementation)",
        n_positions,
    )

    return exit_indices, exit_reasons


def apply_slippage_vectorized(
    prices: np.ndarray,
    directions: np.ndarray,
    slippage_pips: float = 0.5,
) -> np.ndarray:
    """Apply slippage to prices vectorially.

    Args:
        prices: Original prices
        directions: Position directions (1=LONG, -1=SHORT)
        slippage_pips: Slippage in pips (default: 0.5)

    Returns:
        Adjusted prices with slippage applied
    """
    slippage_price = slippage_pips / 10000.0

    # LONG: add slippage (worse fill), SHORT: subtract slippage (worse fill)
    adjusted_prices = prices + (slippage_price * directions)

    return adjusted_prices
