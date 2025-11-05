"""Column-limited typed data loader for large datasets (T057, FR-003).

Loads OHLC candle data with strict column selection and dtype enforcement,
optimizing memory usage for large datasets (≥10M rows).
"""

# pylint: disable=unused-import

from pathlib import Path
from typing import Literal

import pandas as pd


# Required columns with explicit dtypes per FR-003
REQUIRED_COLUMNS = {
    "timestamp_utc": "datetime64[ns]",
    "open": "float64",
    "high": "float64",
    "low": "float64",
    "close": "float64",
}

# Optional columns (allowed but not required)
OPTIONAL_COLUMNS = {
    "volume": "float64",
    "tick_volume": "int64",
}


def load_candles_typed(
    csv_path: str | Path,
    columns: list[str] | None = None,
    validate_strict: bool = True,
) -> pd.DataFrame:
    """
    Load candle data with typed column selection (T057, FR-003, SC-003).

    Enforces explicit dtypes and rejects unexpected columns, optimizing
    memory usage for large datasets.

    Args:
        csv_path: Path to CSV file containing OHLC data.
        columns: Explicit list of columns to load. If None, loads all required
            columns. Use this to load only needed fields (e.g., ["timestamp_utc",
            "close"] for EMA-only strategies).
        validate_strict: If True, reject CSVs with unexpected columns.

    Returns:
        DataFrame with typed columns (float64 for prices, datetime64 for timestamps).

    Raises:
        FileNotFoundError: If CSV file does not exist.
        ValueError: If required columns are missing or unexpected columns present
            (when validate_strict=True).
        TypeError: If columns cannot be coerced to expected dtypes.

    Examples:
        >>> # Load all required columns
        >>> df = load_candles_typed("price_data/processed/eurusd/test.csv")
        >>> df.dtypes["close"]
        dtype('float64')

        >>> # Load only timestamp + close for memory efficiency
        >>> df = load_candles_typed(
        ...     "price_data/processed/eurusd/test.csv",
        ...     columns=["timestamp_utc", "close"]
        ... )
        >>> list(df.columns)
        ['timestamp_utc', 'close']

    Implementation: T057, FR-003, SC-003
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # Determine which columns to load
    if columns is None:
        # Load all required columns
        usecols = list(REQUIRED_COLUMNS.keys())
    else:
        # Validate requested columns
        for col in columns:
            if col not in REQUIRED_COLUMNS and col not in OPTIONAL_COLUMNS:
                raise ValueError(
                    f"Unknown column '{col}' (not in required or optional columns)"
                )
        usecols = columns

    # Read CSV with dtype enforcement
    dtype_spec = {}
    parse_dates = []

    for col in usecols:
        if col in REQUIRED_COLUMNS:
            dtype_str = REQUIRED_COLUMNS[col]
        elif col in OPTIONAL_COLUMNS:
            dtype_str = OPTIONAL_COLUMNS[col]
        else:
            raise ValueError(f"Column '{col}' not recognized")

        if dtype_str.startswith("datetime"):
            parse_dates.append(col)
        else:
            dtype_spec[col] = dtype_str

    try:
        # Load CSV with explicit dtypes and column selection
        df = pd.read_csv(
            csv_path,
            usecols=usecols,
            dtype=dtype_spec,
            parse_dates=parse_dates,
        )
    except ValueError as e:
        # Handle missing required columns
        if "timestamp" in str(e).lower() and "timestamp_utc" in usecols:
            # Try fallback: 'timestamp' instead of 'timestamp_utc'
            usecols_fallback = [
                "timestamp" if c == "timestamp_utc" else c for c in usecols
            ]
            parse_dates_fallback = [
                "timestamp" if c == "timestamp_utc" else c for c in parse_dates
            ]

            df = pd.read_csv(
                csv_path,
                usecols=usecols_fallback,
                dtype=dtype_spec,
                parse_dates=parse_dates_fallback,
            )

            # Rename to standard column name
            if "timestamp" in df.columns:
                df = df.rename(columns={"timestamp": "timestamp_utc"})
        else:
            raise TypeError(
                f"Failed to parse CSV with expected dtypes: {csv_path}"
            ) from e

    # Validate strict mode: reject unexpected columns in source CSV
    if validate_strict:
        # Read header only to check all columns
        header_df = pd.read_csv(csv_path, nrows=0)
        all_columns = set(header_df.columns)

        # Allow 'timestamp' as alias for 'timestamp_utc'
        if "timestamp" in all_columns:
            all_columns.discard("timestamp")
            all_columns.add("timestamp_utc")

        expected_columns = set(REQUIRED_COLUMNS.keys()) | set(OPTIONAL_COLUMNS.keys())
        unexpected = all_columns - expected_columns

        if unexpected:
            raise ValueError(
                f"CSV contains unexpected columns: {sorted(unexpected)}. "
                f"Expected only: {sorted(expected_columns)} (FR-003 strict validation)"
            )

    # Validate loaded DataFrame has expected dtypes
    for col in df.columns:
        if col in REQUIRED_COLUMNS:
            expected_dtype = REQUIRED_COLUMNS[col]
        elif col in OPTIONAL_COLUMNS:
            expected_dtype = OPTIONAL_COLUMNS[col]
        else:
            continue

        actual_dtype = str(df[col].dtype)

        # Allow compatible dtypes (e.g., datetime64[ns, UTC] matches datetime64[ns])
        if expected_dtype.startswith("datetime") and actual_dtype.startswith(
            "datetime"
        ):
            continue

        if expected_dtype != actual_dtype:
            raise TypeError(
                f"Column '{col}' has dtype {actual_dtype}, expected {expected_dtype}"
            )

    return df


def load_candles_memory_efficient(
    csv_path: str | Path,
    chunksize: int = 1_000_000,
) -> pd.DataFrame:
    """
    Load large candle datasets in chunks (T057, SC-003).

    For datasets ≥10M rows, loads in chunks to reduce peak memory usage.
    Uses typed loading per FR-003.

    Args:
        csv_path: Path to CSV file.
        chunksize: Number of rows to load per chunk (default 1M).

    Returns:
        Full DataFrame with all rows concatenated.

    Raises:
        FileNotFoundError: If CSV file does not exist.

    Examples:
        >>> # Load 10M row dataset in 1M row chunks
        >>> df = load_candles_memory_efficient(
        ...     "price_data/processed/eurusd/test.csv",
        ...     chunksize=1_000_000
        ... )
        >>> len(df)
        10000000

    Implementation: T057, SC-003
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # Check header to detect timestamp column name
    header_df = pd.read_csv(csv_path, nrows=0)
    has_timestamp_utc = "timestamp_utc" in header_df.columns
    has_timestamp = "timestamp" in header_df.columns

    # Determine column names to use
    if has_timestamp_utc:
        timestamp_col = "timestamp_utc"
    elif has_timestamp:
        timestamp_col = "timestamp"
    else:
        raise ValueError(
            f"CSV missing timestamp column (expected 'timestamp' or 'timestamp_utc'): {csv_path}"
        )

    # Build usecols list with actual column name
    usecols = [timestamp_col, "open", "high", "low", "close"]

    # Build dtype spec (exclude timestamp for parse_dates)
    dtype_spec = {
        "open": "float64",
        "high": "float64",
        "low": "float64",
        "close": "float64",
    }

    # Read in chunks
    chunks = []

    reader = pd.read_csv(
        csv_path,
        usecols=usecols,
        dtype=dtype_spec,
        chunksize=chunksize,
    )

    for chunk in reader:
        # Parse timestamp column manually
        chunk[timestamp_col] = pd.to_datetime(chunk[timestamp_col])

        # Rename to standard column name if needed
        if timestamp_col == "timestamp":
            chunk = chunk.rename(columns={"timestamp": "timestamp_utc"})

        chunks.append(chunk)

    # Concatenate all chunks
    df = pd.concat(chunks, ignore_index=True)

    return df
