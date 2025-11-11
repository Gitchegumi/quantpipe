"""Legacy ingestion bridge for backward compatibility.

This module provides a compatibility layer for code still using the old
ingest_candles() API. New code should use the two-stage pipeline:
1. ingest_ohlcv_data() - core OHLCV ingestion
2. enrich() - opt-in indicator computation
3. Convert DataFrame to Candle objects

DEPRECATED: This module exists only for backward compatibility during migration.
"""

import logging
from collections.abc import Iterator
from pathlib import Path

from ..indicators.enrich import enrich
from ..io.ingestion import ingest_ohlcv_data
from ..models.core import Candle


logger = logging.getLogger(__name__)


def ingest_candles(  # pylint: disable=unused-argument
    csv_path: str | Path,
    ema_fast: int = 20,
    ema_slow: int = 50,
    atr_period: int = 14,
    rsi_period: int = 14,
    stoch_rsi_period: int = 14,
    expected_timeframe_minutes: int = 1,
    allow_gaps: bool = True,
) -> Iterator[Candle]:
    """
    DEPRECATED: Legacy ingestion function for backward compatibility.

    This function bridges the old single-stage ingestion API to the new
    two-stage pipeline (ingest + enrich). New code should use the new API.

    Args:
        csv_path: Path to CSV file.
        ema_fast: Fast EMA period (default: 20).
        ema_slow: Slow EMA period (default: 50).
        atr_period: ATR period (default: 14).
        rsi_period: RSI period (default: 14).
        stoch_rsi_period: Stochastic RSI period (default: 14).
        expected_timeframe_minutes: Expected candle interval in minutes.
        allow_gaps: Whether to allow timestamp gaps without error.

    Yields:
        Candle objects with indicators populated.

    Note:
        This function assumes the old hardcoded indicator names:
        - ema20, ema50, atr14, stoch_rsi
        If you need different periods, use the new API directly.
    """
    logger.warning(
        "ingest_candles() is deprecated. Use ingest_ohlcv_data() + enrich() instead."
    )

    # Stage 1: Core ingestion
    ingestion_result = ingest_ohlcv_data(
        path=csv_path,
        timeframe_minutes=expected_timeframe_minutes,
        mode="columnar",
        downcast=False,
        use_arrow=True,
        strict_cadence=not allow_gaps,
    )

    # Stage 2: Indicator enrichment
    # Note: Using hardcoded indicator names for backward compatibility
    # Parameters ema_fast, ema_slow, etc. are IGNORED if they don't match 20, 50, 14
    indicator_names = ["ema20", "ema50", "atr14", "stoch_rsi"]

    enrichment_result = enrich(
        core_ref=ingestion_result,
        indicators=indicator_names,
        strict=True,
    )

    # Stage 3: Convert DataFrame to Candle objects
    enriched_df = enrichment_result.enriched

    for _, row in enriched_df.iterrows():
        # Build indicators dict
        indicators_dict = {}
        for indicator_name in indicator_names:
            if indicator_name in row:
                indicators_dict[indicator_name] = row[indicator_name]

        yield Candle(
            timestamp_utc=row["timestamp_utc"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row.get("volume", 0.0),
            indicators=indicators_dict,
            is_gap=row.get("is_gap", False),
        )
