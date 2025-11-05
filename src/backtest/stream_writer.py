"""Streaming/batched writer for memory-efficient intermediate results (T058, FR-007).

Prevents unbounded in-memory growth during backtest execution by writing
intermediate results in batches.
"""

from pathlib import Path
from typing import Any

import pandas as pd


class StreamWriter:
    """
    Batched writer for intermediate backtest results (T058, FR-007, SC-009).

    Accumulates rows in memory up to a configurable batch size, then flushes
    to disk. Prevents unbounded memory growth during large backtests.

    Attributes:
        output_path: Path to output CSV file.
        batch_size: Number of rows to accumulate before flushing.
        buffer: In-memory accumulator for pending rows.
        total_rows_written: Counter for total rows flushed to disk.

    Examples:
        >>> writer = StreamWriter("results/trades.csv", batch_size=1000)
        >>> for trade in trades:
        ...     writer.write_row(trade)
        >>> writer.flush()  # Flush remaining rows
        >>> writer.close()

    Implementation: T058, FR-007
    """

    def __init__(
        self,
        output_path: str | Path,
        batch_size: int = 10_000,
        columns: list[str] | None = None,
    ):
        """
        Initialize streaming writer.

        Args:
            output_path: Path to output CSV file.
            batch_size: Number of rows to accumulate before auto-flush (default 10k).
            columns: Column names for output DataFrame. If None, inferred from
                first row written.

        Raises:
            ValueError: If batch_size ≤ 0.
        """
        if batch_size <= 0:
            raise ValueError(f"batch_size must be > 0, got {batch_size}")

        self.output_path = Path(output_path)
        self.batch_size = batch_size
        self.columns = columns
        self.buffer: list[dict[str, Any]] = []
        self.total_rows_written = 0
        self._header_written = False

    def write_row(self, row: dict[str, Any]) -> None:
        """
        Write a single row to the stream.

        Automatically flushes when buffer reaches batch_size.

        Args:
            row: Dictionary of column->value pairs.

        Examples:
            >>> writer = StreamWriter("output.csv", batch_size=2)
            >>> writer.write_row({"timestamp": "2020-01-01", "price": 1.1})
            >>> writer.write_row({"timestamp": "2020-01-02", "price": 1.2})
            >>> # Auto-flush triggered after 2 rows
        """
        self.buffer.append(row)

        # Auto-flush when batch size reached
        if len(self.buffer) >= self.batch_size:
            self.flush()

    def write_rows(self, rows: list[dict[str, Any]]) -> None:
        """
        Write multiple rows to the stream.

        More efficient than calling write_row() repeatedly for large batches.

        Args:
            rows: List of row dictionaries.

        Examples:
            >>> writer = StreamWriter("output.csv", batch_size=1000)
            >>> rows = [{"symbol": "EURUSD", "pnl": i} for i in range(500)]
            >>> writer.write_rows(rows)
        """
        self.buffer.extend(rows)

        # Flush if buffer exceeded batch size
        while len(self.buffer) >= self.batch_size:
            # Flush in batches
            batch = self.buffer[: self.batch_size]
            self.buffer = self.buffer[self.batch_size :]
            self._flush_batch(batch)

    def flush(self) -> None:
        """
        Flush pending rows in buffer to disk.

        Called automatically when buffer reaches batch_size, or manually
        to flush remaining rows at end of stream.

        Examples:
            >>> writer = StreamWriter("output.csv", batch_size=1000)
            >>> for i in range(150):
            ...     writer.write_row({"index": i})
            >>> writer.flush()  # Flush remaining 150 rows
        """
        if not self.buffer:
            return  # Nothing to flush

        self._flush_batch(self.buffer)
        self.buffer = []

    def _flush_batch(self, batch: list[dict[str, Any]]) -> None:
        """
        Internal: Write a batch to disk.

        Args:
            batch: List of row dictionaries to write.
        """
        if not batch:
            return

        # Convert to DataFrame
        df = pd.DataFrame(batch, columns=self.columns)

        # Write to CSV
        if not self._header_written:
            # First write: create file with header
            df.to_csv(self.output_path, index=False, mode="w")
            self._header_written = True
        else:
            # Subsequent writes: append without header
            df.to_csv(self.output_path, index=False, mode="a", header=False)

        self.total_rows_written += len(df)

    def close(self) -> None:
        """
        Flush remaining rows and close writer.

        Examples:
            >>> writer = StreamWriter("output.csv", batch_size=1000)
            >>> writer.write_row({"symbol": "EURUSD", "pnl": 10.5})
            >>> writer.close()  # Flushes final row
        """
        self.flush()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - auto-flush."""
        self.close()

    def get_memory_usage(self) -> int:
        """
        Get current buffer memory usage in bytes.

        Returns:
            Approximate buffer memory in bytes.

        Examples:
            >>> writer = StreamWriter("output.csv", batch_size=1000)
            >>> writer.write_row({"symbol": "EURUSD", "pnl": 10.5})
            >>> memory_bytes = writer.get_memory_usage()
        """
        if not self.buffer:
            return 0

        # Approximate: convert buffer to DataFrame and measure
        df = pd.DataFrame(self.buffer, columns=self.columns)
        return df.memory_usage(deep=True).sum()


def write_results_streaming(
    rows: list[dict[str, Any]],
    output_path: str | Path,
    batch_size: int = 10_000,
) -> int:
    """
    Write large result sets using streaming writer (T058, FR-007).

    Convenience function for writing complete result sets with batching.

    Args:
        rows: List of result row dictionaries.
        output_path: Path to output CSV file.
        batch_size: Batch size for streaming writes (default 10k).

    Returns:
        Total number of rows written.

    Examples:
        >>> trades = [{"timestamp": f"2020-01-{i:02d}", "pnl": i} for i in range(100_000)]
        >>> total_written = write_results_streaming(trades, "results.csv", batch_size=10_000)
        >>> print(f"Wrote {total_written} rows")
        Wrote 100000 rows

    Implementation: T058, FR-007
    """
    with StreamWriter(output_path, batch_size=batch_size) as writer:
        writer.write_rows(rows)

    return writer.total_rows_written
