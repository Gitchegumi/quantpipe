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
        "--dataset",
        "test",
        "--data-frac",
        "1.0",
        "--use-polars-backend",
    ]
    def run_backtest():
        subprocess.run(command, check=True, capture_output=True, text=True)

    benchmark(run_backtest)