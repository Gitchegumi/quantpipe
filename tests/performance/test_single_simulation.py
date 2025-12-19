"""
Benchmark for a single simulation run.
"""

import subprocess
import sys


def test_single_simulation_performance(benchmark):
    """
    Benchmarks the execution time of a single simulation run using the CLI.
    """
    command = [
        sys.executable,
        "-m",
        "src.cli.run_backtest",
        "--direction",
        "LONG",
        "--data",  # Changed from --dataset to --data to match CLI
        "price_data/processed/EURUSD/test/eurusd_test.parquet",  # Point to actual file
    ]

    def run_backtest():
        subprocess.run(command, check=True, capture_output=True, text=True)

    benchmark(run_backtest)
