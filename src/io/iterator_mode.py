"""Iterator mode implementation for ingestion pipeline.

Provides wrapper class to convert DataFrame to iterator of CoreCandleRecord
objects, enabling memory-efficient streaming consumption.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

import pandas as pd


@dataclass(frozen=True)
class CoreCandleRecord:
    """Single candle record from core ingestion pipeline.

    Immutable data class representing one OHLCV candle with metadata.
    Used in iterator mode to yield individual records instead of DataFrame.

    Attributes:
        timestamp_utc: Candle timestamp in UTC timezone.
        open: Opening price.
        high: Highest price during period.
        low: Lowest price during period.
        close: Closing price.
        volume: Trading volume.
        is_gap: Whether this candle is a synthetic gap-fill.

    Examples:
        >>> record = CoreCandleRecord(
        ...     timestamp_utc=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        ...     open=1.0850,
        ...     high=1.0855,
        ...     low=1.0845,
        ...     close=1.0852,
        ...     volume=1000.0,
        ...     is_gap=False
        ... )
        >>> print(f"Close: {record.close}")
        Close: 1.0852
    """

    timestamp_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_gap: bool


class DataFrameIteratorWrapper:
    """Wraps a DataFrame to yield CoreCandleRecord objects row by row.

    Provides iterator interface over ingestion result DataFrame, converting
    each row to a CoreCandleRecord. Designed for memory-efficient streaming
    consumption when full DataFrame materialization is not needed.

    Attributes:
        df: Source DataFrame with core columns.
        total_rows: Number of rows in DataFrame.

    Examples:
        >>> df = pd.DataFrame({
        ...     'timestamp_utc': [datetime(2024, 1, 1, tzinfo=timezone.utc)],
        ...     'open': [1.0850],
        ...     'high': [1.0855],
        ...     'low': [1.0845],
        ...     'close': [1.0852],
        ...     'volume': [1000.0],
        ...     'is_gap': [False]
        ... })
        >>> wrapper = DataFrameIteratorWrapper(df)
        >>> for record in wrapper:
        ...     print(record.close)
        1.0852
    """

    def __init__(self, df: pd.DataFrame):
        """Initialize iterator wrapper with DataFrame.

        Args:
            df: DataFrame containing core candle columns
                (timestamp_utc, open, high, low, close, volume, is_gap).
        """
        self.df = df
        self.total_rows = len(df)

    def __iter__(self) -> Iterator[CoreCandleRecord]:
        """Yield CoreCandleRecord objects row by row.

        Yields:
            CoreCandleRecord: Immutable record for each DataFrame row.
        """
        for _, row in self.df.iterrows():
            yield CoreCandleRecord(
                timestamp_utc=row["timestamp_utc"],
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                is_gap=bool(row["is_gap"]),
            )

    def __len__(self) -> int:
        """Return total number of records.

        Returns:
            int: Number of rows in wrapped DataFrame.
        """
        return self.total_rows
