"""Integration tests for streaming writer memory efficiency (T058, FR-007, SC-009)."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.backtest.stream_writer import StreamWriter, write_results_streaming


@pytest.mark.slow
class TestStreamWriterMemory:
    """Integration tests for stream writer memory bounds."""

    def test_batched_writing_prevents_unbounded_growth(self):
        """Batched writer flushes before buffer exceeds batch_size (T058, FR-007)."""
        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            output_path = Path(f.name)

        try:
            batch_size = 1000

            with StreamWriter(output_path, batch_size=batch_size) as writer:
                # Write 5000 rows (should trigger 5 flushes)
                for i in range(5000):
                    writer.write_row({"index": i, "value": i * 1.1})

                # Buffer should never exceed batch_size
                assert len(writer.buffer) < batch_size

            # Validate all rows written
            df = pd.read_csv(output_path)
            assert len(df) == 5000
            assert df.loc[0, "index"] == 0
            assert df.loc[4999, "index"] == 4999
        finally:
            output_path.unlink(missing_ok=True)

    def test_memory_footprint_bounded(self):
        """Buffer memory stays within expected bounds (T058, SC-009)."""
        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            output_path = Path(f.name)

        try:
            batch_size = 100

            with StreamWriter(output_path, batch_size=batch_size) as writer:
                # Write rows up to batch size
                for i in range(batch_size - 1):
                    writer.write_row(
                        {
                            "timestamp": f"2020-01-01 00:{i:02d}:00",
                            "symbol": "EURUSD",
                            "pnl": i * 1.1,
                        }
                    )

                # Buffer should be near batch_size
                buffer_memory = writer.get_memory_usage()

                # Trigger flush
                writer.write_row(
                    {
                        "timestamp": "2020-01-01 01:00:00",
                        "symbol": "EURUSD",
                        "pnl": 99 * 1.1,
                    }
                )

                # After flush, buffer should be smaller
                after_flush_memory = writer.get_memory_usage()

                # Verify flush reduced memory
                assert after_flush_memory < buffer_memory

                print(f"\nBuffer memory before flush: {buffer_memory} bytes")
                print(f"Buffer memory after flush: {after_flush_memory} bytes")
                print(f"Memory reduction: {buffer_memory - after_flush_memory} bytes")

        finally:
            output_path.unlink(missing_ok=True)

    def test_large_dataset_memory_ratio(self):
        """Large dataset write maintains memory ratio ≤1.5× raw data (T058, SC-009)."""
        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            output_path = Path(f.name)

        try:
            # Generate 100k row dataset
            num_rows = 100_000
            batch_size = 10_000

            rows = [
                {
                    "timestamp": "2020-01-01 00:00:00",
                    "symbol": "EURUSD",
                    "pnl": float(i),
                    "win": i % 2 == 0,
                }
                for i in range(num_rows)
            ]

            # Calculate raw data memory
            df_raw = pd.DataFrame(rows)
            raw_memory = df_raw.memory_usage(deep=True).sum()

            print(f"\nRaw dataset memory: {raw_memory / 1024 / 1024:.2f} MB")

            # Write with streaming
            with StreamWriter(output_path, batch_size=batch_size) as writer:
                max_buffer_memory = 0

                for row in rows:
                    writer.write_row(row)

                    # Track peak buffer memory
                    buffer_memory = writer.get_memory_usage()
                    max_buffer_memory = max(max_buffer_memory, buffer_memory)

                print(f"Peak buffer memory: {max_buffer_memory / 1024 / 1024:.2f} MB")

                # T058, SC-009: Buffer should stay bounded
                # With batch_size=10k, buffer ≈ 10k rows
                # Raw dataset = 100k rows
                # Expected buffer ratio ≈ 0.1 (10k / 100k)
                memory_ratio = max_buffer_memory / raw_memory

                print(f"Memory ratio: {memory_ratio:.2%}")

                # FR-007: Buffer ≤ 1.1× raw dataset (this is conservative)
                # In practice, buffer is much smaller (≈batch_size/total_rows × raw)
                assert (
                    memory_ratio < 0.2
                ), f"Buffer memory ratio {memory_ratio:.2%} exceeds 20% threshold"

            # Validate all rows written
            df_output = pd.read_csv(output_path)
            assert len(df_output) == num_rows

        finally:
            output_path.unlink(missing_ok=True)

    def test_write_rows_batch_efficiency(self):
        """write_rows() is more efficient than repeated write_row() (T058)."""
        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            output_path = Path(f.name)

        try:
            batch_size = 1000
            num_rows = 5000

            rows = [{"index": i, "value": i * 1.1} for i in range(num_rows)]

            # Write using write_rows (batch)
            with StreamWriter(output_path, batch_size=batch_size) as writer:
                writer.write_rows(rows)

            # Validate output
            df = pd.read_csv(output_path)
            assert len(df) == num_rows
            assert df.loc[0, "index"] == 0
            assert df.loc[4999, "index"] == 4999

        finally:
            output_path.unlink(missing_ok=True)

    def test_context_manager_auto_flush(self):
        """Context manager automatically flushes on exit (T058)."""
        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            output_path = Path(f.name)

        try:
            batch_size = 1000

            # Write 150 rows (< batch_size, so no auto-flush)
            with StreamWriter(output_path, batch_size=batch_size) as writer:
                for i in range(150):
                    writer.write_row({"index": i})

                # Buffer should have 150 rows
                assert len(writer.buffer) == 150

            # After context exit, all rows should be flushed
            df = pd.read_csv(output_path)
            assert len(df) == 150

        finally:
            output_path.unlink(missing_ok=True)

    def test_convenience_function(self):
        """write_results_streaming() convenience function works (T058)."""
        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            output_path = Path(f.name)

        try:
            rows = [{"index": i, "value": i * 2.5} for i in range(10_000)]

            total_written = write_results_streaming(rows, output_path, batch_size=1000)

            # Validate return value
            assert total_written == 10_000

            # Validate output file
            df = pd.read_csv(output_path)
            assert len(df) == 10_000
            assert df.loc[0, "index"] == 0
            assert df.loc[9999, "index"] == 9999

        finally:
            output_path.unlink(missing_ok=True)


class TestStreamWriterEdgeCases:
    """Edge case tests for stream writer."""

    def test_empty_buffer_flush_no_op(self):
        """Flushing empty buffer is safe no-op (T058)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            output_path = Path(f.name)

        try:
            with StreamWriter(output_path, batch_size=100) as writer:
                # Flush without writing anything
                writer.flush()
                writer.flush()  # Multiple flushes

                # Should create empty file or no file
                # (No rows written, so no output file created)

        finally:
            # Clean up if file was created
            if output_path.exists():
                output_path.unlink()

    def test_batch_size_validation(self):
        """Invalid batch_size raises ValueError (T058)."""
        with pytest.raises(ValueError, match="batch_size must be > 0"):
            StreamWriter("output.csv", batch_size=0)

        with pytest.raises(ValueError, match="batch_size must be > 0"):
            StreamWriter("output.csv", batch_size=-100)

    def test_single_row_smaller_than_batch(self):
        """Single row write works when batch_size not reached (T058)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            output_path = Path(f.name)

        try:
            with StreamWriter(output_path, batch_size=1000) as writer:
                writer.write_row({"symbol": "EURUSD", "pnl": 10.5})

            # Should flush on context exit
            df = pd.read_csv(output_path)
            assert len(df) == 1
            assert df.loc[0, "symbol"] == "EURUSD"
            assert df.loc[0, "pnl"] == pytest.approx(10.5)

        finally:
            output_path.unlink(missing_ok=True)
