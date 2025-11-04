"""Command-line interface modules.

This package provides CLI commands for running backtests and analyzing results.

Available Commands:
-------------------

run_long_backtest.py
    Run backtest with long signals only (deprecated - use run_backtest.py)

    Usage:
        poetry run python -m src.cli.run_long_backtest <data_path> <manifest_path>

    Arguments:
        data_path: Path to CSV file with price data
        manifest_path: Path to data manifest YAML file

run_backtest.py
    Run full backtest with configurable direction modes

    Usage:
        poetry run python -m src.cli.run_backtest [options]

    Options:
        --data PATH: Path to price data CSV (required)
        --manifest PATH: Path to data manifest YAML (required)
        --direction {long|short|both}: Trade direction (default: both)
        --output PATH: Output JSON file path (optional)
        --dry-run: Generate signals without execution (FR-024)
        --log-level {DEBUG|INFO|WARNING|ERROR}: Logging level (default: INFO)

    Examples:
        # Run both directions
        poetry run python -m src.cli.run_backtest \
            --data data.csv --manifest manifest.yaml

        # Long signals only
        poetry run python -m src.cli.run_backtest \
            --data data.csv --manifest manifest.yaml --direction long

        # Dry run (signals only, no execution)
        poetry run python -m src.cli.run_backtest \
            --data data.csv --manifest manifest.yaml --dry-run

build_dataset.py (PLACEHOLDER - Feature 004)
    Build time series dataset with test/validation splits

    Usage:
        poetry run python -m src.cli.build_dataset [options]

    Options:
        --symbol SYMBOL: Build dataset for specific symbol
        --all: Build datasets for all discovered symbols
        --force: Force rebuild even if processed data exists

Configuration:
--------------

Strategy parameters are loaded from `src/config/parameters.py` using Pydantic models.

Environment Variables:
    LOG_LEVEL: Override logging level (DEBUG|INFO|WARNING|ERROR)
    DATA_DIR: Base directory for data files
    OUTPUT_DIR: Base directory for backtest outputs

See README.md Configuration section for parameter details.

Quick Start:
------------

1. Install dependencies:
   poetry install

2. Prepare data:
   - CSV file with columns: timestamp, open, high, low, close, volume
   - Manifest YAML with data provenance metadata

3. Run backtest:
   poetry run python -m src.cli.run_backtest \
    --data price_data/EURUSD_15m.csv --manifest price_data/manifest.yaml

4. Review output:
   - Metrics printed to console
   - Optional JSON output with --output flag
   - Logs written to stdout with timestamps

For detailed documentation, see:
- specs/001-trend-pullback/quickstart.md
- specs/001-trend-pullback/spec.md
"""
