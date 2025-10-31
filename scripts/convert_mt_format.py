"""Convert MetaTrader format CSVs to standard format with headers.

MetaTrader format: date,time,open,high,low,close,volume (no header)
Standard format: timestamp,open,high,low,close,volume (with header)

Usage:
    python scripts/convert_mt_format.py \
           price_data/raw/eurusd \
           price_data/raw_converted/eurusd
"""

# pylint: disable=broad-exception-caught line-too-long

import sys
from pathlib import Path

import pandas as pd


def convert_mt_file(input_path: Path, output_path: Path) -> None:
    """Convert single MT format file to standard format.

    Args:
        input_path: Path to MT format CSV (no header)
        output_path: Path for output CSV (with headers)
    """
    # MT format columns (no header in file)
    column_names = ["date", "time", "open", "high", "low", "close", "volume"]

    # Read MT format
    df = pd.read_csv(input_path, names=column_names)

    # Combine date and time into timestamp
    df["timestamp"] = pd.to_datetime(df["date"] + " " + df["time"])

    # Select and reorder columns for standard format
    df_standard = df[["timestamp", "open", "high", "low", "close", "volume"]]

    # Write with header
    df_standard.to_csv(output_path, index=False)

    print(f"✓ Converted {input_path.name} ({len(df)} rows)")


def convert_directory(input_dir: Path, output_dir: Path) -> None:
    """Convert all CSV files in directory.

    Args:
        input_dir: Directory containing MT format CSVs
        output_dir: Directory for converted CSVs
    """
    if not input_dir.exists():
        print(f"Error: Input directory not found: {input_dir}")
        sys.exit(1)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all CSV files
    csv_files = sorted(input_dir.glob("*.csv"))

    if not csv_files:
        print(f"Warning: No CSV files found in {input_dir}")
        return

    print(f"Converting {len(csv_files)} files from {input_dir}")
    print(f"Output directory: {output_dir}")
    print()

    # Convert each file
    for csv_file in csv_files:
        output_path = output_dir / csv_file.name
        try:
            convert_mt_file(csv_file, output_path)
        except Exception as e:
            print(f"✗ Error converting {csv_file.name}: {e}")

    print()
    print(f"✓ Conversion complete! {len(csv_files)} files processed")
    print(f"Files saved to: {output_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/convert_mt_format.py <input_dir> <output_dir>")
        print()
        print("Example:")
        print(
            "  python scripts/convert_mt_format.py price_data/raw/eurusd price_data/raw_converted/eurusd"
        )
        sys.exit(1)

    input_directory = Path(sys.argv[1])
    output_directory = Path(sys.argv[2])

    convert_directory(input_directory, output_directory)
