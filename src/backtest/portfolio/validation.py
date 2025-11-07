"""Validation utilities for multi-symbol portfolio operations.

This module provides validation functions for symbol existence, dataset
overlap, and other multi-symbol preconditions.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from src.models.portfolio import CurrencyPair

logger = logging.getLogger(__name__)


def validate_symbol_exists(
    pair: CurrencyPair, data_dir: Path
) -> tuple[bool, Optional[str]]:
    """Validate that a symbol's dataset exists.

    Args:
        pair: Currency pair to validate
        data_dir: Directory containing processed datasets

    Returns:
        Tuple of (exists, error_message)
    """
    expected_path = data_dir / pair.code.lower() / "processed.csv"

    if not expected_path.exists():
        return (
            False,
            f"Dataset not found for {pair.code} at {expected_path}",
        )

    # Verify file is readable
    try:
        df = pd.read_csv(expected_path, nrows=1)
        if df.empty:
            return (
                False,
                f"Dataset for {pair.code} is empty at {expected_path}",
            )
    except (OSError, pd.errors.ParserError, ValueError) as exc:
        return (
            False,
            f"Failed to read dataset for {pair.code}: {exc}",
        )

    return True, None


def validate_dataset_overlap(
    pairs: list[CurrencyPair],
    data_dir: Path,
    min_overlap_candles: int = 100,  # pylint: disable=unused-argument
) -> tuple[bool, Optional[str]]:
    """Validate that datasets have sufficient temporal overlap.

    Args:
        pairs: List of currency pairs to validate
        data_dir: Directory containing processed datasets
        min_overlap_candles: Minimum required overlapping candles
            (reserved for future enhancement)

    Returns:
        Tuple of (valid, error_message)

    Note:
        Currently performs basic temporal overlap validation.
        Future enhancement will count exact overlapping candles.
    """
    if len(pairs) < 2:
        return True, None

    date_ranges = {}

    for pair in pairs:
        csv_path = data_dir / pair.code.lower() / "processed.csv"

        if not csv_path.exists():
            return (
                False,
                f"Dataset not found for {pair.code} at {csv_path}",
            )

        try:
            df = pd.read_csv(csv_path)
            if "timestamp" not in df.columns:
                return (
                    False,
                    f"Missing timestamp column in {pair.code} dataset",
                )

            date_ranges[pair.code] = {
                "start": df["timestamp"].min(),
                "end": df["timestamp"].max(),
                "count": len(df),
            }

        except (OSError, pd.errors.ParserError, ValueError) as exc:
            return (
                False,
                f"Failed to analyze dataset for {pair.code}: {exc}",
            )

    # Find overlap period
    all_starts = [dr["start"] for dr in date_ranges.values()]
    all_ends = [dr["end"] for dr in date_ranges.values()]

    overlap_start = max(all_starts)
    overlap_end = min(all_ends)

    if overlap_start >= overlap_end:
        return (
            False,
            f"No temporal overlap between datasets. "
            f"Latest start: {overlap_start}, earliest end: {overlap_end}",
        )

    # Estimate overlap candles (rough approximation)
    # Future enhancement: count exact overlapping timestamps
    # and validate against min_overlap_candles parameter
    logger.info(
        "Dataset overlap period: %s to %s",
        overlap_start,
        overlap_end,
    )

    # For now, we'll assume sufficient overlap if period exists
    # More sophisticated validation would count exact overlapping candles
    return True, None


def validate_symbol_list(
    pairs: list[CurrencyPair], data_dir: Path
) -> tuple[list[CurrencyPair], list[str]]:
    """Validate a list of symbols, returning valid ones and error messages.

    Args:
        pairs: List of currency pairs to validate
        data_dir: Directory containing processed datasets

    Returns:
        Tuple of (valid_pairs, error_messages)
    """
    valid_pairs = []
    errors = []

    for pair in pairs:
        exists, error = validate_symbol_exists(pair, data_dir)
        if exists:
            valid_pairs.append(pair)
        else:
            errors.append(error)
            logger.warning("Skipping invalid symbol %s: %s", pair.code, error)

    return valid_pairs, errors
