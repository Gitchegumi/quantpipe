"""Synthetic test fixture generator for dataset builder tests.

Generates minimal CSV files with OHLCV price data for testing purposes.
Feature: 004-timeseries-dataset, Task: T005
"""

# pylint: disable=f-string-without-interpolation

import csv
from datetime import datetime, timedelta
from pathlib import Path


def generate_eurusd_fixture(
    output_dir: Path, num_rows: int = 600, start_date: str = "2020-01-01"
) -> Path:
    """Generate synthetic EURUSD price data for testing.

    Args:
        output_dir: Directory to write CSV file
        num_rows: Number of rows to generate (default 600, per T005 requirement)
        start_date: Starting timestamp in ISO format

    Returns:
        Path to generated CSV file

    Data Schema:
        timestamp,open,high,low,close,volume
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "eurusd_test.csv"

    base_price = 1.1000
    start_dt = datetime.fromisoformat(start_date)

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])

        for i in range(num_rows):
            timestamp = start_dt + timedelta(minutes=i)
            # Simple deterministic price movement for testing
            open_price = base_price + (i % 100) * 0.0001
            high_price = open_price + 0.0005
            low_price = open_price - 0.0003
            close_price = open_price + ((i % 10) - 5) * 0.0001
            volume = 1000 + (i % 500)

            writer.writerow(
                [
                    timestamp.isoformat(),
                    f"{open_price:.5f}",
                    f"{high_price:.5f}",
                    f"{low_price:.5f}",
                    f"{close_price:.5f}",
                    volume,
                ]
            )

    return output_file


if __name__ == "__main__":
    # Generate fixture when run directly
    fixture_path = Path(__file__).parent / "raw" / "eurusd"
    output = generate_eurusd_fixture(fixture_path, num_rows=600)
    print(f"Generated test fixture: {output}")
    print(f"Rows: 600 (meets T005 ≥600 requirement)")
