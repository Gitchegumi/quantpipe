"""
Partition-aware data loading for backtesting.

This module provides functionality to load test and validation partitions
created by the dataset builder, enabling reproducible backtesting with
separate evaluation phases.

Feature: 004-timeseries-dataset
Task: T028 - Partition-aware data loader
"""

# pylint: disable=unused-import unused-variable

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

from ..io.legacy_ingestion import ingest_candles
from ..models.core import Candle


logger = logging.getLogger(__name__)

PartitionType = Literal["test", "validation"]


def check_partitions_exist(
    symbol: str, processed_path: str | Path = "price_data/processed"
) -> dict[str, bool]:
    """
    Check if processed partitions exist for a symbol.

    Args:
        symbol: Symbol identifier (e.g., 'eurusd').
        processed_path: Base path to processed data directory.

    Returns:
        Dictionary with partition existence status:
            {'test': bool, 'validation': bool, 'metadata': bool}

    Examples:
        >>> status = check_partitions_exist('eurusd')
        >>> status['test']
        True
        >>> status['validation']
        True

    Implementation: T031
    """
    processed_path = Path(processed_path)
    symbol_path = processed_path / symbol

    test_csv = symbol_path / "test.csv"
    validation_csv = symbol_path / "validation.csv"
    metadata_json = symbol_path / "metadata.json"

    return {
        "test": test_csv.exists(),
        "validation": validation_csv.exists(),
        "metadata": metadata_json.exists(),
    }


def load_partition(
    symbol: str,
    partition: PartitionType,
    processed_path: str | Path = "price_data/processed",
    ema_fast: int = 9,
    ema_slow: int = 21,
    atr_period: int = 14,
    rsi_period: int = 14,
    stoch_rsi_period: int = 14,
    expected_timeframe_minutes: int = 1,
    allow_gaps: bool = True,
) -> tuple[PartitionType, list[Candle]]:
    """
    Load a processed partition and enrich with indicators.

    Loads either test or validation partition from the processed dataset
    directory and computes technical indicators using the ingestion pipeline.

    Args:
        symbol: Symbol identifier (e.g., 'eurusd').
        partition: Partition type ('test' or 'validation').
        processed_path: Base path to processed data directory.
        ema_fast: Fast EMA period for indicator calculation.
        ema_slow: Slow EMA period for indicator calculation.
        atr_period: ATR period for volatility calculation.
        rsi_period: RSI period for momentum calculation.
        stoch_rsi_period: Stochastic RSI period.
        expected_timeframe_minutes: Expected candle interval in minutes.
        allow_gaps: Whether to allow timestamp gaps without error.

    Returns:
        Tuple of (partition_type, candles_list).

    Raises:
        FileNotFoundError: If partition file does not exist.
        ValueError: If partition type is invalid.

    Examples:
        >>> partition_type, candles = load_partition('eurusd', 'test')
        >>> partition_type
        'test'
        >>> len(candles) > 0
        True

    Implementation: T028
    """
    if partition not in ("test", "validation"):
        raise ValueError(f"Invalid partition type: {partition}")

    processed_path = Path(processed_path)
    partition_csv = processed_path / symbol / f"{partition}.csv"

    if not partition_csv.exists():
        msg = (
            f"Partition file not found: {partition_csv}\n"
            f"Run: poetry run build-dataset --symbol {symbol}"
        )
        logger.error(msg)
        raise FileNotFoundError(msg)

    logger.info(
        "Loading %s partition for symbol %s from %s", partition, symbol, partition_csv
    )

    # Use existing ingestion pipeline
    candles = list(
        ingest_candles(
            csv_path=partition_csv,
            ema_fast=ema_fast,
            ema_slow=ema_slow,
            atr_period=atr_period,
            rsi_period=rsi_period,
            stoch_rsi_period=stoch_rsi_period,
            expected_timeframe_minutes=expected_timeframe_minutes,
            allow_gaps=allow_gaps,
        )
    )

    logger.info("Loaded %d candles from %s partition", len(candles), partition)

    return (partition, candles)


def load_both_partitions(
    symbol: str,
    processed_path: str | Path = "price_data/processed",
    ema_fast: int = 9,
    ema_slow: int = 21,
    atr_period: int = 14,
    rsi_period: int = 14,
    stoch_rsi_period: int = 14,
    expected_timeframe_minutes: int = 1,
    allow_gaps: bool = True,
) -> dict[PartitionType, list[Candle]]:
    """
    Load both test and validation partitions for a symbol.

    Convenience function to load both partitions in one call, ensuring
    consistent indicator parameters across both.

    Args:
        symbol: Symbol identifier (e.g., 'eurusd').
        processed_path: Base path to processed data directory.
        ema_fast: Fast EMA period for indicator calculation.
        ema_slow: Slow EMA period for indicator calculation.
        atr_period: ATR period for volatility calculation.
        rsi_period: RSI period for momentum calculation.
        stoch_rsi_period: Stochastic RSI period.
        expected_timeframe_minutes: Expected candle interval in minutes.
        allow_gaps: Whether to allow timestamp gaps without error.

    Returns:
        Dictionary mapping partition type to candles list:
            {'test': [...], 'validation': [...]}

    Raises:
        FileNotFoundError: If either partition file does not exist.

    Examples:
        >>> partitions = load_both_partitions('eurusd')
        >>> 'test' in partitions and 'validation' in partitions
        True
        >>> len(partitions['test']) > 0
        True

    Implementation: T028
    """
    # Check existence first to provide helpful error message
    status = check_partitions_exist(symbol, processed_path)

    missing = [k for k, v in status.items() if k != "metadata" and not v]
    if missing:
        msg = (
            f"Missing partitions for symbol {symbol}: {missing}\n"
            f"Run: poetry run build-dataset --symbol {symbol}"
        )
        logger.error(msg)
        raise FileNotFoundError(msg)

    # Load both partitions with consistent parameters
    test_partition, test_candles = load_partition(
        symbol=symbol,
        partition="test",
        processed_path=processed_path,
        ema_fast=ema_fast,
        ema_slow=ema_slow,
        atr_period=atr_period,
        rsi_period=rsi_period,
        stoch_rsi_period=stoch_rsi_period,
        expected_timeframe_minutes=expected_timeframe_minutes,
        allow_gaps=allow_gaps,
    )

    validation_partition, validation_candles = load_partition(
        symbol=symbol,
        partition="validation",
        processed_path=processed_path,
        ema_fast=ema_fast,
        ema_slow=ema_slow,
        atr_period=atr_period,
        rsi_period=rsi_period,
        stoch_rsi_period=stoch_rsi_period,
        expected_timeframe_minutes=expected_timeframe_minutes,
        allow_gaps=allow_gaps,
    )

    return {
        "test": test_candles,
        "validation": validation_candles,
    }
