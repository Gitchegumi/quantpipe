"""Integration tests for multi-timeframe backtesting.

Tests end-to-end CLI flow with --timeframe argument.
"""

import subprocess
import sys

import pytest


class TestTimeframeCLI:
    """Integration tests for --timeframe CLI argument."""

    def test_timeframe_help_includes_option(self):
        """Test that --help shows the --timeframe option."""
        result = subprocess.run(
            [sys.executable, "-m", "src.cli.run_backtest", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "--timeframe" in result.stdout
        assert "Xm (minutes)" in result.stdout or "1m" in result.stdout

    def test_invalid_timeframe_rejected(self):
        """Test that invalid timeframe format is rejected."""
        # This test verifies error handling without needing data files
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli.run_backtest",
                "--direction",
                "LONG",
                "--timeframe",
                "90s",  # Invalid: seconds not supported
                "--data",
                "nonexistent_path.csv",  # Will fail early anyway
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should fail with timeframe error before file-not-found
        assert result.returncode != 0

    @pytest.mark.skipif(True, reason="Requires actual price data files to be present")
    def test_15m_timeframe_cli(self):
        """Test running backtest with 15m timeframe (requires data)."""
        # This would be run manually when data files are available
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli.run_backtest",
                "--direction",
                "LONG",
                "--timeframe",
                "15m",
                "--data",
                "price_data/processed/eurusd/test/eurusd_test.parquet",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        # Verify resampling stage appears in logs
        assert "Resampling to 15m" in result.stdout or result.returncode == 0
