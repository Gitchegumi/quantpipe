"""Market Replay CLI -- qp-replay.

Step-through interactive market replay with a real-time HoloViews dashboard.
Streams candles from any processed test/validation partition and visualizes
them with full OHLC charts, trade overlays, and portfolio tracking.
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import polars as pl

from src.backtest.replay import ReplaySession, ReplayConfig
from src.data_io.ingestion import ingest_ohlcv_data
from src.data_io.partition_loader import check_partitions_exist, load_partition
from src.visualization.replay_dashboard import ReplayDashboard


logger = logging.getLogger(__name__)


DEFAULT_PROCESSED_PATH = "price_data/processed"
DEFAULT_BUFFER_SIZE = 300
DEFAULT_INITIAL_BALANCE = 2_500.0
DEFAULT_RISK_PER_TRADE = 6.25


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for qp-replay."""
    parser = argparse.ArgumentParser(
        prog="qp-replay",
        description="Market Replay Dashboard -- step through historical data interactively",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="Trading pair symbol (e.g., EURUSD)",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        choices=["test", "validate", "validation"],
        default="test",
        help="Dataset partition to replay (default: test)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Optional start date filter (YYYY-MM-DD). "
             "Defaults to start of partition.",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Optional end date filter (YYYY-MM-DD). "
             "Defaults to end of partition.",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=0.5,
        dest="speed",
        metavar="SECONDS",
        help="Seconds per candle during playback (default: 0.5, range: 0.1-5.0)",
    )
    parser.add_argument(
        "--buffer-size",
        type=int,
        default=DEFAULT_BUFFER_SIZE,
        help=f"Number of candles in rolling chart window (default: {DEFAULT_BUFFER_SIZE})",
    )
    parser.add_argument(
        "--balance",
        type=float,
        default=DEFAULT_INITIAL_BALANCE,
        dest="balance",
        help=f"Initial portfolio balance in dollars (default: {DEFAULT_INITIAL_BALANCE})",
    )
    parser.add_argument(
        "--risk",
        type=float,
        default=DEFAULT_RISK_PER_TRADE,
        help=f"Dollar risk per 1R per trade (default: {DEFAULT_RISK_PER_TRADE})",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        dest="output_file",
        metavar="PATH",
        help="Path to save the dashboard as HTML on exit",
    )
    parser.add_argument(
        "--processed-path",
        type=str,
        default=DEFAULT_PROCESSED_PATH,
        dest="processed_path",
        help=f"Base path to processed partition data (default: {DEFAULT_PROCESSED_PATH})",
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default="1m",
        help="Expected candle timeframe (used in title; default: 1m)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )
    return parser


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse a YYYY-MM-DD date string into a datetime object."""
    if date_str is None:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{date_str}': expected YYYY-MM-DD"
        ) from exc


def _resolve_data(
    symbol: str,
    dataset: str,
    processed_path: Path,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    symbol_lower: str,
) -> pl.DataFrame:
    """
    Resolve the input DataFrame for the replay session.

    Tries three sources in order:
    1. Partition CSV file (test/validation) under processed_path
    2. Top-level CSV under the symbol path matching the dataset
    3. Top-level Parquet under the symbol path matching the dataset

    Args:
        symbol: Human-readable symbol (e.g., 'EURUSD').
        dataset: Partition name ('test' or 'validation').
        processed_path: Base path to processed data.
        start_date: Optional start date filter.
        end_date: Optional end date filter.
        symbol_lower: Lowercase symbol for file lookup.

    Returns:
        Polars DataFrame with timestamp_utc, open, high, low, close, volume columns.

    Raises:
        FileNotFoundError: If no suitable data file is found.
    """
    # Normalize dataset name
    if dataset in ("validate", "validation"):
        dataset = "validation"

    # Check processed/{symbol}/{dataset}.csv first
    partition_csv = processed_path / symbol_lower / f"{dataset}.csv"
    if partition_csv.exists():
        logger.info("Loading from partition CSV: %s", partition_csv)
        return _load_csv_filtered(partition_csv, start_date, end_date)

    # Fallback: look for any CSV in symbol directory that matches the partition
    symbol_dir = processed_path / symbol_lower
    if symbol_dir.exists():
        for candidate in sorted(symbol_dir.glob("*.csv")):
            name = candidate.stem.lower()
            # Accept either the exact partition name or a bare {symbol}_{timeframe} name
            if dataset in name or name == symbol_lower or name == f"{symbol_lower}_{dataset}":
                logger.info("Loading from CSV: %s", candidate)
                return _load_csv_filtered(candidate, start_date, end_date)

        # Also check Parquet
        for candidate in sorted(symbol_dir.glob("*.parquet")):
            name = candidate.stem.lower()
            if dataset in name or name == symbol_lower or name == f"{symbol_lower}_{dataset}":
                logger.info("Loading from Parquet: %s", candidate)
                df = pl.read_parquet(candidate)
                return _filter_df(df, start_date, end_date)

    raise FileNotFoundError(
        f"No data found for {symbol} in {processed_path}. "
        f"Run 'poetry run build-dataset --symbol {symbol}' first."
    )


def _load_csv_filtered(
    path: Path,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> pl.DataFrame:
    """Load a CSV into Polars and apply optional date filters."""
    df = pl.read_csv(path, has_header=True)
    return _filter_df(df, start_date, end_date)


def _filter_df(
    df: pl.DataFrame,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> pl.DataFrame:
    """Apply optional start/end date filters to a DataFrame."""
    # Ensure timestamp_utc column exists
    ts_col = "timestamp_utc"
    if ts_col not in df.columns:
        if "timestamp" in df.columns:
            df = df.with_columns(
                pl.col("timestamp")
                .str.to_datetime(format="%Y-%m-%d %H:%M:%S%z")
                .dt.replace_time_zone("UTC")
                .alias(ts_col)
            )
        else:
            raise ValueError(f"DataFrame must have 'timestamp' or '{ts_col}' column")

    # Parse filter dates to UTC
    if start_date is not None:
        start_ts = start_date.replace(tzinfo=None)  # naive for comparison
        df = df.filter(pl.col(ts_col) >= start_ts)

    if end_date is not None:
        end_ts = end_date.replace(tzinfo=None)
        df = df.filter(pl.col(ts_col) <= end_ts)

    # Sort and return
    return df.sort(ts_col)


def run(args: argparse.Namespace) -> int:
    """
    Execute the replay command.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code (0 on success, non-zero on error).
    """
    # Normalize dataset name
    dataset = "validation" if args.dataset in ("validate", "validation") else args.dataset

    processed_path = Path(args.processed_path)
    symbol_lower = args.symbol.lower()

    # Check partitions exist
    status = check_partitions_exist(symbol_lower, processed_path)
    if not any([status.get("test"), status.get("validation")]):
        logger.warning(
            "No processed partitions found for %s at %s. "
            "Run 'poetry run build-dataset --symbol %s' first.",
            args.symbol,
            processed_path,
            args.symbol,
        )

    # Resolve data
    try:
        data = _resolve_data(
            symbol=args.symbol,
            dataset=dataset,
            processed_path=processed_path,
            start_date=args.start_date,
            end_date=args.end_date,
            symbol_lower=symbol_lower,
        )
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 1

    if data.is_empty():
        logger.error("No data loaded after filtering.")
        return 1

    logger.info(
        "Loaded %d candles for %s (%s)", len(data), args.symbol, dataset
    )

    # Build replay config
    config = ReplayConfig(
        symbol=args.symbol,
        timeframe=args.timeframe,
        buffer_size=args.buffer_size,
    )

    # Create session
    session = ReplaySession(data, config)

    # Optional output file
    output_file = Path(args.output_file) if args.output_file else None

    # Create and show dashboard
    dashboard = ReplayDashboard(
        session=session,
        initial_balance=args.balance,
        risk_per_trade=args.risk,
        output_file=output_file,
    )

    logger.info(
        "Starting replay dashboard for %s (%s) -- press Ctrl+C to exit",
        args.symbol,
        args.timeframe,
    )
    dashboard.show(threaded=True)

    return 0


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        return run(args)
    except KeyboardInterrupt:
        logger.info("Replay cancelled by user.")
        return 0
    except Exception as exc:
        logger.error("Replay failed: %s", exc, exc_info=True)
        return 1
